"""Stores: the ones registered on this machine, and the project's own store."""

import json
import os
from pathlib import Path

from reference_store.core import config, disk, names
from reference_store.core.config import Config, StoreRecord
from reference_store.models import ReferenceStoreError, Store

STORE_FILE = ".store.json"
STORE_VERSION = 1
PROJECT_FOLDER = ".reference-store"
GITHUB_PREFIXES = ("https://github.com/", "http://github.com/", "git@github.com:", "github.com/")


def add_store(name: str, location: str, default: bool = False) -> Store:
    """Registers a directory store, making the folder a store first when it isn't one."""
    if location.startswith(GITHUB_PREFIXES):
        raise NotImplementedError
    if "://" in location:
        raise ReferenceStoreError(f"{location} is neither a folder nor a GitHub repository, so it can't be a store.")
    names.check_name(name, "a store")
    path = _folder_of(Path(location))
    with config.changing() as current:
        for record in current.stores:
            if names.key(record.name) == names.key(name):
                raise ReferenceStoreError(f"There is already a store named {record.name}. Pick another name.")
            if _same_path(Path(record.location), path):
                raise ReferenceStoreError(f"{path} is already registered, as the store {record.name}.")
        _make_store(path)
        record = StoreRecord(
            name=name,
            location=path.as_posix(),
            priority_order=max((each.priority_order for each in current.stores), default=0) + 1,
        )
        current.stores.append(record)
        if default or current.default_store is None:
            current.default_store = name
        return _store(record, current)


def list_stores() -> list[Store]:
    """Returns the stores in priority order, starting with the project's store when there is one."""
    current = config.read()
    registered = [_store(record, current) for record in _by_priority(current)]
    project = project_folder()
    if project is None:
        return registered
    same = next((store for store in registered if _same_path(store.path, project)), None)
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


def set_default_store(name: str) -> Store:
    """Makes a registered store the default."""
    with config.changing() as current:
        record = _record(current, name)
        current.default_store = record.name
        return _store(record, current)


def set_store_priority(name: str, priority_order: int) -> list[Store]:
    """Gives a registered store a place in the order, and moves the others to make room."""
    with config.changing() as current:
        record = _record(current, name)
        count = len(current.stores)
        if not 1 <= priority_order <= count:
            raise ReferenceStoreError(
                f"There is no priority {priority_order}. With {count} stores registered, it goes from 1 to {count}."
            )
        ordered = [each for each in _by_priority(current) if each is not record]
        ordered.insert(priority_order - 1, record)
        _renumber(current, ordered)
    return list_stores()


def remove_store(name: str) -> None:
    """Unregisters a store, leaving its files as they are."""
    with config.changing() as current:
        record = _record(current, name)
        _renumber(current, [each for each in _by_priority(current) if each is not record])
        if current.default_store == record.name:
            current.default_store = current.stores[0].name if current.stores else None


def project_folder() -> Path | None:
    """Returns the `.reference-store` folder of the project the current directory is in, if it is in one."""
    here = Path.cwd()
    return next(
        (folder / PROJECT_FOLDER for folder in (here, *here.parents) if (folder / PROJECT_FOLDER).is_dir()), None
    )


def _folder_of(location: Path) -> Path:
    """Returns the folder a location registers: the location, or the store in it when it is a project's folder."""
    path = location.expanduser().resolve()
    project = path / PROJECT_FOLDER
    if not (path / STORE_FILE).is_file() and project.is_dir():
        return project
    return path


def _make_store(path: Path) -> None:
    if path.exists() and not path.is_dir():
        raise ReferenceStoreError(f"{path} is a file, and a store has to be a folder.")
    marker = path / STORE_FILE
    if marker.is_file():
        return
    try:
        disk.write_text(marker, json.dumps({"version": STORE_VERSION}, indent=2) + "\n")
    except OSError as error:
        raise ReferenceStoreError(f"Couldn't make a store at {path}: {error.strerror or error}.") from None


def _store(record: StoreRecord, current: Config) -> Store:
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


def _record(current: Config, name: str) -> StoreRecord:
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
    known = ", ".join(each.name for each in _by_priority(current))
    raise ReferenceStoreError(f"There is no store named {name}. The stores are {known}.")


def _by_priority(current: Config) -> list[StoreRecord]:
    return sorted(current.stores, key=lambda record: record.priority_order)


def _renumber(current: Config, ordered: list[StoreRecord]) -> None:
    for number, record in enumerate(ordered, start=1):
        record.priority_order = number
    current.stores = ordered


def _same_path(first: Path, second: Path) -> bool:
    return os.path.normcase(first) == os.path.normcase(second)
