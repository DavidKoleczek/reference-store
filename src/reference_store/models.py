"""The data the library takes and returns."""

from pydantic import BaseModel


class ReferenceStoreError(Exception):
    """A failure the caller can act on. Its message says what went wrong and how to fix it."""


class App(BaseModel):
    """The app while it is being served."""

    url: str
