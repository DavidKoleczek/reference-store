"""Registering stores on this machine, and choosing the default and the order they are searched in."""

from pathlib import Path

from reference_store.core import config, names, stores
from reference_store.core.config import Config, StoreRecord
from reference_store.core.remotes import background, clones, sync
from reference_store.core.remotes.git import GitError
from reference_store.models import ReferenceStoreError, Store


def add_store(name: str, location: str, default: bool = False, push: bool = False) -> Store:
    """Registers a folder or a repository on GitHub as a store, making it a store first when it isn't one."""
    url = stores.github_url(location)
    if url is None and "://" in location:
        raise ReferenceStoreError(f"{location} is neither a folder nor a GitHub repository, so it can't be a store.")
    names.check_name(name, "a store")
    path = stores.clone_folder(name) if url is not None else _folder_of(Path(location))
    kept = url or path.as_posix()
    # A clone is made before the configuration is held, since it can take as long as the repository is large.
    _check_free(config.read(), name, kept)
    if url is not None:
        clones.clone(url, path, push)
    elif push:
        clones.check_folder(path)
    try:
        with config.changing() as current:
            _check_free(current, name, kept)
            if url is None:
                stores.make_store(path)
            record = StoreRecord(
                name=name,
                location=kept,
                priority_order=max((each.priority_order for each in current.stores), default=0) + 1,
                push=push,
            )
            current.stores.append(record)
            if default or current.default_store is None:
                current.default_store = name
            store = stores.store_of(record, current)
    except BaseException:
        if url is not None:
            clones.delete(path)
        raise
    background.changed(store)
    return store


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
    """Unregisters a store, leaving its files as they are. A clone the library made is deleted, since GitHub has what
    was in it."""
    with config.changing() as current:
        record = stores.record_named(current, name)
        store = stores.store_of(record, current)
        clone = stores.clone_folder(record.name) if store.kind == "github" else None
        if clone is not None and store.push and clone.is_dir():
            _check_nothing_waits(store, clone)
        _renumber(current, [each for each in stores.by_priority(current) if each is not record])
        if current.default_store == record.name:
            current.default_store = current.stores[0].name if current.stores else None
    if clone is not None and clone.exists():
        clones.delete(clone)


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


def _check_free(current: Config, name: str, location: str) -> None:
    """Raises when a registered store has the name or the location already."""
    for record in current.stores:
        if names.key(record.name) == names.key(name):
            raise ReferenceStoreError(f"There is already a store named {record.name}. Pick another name.")
        same = (
            record.location.lower() == location.lower()
            if stores.github_url(location)
            else stores.github_url(record.location) is None and stores.same_path(Path(record.location), Path(location))
        )
        if same:
            raise ReferenceStoreError(f"{location} is already registered, as the store {record.name}.")


def _check_nothing_waits(store: Store, clone: Path) -> None:
    """Raises when deleting a store's clone would lose something that isn't on GitHub."""
    try:
        waiting = sync.waiting_changes(clone)
    except GitError as error:
        waiting = f"what it has that GitHub doesn't couldn't be told: {error}"
    if waiting is not None:
        raise ReferenceStoreError(
            f"The store {store.name} can't be removed yet, since {waiting}, and removing it deletes its copy in "
            f"{clone}. Sync it first, or move what can't be pushed to another store."
        )
