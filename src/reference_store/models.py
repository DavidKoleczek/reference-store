"""The data the library takes and returns."""

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


class App(BaseModel):
    """The app while it is being served."""

    url: str
