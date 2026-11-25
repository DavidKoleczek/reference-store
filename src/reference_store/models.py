"""The data the library takes and returns."""

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class ReferenceStoreError(Exception):
    """A failure the caller can act on. Its message says what went wrong and how to fix it."""


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


class App(BaseModel):
    """The app while it is being served."""

    url: str
