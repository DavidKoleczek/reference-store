"""The catalog read from the index, which takes about as long for a large store as for a small one."""

from collections import defaultdict
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
from typing import Any

from reference_store.core import entries, stores
from reference_store.core.catalog import index, upkeep
from reference_store.core.catalog.index import FileRow
from reference_store.core.filters import Filters
from reference_store.models import Entry, EntryFile, EntrySummary, FileMatch, Store


class Indexed:
    """A `Catalog` that answers from the index, once `upkeep` has brought it up to date."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def summaries(self, keep: Filters, store: str | None) -> list[EntrySummary]:
        """Returns the entries that pass the filters, without their files."""
        found: list[EntrySummary] = []
        for each in self._stores(store):
            held = index.store_key(each.path)
            with_file = self._with_kept_file(held, keep)
            for name, summary in index.summaries(self._connection, held):
                if with_file is not None and name not in with_file:
                    continue
                entry = EntrySummary.model_validate(_fields(each, name, summary))
                if keep.keeps_summary(entry):
                    found.append(entry)
        return found

    def files(self, keep: Filters, store: str | None, wanted: Callable[[str, str], bool]) -> list[FileMatch]:
        """Returns the files that pass the filters, in entries that pass them, and that `wanted` picks."""
        found: list[FileMatch] = []
        for each in self._stores(store):
            held = index.store_key(each.path)
            kept: set[str] | None = None
            if keep.about_entries:
                kept = {entry.name for entry in self._summaries(each) if keep.keeps_summary(entry)}
            for name, file in index.files(self._connection, held, bool(keep.file_tags), wanted):
                if (kept is None or name in kept) and keep.keeps_file_tags(file.tags):
                    found.append(FileMatch(**_file_fields(each.path / name, file), entry=name, store=each.name))
        return found

    def tags(self, store: str | None) -> Iterator[tuple[list[str], list[list[str]]]]:
        """Yields each entry's tags, and the tags of each of its files that has any."""
        for each in self._stores(store):
            held = index.store_key(each.path)
            tagged: dict[str, list[tuple[str, list[str]]]] = defaultdict(list)
            for name, path, tags in index.file_tags(self._connection, held):
                tagged[name].append((path, tags))
            for name, tags in index.entry_tags(self._connection, held):
                in_order = sorted(tagged.get(name, []), key=lambda file: entries.path_order(file[0]))
                yield tags, [tags_of_file for _, tags_of_file in in_order]

    def entries(self, keep: Filters, store: str | None) -> Iterator[Entry]:
        """Yields the entries that pass the filters, with their files."""
        for each in self._stores(store):
            held = index.store_key(each.path)
            files: dict[str, list[FileRow]] = defaultdict(list)
            for name, file in index.files(self._connection, held, tagged=False):
                files[name].append(file)
            for name, summary in index.summaries(self._connection, held):
                folder = each.path / name
                entry = Entry.model_validate(
                    {
                        **_fields(each, name, summary),
                        "folder": folder,
                        "files": [
                            EntryFile(**_file_fields(folder, file))
                            for file in sorted(files.get(name, []), key=lambda file: entries.path_order(file.path))
                        ],
                    }
                )
                if keep.keeps(entry):
                    yield entry

    def changed(self, store: Store, name: str) -> None:
        """Reads the entry into the index again, or takes it out when it is gone."""
        upkeep.changed(self._connection, store.path, name)

    def _stores(self, store: str | None) -> list[Store]:
        """Returns the stores to read, with the index brought up to date with them."""
        searched = stores.searched(store)
        upkeep.ready(self._connection, [each.path for each in searched])
        return searched

    def _summaries(self, store: Store) -> Iterator[EntrySummary]:
        for name, summary in index.summaries(self._connection, index.store_key(store.path)):
            yield EntrySummary.model_validate(_fields(store, name, summary))

    def _with_kept_file(self, held: str, keep: Filters) -> set[str] | None:
        """Returns the names of the entries with a file that has the file tags, or None when there are no file tags."""
        if not keep.file_tags:
            return None
        return {name for name, _, tags in index.file_tags(self._connection, held) if keep.keeps_file_tags(tags)}


def _fields(store: Store, name: str, summary: str) -> dict[str, Any]:
    """Returns the fields of an entry's summary, from what the index keeps of it."""
    fields = json.loads(summary)
    fields["store"] = store.name
    if fields["preview"] is not None:
        fields["preview"]["path"] = store.path / name / fields["preview"]["path"]
    return fields


def _file_fields(folder: Path, file: FileRow) -> dict[str, Any]:
    """Returns the fields of a file in the entry in a folder, from what the index keeps of it."""
    return {
        "path": file.path,
        "full_path": folder / file.path,
        "size": file.size,
        "modified": datetime.fromtimestamp(file.modified, UTC),
        "description": file.description,
        "notes": file.notes,
        "tags": file.tags,
    }
