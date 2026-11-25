"""Bringing a store's clone and its repository on GitHub in step.

A store that is pushed has everything in its folder committed, what the other devices pushed merged in, and the
result pushed. A clone that isn't pushed is only made to match GitHub.

Changes are committed as they are found and not as each call makes them, so that a file added by hand is shared like
any other, and a call never waits for `git`.
"""

import contextlib
import hashlib
import os
from pathlib import Path, PurePosixPath
import time

from filelock import FileLock, Timeout
from pydantic import ValidationError

from reference_store.core import config, disk
from reference_store.core.catalog import catalog
from reference_store.core.entries import ENTRY_FILE, EntryRecord
from reference_store.core.remotes import background, git, merge, status
from reference_store.core.remotes.git import GitError
from reference_store.core.stores import LARGEST_PUSHED_BYTES
from reference_store.models import ReferenceStoreError, Store, StoreSync

# How long a sync waits for one of the same store that another process is doing.
WAIT_SECONDS = 10 * 60
# GitHub can change between a pull and the push after it, and a store can change between a commit and a merge or while
# a push runs. Each is put right by another round. What is left after these waits for the next sync.
ROUNDS = 3
# What the library writes on the way to a file or a folder, which is gone a moment later.
PASSING = (":(exclude,glob)**/.??????.tmp", ":(exclude,glob)**/.??????.tmp/**")


def run(store: Store, asked: bool) -> StoreSync:
    """Syncs a store with GitHub, and returns how it went. What it changed in the store's folder is told to the index.

    `asked` is whether someone asked for the sync, which then always goes to GitHub. One started in the background
    goes there only with something to push, or when a sync is due. It also gives way to another that is waiting
    to start, since that one takes in the same changes.
    """
    root = status.root_of(store.path)
    result = StoreSync(store=store.name, pulled=0, pushed=0, left_out=[], error=None)
    lock = _lock(root, "sync")
    waiting = _lock(root, "sync-waiting")
    try:
        if not asked:
            waiting.acquire(timeout=0)
        try:
            lock.acquire(timeout=WAIT_SECONDS)
        finally:
            if not asked:
                waiting.release()
    except Timeout:
        if asked:
            result.error = "Another process has been syncing it for a long time. Try again later."
        return result
    changed: set[str] = set()
    try:
        reached = True
        try:
            if store.push:
                reached = _share(root, result, changed, asked or background.is_due(store, time.time()))
            else:
                _follow(root, store, result, changed)
        except GitError as error:
            result.error = str(error)
        kept = status.read(root)
        kept.left_out = result.left_out
        # A sync that had no reason to ask GitHub says nothing about being in step with it.
        if reached:
            kept.error = result.error
            kept.synced = kept.synced if result.error else time.time()
        status.write(root, kept)
    finally:
        lock.release()
    # The change is in the store's folder by now, so an index that can't take it in is put right by its next check.
    with contextlib.suppress(OSError, ReferenceStoreError), catalog.reading() as held:
        for name in sorted(changed):
            held.changed(store, name)
    return result


def waiting_changes(root: Path) -> str | None:
    """Returns what a clone has that GitHub doesn't, as far as can be told without asking GitHub, or None."""
    paths = _uncommitted(root)
    left = [path for path in paths if _stays(root, path)]
    if left:
        return f"{len(left)} of its files can't be pushed, such as {left[0]}"
    if paths or _staged(root):
        return "it has changes that aren't committed yet"
    current = git.head(root)
    if current is not None:
        theirs = f"origin/{git.branch(root)}"
        if not _exists(root, theirs) or _count(root, f"{theirs}..HEAD"):
            return "it has changes that aren't pushed yet"
    return None


def _share(root: Path, result: StoreSync, changed: set[str], reach_github: bool) -> bool:
    """Commits what is in the clone, merges what GitHub has, and pushes. Returns whether GitHub was asked, which it
    isn't when there was no reason to and nothing to push."""
    branch = git.branch(root)
    theirs = f"origin/{branch}"
    failure = None
    for _ in range(ROUNDS):
        failure = None
        result.left_out = _commit(root)
        current = git.head(root)
        if not reach_github and current is not None and _exists(root, theirs) and not _count(root, f"{theirs}..HEAD"):
            return False
        reach_github = True
        git.run(root, "fetch", "--quiet", "origin", seconds=git.NETWORK_SECONDS)
        behind = _behind(root, theirs, current)
        if behind:
            failure = _merge(root, theirs)
            if failure is not None:
                continue
            changed.update(_entries_between(root, "", current, "HEAD"))
            result.pulled += behind
            current = git.head(root)
        ahead = _count(root, f"{theirs}..HEAD" if _exists(root, theirs) else "HEAD") if current else 0
        if ahead:
            pushed = git.call(
                root, "push", "--quiet", "origin", f"HEAD:refs/heads/{branch}", seconds=git.NETWORK_SECONDS
            )
            if not pushed.worked:
                failure = pushed.said
                # A push is turned down when another device pushed since the fetch, which the next round merges in.
                # Turned down with nothing new to fetch, it would only be turned down again.
                git.run(root, "fetch", "--quiet", "origin", seconds=git.NETWORK_SECONDS)
                if not _behind(root, theirs, current):
                    break
                continue
            result.pushed += ahead
        # What changed while this round ran goes in the next, since the sync that change started may have given way
        # to this one.
        if len(_uncommitted(root)) == len(result.left_out):
            break
    if failure is not None:
        raise GitError(failure)
    return True


def _follow(root: Path, store: Store, result: StoreSync, changed: set[str]) -> None:
    """Makes a clone that isn't pushed the same as GitHub has it."""
    theirs = f"origin/{git.branch(root)}"
    git.run(root, "fetch", "--quiet", "origin", seconds=git.NETWORK_SECONDS)
    current = git.head(root)
    if not _exists(root, theirs) or current == git.run(root, "rev-parse", theirs).strip():
        return
    behind = _behind(root, theirs, current)
    # Nothing is committed in this clone, so there is nothing of its own to keep.
    git.run(root, "reset", "--hard", "--quiet", theirs, seconds=git.NETWORK_SECONDS)
    inside = store.path.relative_to(root).as_posix()
    changed.update(_entries_between(root, "" if inside == "." else f"{inside}/", current, "HEAD"))
    result.pulled = behind


def _commit(root: Path) -> list[str]:
    """Commits everything in the clone that can be pushed, and returns what can't be."""
    paths = _uncommitted(root)
    left_out = [path for path in paths if _stays(root, path)]
    if len(paths) > len(left_out):
        kept = [".", *PASSING, *(f":(exclude,literal){path.rstrip('/')}" for path in left_out)]
        # Everything goes in, whatever a `.gitignore` says, such as the one in a saved copy of a project. The store
        # is a folder of files to the library, and has the same files on every device.
        git.run(root, "add", "--all", "--force", "--pathspec-from-file=-", "--pathspec-file-nul", given="\0".join(kept))
    staged = _staged(root)
    if staged:
        git.commit(root, "--message", _message(staged))
    return left_out


def _uncommitted(root: Path) -> list[str]:
    """Returns the path of everything in the clone's folder that was added, changed, or deleted since it was last
    staged, files that `git` is told to ignore included."""
    listed = git.run(root, "ls-files", "--others", "--modified", "--deleted", "-z").split("\0")
    passing = (path for path in listed if any(disk.is_temporary(part) for part in path.split("/")))
    return sorted(set(listed).difference(passing, [""]))


def _staged(root: Path) -> list[str]:
    """Returns the path of everything staged in the clone and not committed."""
    return [each for each in git.run(root, "diff", "--cached", "--name-only", "-z").split("\0") if each]


def _stays(root: Path, path: str) -> bool:
    """Returns whether something in the clone can't be pushed."""
    # A folder that is a repository of its own is listed as a folder, where every other folder is listed file by file.
    if path.endswith("/"):
        return True
    try:
        return (root / path).stat().st_size > LARGEST_PUSHED_BYTES
    except OSError:
        return False


def _message(staged: list[str]) -> str:
    tops = sorted({path.split("/")[0] for path in staged if "/" in path})
    if not tops:
        return "Update the store"
    if len(tops) <= 2:
        return f"Update {' and '.join(tops)}"
    return f"Update {len(tops)} entries"


def _merge(root: Path, theirs: str) -> str | None:
    """Merges what GitHub has into the clone, settling what both changed, and returns None, or why it couldn't start.

    It can't start when a file it would replace changed in the folder a moment ago, which the next commit takes in.

    Raises:
        GitError: What both changed couldn't be settled. The clone is left as it was.
    """
    tried = git.call(
        root, "merge", "--no-edit", "--quiet", theirs, seconds=git.NETWORK_SECONDS, env=git.committer(root)
    )
    if tried.worked:
        return None
    unsettled = _unsettled(root)
    if not unsettled:
        git.call(root, "merge", "--abort")
        return tried.said
    try:
        for path, stages in unsettled.items():
            _settle(root, theirs, path, stages)
        git.commit(root, "--no-edit")
    except (GitError, OSError) as error:
        git.call(root, "merge", "--abort")
        raise GitError(f"What this device and another both changed couldn't be merged: {error}") from None
    return None


def _unsettled(root: Path) -> dict[str, dict[int, str]]:
    """Returns each path a merge left for someone to settle, with the version each side and their base has of it."""
    unsettled: dict[str, dict[int, str]] = {}
    for line in git.run(root, "ls-files", "--unmerged", "-z").split("\0"):
        if line:
            about, path = line.split("\t", 1)
            _, version, stage = about.split()
            unsettled.setdefault(path, {})[int(stage)] = version
    return unsettled


def _settle(root: Path, theirs: str, path: str, stages: dict[int, str]) -> None:
    """Settles one path both sides changed: an `.entry.json` field by field, and anything else by taking the version
    committed later. A file one side deleted and the other changed is kept, as the merge leaves it in the folder."""
    ours, other = stages.get(2), stages.get(3)
    if ours is None and other is None:
        git.run(root, "rm", "--quiet", "--cached", "--", path)
        return
    if ours is not None and other is not None:
        text = _merged_entry(root, stages.get(1), ours, other) if _is_entry_file(path) else None
        if text is not None:
            disk.write_text(root / path, text)
        else:
            side = "--theirs" if _committed(root, theirs, path) >= _committed(root, "HEAD", path) else "--ours"
            git.run(root, "checkout", side, "--", path, seconds=git.NETWORK_SECONDS)
    git.run(root, "add", "--", path)


def _is_entry_file(path: str) -> bool:
    return PurePosixPath(path).name == ENTRY_FILE and path.count("/") == 1


def _merged_entry(root: Path, base: str | None, ours: str, other: str) -> str | None:
    """Returns the `.entry.json` with both sides' changes, or None when one of them can't be read as an entry."""
    try:
        mine = EntryRecord.model_validate_json(git.run(root, "cat-file", "blob", ours))
        theirs = EntryRecord.model_validate_json(git.run(root, "cat-file", "blob", other))
    except ValidationError:
        return None
    was = None
    if base is not None:
        with contextlib.suppress(ValidationError):
            was = EntryRecord.model_validate_json(git.run(root, "cat-file", "blob", base))
    return merge.merged(was, mine, theirs).model_dump_json(indent=2) + "\n"


def _committed(root: Path, commit: str, path: str) -> int:
    """Returns when a path was last committed on the way to a commit."""
    moment = git.run(root, "log", "-1", "--format=%ct", commit, "--", path).strip()
    return int(moment) if moment else 0


def _entries_between(root: Path, inside: str, before: str | None, after: str) -> set[str]:
    """Returns the names of the entries that differ between two commits, in the store at `inside` of the clone."""
    if before is None:
        listed = git.run(root, "ls-tree", "-r", "--name-only", "-z", after)
    else:
        listed = git.run(root, "diff", "--name-only", "--no-renames", "-z", before, after)
    names: set[str] = set()
    for path in listed.split("\0"):
        if path.startswith(inside) and "/" in path[len(inside) :]:
            names.add(path[len(inside) :].split("/")[0])
    return names


def _behind(root: Path, theirs: str, current: str | None) -> int:
    """Returns how many commits GitHub has that the clone doesn't, as of the last fetch."""
    if not _exists(root, theirs):
        return 0
    return _count(root, f"HEAD..{theirs}" if current else theirs)


def _exists(root: Path, commit: str) -> bool:
    return git.call(root, "rev-parse", "--verify", "--quiet", commit).worked


def _count(root: Path, commits: str) -> int:
    return int(git.run(root, "rev-list", "--count", commits).strip())


def _lock(root: Path, kind: str) -> FileLock:
    return config.lock_named(f"{kind}-{hashlib.sha256(os.path.normcase(root).encode()).hexdigest()[:32]}")
