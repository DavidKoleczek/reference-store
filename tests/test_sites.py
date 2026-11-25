"""Where a link points, the site filters that pick links out, and the site patterns in `config.json`."""

import json
from pathlib import Path

import pytest

from reference_store.core import sites
from reference_store.core.sites import DEFAULT_PATTERNS, Sites, Source
from reference_store.models import ReferenceStoreError

SHIPPED = Sites(DEFAULT_PATTERNS)


@pytest.mark.parametrize(
    ("url", "source"),
    [
        ("https://github.com/octocat/hello-world", Source("github.com", "octocat")),
        ("https://www.GitHub.com/Octocat", Source("github.com", "Octocat")),
        ("http://github.com/", Source("github.com", None)),
        ("https://github.com/orgs/some-org/projects", Source("github.com", "some-org")),
        ("https://github.com/topics/godot", Source("github.com", None)),
        ("https://gist.github.com/octocat/1", Source("gist.github.com", None)),
        ("https://twitter.com/someone/status/1", Source("x.com", "someone")),
        ("https://mobile.twitter.com/@someone", Source("x.com", "someone")),
        ("https://x.com/i/web/status/1", Source("x.com", None)),
        ("https://x.com.example.org/someone", Source("x.com.example.org", None)),
        ("https://old.reddit.com/r/godot/comments/1", Source("reddit.com", "godot")),
        ("https://bsky.app/profile/someone.bsky.social/post/1", Source("bsky.app", "someone.bsky.social")),
        ("https://www.youtube.com/@channel-1/videos", Source("youtube.com", "channel-1")),
        ("https://youtu.be/1", Source("youtube.com", None)),
        ("https://huggingface.co/datasets/some-org/data", Source("huggingface.co", "some-org")),
        ("https://huggingface.co/some-org/model-1", Source("huggingface.co", "some-org")),
        ("https://huggingface.co/models", Source("huggingface.co", None)),
        ("https://gitlab.com/group/subgroup/project", Source("gitlab.com", "group")),
        ("https://someone.itch.io/game-1", Source("itch.io", "someone")),
        ("https://itch.io/games", Source("itch.io", None)),
        ("https://example.com.:8080/a", Source("example.com", None)),
        ("ftp://example.com/file", None),
        ("mailto:someone@example.com", None),
        ("example.com/a", None),
        ("https://[bad", None),
    ],
)
def test_a_link_points_to_a_site_and_to_its_group_on_sites_that_have_groups(url: str, source: Source | None) -> None:
    assert SHIPPED.source_of(url) == source


@pytest.mark.parametrize(
    ("site", "kept", "left_out"),
    [
        ("github.com", "https://github.com/octocat/a", "https://gist.github.com/octocat/1"),
        ("www.github.com/", "https://github.com/octocat/a", "https://gitlab.com/octocat/a"),
        ("github.com/OCTOCAT", "https://github.com/octocat/a", "https://github.com/someone/a"),
        ("twitter.com", "https://x.com/someone/status/1", "https://example.com/x.com"),
        ("https://x.com/someone/status/2", "https://twitter.com/Someone/status/1", "https://x.com/i/web/status/1"),
        ("reddit.com/r/godot", "https://reddit.com/r/godot/comments/1", "https://reddit.com/r/gamedev"),
        ("itch.io/someone", "https://someone.itch.io/game-1", "https://itch.io/games"),
    ],
)
def test_a_site_filter_keeps_the_links_to_that_site_or_group(site: str, kept: str, left_out: str) -> None:
    wanted = sites.wanted(SHIPPED, site)
    assert (wanted.keeps(kept), wanted.keeps(left_out), wanted.keeps(None)) == (True, False, False)


@pytest.mark.parametrize("site", ["example.com/blog", "github.com/topics/godot", "https://[bad"])
def test_a_site_filter_that_names_no_site_or_group_is_refused(site: str) -> None:
    with pytest.raises(ReferenceStoreError):
        sites.wanted(SHIPPED, site)


def test_config_adds_sites_replaces_and_turns_off_shipped_ones_and_comes_first(workspace: Path) -> None:
    configured = {
        "docs.example.com": {"pattern": r"docs\.example\.com/(?P<group>[^/]+)"},
        "github.com": {"pattern": r"github\.com/[^/]+/(?P<group>[^/]+)"},
        "www.X.com": None,
        "example.com": {"pattern": r"(?:[^/]+\.)?example\.(?:com|org)"},
    }
    home = workspace.parent / "home"
    home.mkdir()
    (home / "config.json").write_text(json.dumps({"sites": configured}), encoding="utf-8")
    known = sites.in_use()
    assert list(known.patterns)[:4] == ["docs.example.com", "github.com", "example.com", "gitlab.com"]
    assert known.source_of("https://docs.example.com/guide-1/a") == Source("docs.example.com", "guide-1")
    assert known.source_of("https://blog.example.org/a") == Source("example.com", None)
    assert known.source_of("https://github.com/octocat/hello-world") == Source("github.com", "hello-world")
    assert known.source_of("https://twitter.com/someone") == Source("twitter.com", None)
    assert known.source_of("https://someone.itch.io/game-1") == Source("itch.io", "someone")

    (home / "config.json").write_text(json.dumps({"sites": {"bad.com": {"pattern": "(unclosed"}}}), encoding="utf-8")
    with pytest.raises(ReferenceStoreError, match=r"bad\.com in .*config\.json isn't a regular expression"):
        sites.in_use()
