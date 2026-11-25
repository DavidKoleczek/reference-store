"""The stores on this machine: those registered, and the project's own store."""

import json
import os
from pathlib import Path

from reference_store.core import config, disk, names
from reference_store.core.config import Config, StoreRecord
from reference_store.models import ReferenceStoreError, Store

STORE_FILE = ".store.json"
STORE_VERSION = 1
PROJECT_FOLDER = ".reference-store"


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
    if store is not None:
        return [find_store(store)]
    return [each for each in list_stores() if each.available]


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
    path = Path(record.location)
    return Store(
        name=record.name,
        kind="directory",
        location=record.location,
        path=path,
        default=record.name == current.default_store,
        priority_order=record.priority_order,
        available=(path / STORE_FILE).is_file(),
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
