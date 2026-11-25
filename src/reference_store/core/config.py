"""The configuration kept on this machine, in `config.json`, and the locks that keep processes from changing the same
thing at once."""

from collections.abc import Generator
import contextlib
import os
from pathlib import Path
import sys

from filelock import FileLock, Timeout
from pydantic import BaseModel, ValidationError

from reference_store.core import disk
from reference_store.models import ReferenceStoreError

HOME_VARIABLE = "REFERENCE_STORE_HOME"
FOLDER = "reference-store"
CONFIG_FILE = "config.json"
LOCKS = "locks"
LOCK_SECONDS = 30


class StoreRecord(BaseModel):
    """A registered store, as `config.json` has it."""

    name: str
    location: str
    priority_order: int
    push: bool = False


class SiteRule(BaseModel):
    """How to tell a site's links and their groups apart, as `config.json` has it."""

    pattern: str  # a regular expression, with a named group `group` when the site's links have groups


class Config(BaseModel):
    """What `config.json` holds."""

    default_store: str | None = None
    stores: list[StoreRecord] = []
    sites: dict[str, SiteRule | None] = {}  # None turns off a site the library ships


def home() -> Path:
    """Returns the folder everything kept on this machine is in: `REFERENCE_STORE_HOME`, or one in the user's config
    folder."""
    if override := os.environ.get(HOME_VARIABLE):
        return Path(override).expanduser().resolve()
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / FOLDER


@contextlib.contextmanager
def locked(name: str) -> Generator[None]:
    """Holds the lock called `name`, which only one process on the machine can hold at a time, while the block runs.

    Raises:
        ReferenceStoreError: Another process held it for longer than `LOCK_SECONDS`.
    """
    lock = lock_named(name)
    try:
        lock.acquire(timeout=LOCK_SECONDS)
    except Timeout:
        raise ReferenceStoreError(
            f"Another process has been changing the same thing for over {LOCK_SECONDS} seconds. Try again once it is "
            "done."
        ) from None
    try:
        yield
    finally:
        lock.release()


def lock_named(name: str) -> FileLock:
    """Returns the lock called `name`, for a caller that waits for it in its own way."""
    path = home() / LOCKS / f"{name}.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    # One instance per file, so a thread that already holds the lock can take it again, as reading an entry does
    # while the entry is being changed.
    return FileLock(path, is_singleton=True)


def read() -> Config:
    """Returns the configuration, which is empty before anything is saved.

    Raises:
        ReferenceStoreError: `config.json` can't be read as a configuration.
    """
    path = home() / CONFIG_FILE
    text = disk.read_text(path)
    if text is None:
        return Config()
    try:
        return Config.model_validate_json(text)
    except ValidationError as error:
        raise ReferenceStoreError(f"{path} can't be read as a configuration. Fix or delete it.\n{error}") from None


@contextlib.contextmanager
def changing() -> Generator[Config]:
    """Yields the configuration to change, and saves it if the block ends without an error. No other process changes
    it in the meantime."""
    with locked("config"):
        config = read()
        yield config
        disk.write_text(home() / CONFIG_FILE, config.model_dump_json(indent=2) + "\n")
