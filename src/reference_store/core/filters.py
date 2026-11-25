"""The filters that listing, grep, and glob share: tags, file tags, a lowest rating, and sites."""

from dataclasses import dataclass

from reference_store.core import entries, names
from reference_store.core import sites as site_rules
from reference_store.core.sites import SiteFilter, Sites
from reference_store.models import Entry, EntryFile, EntrySummary, ReferenceStoreError, TagMatch


@dataclass(frozen=True)
class Filters:
    """What an entry needs to be kept. A filter left empty keeps every entry."""

    tags: list[str]
    file_tags: list[str]
    tag_match: TagMatch
    min_rating: int | None
    sites: list[SiteFilter]
    without_tags: bool
    # The sites in use, which tell whether a link points to one, when only entries that link to none are kept.
    without_site: Sites | None

    def keeps(self, entry: Entry) -> bool:
        """Returns whether the entry passes every filter."""
        if not self.keeps_summary(entry):
            return False
        return any(self.keeps_file(file) for file in entry.files) if self.file_tags else True

    def keeps_summary(self, entry: EntrySummary) -> bool:
        """Returns whether the entry passes the filters that are about the entry, and not about its files."""
        if self.min_rating is not None and (entry.rating is None or entry.rating < self.min_rating):
            return False
        if self.sites and not any(site.keeps(entry.url) for site in self.sites):
            return False
        if self.without_site is not None and entry.url and self.without_site.source_of(entry.url) is not None:
            return False
        if self.without_tags and entry.tags:
            return False
        return not self.tags or self.has_tags(entry.tags, self.tags)

    def keeps_file(self, file: EntryFile) -> bool:
        """Returns whether a file has the file tags, which every file does when there are none."""
        return self.keeps_file_tags(file.tags)

    def keeps_file_tags(self, tags: list[str]) -> bool:
        """Returns whether a file with these tags has the file tags."""
        return not self.file_tags or self.has_tags(tags, self.file_tags)

    @property
    def about_entries(self) -> bool:
        """Whether a filter that is about the entry, and not about its files, is set."""
        return bool(
            self.min_rating is not None or self.sites or self.tags or self.without_tags or self.without_site is not None
        )

    def has_tags(self, tags: list[str], wanted: list[str]) -> bool:
        """Returns whether the tags hold every one wanted, or one of them when `tag_match` is `any`."""
        held = {names.key(tag) for tag in tags}
        found = (names.key(tag) in held for tag in wanted)
        return any(found) if self.tag_match == "any" else all(found)


EVERYTHING = Filters(
    tags=[], file_tags=[], tag_match="all", min_rating=None, sites=[], without_tags=False, without_site=None
)


def filters(
    tags: list[str] | None,
    file_tags: list[str] | None,
    tag_match: TagMatch,
    min_rating: int | None,
    sites: list[str] | None,
    without_tags: bool,
    without_site: bool,
) -> Filters:
    """Returns the filters, checked.

    Raises:
        ReferenceStoreError: A tag is empty, `tag_match` is neither `all` nor `any`, the rating is outside 1 to 5, a
            site isn't one, a site pattern in `config.json` isn't a regular expression, or a filter asks for entries
            that have something and another for entries without it.
    """
    if tag_match not in ("all", "any"):
        raise ReferenceStoreError(f"tag_match is all or any, so it can't be {tag_match}.")
    entries.check_rating(min_rating)
    kept_tags = entries.clean_tags(tags or [])
    if kept_tags and without_tags:
        raise ReferenceStoreError("without_tags keeps the entries with no tags, so it can't go with tags.")
    if sites and without_site:
        raise ReferenceStoreError("without_site keeps the entries that link to no site, so it can't go with sites.")
    known = site_rules.in_use() if sites or without_site else None
    return Filters(
        tags=kept_tags,
        file_tags=entries.clean_tags(file_tags or []),
        tag_match=tag_match,
        min_rating=min_rating,
        sites=[site_rules.wanted(known, site) for site in sites or []] if known is not None else [],
        without_tags=without_tags,
        without_site=known if without_site else None,
    )
