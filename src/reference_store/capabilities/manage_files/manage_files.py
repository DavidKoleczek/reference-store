"""Adding files to an entry, and changing, renaming, and deleting them."""

from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from reference_store.core import disk, entries, names, new_files
from reference_store.core.catalog import catalog
from reference_store.core.entries import EntryRecord
from reference_store.models import Entry, NewFile, NotGiven, ReferenceStoreError


def add_files(name: str, files: list[NewFile], store: str | None) -> Entry:
    """Copies or moves files and folders into an entry, all of them or none."""
    target, folder = entries.find(name, store)
    with entries.locked(folder):
        record = entries.read(folder)
        placings = new_files.planned(folder, files)
        if placings:
            new_files.describe(record, placings)
            record.updated = entries.in_utc(datetime.now(UTC))
            with new_files.placed(folder, placings):
                entries.write(folder, record)
            new_files.finish_moves(placings)
    catalog.changed(target, folder.name)
    return entries.entry_of(target, folder, record)


def update_file(
    name: str,
    path: str,
    description: str | NotGiven,
    notes: str | NotGiven,
    add_tags: list[str] | None,
    remove_tags: list[str] | None,
    store: str | None,
) -> Entry:
    """Changes what is said about a file, or the tags of every file in a folder."""
    adding, removing = entries.tag_changes(add_tags, remove_tags)
    target, folder = entries.find(name, store)
    with entries.locked(folder):
        record = entries.read(folder)
        found = _found(folder, path)
        if found.is_dir() and not (isinstance(description, NotGiven) and isinstance(notes, NotGiven)):
            raise ReferenceStoreError(
                f"{_inside(folder, found)} is a folder, and a description or notes are for one file. A folder only "
                "takes tags."
            )
        before = record.model_copy(deep=True)
        for each in _files_at(folder, record, found):
            about = entries.said_about(record, each)
            if not isinstance(description, NotGiven):
                about.description = description
            if not isinstance(notes, NotGiven):
                about.notes = notes
            about.tags = entries.retagged(about.tags, adding, removing)
            entries.say_about(record, each, about)
        if record != before:
            record.updated = entries.in_utc(datetime.now(UTC))
            entries.write(folder, record)
    catalog.changed(target, folder.name)
    return entries.entry_of(target, folder, record)


def rename_file(name: str, path: str, new_path: str, store: str | None) -> Entry:
    """Renames a file or a folder in an entry, or moves it to another folder there, with what was said about it."""
    target, folder = entries.find(name, store)
    with entries.locked(folder):
        record = entries.read(folder)
        found = _found(folder, path)
        old = _inside(folder, found)
        new, there = entries.spelled(folder, _new_path(new_path, found.name))
        if _within(new, old):
            raise ReferenceStoreError(f"{old} can't go inside itself.")
        if new == old:
            return entries.entry_of(target, folder, record)
        if there is not None and there != found:
            what = "a folder" if there.is_dir() else "a file"
            raise ReferenceStoreError(f"{folder.name} already has {what} at {_inside(folder, there)}.")
        _check_lengths(folder, found, new)
        made: list[Path] = []
        try:
            made = disk.make_folders(folder, new)
            disk.rename(found, folder / new)
        except OSError as error:
            disk.delete_empty(made[::-1])
            raise ReferenceStoreError(
                f"Couldn't rename {old} in {folder.name}: {error.strerror or error}. A file in it may be open in "
                "another program. Close it and try again."
            ) from None
        # What was said about a file at the new path before, since gone, would otherwise go to the one moved there.
        moved = {
            _renamed(each, old, new): about
            for each, about in record.files.items()
            if _within(each, old) is not None or _within(each, new) is None
        }
        record.files = dict(sorted(moved.items(), key=lambda item: entries.path_order(item[0])))
        if record.preview is not None:
            record.preview.file = _renamed(record.preview.file, old, new)
        _delete_emptied(folder, old)
        record.updated = entries.in_utc(datetime.now(UTC))
        entries.write(folder, record)
    catalog.changed(target, folder.name)
    return entries.entry_of(target, folder, record)


def delete_file(name: str, path: str, store: str | None) -> Entry:
    """Deletes a file, or a folder and everything in it, from an entry."""
    target, folder = entries.find(name, store)
    with entries.locked(folder):
        record = entries.read(folder)
        found = _found(folder, path)
        old = _inside(folder, found)
        try:
            if found.is_dir():
                disk.delete_folder(found)
            else:
                disk.delete_file(found)
        except OSError as error:
            raise ReferenceStoreError(
                f"Couldn't delete {old} from {folder.name}: {error.strerror or error}. A file in it may be open in "
                "another program. Close it and try again. Nothing was deleted."
            ) from None
        record.files = {each: about for each, about in record.files.items() if _within(each, old) is None}
        if record.preview is not None and _within(record.preview.file, old) is not None:
            record.preview = None
        _delete_emptied(folder, old)
        record.updated = entries.in_utc(datetime.now(UTC))
        entries.write(folder, record)
    catalog.changed(target, folder.name)
    return entries.entry_of(target, folder, record)


def _found(folder: Path, path: str) -> Path:
    """Returns the file or folder at `path` in the entry, refusing one that isn't there or is the library's own."""
    wanted = names.slashed(path)
    found = entries.at(folder, wanted) if wanted else None
    if found is None or entries.is_the_librarys(_inside(folder, found)) or not (found.is_file() or found.is_dir()):
        raise ReferenceStoreError(f"{folder.name} has no file or folder {wanted}.")
    return found


def _inside(folder: Path, path: Path) -> str:
    return path.relative_to(folder).as_posix()


def _files_at(folder: Path, record: EntryRecord, found: Path) -> list[str]:
    """Returns the paths of the entry's files that are `found`, or in it when it is a folder."""
    at = _inside(folder, found)
    return [file.path for file in entries.files_of(folder, record) if _within(file.path, at) is not None]


def _new_path(new_path: str, name: str) -> str:
    """Returns where a renamed file or folder goes: the path given, or the folder given with its own name in it."""
    given = names.slashed(new_path)
    if given == "." or new_path.rstrip().endswith(("/", "\\")):
        return entries.check_file_path(PurePosixPath(given, name).as_posix())
    return entries.check_file_path(given)


def _within(path: str, folder: str) -> list[str] | None:
    """Returns the parts of `path` after `folder` when it is `folder` or in it, whatever the case, or None."""
    parts, folder_parts = path.split("/"), folder.split("/")
    if entries.path_order("/".join(parts[: len(folder_parts)])) != entries.path_order(folder):
        return None
    return parts[len(folder_parts) :]


def _renamed(path: str, old: str, new: str) -> str:
    """Returns `path` after `old` is renamed to `new`, which is itself when it isn't `old` or in it."""
    rest = _within(path, old)
    return path if rest is None else "/".join([new, *rest])


def _check_lengths(folder: Path, found: Path, new: str) -> None:
    """Refuses a new path that would make a path in the entry too long for Windows."""
    target = folder / new
    if found.is_dir():
        inside = [each.relative_to(found) for each in found.rglob("*")]
        longest = max(inside, key=lambda each: len(str(each)), default=None)
        names.check_folder_path(target, new)
        if longest is not None:
            names.check_full_path(target / longest, new)
    else:
        names.check_full_path(target, new)
    if not target.parent.is_dir():
        names.check_folder_path(target.parent, PurePosixPath(new).parent.as_posix())


def _delete_emptied(folder: Path, path: str) -> None:
    """Deletes the folders `path` was in that it left empty, up to the entry's own folder."""
    disk.delete_empty([folder / each for each in PurePosixPath(path).parents[:-1]])
