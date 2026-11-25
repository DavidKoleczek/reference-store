"""Renaming entries, and moving them to other stores, with everything in their folders."""

from datetime import UTC, datetime
from pathlib import Path

from reference_store.core import changes, disk, entries, names, stores
from reference_store.core.entries import ENTRY_FILE
from reference_store.models import Entry, ReferenceStoreError, Store


def rename_entry(name: str, new_name: str, store: str | None) -> Entry:
    """Renames the entry's folder. A name that only changes case is a rename too."""
    names.check_name(new_name, "an entry")
    target, folder = entries.find_to_change(name, store)
    if folder.name == new_name:
        return entries.entry_of(target, folder, entries.read(folder))
    return _relocated(target, folder, target, target.path / new_name, "the new name")


def move_entry(name: str, to_store: str, store: str | None) -> Entry:
    """Moves the entry's folder to another store, under the same name."""
    destination = stores.find_store(to_store)
    stores.check_can_change(destination)
    source, folder = entries.find_to_change(name, store)
    if stores.same_path(source.path, destination.path):
        raise ReferenceStoreError(f"{folder.name} is in the store {destination.name} already.")
    stores.check_sizes(destination, (path for path in folder.rglob("*") if path.is_file()))
    return _relocated(source, folder, destination, destination.path / folder.name, "the entry's name")


def _relocated(source: Store, folder: Path, destination: Store, new_folder: Path, shorten: str) -> Entry:
    """Moves an entry's folder to `new_folder`, refusing when something has that name, and returns the entry there."""
    _check_lengths(folder, new_folder, shorten)
    with entries.locked(folder, new_folder):
        record = entries.read(folder)
        taken = entries.child(destination.path, new_folder.name)
        if taken is not None and not stores.same_path(taken, folder):
            what = f"The store {destination.name} already has {entries.what_is(taken)} named {taken.name}"
            raise ReferenceStoreError(
                f"{what}. Pick another name."
                if source is destination
                else f"{what}, so {folder.name} can't be moved there. Rename one of them first."
            )
        if destination.priority_order == 0:
            stores.make_store(destination.path)
        try:
            disk.move_folder(folder, new_folder)
        except OSError as error:
            raise ReferenceStoreError(
                f"Couldn't move {folder} to {new_folder}: {error.strerror or error}. A file in it may be open in "
                "another program. Close it and try again."
            ) from None
        record.updated = entries.in_utc(datetime.now(UTC))
        entries.write(new_folder, record)
    changes.made(source, folder.name)
    changes.made(destination, new_folder.name)
    return entries.entry_of(destination, new_folder, record)


def _check_lengths(folder: Path, new_folder: Path, shorten: str) -> None:
    """Refuses a new folder that would make the longest path in the entry too long for Windows."""
    inside = [path.relative_to(folder) for path in folder.rglob("*")]
    longest = max(inside, key=lambda path: len(str(path)), default=Path(ENTRY_FILE))
    names.check_full_path(new_folder / longest, shorten)
