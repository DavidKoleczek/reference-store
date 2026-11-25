"""Sites: where an entry's link points, and its group on that site, such as a GitHub owner, an X user, or a subreddit.

A site's links and their groups are told apart by a pattern. The library ships patterns for some sites, and `sites` in
`config.json` adds others or replaces them, so a site can be added without a new version of the library.
"""

from dataclasses import dataclass
import re
from typing import NamedTuple
from urllib.parse import unquote, urlsplit

from reference_store.core import config, names
from reference_store.models import ReferenceStoreError

GROUP = "group"
# Each is matched, ignoring case, against the start of a link without its scheme and `www.`, such as
# github.com/octocat/hello-world. A lookahead leaves out the pages near the top of a site that are nobody's, such as
# github.com/topics.
DEFAULT_PATTERNS = {
    "github.com": (
        r"github\.com/(?:(?:orgs|users)/)?"
        r"(?!(?:about|collections|explore|features|marketplace|search|settings|sponsors|topics|trending)(?:/|$))"
        r"(?P<group>[^/]+)"
    ),
    "gitlab.com": r"gitlab\.com/(?:(?:groups|users)/)?(?!(?:dashboard|explore|help|search)(?:/|$))(?P<group>[^/]+)",
    "codeberg.org": r"codeberg\.org/(?!(?:explore|user)(?:/|$))(?P<group>[^/]+)",
    "huggingface.co": (
        r"huggingface\.co/(?:(?:collections|datasets|spaces)/)?"
        r"(?!(?:blog|collections|datasets|docs|learn|models|papers|pricing|search|settings|spaces)(?:/|$))"
        r"(?P<group>[^/]+)"
    ),
    "x.com": (
        r"(?:mobile\.)?(?:x|twitter)\.com"
        r"(?:/(?!(?:explore|hashtag|home|i|intent|messages|notifications|search|settings|share)(?:/|$))"
        r"@?(?P<group>[^/]+))?"
    ),
    "bsky.app": r"bsky\.app/profile/(?P<group>[^/]+)",
    "reddit.com": r"(?:old\.)?reddit\.com(?:/(?:r|u|user)/(?P<group>[^/]+))?",
    "youtube.com": r"(?:(?:m\.)?youtube\.com|youtu\.be)(?:/(?:@|(?:c|channel|user)/)(?P<group>[^/]+))?",
    "itch.io": r"(?P<group>[^./]+)\.itch\.io",
    "github.io": r"(?P<group>[^./]+)\.github\.io",
}


class Source(NamedTuple):
    """Where a link points: the site, and its group on the site when the site's links have groups."""

    site: str
    group: str | None


class Sites:
    """The site patterns in use, in the order they are tried."""

    def __init__(self, patterns: dict[str, str]) -> None:
        """Compiles the patterns.

        Raises:
            ReferenceStoreError: A pattern isn't a regular expression.
        """
        self.patterns: dict[str, re.Pattern[str]] = {}
        for site, pattern in patterns.items():
            try:
                self.patterns[site] = re.compile(pattern, re.IGNORECASE)
            except re.error as error:
                raise ReferenceStoreError(
                    f"The pattern for {site} in {config.home() / config.CONFIG_FILE} isn't a regular expression: "
                    f"{error}."
                ) from None

    def source_of(self, url: str) -> Source | None:
        """Returns where a web link points, or None when it isn't one.

        The first pattern that matches the whole host and maybe more names the site, and what it captures as `group`
        is the link's group. A link no pattern matches is on the site its host names, without `www.`.
        """
        try:
            parts = urlsplit(url.strip())
            host = parts.hostname
        except ValueError:
            return None
        if parts.scheme.lower() not in ("http", "https") or not host:
            return None
        host = host.rstrip(".").removeprefix("www.")
        link = f"{host}{unquote(parts.path)}"
        for site, pattern in self.patterns.items():
            match = pattern.match(link)
            if match is not None and match.end() >= len(host):
                return Source(site, match.groupdict().get(GROUP) or None)
        return Source(host, None)


@dataclass(frozen=True)
class SiteFilter:
    """Keeps the links to a site, or to one group on it."""

    sites: Sites
    place: Source

    def keeps(self, url: str | None) -> bool:
        """Returns whether the link points to the site, and to the group when the filter names one."""
        source = None if url is None else self.sites.source_of(url)
        if source is None or source.site != self.place.site:
            return False
        if self.place.group is None:
            return True
        return source.group is not None and names.key(source.group) == names.key(self.place.group)


def wanted(sites: Sites, site: str) -> SiteFilter:
    """Returns the filter that `site` names: a site, such as `github.com`, or a group on it, such as
    `github.com/octocat`. A link to the site or the group works too.

    Raises:
        ReferenceStoreError: It names neither.
    """
    text = site.strip()
    link = text if "://" in text else f"https://{text}"
    source = sites.source_of(link)
    if source is None:
        raise ReferenceStoreError(f"{site} isn't a site, such as github.com.")
    rest = urlsplit(link).path.strip("/")
    if source.group is None and rest:
        if "/" in rest or source.site not in sites.patterns:
            raise ReferenceStoreError(
                f"{site} names neither a site nor a group on one. A site is named on its own, such as github.com, "
                f"and a group after it, such as github.com/octocat. These sites have groups: "
                f"{', '.join(sites.patterns)}."
            )
        source = Source(source.site, unquote(rest))
    return SiteFilter(sites, source)


def in_use() -> Sites:
    """Returns the sites in `config.json`, then those the library ships that it doesn't replace or turn off.

    Raises:
        ReferenceStoreError: A pattern in `config.json` isn't a regular expression.
    """
    configured = {_site_name(site): rule for site, rule in config.read().sites.items()}
    patterns = {site: rule.pattern for site, rule in configured.items() if rule is not None}
    patterns |= {site: pattern for site, pattern in DEFAULT_PATTERNS.items() if site not in configured}
    return Sites(patterns)


def _site_name(site: str) -> str:
    return site.strip().lower().removeprefix("www.")
