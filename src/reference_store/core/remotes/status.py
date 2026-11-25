"""What is kept about the last sync of a store's clone, in a small file in the clone's `.git` folder.

It is there so that listing stores can say when a store last synced and what went wrong without running `git`, and it
goes when the clone does.
"""

import contextlib
from pathlib import Path

from pydantic import BaseModel, ValidationError

from reference_store.core import disk

FILE = "reference-store.json"


class Status(BaseModel):
    """How a clone's last sync went."""

    synced: float | None = None  # when it was last in step with GitHub
    asked: float | None = None  # when a read last started a sync because the last one was old
    error: str | None = None  # what went wrong the last time, if it did
    left_out: list[str] = []  # what is in the store but can't be pushed


def root_of(store_folder: Path) -> Path:
    """Returns the top of the clone a store's folder is in: the folder, or the one above a project's own store."""
    return store_folder if (store_folder / ".git").is_dir() else store_folder.parent


def read(root: Path) -> Status:
    """Returns what is kept about the clone in `root`, which is nothing before its first sync."""
    try:
        text = disk.read_text(root / ".git" / FILE)
    except OSError:
        return Status()
    if text is None:
        return Status()
    try:
        return Status.model_validate_json(text)
    except ValidationError:
        return Status()


def write(root: Path, status: Status) -> None:
    """Saves what is kept about the clone in `root`. When it can't be saved, the next sync says it again."""
    with contextlib.suppress(OSError):
        disk.write_text(root / ".git" / FILE, status.model_dump_json(indent=2) + "\n")
