"""The catalog read from the stores' folders on every call, which is always what the files say and takes as long as
the stores are large."""

from collections.abc import Callable, Iterator

from reference_store.core import entries
from reference_store.core.filters import Filters
from reference_store.models import Entry, EntrySummary, FileMatch, Store


class Scanned:
    """A `Catalog` that keeps nothing between calls."""

    def summaries(self, keep: Filters, store: str | None) -> list[EntrySummary]:
        """Returns the entries that pass the filters, without their files."""
        return [entries.summary_of(entry) for entry in self.entries(keep, store)]

    def files(self, keep: Filters, store: str | None, wanted: Callable[[str, str], bool]) -> list[FileMatch]:
        """Returns the files that pass the filters, in entries that pass them, and that `wanted` picks."""
        return [
            FileMatch.model_validate({**file.model_dump(), "entry": entry.name, "store": entry.store})
            for entry in entries.every_entry(store)
            if keep.keeps_summary(entry)
            for file in entry.files
            if keep.keeps_file(file) and wanted(entry.name, file.path)
        ]

    def tags(self, store: str | None) -> Iterator[tuple[list[str], list[list[str]]]]:
        """Yields each entry's tags, and the tags of each of its files that has any."""
        for entry in entries.every_entry(store):
            yield entry.tags, [file.tags for file in entry.files if file.tags]

    def entries(self, keep: Filters, store: str | None) -> Iterator[Entry]:
        """Yields the entries that pass the filters, with their files."""
        return (entry for entry in entries.every_entry(store) if keep.keeps(entry))

    def changed(self, store: Store, name: str) -> None:
        """Does nothing, since the next call reads the folders again."""
