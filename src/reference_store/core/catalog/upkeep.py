"""Keeping the index the same as the stores' files.

The library tells the index of each entry it changes. Changes made any other way, such as by hand or by a folder that
syncs, are found in two ways. Each read compares the names of a store's entries with the index, which costs one
listing of the store's folder. Once a day a read also starts a check of every folder, in a process of its own, so the
read doesn't wait for it.

A modified time can't stand in for the daily check. On NTFS the listing of a store's folder goes on giving an entry's
folder the time it had before a file was added to it or deleted from it, until something asks the folder itself. Asking
every folder takes a request each, which is what the index is there to save on a network drive.
"""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time

from reference_store.core import detached, entries, names
from reference_store.core.catalog import index
from reference_store.core.catalog.index import EntryRow, FileRow
from reference_store.core.entries import ENTRY_FILE, Found
from reference_store.models import ReferenceStoreError

CHECK_EVERY_SECONDS = 24 * 60 * 60
# A check that was started and never finished, such as one ended with the process that started it, is started again
# only after this long, so that not every read starts one.
CHECK_AGAIN_SECONDS = 60 * 60
# How many entries are saved at once while a whole store is read, so that other processes get their turn.
BATCH = 500
CHECK_MODULE = "reference_store.core.catalog.check"


def ready(connection: sqlite3.Connection, folders: list[Path]) -> None:
    """Brings the index up to date with the stores in these folders, as far as a read waits for.

    A store the index has not read is read in full. For the others, the names of their entries are compared, and a
    check of everything in them is started when the last one is a day old. A store that can't be read just now is left
    as the index has it.
    """
    overdue: list[Path] = []
    for folder in folders:
        store = index.store_key(folder)
        try:
            last = index.checked(connection, store)
            if last is None:
                read_store(connection, folder)
                continue
            compare_names(connection, folder)
        except OSError:
            continue
        now = time.time()
        if now - last > CHECK_EVERY_SECONDS and index.claim_check(connection, store, now, now - CHECK_AGAIN_SECONDS):
            overdue.append(folder)
    if overdue:
        _start_check(overdue)


def read_store(connection: sqlite3.Connection, folder: Path) -> None:
    """Reads every entry of a store into the index, and takes out those that are no longer there.

    Raises:
        OSError: The store can't be read. The index keeps what it had of it.
    """
    store = index.store_key(folder)
    started = time.time()
    held = index.entry_names(connection, store)
    batch: list[EntryRow] = []
    for name in _listed(folder):
        row = read_entry(folder / name)
        if row is None:
            continue
        held.discard(name)
        batch.append(row)
        if len(batch) == BATCH:
            index.put(connection, store, batch)
            batch = []
    index.put(connection, store, batch)
    index.drop(connection, store, held, started)
    index.set_checked(connection, store, time.time())


def compare_names(connection: sqlite3.Connection, folder: Path) -> None:
    """Reads the entries whose names the index doesn't have, and takes out those whose folders are gone.

    Raises:
        OSError: The store can't be read. The index keeps what it had of it.
    """
    store = index.store_key(folder)
    started = time.time()
    held = index.entry_names(connection, store)
    listed = _listed(folder)
    rows = [read_entry(folder / name) for name in listed if name not in held]
    index.put(connection, store, [row for row in rows if row is not None])
    index.drop(connection, store, held.difference(listed), started)


def check_store(connection: sqlite3.Connection, folder: Path) -> None:
    """Compares every file of a store with the index, and reads again the entries that differ.

    An entry differs when a file was added to it, removed from it, or renamed in it, or when a file's size or modified
    time changed, its `.entry.json` included. No file is opened to tell.

    Raises:
        OSError: The store can't be read. The index keeps what it had of it, and the check counts as not done.
    """
    store = index.store_key(folder)
    started = time.time()
    held = index.seen(connection, store)
    for name in _listed(folder):
        found = entries.found_in(folder / name)
        if held.get(name) == _seen(found):
            del held[name]
            continue
        row = read_entry(folder / name)
        if row is not None:
            held.pop(name, None)
            index.put(connection, store, [row])
    # What is left has no entry in its folder. A store that went out of reach partway looks the same, so its folder is
    # listed once more, which fails then, and nothing is taken out.
    _listed(folder)
    index.drop(connection, store, held, started)
    index.set_checked(connection, store, time.time())


def rebuild(connection: sqlite3.Connection, folder: Path) -> None:
    """Reads a store into the index from nothing.

    Raises:
        OSError: The store can't be read.
    """
    index.forget(connection, index.store_key(folder))
    read_store(connection, folder)


def changed(connection: sqlite3.Connection, folder: Path, name: str) -> None:
    """Reads one entry into the index again, or takes it out when it is no longer in the store.

    Raises:
        OSError: The entry can't be read. The index keeps what it had of it.
    """
    store = index.store_key(folder)
    started = time.time()
    row = read_entry(folder / name)
    # A name is one whatever its case, so a row under another spelling is the entry before it was renamed.
    others = [each for each in index.spellings(connection, store, name) if row is None or each != row.name]
    index.drop(connection, store, others, started)
    if row is not None:
        index.put(connection, store, [row])


def read_entry(folder: Path) -> EntryRow | None:
    """Returns what the index keeps of the entry in a folder, or None when the folder holds no entry that can be read.

    Raises:
        OSError: The folder can't be read, other than for having no `.entry.json`.
    """
    read_at = time.time()
    try:
        record = entries.read(folder)
    except ReferenceStoreError:
        return None
    found = entries.found_in(folder)
    entry = entries.entry_from("", folder, record, found)
    summary = entry.model_dump(mode="json", exclude={"store", "folder", "files"})
    if entry.preview is not None:
        summary["preview"]["path"] = entry.preview.path.relative_to(folder).as_posix()
    return EntryRow(
        name=entry.name,
        seen=_seen(found),
        read_at=read_at,
        summary=json.dumps(summary),
        tags=entry.tags,
        files=[
            FileRow(
                path=file.path,
                size=file.size,
                modified=int(file.modified.timestamp()),
                description=file.description,
                notes=file.notes,
                tags=file.tags,
            )
            for file in entry.files
        ],
    )


def _listed(folder: Path) -> list[str]:
    """Returns the names of the folders in a store that can be entries, in the order of the names."""
    with os.scandir(folder) as found:
        # A name can't start with a dot, so such a folder is the library's own, such as one being deleted.
        listed = [item.name for item in found if item.is_dir() and not item.name.startswith(".")]
    return sorted(listed, key=names.key)


def _seen(found: list[Found]) -> str:
    """Returns what stands for the files found in an entry's folder: it differs when a file was added, removed, or
    renamed, or when one's size or modified time changed. A folder with no `.entry.json` gives nothing."""
    if not any(names.key(path) == ENTRY_FILE for path, _, _ in found):
        return ""
    digest = hashlib.sha256()
    for path, _, info in sorted(found, key=lambda each: each[0]):
        digest.update(f"{path}\0{info.st_size}\0{info.st_mtime_ns}\n".encode())
    return digest.hexdigest()


def _start_check(folders: list[Path]) -> None:
    """Starts a process that checks the stores in these folders, and goes on after this one ends."""
    detached.start(CHECK_MODULE, [str(folder) for folder in folders])
