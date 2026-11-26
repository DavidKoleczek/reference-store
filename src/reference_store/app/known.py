"""Where the files the library returned to the view are on this machine, by their store, entry, and path.

The view names a file by its store, its entry, and its path in the entry, and never by a path on this machine. Only a
file the library listed can be read through the app, so nothing else on the machine can be reached from the view.
"""

from collections import OrderedDict
from pathlib import Path
import threading

from reference_store import lib
from reference_store.app import images
from reference_store.models import (
    Entry,
    EntryListing,
    EntrySummary,
    FileListing,
    GrepListing,
    ReferenceStoreError,
    Store,
)

# Every file of a few large entries and many pages of them, which is little next to what the page holds.
MOST = 200_000

Key = tuple[str, ...]


class Known:
    """The files, previews, entry folders, and stores the library has returned, the most recent kept."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._paths: OrderedDict[Key, Path | None] = OrderedDict()
        # The same files by where they are, to tell whether a path is one of them.
        self._files: set[str] = set()

    def record(self, value: object) -> None:
        """Remembers where the files, previews, folders, and stores in what a library function returned are."""
        if isinstance(value, list):
            for each in value:
                self.record(each)
        elif isinstance(value, EntryListing):
            self.record(value.entries)
        elif isinstance(value, GrepListing):
            self.record([result.entry for result in value.results])
        elif isinstance(value, FileListing):
            for file in value.files:
                self._put(("file", file.store, file.entry, file.path), file.full_path)
        elif isinstance(value, Entry):
            self._put(("folder", value.store, value.name), value.folder)
            for file in value.files:
                self._put(("file", value.store, value.name, file.path), file.full_path)
            self._put(("preview", value.store, value.name), value.preview.path if value.preview else None)
            first = next((file.full_path for file in value.files if images.is_image(file.full_path)), None)
            self._put(("cover", value.store, value.name), first)
        elif isinstance(value, EntrySummary):
            self._put(("preview", value.store, value.name), value.preview.path if value.preview else None)
        elif isinstance(value, Store):
            self._put(("store", value.name), value.path)

    def file(self, store: str, entry: str, path: str) -> Path:
        """Returns where one of an entry's files is.

        Raises:
            ReferenceStoreError: There is no such entry, or it has no such file.
        """
        found = self._find(("file", store, entry, path), store, entry)
        if found is None:
            raise ReferenceStoreError(f"{entry} in {store} has no file {path}.")
        return found

    def cover(self, store: str, entry: str) -> Path:
        """Returns the image that stands for an entry: its preview, or the first of its images when it has none.

        Raises:
            ReferenceStoreError: There is no such entry, or it has no image.
        """
        found = self._get(("preview", store, entry)) or self._get(("cover", store, entry))
        if found is None or not found.is_file():
            self.record(lib.get_entry(entry, store))
            found = self._get(("preview", store, entry)) or self._get(("cover", store, entry))
        if found is None:
            raise ReferenceStoreError(f"{entry} in {store} has no image.")
        return found

    def folder(self, store: str, entry: str) -> Path:
        """Returns an entry's folder.

        Raises:
            ReferenceStoreError: There is no such entry.
        """
        found = self._find(("folder", store, entry), store, entry, False)
        if found is None:
            raise ReferenceStoreError(f"There is no entry {entry} in {store}.")
        return found

    def is_file(self, path: Path) -> bool:
        """Returns whether `path` is a file of an entry the library returned."""
        with self._lock:
            return _folded(path) in self._files

    def store(self, name: str) -> Path:
        """Returns a store's folder.

        Raises:
            ReferenceStoreError: There is no such store.
        """
        key = ("store", name)
        found = self._get(key)
        if found is None:
            self.record(lib.list_stores())
            found = self._get(key)
        if found is None:
            raise ReferenceStoreError(f"There is no store {name}.")
        return found

    def _find(self, key: Key, store: str, entry: str, is_file: bool = True) -> Path | None:
        """What `key` names, reading the entry again when it isn't known or isn't there any more."""
        found = self._get(key)
        if found is None or not (found.is_file() if is_file else found.is_dir()):
            self.record(lib.get_entry(entry, store))
            found = self._get(key)
        return found

    def _get(self, key: Key) -> Path | None:
        folded = tuple(part.casefold() for part in key)
        with self._lock:
            found = self._paths.get(folded)
            if found is not None:
                self._paths.move_to_end(folded)
            return found

    def _put(self, key: Key, path: Path | None) -> None:
        folded = tuple(part.casefold() for part in key)
        with self._lock:
            self._paths[folded] = path
            self._paths.move_to_end(folded)
            if key[0] == "file" and path is not None:
                self._files.add(_folded(path))
            while len(self._paths) > MOST:
                (kind, *_), gone = self._paths.popitem(last=False)
                if kind == "file" and gone is not None:
                    self._files.discard(_folded(gone))


def _folded(path: Path) -> str:
    return str(path).casefold()
