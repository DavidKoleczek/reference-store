"""The index: a SQLite database of what the stores hold, kept beside the configuration.

It is made from the stores' files and never the other way around, so it can be deleted at any time. A store's rows
are under its folder, so they stay when the store gets another name.
"""

from collections.abc import Callable, Generator, Iterable, Iterator
import contextlib
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sqlite3

from reference_store.core import config, names

FOLDER = "index"
FILE = "index.sqlite"
# Goes up whenever the tables or the fields of an entry's summary change, so an index made by another version is made
# again.
VERSION = 2
# How long a process waits for another one that is writing.
WAIT_SECONDS = 30
TABLES = """
create table stores (
    path text primary key,
    checked real,
    started real
) without rowid;
create table entries (
    store text not null,
    name text not null,
    key text not null,
    seen text not null,
    read_at real not null,
    summary text not null,
    tags text not null,
    primary key (store, name)
) without rowid;
create index entries_by_key on entries (store, key, name);
create table files (
    store text not null,
    entry text not null,
    path text not null,
    size integer not null,
    modified integer not null,
    description text not null,
    notes text not null,
    tags text not null,
    primary key (store, entry, path)
) without rowid;
"""


@dataclass(frozen=True)
class FileRow:
    """What the index keeps of a file in an entry."""

    path: str
    size: int
    modified: int  # in seconds since 1970
    description: str
    notes: str
    tags: list[str]


@dataclass(frozen=True)
class EntryRow:
    """What the index keeps of an entry."""

    name: str
    seen: str  # stands for the files its folder held when it was read, with their sizes and times
    read_at: float  # when reading it started
    summary: str  # the entry as JSON, without its store and files, and with its preview as a path in the entry
    tags: list[str]
    files: list[FileRow]


def location() -> Path:
    """Returns where the index is."""
    return config.home() / FOLDER / FILE


def connect() -> sqlite3.Connection:
    """Opens the index, making it when it is missing, was made by another version, or can't be read as a database.

    Raises:
        OSError: Its folder can't be written.
        sqlite3.Error: It can't be opened.
    """
    path = location()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        return _opened(path)
    except sqlite3.OperationalError:
        raise
    except sqlite3.DatabaseError:
        for each in (path, path.with_name(f"{FILE}-wal"), path.with_name(f"{FILE}-shm")):
            each.unlink(missing_ok=True)
        return _opened(path)


def store_key(path: Path) -> str:
    """Returns what a store's rows are under: its folder, as the system compares paths."""
    return os.path.normcase(path)


def checked(connection: sqlite3.Connection, store: str) -> float | None:
    """Returns when the store was last read or checked in full, or None when it never was."""
    row = connection.execute("select checked from stores where path = ?", (store,)).fetchone()
    return None if row is None else row[0]


def set_checked(connection: sqlite3.Connection, store: str, when: float) -> None:
    """Records that the store was read or checked in full."""
    with _writing(connection):
        connection.execute(
            "insert into stores (path, checked) values (?, ?) on conflict (path) do update set checked = ?",
            (store, when, when),
        )


def claim_check(connection: sqlite3.Connection, store: str, now: float, not_since: float) -> bool:
    """Returns whether the caller is the one to start a check of the store, which it is when none was started since
    `not_since`. Of the processes that ask at once, one gets it."""
    with _writing(connection):
        claimed = connection.execute(
            "update stores set started = ? where path = ? and (started is null or started < ?)",
            (now, store, not_since),
        )
        return claimed.rowcount == 1


def put(connection: sqlite3.Connection, store: str, rows: Iterable[EntryRow]) -> None:
    """Saves entries, each in place of what the index had under its name, unless that was read later."""
    with _writing(connection):
        for row in rows:
            held = connection.execute(
                "select read_at from entries where store = ? and name = ?", (store, row.name)
            ).fetchone()
            if held is not None and held[0] > row.read_at:
                continue
            connection.execute("delete from files where store = ? and entry = ?", (store, row.name))
            connection.execute(
                "insert or replace into entries values (?, ?, ?, ?, ?, ?, ?)",
                (store, row.name, names.key(row.name), row.seen, row.read_at, row.summary, json.dumps(row.tags)),
            )
            connection.executemany(
                "insert into files values (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    (
                        store,
                        row.name,
                        file.path,
                        file.size,
                        file.modified,
                        file.description,
                        file.notes,
                        json.dumps(file.tags),
                    )
                    for file in row.files
                ),
            )


def drop(connection: sqlite3.Connection, store: str, entry_names: Iterable[str], as_of: float) -> None:
    """Takes entries out, unless they were read after `as_of`, when they were found gone."""
    with _writing(connection):
        for name in entry_names:
            gone = connection.execute(
                "delete from entries where store = ? and name = ? and read_at <= ?", (store, name, as_of)
            )
            if gone.rowcount:
                connection.execute("delete from files where store = ? and entry = ?", (store, name))


def forget(connection: sqlite3.Connection, store: str) -> None:
    """Takes out everything about a store."""
    with _writing(connection):
        for table, column in (("files", "store"), ("entries", "store"), ("stores", "path")):
            connection.execute(f"delete from {table} where {column} = ?", (store,))


def entry_names(connection: sqlite3.Connection, store: str) -> set[str]:
    """Returns the names of a store's entries."""
    return {name for (name,) in connection.execute("select name from entries where store = ?", (store,))}


def seen(connection: sqlite3.Connection, store: str) -> dict[str, str]:
    """Returns each entry of a store by name, with what stands for the files it held when it was read."""
    return dict(connection.execute("select name, seen from entries where store = ?", (store,)))


def spellings(connection: sqlite3.Connection, store: str, name: str) -> list[str]:
    """Returns the names in a store that are `name` whatever their case."""
    found = connection.execute("select name from entries where store = ? and key = ?", (store, names.key(name)))
    return [each for (each,) in found]


def summaries(connection: sqlite3.Connection, store: str) -> list[tuple[str, str]]:
    """Returns each entry of a store in the order of the names: its name, and its summary."""
    return connection.execute(
        "select name, summary from entries where store = ? order by key, name", (store,)
    ).fetchall()


def entry_tags(connection: sqlite3.Connection, store: str) -> list[tuple[str, list[str]]]:
    """Returns each entry of a store in the order of the names: its name, and its tags."""
    found = connection.execute("select name, tags from entries where store = ? order by key, name", (store,))
    return [(name, json.loads(tags)) for name, tags in found]


def files(
    connection: sqlite3.Connection, store: str, tagged: bool, wanted: Callable[[str, str], bool] | None = None
) -> Iterator[tuple[str, FileRow]]:
    """Yields each file of a store with its entry's name. `tagged` leaves out the files with no tag, and `wanted`
    those it doesn't pick by their entry's name and their path."""
    found = connection.execute(
        "select entry, path, size, modified, description, notes, tags from files where store = ?"
        + (" and tags != '[]'" if tagged else ""),
        (store,),
    )
    for entry, path, size, modified, description, notes, tags in found:
        if wanted is None or wanted(entry, path):
            yield entry, FileRow(path, size, modified, description, notes, json.loads(tags) if tags != "[]" else [])


def file_tags(connection: sqlite3.Connection, store: str) -> Iterator[tuple[str, str, list[str]]]:
    """Yields each file of a store that has a tag: its entry's name, its path, and its tags."""
    found = connection.execute("select entry, path, tags from files where store = ? and tags != '[]'", (store,))
    for entry, path, tags in found:
        yield entry, path, json.loads(tags)


def _opened(path: Path) -> sqlite3.Connection:
    # Transactions are started and ended here by hand, so a read never holds one open.
    connection = sqlite3.connect(path, timeout=WAIT_SECONDS, isolation_level=None)
    try:
        # Readers and a writer don't wait for each other in this mode.
        connection.execute("pragma journal_mode = wal")
        connection.execute("pragma synchronous = normal")
        if connection.execute("pragma user_version").fetchone()[0] != VERSION:
            with _writing(connection):
                if connection.execute("pragma user_version").fetchone()[0] != VERSION:
                    for table in ("files", "entries", "stores"):
                        connection.execute(f"drop table if exists {table}")
                    for statement in TABLES.split(";"):
                        connection.execute(statement)
                    connection.execute(f"pragma user_version = {VERSION}")
    except BaseException:
        connection.close()
        raise
    return connection


@contextlib.contextmanager
def _writing(connection: sqlite3.Connection) -> Generator[None]:
    """Makes the block's changes all at once, or none of them when it fails."""
    connection.execute("begin immediate")
    try:
        yield
    except BaseException:
        connection.execute("rollback")
        raise
    connection.execute("commit")
