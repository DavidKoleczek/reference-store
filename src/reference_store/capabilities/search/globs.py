"""Glob patterns, matched against a file's path starting with its entry's name, such as game-1/screenshots/menu.png."""

import glob
import re

from reference_store.core import names
from reference_store.models import ReferenceStoreError


def compiled(pattern: str) -> re.Pattern[str]:
    """Returns a glob pattern as a regular expression that matches the same paths, whatever their case.

    `*` matches within a name, `**` any number of folders, `?` one character, and `[...]` one of the characters in it.
    Each of them matches names that start with a dot too.

    Raises:
        ReferenceStoreError: The pattern is empty.
    """
    cleaned = names.slashed(pattern)
    if not cleaned:
        raise ReferenceStoreError("A glob pattern can't be empty. ** matches every file.")
    return re.compile(glob.translate(cleaned, recursive=True, include_hidden=True, seps="/"), re.IGNORECASE)


def matches(pattern: re.Pattern[str], entry: str, path: str) -> bool:
    """Returns whether a file's path, starting with its entry's name, matches a pattern from `compiled`."""
    return pattern.match(f"{entry}/{path}") is not None
