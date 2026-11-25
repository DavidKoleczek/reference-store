"""Listing what the stores hold: their entries a page at a time, and the tags and sites across them.

Each call reads the stores' folders, so what was changed by hand shows at once.
"""

from typing import get_args

from reference_store.core import entries, filters, names, pages, sites
from reference_store.core.pages import Key
from reference_store.models import (
    Entry,
    EntryListing,
    EntrySort,
    GroupCount,
    ReferenceStoreError,
    SiteCount,
    TagCount,
    TagMatch,
)

SORTS: tuple[EntrySort, ...] = get_args(EntrySort)
# The sorts that start with the newest, the best, or the largest. The rest go from A.
LARGEST_FIRST = ("created", "updated", "rating", "size", "files")


def list_entries(
    tags: list[str] | None,
    file_tags: list[str] | None,
    tag_match: TagMatch,
    min_rating: int | None,
    site: str | None,
    store: str | None,
    sort: EntrySort,
    descending: bool | None,
    limit: int,
    after: str | None,
) -> EntryListing:
    """Returns a page of the entries that pass the filters, in the order asked for."""
    if sort not in SORTS:
        raise ReferenceStoreError(f"There is no sort {sort}. It is one of: {', '.join(SORTS)}.")
    keep = filters.filters(tags, file_tags, tag_match, min_rating, site)
    downward = sort in LARGEST_FIRST if descending is None else descending
    found = [entry for entry in entries.every_entry(store) if keep.keeps(entry)]
    shown, total, next_after = pages.page(
        found,
        key=lambda entry: _sort_key(entry, sort),
        # An entry with nothing to sort by comes last either way, and ties go by name, then by store.
        descending=[False, downward, False, False],
        limit=limit,
        after=after,
        made_for=f"entries sorted by {sort}, {'descending' if downward else 'ascending'}",
    )
    return EntryListing(entries=[entries.summary_of(entry) for entry in shown], total=total, after=next_after)


def list_tags(store: str | None) -> list[TagCount]:
    """Returns each tag with how many entries and files have it, the most used first.

    Tags that differ only by case are one, spelled as it is first found.
    """
    counts: dict[str, TagCount] = {}
    for entry in entries.every_entry(store):
        for tag in entry.tags:
            _counted(counts, tag).entries += 1
        for file in entry.files:
            for tag in file.tags:
                _counted(counts, tag).files += 1
    return sorted(counts.values(), key=lambda count: (-(count.entries + count.files), names.key(count.tag)))


def list_sites(store: str | None) -> list[SiteCount]:
    """Returns each site the entries link to with how many do, the most first, and on it each group the same way.

    Groups that differ only by case are one, spelled as it is first found.
    """
    known = sites.in_use()
    counts: dict[str, SiteCount] = {}
    groups: dict[str, dict[str, GroupCount]] = {}
    for entry in entries.every_entry(store):
        source = None if entry.url is None else known.source_of(entry.url)
        if source is None:
            continue
        site = counts.setdefault(source.site, SiteCount(site=source.site, entries=0, groups=[]))
        site.entries += 1
        if source.group is not None:
            on_site = groups.setdefault(source.site, {})
            on_site.setdefault(names.key(source.group), GroupCount(group=source.group, entries=0)).entries += 1
    for site in counts.values():
        site.groups = sorted(
            groups.get(site.site, {}).values(), key=lambda count: (-count.entries, names.key(count.group))
        )
    return sorted(counts.values(), key=lambda count: (-count.entries, count.site))


def _sort_key(entry: Entry, sort: EntrySort) -> Key:
    """Returns whether the entry has nothing to sort by, what it is sorted by, its name, and its store."""
    value: str | int | None = {
        "name": names.key(entry.title or entry.name),
        "created": int(entry.created.timestamp()),
        "updated": int(entry.updated.timestamp()),
        "rating": entry.rating,
        "size": entry.size,
        "files": entry.file_count,
        "tags": names.key(", ".join(entry.tags)) or None,
        "store": names.key(entry.store),
    }[sort]
    empty = "" if sort == "tags" else 0
    return [value is None, empty if value is None else value, names.key(entry.name), names.key(entry.store)]


def _counted(counts: dict[str, TagCount], tag: str) -> TagCount:
    return counts.setdefault(names.key(tag), TagCount(tag=tag, entries=0, files=0))
