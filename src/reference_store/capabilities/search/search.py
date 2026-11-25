"""Finding what the stores hold: entries by what they say and what their files hold, and files by their paths."""

import codecs
from collections.abc import Iterator
from pathlib import Path
import re
from typing import get_args

from reference_store.capabilities.search import globs
from reference_store.core import entries, filters, names, pages
from reference_store.core.catalog import catalog
from reference_store.models import (
    Entry,
    EntryFile,
    FileListing,
    GrepField,
    GrepListing,
    GrepMatch,
    GrepResult,
    ReferenceStoreError,
    TagMatch,
)

FIELDS: tuple[GrepField, ...] = get_args(GrepField)
# Enough of a file to tell text from an image or a video before reading the rest of it.
SNIFF_BYTES = 8192
# A longer line, such as one of a saved page's HTML, is cut to the part around its match.
LINE_LIMIT = 300


def grep_entries(
    pattern: str,
    fields: list[GrepField] | None,
    glob: str | None,
    ignore_case: bool,
    tags: list[str] | None,
    file_tags: list[str] | None,
    tag_match: TagMatch,
    min_rating: int | None,
    site: str | None,
    store: str | None,
    matches_per_entry: int,
    limit: int,
    after: str | None,
) -> GrepListing:
    """Returns a page of the entries with a line or a value that matches `pattern`, sorted by name."""
    try:
        regex = re.compile(pattern, re.IGNORECASE if ignore_case else 0)
    except re.error as error:
        raise ReferenceStoreError(f"{pattern!r} isn't a regular expression: {error}.") from None
    looked_in = _fields(fields)
    if matches_per_entry < 0:
        raise ReferenceStoreError(f"matches_per_entry can't be less than 0, so it can't be {matches_per_entry}.")
    paths = None if glob is None else globs.compiled(glob)
    keep = filters.filters(tags, file_tags, tag_match, min_rating, site)
    results: list[GrepResult] = []
    with catalog.reading() as held:
        for entry in held.entries(keep, store):
            files = [
                file
                for file in entry.files
                if keep.keeps_file(file) and (paths is None or globs.matches(paths, entry.name, file.path))
            ]
            shown: list[GrepMatch] = []
            count = 0
            for match in _matches(entry, files, looked_in, regex):
                count += 1
                if len(shown) < matches_per_entry:
                    shown.append(match)
            if count:
                results.append(GrepResult(entry=entries.summary_of(entry), matches=shown, match_count=count))
    page, total, next_after = pages.page(
        results,
        key=lambda result: [
            names.key(result.entry.title or result.entry.name),
            names.key(result.entry.name),
            names.key(result.entry.store),
        ],
        descending=[False, False, False],
        limit=limit,
        after=after,
        made_for="entries that match, sorted by name",
    )
    return GrepListing(results=page, total=total, after=next_after)


def glob_files(
    pattern: str,
    file_tags: list[str] | None,
    tags: list[str] | None,
    tag_match: TagMatch,
    min_rating: int | None,
    site: str | None,
    store: str | None,
    limit: int,
    after: str | None,
) -> FileListing:
    """Returns a page of the files whose path, starting with their entry's name, matches `pattern`."""
    paths = globs.compiled(pattern)
    keep = filters.filters(tags, file_tags, tag_match, min_rating, site)
    with catalog.reading() as held:
        found = held.files(keep, store, lambda entry, path: globs.matches(paths, entry, path))
    shown, total, next_after = pages.page(
        found,
        # Entries that share a name in two stores keep their files apart.
        key=lambda file: [names.key(file.entry), names.key(file.store), entries.path_order(file.path)],
        descending=[False, False, False],
        limit=limit,
        after=after,
        made_for="files in the order of their paths",
    )
    return FileListing(files=shown, total=total, after=next_after)


def _fields(fields: list[GrepField] | None) -> list[GrepField]:
    """Returns the fields to look in, in the order of `GrepField`, which is every one when none are given."""
    if not fields:
        return list(FIELDS)
    unknown = next((field for field in fields if field not in FIELDS), None)
    if unknown is not None:
        raise ReferenceStoreError(f"There is no field {unknown}. A field is one of: {', '.join(FIELDS)}.")
    return [field for field in FIELDS if field in fields]


def _matches(
    entry: Entry, files: list[EntryFile], fields: list[GrepField], regex: re.Pattern[str]
) -> Iterator[GrepMatch]:
    """Yields each line or value that matches, field by field, and for the fields about files, file by file."""
    for field in fields:
        if not field.startswith("file_"):
            for value in _entry_values(entry, field):
                found = regex.search(value)
                if found is not None:
                    yield GrepMatch(field=field, path=None, full_path=None, line=None, text=_shown(value, found))
            continue
        for file in files:
            lines = _text_lines(file.full_path) if field == "file_contents" else enumerate(_file_values(file, field))
            for number, value in lines:
                found = regex.search(value)
                if found is not None:
                    yield GrepMatch(
                        field=field,
                        path=file.path,
                        full_path=file.full_path,
                        line=number if field == "file_contents" else None,
                        text=_shown(value, found),
                    )


def _entry_values(entry: Entry, field: GrepField) -> list[str]:
    """Returns what an entry has in a field, a value or a line at a time."""
    if field == "name":
        return [entry.name]
    if field == "title":
        return [entry.title] if entry.title else []
    if field == "description":
        return entry.description.splitlines()
    if field == "url":
        return [entry.url] if entry.url else []
    if field == "tags":
        return entry.tags
    return entry.notes.splitlines()


def _file_values(file: EntryFile, field: GrepField) -> list[str]:
    """Returns what a file has in a field about files other than its contents, a value or a line at a time."""
    if field == "file_descriptions":
        return file.description.splitlines()
    if field == "file_notes":
        return file.notes.splitlines()
    return file.tags


def _text_lines(path: Path) -> Iterator[tuple[int, str]]:
    """Yields each line of a file with its number, counting from 1, when the file reads as UTF-8 text.

    A file is text when its start has no null byte and is UTF-8. A byte later on that isn't reads as a replacement
    character, so one odd byte doesn't hide a whole file.
    """
    try:
        with path.open("rb") as raw:
            head = raw.read(SNIFF_BYTES)
        if b"\x00" in head:
            return
        try:
            # Only a head cut short of the whole file can end partway through a character.
            codecs.getincrementaldecoder("utf-8")().decode(head, final=len(head) < SNIFF_BYTES)
        except UnicodeDecodeError:
            return
        with path.open(encoding="utf-8-sig", errors="replace") as text:
            for number, line in enumerate(text, start=1):
                yield number, line.rstrip("\n")
    except OSError:
        return


def _shown(text: str, found: re.Match[str]) -> str:
    """Returns the text, or the part of a long one around the match, with ... where it was cut."""
    if len(text) <= LINE_LIMIT:
        return text
    start = max(0, min(found.start() - LINE_LIMIT // 3, len(text) - LINE_LIMIT))
    end = start + LINE_LIMIT
    return f"{'...' if start else ''}{text[start:end]}{'...' if end < len(text) else ''}"
