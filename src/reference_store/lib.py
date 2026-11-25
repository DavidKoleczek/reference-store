"""Everything Reference Store does. The CLI and the app are thin wrappers over this module."""

from datetime import datetime

from reference_store.app.server import AppServer
from reference_store.core import entries, stores
from reference_store.models import Entry, NewPreview, Store
from reference_store.skill import skill as skill_module


def add_store(name: str, location: str, default: bool = False) -> Store:
    """Registers a store on this machine.

    `location` is a folder. An empty or missing folder becomes a new store, and one that already holds a store is
    connected as it is. A folder with other things in it becomes a store too, and they are left alone. A project's
    folder, one with a `.reference-store` store in it, registers that store.

    The first store added is the default, and a new store gets the lowest priority.

    Raises:
        ReferenceStoreError: The name breaks a rule or is taken, the folder is registered already, or it can't be made
            into a store.
    """
    return stores.add_store(name, location, default)


def list_stores() -> list[Store]:
    """Returns the stores in priority order.

    Inside a project that has its own store, that store comes first, with a `priority_order` of 0.
    """
    return stores.list_stores()


def set_default_store(name: str) -> Store:
    """Makes a registered store the default, which is where entries are added when no store is given.

    Raises:
        ReferenceStoreError: There is no registered store with that name.
    """
    return stores.set_default_store(name)


def set_store_priority(name: str, priority_order: int) -> list[Store]:
    """Gives a registered store a place in the order, where 1 is the highest, and returns the stores.

    The other stores shift to make room, so no two share a `priority_order`.

    Raises:
        ReferenceStoreError: There is no registered store with that name, or no such place.
    """
    return stores.set_store_priority(name, priority_order)


def remove_store(name: str) -> None:
    """Unregisters a store. Nothing in it is deleted.

    When it was the default, the store with the highest priority left becomes the default.

    Raises:
        ReferenceStoreError: There is no registered store with that name.
    """
    stores.remove_store(name)


def add_entry(
    name: str,
    title: str | None = None,
    description: str = "",
    url: str | None = None,
    tags: list[str] | None = None,
    notes: str = "",
    rating: int | None = None,
    preview: NewPreview | None = None,
    created: datetime | None = None,
    store: str | None = None,
) -> Entry:
    """Adds an entry: one reference, such as a repo, a website, or a game with its screenshots.

    It only saves what it is given, and never fetches anything. `name` is the name of the entry's folder, and `title`
    is for a title the name can't be, such as one with a colon. Tags that differ only by case are the same tag.

    A preview's `source` is copied into the entry. `created` keeps the date of a reference that was saved somewhere
    else before, and is now when left out.

    Without `store`, it goes in the project's store when there is one, and in the default store otherwise.

    Raises:
        ReferenceStoreError: The name breaks a rule or is taken in the store, the rating is outside 1 to 5, the
            preview can't be one, or there is no store to add it to.
    """
    return entries.add_entry(name, title, description, url, tags, notes, rating, preview, created, store)


def get_entry(name: str, store: str | None = None) -> Entry:
    """Returns an entry and its files, including files put in its folder by hand.

    Without `store`, it comes from the store with the highest priority that has an entry with that name.

    Raises:
        ReferenceStoreError: There is no entry with that name, or the store named can't be used.
    """
    return entries.get_entry(name, store)


def app_server() -> AppServer:
    """Returns the app's server. `AppServer.open` serves the app in a browser page, and `close` stops it."""
    return AppServer(skill_module.DISTRIBUTION, skill_module.tool_version())


def skill() -> str:
    """Returns the tool's skill, which tells an agent how to use it."""
    return skill_module.tool_skill()


def version() -> str:
    """Returns the installed package's version, from its metadata."""
    return skill_module.tool_version()
