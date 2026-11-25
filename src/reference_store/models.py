"""The data the library takes and returns."""

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class ReferenceStoreError(Exception):
    """A failure the caller can act on. Its message says what went wrong and how to fix it."""


class NotGiven:
    """The type of `NOT_GIVEN`: an argument left out, which keeps what is there, where None would clear it."""

    def __repr__(self) -> str:
        return "NOT_GIVEN"


NOT_GIVEN = NotGiven()


class Store(BaseModel):
    """A place that holds entries: a directory, or a GitHub repository."""

    name: str
    kind: Literal["directory", "github"]
    location: str
    path: Path  # where its files are on this machine
    default: bool
    priority_order: int  # 1 is the highest, and 0 is the project's store
    available: bool  # False when it can't be reached, such as a NAS that is offline


class NewPreview(BaseModel):
    """An image to make an entry's preview."""

    source: Path | None = None  # an image anywhere on the machine
    file: str | None = None  # or the path of one of the entry's files
    url: str | None = None  # where the image came from


class NewFile(BaseModel):
    """A file or a folder to copy or move into an entry, and what to say about it."""

    source: Path  # a file or a folder anywhere on the machine
    path: str | None = None  # where it goes in the entry
    description: str = ""
    notes: str = ""
    tags: list[str] | None = None
    move: bool = False


class Preview(BaseModel):
    """The one image that stands for an entry."""

    path: Path  # the image on this machine
    url: str | None


class EntryFile(BaseModel):
    """A file in an entry, and what was said about it."""

    path: str  # inside the entry, such as screenshots/menu.png
    full_path: Path  # on this machine
    size: int
    modified: datetime
    description: str
    notes: str
    tags: list[str]


class EntrySummary(BaseModel):
    """One reference, without its files."""

    id: str  # stays the same when the entry is renamed or moved
    name: str
    title: str | None  # shown in place of the name
    store: str
    description: str
    url: str | None
    tags: list[str]
    notes: str
    rating: int | None  # 1 to 5
    preview: Preview | None
    file_count: int
    size: int  # of all its files, in bytes
    created: datetime
    updated: datetime


class Entry(EntrySummary):
    """One reference, with its files."""

    folder: Path  # where its files are on this machine
    files: list[EntryFile]


TagMatch = Literal["all", "any"]
EntrySort = Literal["name", "created", "updated", "rating", "size", "files", "tags", "store"]


class EntryListing(BaseModel):
    """A page of entries."""

    entries: list[EntrySummary]
    total: int
    after: str | None  # None on the last page


class TagCount(BaseModel):
    """A tag, and how many entries and files have it."""

    tag: str
    entries: int
    files: int


class GroupCount(BaseModel):
    """A group on a site that entries link to, and how many do."""

    group: str  # such as an owner on GitHub, a user on X, or a subreddit
    entries: int


class SiteCount(BaseModel):
    """A site entries link to, and how many do."""

    site: str  # such as github.com
    entries: int
    groups: list[GroupCount]


GrepField = Literal[
    "name",
    "title",
    "description",
    "url",
    "tags",
    "notes",
    "file_descriptions",
    "file_notes",
    "file_tags",
    "file_contents",
]


class GrepMatch(BaseModel):
    """A line or a value that matched."""

    field: GrepField
    path: str | None  # the file, for the fields about files
    full_path: Path | None  # the same file on this machine
    line: int | None  # for file_contents, counting from 1
    text: str  # the line or value that matched


class GrepResult(BaseModel):
    """An entry that matched, and its first matches."""

    entry: EntrySummary
    matches: list[GrepMatch]  # the first matches_per_entry of them
    match_count: int


class GrepListing(BaseModel):
    """A page of entries that matched."""

    results: list[GrepResult]
    total: int
    after: str | None  # None on the last page


class FileMatch(EntryFile):
    """A file whose path matched, and its entry."""

    entry: str
    store: str


class FileListing(BaseModel):
    """A page of files."""

    files: list[FileMatch]
    total: int
    after: str | None  # None on the last page


class App(BaseModel):
    """The app while it is being served."""

    url: str
