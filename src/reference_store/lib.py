"""Everything Reference Store does. The CLI and the app are thin wrappers over this module."""

from reference_store.app.server import AppServer
from reference_store.core import stores
from reference_store.models import Store
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


def app_server() -> AppServer:
    """Returns the app's server. `AppServer.open` serves the app in a browser page, and `close` stops it."""
    return AppServer(skill_module.DISTRIBUTION, skill_module.tool_version())


def skill() -> str:
    """Returns the tool's skill, which tells an agent how to use it."""
    return skill_module.tool_skill()


def version() -> str:
    """Returns the installed package's version, from its metadata."""
    return skill_module.tool_version()
