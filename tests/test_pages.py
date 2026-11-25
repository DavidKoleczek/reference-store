"""Returning an ordered list a page at a time."""

import itertools

import pytest

from reference_store.core import pages
from reference_store.models import ReferenceStoreError

# A size, then a name that tells apart items of the same size.
ITEMS = [(3, "c"), (1, "b"), (2, "a"), (3, "a"), (1, "a"), (2, "b"), (3, "b")]


def all_pages(items: list[tuple[int, str]], limit: int, descending: list[bool]) -> list[tuple[int, str]]:
    shown: list[tuple[int, str]] = []
    after = None
    while True:
        page, total, after = pages.page(items, list, descending, limit, after, "items")
        assert total == len(items)
        shown.extend(page)
        if after is None:
            return shown


@pytest.mark.parametrize(
    ("limit", "descending"),
    list(itertools.product([1, 2, 3, 7, 100], [[False, False], [True, False], [False, True], [True, True]])),
)
def test_pages_hold_every_item_once_in_order(limit: int, descending: list[bool]) -> None:
    expected = sorted(ITEMS, key=lambda item: item[1], reverse=descending[1])
    expected.sort(key=lambda item: item[0], reverse=descending[0])
    assert all_pages(ITEMS, limit, descending) == expected


def test_the_next_page_carries_on_from_the_last_item_shown_even_when_items_change() -> None:
    first, _, after = pages.page(ITEMS, list, [False, False], 3, None, "items")
    assert first == [(1, "a"), (1, "b"), (2, "a")]
    changed = [item for item in ITEMS if item not in first] + [(0, "z"), (2, "aa")]
    second, total, _ = pages.page(changed, list, [False, False], 3, after, "items")
    assert (second, total) == ([(2, "aa"), (2, "b"), (3, "a")], 6)


@pytest.mark.parametrize("after", ["not-a-page", "", "W10", "WyJ4Il0"])
def test_an_after_from_elsewhere_is_refused(after: str) -> None:
    _, _, made = pages.page(ITEMS, list, [False, False], 2, None, "other items")
    for each in (after, made):
        with pytest.raises(ReferenceStoreError, match="isn't from a page of items"):
            pages.page(ITEMS, list, [False, False], 2, each, "items")
