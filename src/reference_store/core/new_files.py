"""Copying and moving files and folders from elsewhere on the machine into an entry."""

from collections.abc import Generator
import contextlib
from dataclasses import dataclass, replace
import errno
from pathlib import Path, PurePosixPath

from reference_store.core import disk, entries, names
from reference_store.core.entries import EntryRecord, FileRecord
from reference_store.models import NewFile, ReferenceStoreError


@dataclass(frozen=True)
class Placing:
    """One file to put in an entry, and what is said about it."""

    source: Path
    path: str  # inside the entry
    move: bool
    about: FileRecord
    added_folder: Path | None  # the folder it is in, when that folder was added


def planned(folder: Path, files: list[NewFile]) -> list[Placing]:
    """Returns each file to put in the entry, with the folders on its way spelled as they are there already.

    Everything is checked before anything is copied, so nothing is added when one of them can't be.

    Raises:
        ReferenceStoreError: A source can't be added, or something is at the path one of its files would take.
    """
    placings = [placing for new in files for placing in _placings_of(folder, new)]
    # A folder new to the entry is spelled as the first file that goes in it spells it.
    spellings: dict[str, str] = {}
    taken: set[str] = set()
    spelled: list[Placing] = []
    for placing in placings:
        path, there = entries.spelled(folder, placing.path)
        if there is not None:
            what = "a folder" if there.is_dir() else "a file"
            raise ReferenceStoreError(f"{folder.name} already has {what} at {there.relative_to(folder).as_posix()}.")
        *parts, last = path.split("/")
        for index, part in enumerate(parts):
            prefix = names.key("/".join(parts[: index + 1]))
            if prefix in taken:
                raise ReferenceStoreError(f"Two of the files would take {'/'.join(parts[: index + 1])}.")
            parts[index] = spellings.setdefault(prefix, part)
        path = "/".join([*parts, last])
        if names.key(path) in taken or names.key(path) in spellings:
            raise ReferenceStoreError(f"Two of the files would take {path}.")
        taken.add(names.key(path))
        _check_lengths(folder, path)
        spelled.append(replace(placing, path=path))
    return spelled


def describe(record: EntryRecord, placings: list[Placing]) -> None:
    """Says in the record what was said about each file, in place of anything said about a file at its path before."""
    for placing in placings:
        entries.say_about(record, placing.path, placing.about.model_copy(deep=True))


@contextlib.contextmanager
def placed(folder: Path, placings: list[Placing]) -> Generator[None]:
    """Puts each file in the entry, and takes them back out when one can't go in or the block raises.

    A file that is moved is renamed into place. One on another drive is copied, and `finish_moves` deletes it from
    there once the block is done.

    Raises:
        ReferenceStoreError: A file couldn't be put in, and nothing was.
    """
    done: list[tuple[Placing, bool]] = []
    made: list[Path] = []
    try:
        for placing in placings:
            target = folder / placing.path
            try:
                made.extend(disk.make_folders(folder, placing.path))
                renamed = placing.move and _renamed(placing.source, target)
                if not renamed:
                    disk.copy_file(placing.source, target)
            except OSError as error:
                raise ReferenceStoreError(
                    f"Couldn't put {placing.source} in {folder.name}: {error.strerror or error}. It may be open in "
                    "another program. Close it and try again. Nothing was added."
                ) from None
            done.append((placing, renamed))
        yield
    except BaseException:
        for placing, renamed in reversed(done):
            with contextlib.suppress(OSError):
                if renamed:
                    disk.rename(folder / placing.path, placing.source)
                else:
                    (folder / placing.path).unlink()
        disk.delete_empty(made[::-1])
        raise


def finish_moves(placings: list[Placing]) -> None:
    """Deletes what was copied from another drive to be moved, and each folder moved in once it is empty.

    Raises:
        ReferenceStoreError: A file was copied in, but couldn't be deleted from where it was.
    """
    left: list[tuple[Path, OSError]] = []
    for placing in placings:
        if placing.move and placing.source.exists():
            try:
                disk.delete_file(placing.source)
            except OSError as error:
                left.append((placing.source, error))
    emptied: dict[Path, None] = {}
    for placing in placings:
        if placing.move and placing.added_folder is not None:
            emptied[placing.added_folder] = None
    for added in emptied:
        disk.delete_empty([each for each, _, _ in added.walk(top_down=False)])
    if left:
        source, error = left[0]
        raise ReferenceStoreError(
            f"The files are in the entry, but {len(left)} couldn't be deleted from where they were, such as {source}: "
            f"{error.strerror or error}. Delete them once no program has them open."
        )


def _placings_of(folder: Path, new: NewFile) -> list[Placing]:
    source = new.source.expanduser().resolve()
    entry = folder.resolve()
    if not source.exists():
        raise ReferenceStoreError(f"There is nothing at {source}.")
    if source.is_relative_to(entry):
        raise ReferenceStoreError(f"{source} is in {folder.name} already.")
    if entry.is_relative_to(source):
        raise ReferenceStoreError(f"{source} holds {folder.name} itself, so it can't go in it.")
    about = FileRecord(description=new.description, notes=new.notes, tags=entries.clean_tags(new.tags or []))
    if source.is_file():
        return [Placing(source, entries.check_file_path(_base(new, source, False)), new.move, about, None)]
    if not source.is_dir():
        raise ReferenceStoreError(f"{source} isn't a file or a folder.")
    if new.description or new.notes:
        raise ReferenceStoreError(
            f"{source} is a folder, and a description or notes are for one file. Add its files one at a time to say "
            "something about each."
        )
    base = _base(new, source, True)
    files = sorted(
        (each for each in source.rglob("*") if each.is_file()),
        key=lambda each: entries.path_order(each.relative_to(source).as_posix()),
    )
    if not files:
        raise ReferenceStoreError(f"There are no files in {source}.")
    return [
        Placing(
            each,
            entries.check_file_path(PurePosixPath(base, each.relative_to(source).as_posix()).as_posix()),
            new.move,
            about,
            source,
        )
        for each in files
    ]


def _base(new: NewFile, source: Path, is_folder: bool) -> str:
    """Returns where the source goes in the entry: the path of a file, or of the folder a folder's files go in, which
    is empty for the top."""
    if new.path is None:
        return source.name
    given = names.slashed(new.path)
    if given == ".":
        return "" if is_folder else source.name
    if new.path.rstrip().endswith(("/", "\\")):
        return f"{given}/{source.name}"
    return given


def _check_lengths(folder: Path, path: str) -> None:
    target = folder / path
    names.check_full_path(target, path)
    if not target.parent.is_dir():
        names.check_folder_path(target.parent, PurePosixPath(path).parent.as_posix())


def _renamed(source: Path, target: Path) -> bool:
    """Moves a file by renaming it, and returns False, leaving it where it is, when `target` is on another drive."""
    try:
        disk.rename(source, target)
    except OSError as error:
        if error.errno != errno.EXDEV:
            raise
        return False
    return True
