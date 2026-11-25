"""The stores on this machine: those registered, and the project's own store."""

from collections.abc import Iterable
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re

from reference_store.core import config, disk, names
from reference_store.core.config import Config, StoreRecord
from reference_store.core.remotes import background, status
from reference_store.models import ReferenceStoreError, Store

STORE_FILE = ".store.json"
STORE_VERSION = 1
PROJECT_FOLDER = ".reference-store"
CLONES = "stores"
GITHUB = re.compile(
    r"(?:https?://github\.com/|git@github\.com:|github\.com/)(?P<repository>[^/\s]+/[^/\s]+?)(?:\.git)?/?"
)
# GitHub blocks a file larger than this.
LARGEST_PUSHED_BYTES = 100 * 1024 * 1024


def list_stores() -> list[Store]:
    """Returns the stores in priority order, starting with the project's store when there is one."""
    current = config.read()
    registered = [store_of(record, current) for record in by_priority(current)]
    project = project_folder()
    if project is None:
        return registered
    same = next((store for store in registered if same_path(store.path, project)), None)
    if same is not None:
        registered.remove(same)
        return [same.model_copy(update={"priority_order": 0}), *registered]
    own = Store(
        name=project.parent.name,
        kind="directory",
        location=project.as_posix(),
        path=project,
        default=False,
        priority_order=0,
        available=True,
    )
    return [own, *registered]


def find_store(name: str) -> Store:
    """Returns the store with that name, the project's own included.

    Raises:
        ReferenceStoreError: There is no such store, or it is not available.
    """
    listed = list_stores()
    store = next((each for each in listed if names.key(each.name) == names.key(name)), None)
    if store is None:
        known = ", ".join(each.name for each in listed) or "none"
        raise ReferenceStoreError(f"There is no store named {name}. The stores are: {known}.")
    if not store.available:
        raise ReferenceStoreError(f"The store {store.name} is not available, since {store.path} can't be reached.")
    return store


def searched(store: str | None) -> list[Store]:
    """Returns the store named, or every store that is available, in priority order.

    Raises:
        ReferenceStoreError: The store named can't be used.
    """
    found = [find_store(store)] if store is not None else [each for each in list_stores() if each.available]
    # Every call that reads or changes a store comes through here, so this is where one that hasn't synced with
    # GitHub in a while is noticed.
    background.read(found)
    return found


def project_folder() -> Path | None:
    """Returns the `.reference-store` folder of the project the current directory is in, if it is in one."""
    here = Path.cwd()
    return next(
        (folder / PROJECT_FOLDER for folder in (here, *here.parents) if (folder / PROJECT_FOLDER).is_dir()), None
    )


def make_store(path: Path) -> None:
    """Makes a folder a store, unless it is one already. The folder is made when it is missing."""
    if path.exists() and not path.is_dir():
        raise ReferenceStoreError(f"{path} is a file, and a store has to be a folder.")
    marker = path / STORE_FILE
    if marker.is_file():
        return
    try:
        disk.write_text(marker, json.dumps({"version": STORE_VERSION}, indent=2) + "\n")
    except OSError as error:
        raise ReferenceStoreError(f"Couldn't make a store at {path}: {error.strerror or error}.") from None


def store_of(record: StoreRecord, current: Config) -> Store:
    """Returns the registered store as callers see it."""
    url = github_url(record.location)
    if url is None:
        path = Path(record.location)
        available = (path / STORE_FILE).is_file()
    else:
        clone = clone_folder(record.name)
        own = clone / PROJECT_FOLDER
        # A project's repository has its store in a folder of it, and any other is a store itself.
        path = own if own.is_dir() and not (clone / STORE_FILE).is_file() else clone
        available = path.is_dir() and (clone / ".git").is_dir()
    synced = record.push or url is not None
    kept = status.read(status.root_of(path)) if synced and available else None
    return Store(
        name=record.name,
        kind="directory" if url is None else "github",
        location=record.location,
        path=path,
        default=record.name == current.default_store,
        priority_order=record.priority_order,
        available=available,
        push=record.push,
        read_only=url is not None and not record.push,
        synced=datetime.fromtimestamp(int(kept.synced), UTC) if kept and kept.synced else None,
        sync_error=kept.error if kept else None,
    )


def github_url(location: str) -> str | None:
    """Returns the repository on GitHub a location names, as the URL it is cloned from, or None for a folder."""
    match = GITHUB.fullmatch(location.strip())
    if match is None:
        return None
    if location.strip().startswith("git@"):
        return f"git@github.com:{match['repository']}.git"
    return f"https://github.com/{match['repository']}"


def clone_folder(name: str) -> Path:
    """Returns where the clone of the GitHub store with that name is kept."""
    return config.home() / CLONES / name


def check_can_change(store: Store) -> None:
    """Raises when a store can only be read.

    Raises:
        ReferenceStoreError: The store is a clone of a repository that isn't pushed to.
    """
    if store.read_only:
        raise ReferenceStoreError(
            f"The store {store.name} is a copy of {store.location} that isn't pushed to, so it can only be read. "
            "Change it in a folder where that repository is checked out, or use another store."
        )


def check_sizes(store: Store, files: Iterable[Path]) -> None:
    """Raises when one of these files is too large for the store.

    Raises:
        ReferenceStoreError: The store is pushed to GitHub, which blocks a file that large.
    """
    if not store.push:
        return
    for file in files:
        try:
            size = file.stat().st_size
        except OSError:
            continue
        if size > LARGEST_PUSHED_BYTES:
            raise ReferenceStoreError(
                f"{file} is over 100 MB, which GitHub refuses, so it can't go in the store {store.name}, which is "
                "pushed there. Put it in a store that isn't."
            )


def record_named(current: Config, name: str) -> StoreRecord:
    """Returns the registered store with that name.

    Raises:
        ReferenceStoreError: No registered store has that name.
    """
    record = next((each for each in current.stores if names.key(each.name) == names.key(name)), None)
    if record is not None:
        return record
    project = project_folder()
    if project is not None and names.key(project.parent.name) == names.key(name):
        raise ReferenceStoreError(
            f"{name} is this project's own store, which isn't registered. Register {project} as a store first."
        )
    if not current.stores:
        raise ReferenceStoreError(f"There is no store named {name}. No stores are registered.")
    known = ", ".join(each.name for each in by_priority(current))
    raise ReferenceStoreError(f"There is no store named {name}. The stores are {known}.")


def by_priority(current: Config) -> list[StoreRecord]:
    """Returns the registered stores in priority order."""
    return sorted(current.stores, key=lambda record: record.priority_order)


def same_path(first: Path, second: Path) -> bool:
    """Returns whether two paths name the same folder, as the system compares them."""
    return os.path.normcase(first) == os.path.normcase(second)
