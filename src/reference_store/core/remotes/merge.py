"""Making one `.entry.json` of two that were changed on different devices since they were the same.

Each side's changes are kept. Where both changed the same thing, the side whose entry was updated later has it.
"""

from reference_store.core import entries, names
from reference_store.core.entries import EntryRecord, FileRecord

PICKED = ("id", "title", "description", "url", "notes", "rating", "preview", "source_published_at", "created")


def merged(base: EntryRecord | None, ours: EntryRecord, theirs: EntryRecord) -> EntryRecord:
    """Returns the entry with what both sides changed since `base`, which is None when each side added the entry."""
    later = theirs if theirs.updated >= ours.updated else ours
    # With no base, a field one side left as it starts out is one that side didn't change.
    picked = {
        field: _picked(
            getattr(base, field) if base else EntryRecord.model_fields[field].get_default(),
            getattr(ours, field),
            getattr(theirs, field),
            getattr(later, field),
        )
        for field in PICKED
    }
    return EntryRecord(
        **picked,
        tags=_tags(base.tags if base else [], ours.tags, theirs.tags),
        updated=max(ours.updated, theirs.updated),
        files=_files(base.files if base else {}, ours.files, theirs.files, later is theirs),
    )


def _picked[T](was: T, mine: T, other: T, later: T) -> T:
    """Returns the value only one side changed, or the later side's when both did."""
    if mine == other or other == was:
        return mine
    if mine == was:
        return other
    return later


def _tags(was: list[str], mine: list[str], other: list[str]) -> list[str]:
    """Returns the tags with what each side added and without what each side removed, in the order they were in."""
    before = {names.key(tag) for tag in was}
    here = {names.key(tag) for tag in mine}
    there = {names.key(tag) for tag in other}
    kept = [tag for tag in mine if names.key(tag) in there or names.key(tag) not in before]
    added = [tag for tag in other if names.key(tag) not in here and names.key(tag) not in before]
    return kept + added


def _files(
    was: dict[str, FileRecord], mine: dict[str, FileRecord], other: dict[str, FileRecord], other_is_later: bool
) -> dict[str, FileRecord]:
    """Returns what is said about each file, a file at a time, as `merged` does for the entry."""
    before = {names.key(path): about for path, about in was.items()}
    there = {names.key(path): about for path, about in other.items()}
    here = {names.key(path) for path in mine}
    result: dict[str, FileRecord] = {}
    for path, about in mine.items():
        old, new = before.get(names.key(path)), there.get(names.key(path))
        if new is None:
            # The other side took it out, which stands unless this side changed it since.
            if old is None or about != old:
                result[path] = about
            continue
        later = new if other_is_later else about
        old = old or FileRecord()
        result[path] = FileRecord(
            description=_picked(old.description, about.description, new.description, later.description),
            notes=_picked(old.notes, about.notes, new.notes, later.notes),
            tags=_tags(old.tags, about.tags, new.tags),
        )
    for path, about in other.items():
        old = before.get(names.key(path))
        if names.key(path) not in here and (old is None or about != old):
            result[path] = about
    return dict(sorted(result.items(), key=lambda item: entries.path_order(item[0])))
