"""Getting a repository ready to be a store: cloning one from GitHub, and checking a clone someone else made."""

import contextlib
from pathlib import Path
import time

from reference_store.core import disk, stores
from reference_store.core.remotes import git, status
from reference_store.core.remotes.git import GitError
from reference_store.core.remotes.status import Status
from reference_store.models import ReferenceStoreError


def clone(url: str, folder: Path, push: bool) -> None:
    """Clones a repository on GitHub into a folder, as a store that is pushed or one that is only read.

    A repository with no store in it is made one when it is pushed. One that is only read has to hold a store: at its
    top, or in a project's `.reference-store` folder, which is then all that is downloaded.

    Raises:
        ReferenceStoreError: It can't be cloned, it can't be a store of that kind, or it can't be pushed to. Nothing is
            left in the folder.
    """
    if folder.exists():
        raise ReferenceStoreError(f"{folder} is in the way of the clone. Delete it, or pick another name.")
    folder.parent.mkdir(parents=True, exist_ok=True)
    try:
        # No file is downloaded before it is checked out, and nothing is checked out until it is known how much of
        # the repository is the store, so a large one costs little.
        git.run(
            None,
            "clone",
            "--quiet",
            "--filter=blob:none",
            "--no-checkout",
            url,
            str(folder),
            seconds=git.NETWORK_SECONDS,
        )
        top = _top_names(folder)
        is_store = stores.STORE_FILE in top
        is_project = stores.PROJECT_FOLDER in top and not is_store
        if push:
            _ready_to_push(url, folder, is_store, is_project)
        elif is_project:
            git.run(folder, "sparse-checkout", "set", "--no-cone", f"/{stores.PROJECT_FOLDER}/")
            _check_out(folder)
        elif is_store:
            _check_out(folder)
        else:
            raise ReferenceStoreError(f"{url} holds no store. Add it with push to make it one.")
        status.write(folder, Status(synced=time.time()))
    except BaseException as error:
        with contextlib.suppress(OSError, ReferenceStoreError):
            if folder.exists():
                disk.delete_folder(folder)
        if isinstance(error, GitError):
            raise ReferenceStoreError(
                f"Couldn't clone {url}: {error} A private repository needs git signed in to GitHub on this machine."
            ) from None
        raise


def check_folder(path: Path) -> None:
    """Checks that a folder is a clone the library can push, and makes it a store when it isn't one.

    Raises:
        ReferenceStoreError: It isn't a clone of a repository that is only a store, or it can't be pushed to.
    """
    try:
        top = git.call(path, "rev-parse", "--show-toplevel") if path.is_dir() else None
        if top is None or not top.worked:
            raise ReferenceStoreError(
                f"{path} isn't a clone of a repository, so there is nowhere to push it. Clone the repository there "
                "first, or add the store by its GitHub URL."
            )
        root = Path(top.out.strip())
        if not stores.same_path(root, path) or not (path / ".git").is_dir():
            raise ReferenceStoreError(
                f"{path} is part of the repository in {root}, and only a repository that is nothing but a store is "
                "pushed. Add it without push."
            )
        if not git.call(path, "remote", "get-url", "origin").worked:
            raise ReferenceStoreError(f"The repository in {path} has no remote named origin to push to.")
        if git.head(path) is None:
            # A dry run of a push needs a commit to offer.
            stores.make_store(path)
            _commit_store_file(path)
        _check_push(path)
        stores.make_store(path)
    except GitError as error:
        raise ReferenceStoreError(f"{path} can't be added with push: {error}") from None


def delete(root: Path) -> None:
    """Deletes a clone the library made.

    Raises:
        ReferenceStoreError: Some of it couldn't be deleted.
    """
    try:
        disk.delete_folder(root)
    except OSError as error:
        raise ReferenceStoreError(
            f"Couldn't delete the clone in {root}: {error.strerror or error}. A file in it may be open in another "
            "program. Delete it once nothing has it open."
        ) from None


def _ready_to_push(url: str, folder: Path, is_store: bool, is_project: bool) -> None:
    if is_project:
        raise ReferenceStoreError(
            f"{url} is a project's repository, with its store in {stores.PROJECT_FOLDER}, and only a repository that "
            "is nothing but a store is pushed. Add it without push to read it."
        )
    _check_out(folder)
    try:
        if is_store:
            _check_push(folder)
            return
        stores.make_store(folder)
        _commit_store_file(folder)
        git.run(
            folder, "push", "--quiet", "origin", f"HEAD:refs/heads/{git.branch(folder)}", seconds=git.NETWORK_SECONDS
        )
    except GitError as error:
        raise ReferenceStoreError(
            f"{url} can't be pushed to, so it can't be added with push: {error} Add it without push to read it."
        ) from None


def _check_out(root: Path) -> None:
    """Puts the files of a clone's last commit in its folder, which has none before its first one."""
    if git.head(root) is not None:
        git.run(root, "reset", "--hard", "--quiet", seconds=git.NETWORK_SECONDS)


def _check_push(root: Path) -> None:
    """Raises when pushing a clone isn't allowed. Nothing is pushed to tell.

    Raises:
        GitError: The push would be turned down.
    """
    git.run(
        root,
        "push",
        "--dry-run",
        "--quiet",
        "origin",
        f"HEAD:refs/heads/{git.branch(root)}",
        seconds=git.NETWORK_SECONDS,
    )


def _commit_store_file(root: Path) -> None:
    git.run(root, "add", "--", stores.STORE_FILE)
    git.commit(root, "--message", "Make this a store")


def _top_names(root: Path) -> set[str]:
    """Returns the names of what is at the top of a clone's repository, which is nothing before its first commit."""
    if git.head(root) is None:
        return set()
    return {name for name in git.run(root, "ls-tree", "--name-only", "-z", "HEAD").split("\0") if name}
