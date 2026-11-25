"""Glob patterns, matched against a file's path starting with its entry's name."""

import pytest

from reference_store.capabilities.search import globs
from reference_store.models import ReferenceStoreError


@pytest.mark.parametrize(
    ("pattern", "path", "matched"),
    [
        ("**/*.md", "game-1/notes.md", True),
        ("**/*.md", "game-1/docs/old/notes.md", True),
        ("**/*.md", "game-1/.notes.md", True),
        ("**/*.md", "game-1/notes.md.bak", False),
        ("GAME-1/Screenshots/*", "game-1/screenshots/menu.png", True),
        ("game-1/screenshots/*", "game-1/screenshots/captures/level-1.png", False),
        ("game-1/**", "game-1/screenshots/captures/level-1.png", True),
        ("game-1/**/*.png", "game-1/menu.png", True),
        ("*", "game-1/menu.png", False),
        ("*/*", "game-1/menu.png", True),
        ("**", "game-1/menu.png", True),
        ("game-?/menu.png", "game-2/menu.png", True),
        ("game-[12]/*", "game-3/menu.png", False),
        ("game-1\\screenshots\\*", "game-1/screenshots/menu.png", True),
        ("/game-1/menu.png/", "game-1/menu.png", True),
        ("game-1/a[b.png", "game-1/a[b.png", True),
        ("game 1 (2024)/*.png", "Game 1 (2024)/menu.png", True),
    ],
)
def test_a_pattern_matches_paths_as_a_glob_whatever_their_case(pattern: str, path: str, matched: bool) -> None:
    entry, _, inside = path.partition("/")
    assert globs.matches(globs.compiled(pattern), entry, inside) is matched


def test_an_empty_pattern_is_refused() -> None:
    with pytest.raises(ReferenceStoreError, match="can't be empty"):
        globs.compiled(" / ")
