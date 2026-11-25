"""Pages: a long list returned a part at a time, where `after` carries on where the last part stopped.

`after` holds the place of the last item returned rather than a count, so items added or removed between two calls
don't make the next page skip or repeat any.
"""

import base64
import binascii
import bisect
from collections.abc import Callable
import functools
import hashlib
import json
from typing import Any

from reference_store.models import ReferenceStoreError

# A key is a list of JSON values, so `after` can carry one and compare it with the keys of items read later.
Key = list[Any]


def page[T](
    items: list[T], key: Callable[[T], Key], descending: list[bool], limit: int, after: str | None, made_for: str
) -> tuple[list[T], int, str | None]:
    """Returns the page of items that comes after `after`, how many items there are, and the `after` of the next page.

    Args:
        items: Everything to page through, in any order.
        key: The values that order an item. Together they have to tell it from every other item.
        descending: For each value in the key, whether it goes from the largest.
        limit: How many items a page has at most.
        after: The `after` of the page before, or None for the first page.
        made_for: What the items are and how they are ordered. An `after` only works with the same.

    Raises:
        ReferenceStoreError: `limit` is less than 1, or `after` wasn't made for these items in this order.
    """
    if limit < 1:
        raise ReferenceStoreError(f"limit is how many to return at once, so it has to be 1 or more, not {limit}.")
    order = functools.cmp_to_key(lambda first, second: _compare(first, second, descending))
    ordered = [(key(item), item) for item in items]
    # One sort for each value, from the last to the first, orders the items as `_compare` does, since a sort keeps
    # the order of items that are equal. It is much quicker than a sort that calls `_compare` for every pair.
    try:
        for place in reversed(range(len(descending))):
            ordered.sort(key=lambda pair: pair[0][place], reverse=descending[place])
    except TypeError:
        ordered.sort(key=lambda pair: order(pair[0]))
    start = 0
    if after is not None:
        last = _decoded(after, made_for)
        try:
            start = bisect.bisect_right(ordered, order(last), key=lambda pair: order(pair[0]))
        except (TypeError, ValueError):
            raise _not_made_for(made_for) from None
    shown = ordered[start : start + limit]
    more = start + limit < len(ordered)
    return [item for _, item in shown], len(items), _encoded(shown[-1][0], made_for) if more else None


def _compare(first: Key, second: Key, descending: list[bool]) -> int:
    for one, other, downward in zip(first, second, descending, strict=True):
        if one != other:
            earlier = one > other if downward else one < other
            return -1 if earlier else 1
    return 0


def _encoded(key: Key, made_for: str) -> str:
    text = json.dumps([_mark(made_for), *key], ensure_ascii=False, separators=(",", ":"))
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def _decoded(after: str, made_for: str) -> Key:
    try:
        text = base64.urlsafe_b64decode(after + "=" * (-len(after) % 4)).decode()
        data = json.loads(text)
    except (binascii.Error, UnicodeDecodeError, ValueError):
        raise _not_made_for(made_for) from None
    if not isinstance(data, list) or not data or data[0] != _mark(made_for):
        raise _not_made_for(made_for)
    return data[1:]


def _mark(made_for: str) -> str:
    """Returns a short stand-in for what an `after` was made for, which keeps `after` short."""
    return hashlib.sha256(made_for.encode()).hexdigest()[:6]


def _not_made_for(made_for: str) -> ReferenceStoreError:
    return ReferenceStoreError(
        f"That after isn't from a page of {made_for}. Pass the after of the page before, with the same sort."
    )
