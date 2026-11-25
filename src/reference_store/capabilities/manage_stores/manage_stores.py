"""Registering stores on this machine, and choosing the default and the order they are searched in."""

from pathlib import Path

from reference_store.core import config, names, stores
from reference_store.core.config import Config, StoreRecord
from reference_store.models import ReferenceStoreError, Store

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
            if stores.same_path(Path(record.location), path):
                raise ReferenceStoreError(f"{path} is already registered, as the store {record.name}.")
        stores.make_store(path)
        record = StoreRecord(
            name=name,
            location=path.as_posix(),
            priority_order=max((each.priority_order for each in current.stores), default=0) + 1,
        )
        current.stores.append(record)
        if default or current.default_store is None:
            current.default_store = name
        return stores.store_of(record, current)


def set_default_store(name: str) -> Store:
    """Makes a registered store the default."""
    with config.changing() as current:
        record = stores.record_named(current, name)
        current.default_store = record.name
        return stores.store_of(record, current)


def set_store_priority(name: str, priority_order: int) -> list[Store]:
    """Gives a registered store a place in the order, and moves the others to make room."""
    with config.changing() as current:
        record = stores.record_named(current, name)
        count = len(current.stores)
        if not 1 <= priority_order <= count:
            raise ReferenceStoreError(
                f"There is no priority {priority_order}. With {count} stores registered, it goes from 1 to {count}."
            )
        ordered = [each for each in stores.by_priority(current) if each is not record]
        ordered.insert(priority_order - 1, record)
        _renumber(current, ordered)
    return stores.list_stores()


def remove_store(name: str) -> None:
    """Unregisters a store, leaving its files as they are."""
    with config.changing() as current:
        record = stores.record_named(current, name)
        _renumber(current, [each for each in stores.by_priority(current) if each is not record])
        if current.default_store == record.name:
            current.default_store = current.stores[0].name if current.stores else None


def _folder_of(location: Path) -> Path:
    """Returns the folder a location registers: the location, or the store in it when it is a project's folder."""
    path = location.expanduser().resolve()
    project = path / stores.PROJECT_FOLDER
    if not (path / stores.STORE_FILE).is_file() and project.is_dir():
        return project
    return path


def _renumber(current: Config, ordered: list[StoreRecord]) -> None:
    for number, record in enumerate(ordered, start=1):
        record.priority_order = number
    current.stores = ordered
