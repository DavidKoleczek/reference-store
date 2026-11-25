"""The filters that listing, grep, and glob share: tags, file tags, a lowest rating, and a site."""

from dataclasses import dataclass

from reference_store.core import entries, names, sites
from reference_store.core.sites import SiteFilter
from reference_store.models import Entry, ReferenceStoreError, TagMatch


@dataclass(frozen=True)
class Filters:
    """What an entry needs to be kept. A filter left empty keeps every entry."""

    tags: list[str]
    file_tags: list[str]
    tag_match: TagMatch
    min_rating: int | None
    site: SiteFilter | None

    def keeps(self, entry: Entry) -> bool:
        """Returns whether the entry passes every filter."""
        if self.min_rating is not None and (entry.rating is None or entry.rating < self.min_rating):
            return False
        if self.site is not None and not self.site.keeps(entry.url):
            return False
        if self.tags and not self.has_tags(entry.tags, self.tags):
            return False
        return not self.file_tags or any(self.has_tags(file.tags, self.file_tags) for file in entry.files)

    def has_tags(self, tags: list[str], wanted: list[str]) -> bool:
        """Returns whether the tags hold every one wanted, or one of them when `tag_match` is `any`."""
        held = {names.key(tag) for tag in tags}
        found = (names.key(tag) in held for tag in wanted)
        return any(found) if self.tag_match == "any" else all(found)


def filters(
    tags: list[str] | None,
    file_tags: list[str] | None,
    tag_match: TagMatch,
    min_rating: int | None,
    site: str | None,
) -> Filters:
    """Returns the filters, checked.

    Raises:
        ReferenceStoreError: A tag is empty, `tag_match` is neither `all` nor `any`, the rating is outside 1 to 5, the
            site isn't one, or a site pattern in `config.json` isn't a regular expression.
    """
    if tag_match not in ("all", "any"):
        raise ReferenceStoreError(f"tag_match is all or any, so it can't be {tag_match}.")
    entries.check_rating(min_rating)
    return Filters(
        tags=entries.clean_tags(tags or []),
        file_tags=entries.clean_tags(file_tags or []),
        tag_match=tag_match,
        min_rating=min_rating,
        site=None if site is None else sites.wanted(sites.in_use(), site),
    )
