"""What the stores hold, as a read asks for it.

Listing and search ask a `Catalog` and not the stores' folders, so how the answer is come by can change without
them. `indexed` answers from the index, and `scanned` reads the folders on every call.
"""

from collections.abc import Callable, Generator, Iterator
import contextlib
import sqlite3
from typing import Protocol

from reference_store.core import stores
from reference_store.core.catalog import index, upkeep
from reference_store.core.catalog.indexed import Indexed
from reference_store.core.catalog.scanned import Scanned
from reference_store.core.filters import Filters
from reference_store.models import Entry, EntrySummary, FileMatch, ReferenceStoreError, Store


class Catalog(Protocol):
    """What the stores hold. `store` is the one store to read, or None for every store that is available.

    Entries come a store at a time in priority order, and in the order of their names.
    """

    def summaries(self, keep: Filters, store: str | None) -> list[EntrySummary]:
        """Returns the entries that pass the filters, without their files."""
        ...

    def files(self, keep: Filters, store: str | None, wanted: Callable[[str, str], bool]) -> list[FileMatch]:
        """Returns the files that pass the filters, in entries that pass them, and that `wanted` picks.

        `wanted` is given the name of a file's entry and the file's path in it.
        """
        ...

    def tags(self, store: str | None) -> Iterator[tuple[list[str], list[list[str]]]]:
        """Yields each entry's tags, and the tags of each of its files that has any."""
        ...

    def entries(self, keep: Filters, store: str | None) -> Iterator[Entry]:
        """Yields the entries that pass the filters, with their files."""
        ...

    def changed(self, store: Store, name: str) -> None:
        """Hears that the entry with that name in a store was added, changed, or removed."""
        ...


@contextlib.contextmanager
def reading() -> Generator[Catalog]:
    """Yields the catalog to ask while the block runs: the index, or the folders when the index can't be opened, such
    as in a folder that can't be written.

    Raises:
        ReferenceStoreError: The index stopped working partway.
    """
    try:
        connection = index.connect()
    except (OSError, sqlite3.Error):
        yield Scanned()
        return
    try:
        yield Indexed(connection)
    except sqlite3.Error as error:
        raise ReferenceStoreError(
            f"The index in {index.location().parent} couldn't be used: {error}. Delete that folder to have it made "
            "again."
        ) from None
    finally:
        connection.close()


def changed(store: Store, name: str) -> None:
    """Tells the catalog that the entry with that name in a store was added, changed, or removed."""
    # The change itself is done by now, so a catalog that can't take it in is left for its next check to put right.
    with contextlib.suppress(OSError, ReferenceStoreError), reading() as held:
        held.changed(store, name)


def rebuild(store: str | None) -> None:
    """Reads a store into the index from nothing, or every store that is available.

    Raises:
        ReferenceStoreError: The store named can't be used, or the index couldn't be rebuilt.
    """
    searched = stores.searched(store)
    try:
        with contextlib.closing(index.connect()) as connection:
            for each in searched:
                upkeep.rebuild(connection, each.path)
    except (OSError, sqlite3.Error) as error:
        raise ReferenceStoreError(f"The index in {index.location().parent} couldn't be rebuilt: {error}.") from None
