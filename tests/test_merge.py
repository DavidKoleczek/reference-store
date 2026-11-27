"""Merging two versions of an `.entry.json` that were changed on different devices."""

from datetime import UTC, datetime
from typing import Any

import pytest

from reference_store.core.entries import EntryRecord
from reference_store.core.remotes import merge

EARLY = datetime(2026, 1, 1, tzinfo=UTC)
LATE = datetime(2026, 1, 2, tzinfo=UTC)
NOTES = {"notes.md": {"description": "Notes.", "tags": ["ux"]}}


def record(updated: datetime = EARLY, **fields: Any) -> EntryRecord:
    return EntryRecord.model_validate({"id": "id-1", "created": EARLY, "updated": updated, **fields})


@pytest.mark.parametrize(
    ("base", "ours", "theirs", "expected"),
    [
        pytest.param(
            {"description": "Old.", "rating": 2},
            {"description": "Ours.", "rating": 2, "source_published_at": EARLY},
            {"description": "Old.", "rating": 5, "url": "https://example.com"},
            {"description": "Ours.", "rating": 5, "url": "https://example.com", "source_published_at": EARLY},
            id="each side's change to a different field is kept",
        ),
        pytest.param(
            {"description": "Old."},
            {"description": "Ours.", "updated": LATE},
            {"description": "Theirs."},
            {"description": "Ours.", "updated": LATE},
            id="a field both changed is the later side's, when that is ours",
        ),
        pytest.param(
            {"description": "Old."},
            {"description": "Ours."},
            {"description": "Theirs.", "updated": LATE},
            {"description": "Theirs.", "updated": LATE},
            id="a field both changed is the later side's, when that is theirs",
        ),
        pytest.param(
            {"title": "Old", "rating": 3},
            {"title": None, "rating": 3},
            {"title": "Old", "rating": None, "updated": LATE},
            {"title": None, "rating": None, "updated": LATE},
            id="a field one side cleared stays cleared",
        ),
        pytest.param(
            {"tags": ["game", "old", "puzzle"]},
            {"tags": ["game", "puzzle", "ours"]},
            {"tags": ["Game", "old", "theirs"]},
            {"tags": ["game", "ours", "theirs"]},
            id="tags each side added are kept, and those either removed are gone",
        ),
        pytest.param(
            {"files": NOTES},
            {"files": {"notes.md": {"description": "Ours.", "tags": ["ux"]}}},
            {
                "files": {
                    "Notes.md": {"description": "Notes.", "tags": ["ux", "market"]},
                    "art/a.png": {"notes": "New."},
                }
            },
            {"files": {"art/a.png": {"notes": "New."}, "notes.md": {"description": "Ours.", "tags": ["ux", "market"]}}},
            id="what is said about a file merges like the entry, and a file one side described is kept",
        ),
        pytest.param(
            {"files": NOTES | {"old.md": {"notes": "Old."}}},
            {"files": {"old.md": {"notes": "Old."}}},
            {"files": {"notes.md": {"description": "Changed.", "tags": ["ux"]}}},
            {"files": {"notes.md": {"description": "Changed.", "tags": ["ux"]}}},
            id="what one side took out is gone, unless the other changed it since",
        ),
        pytest.param(
            None,
            {"description": "Ours.", "tags": ["game"], "id": "id-2"},
            {"title": "Theirs", "tags": ["puzzle"], "updated": LATE},
            {"description": "Ours.", "title": "Theirs", "tags": ["game", "puzzle"], "updated": LATE},
            id="an entry both added has what each said, and the later side's where both did",
        ),
    ],
)
def test_two_versions_of_an_entry_are_merged(
    base: dict[str, Any] | None, ours: dict[str, Any], theirs: dict[str, Any], expected: dict[str, Any]
) -> None:
    merged = merge.merged(None if base is None else record(**base), record(**ours), record(**theirs))
    assert merged == record(**expected)
    assert list(merged.files) == list(record(**expected).files)
