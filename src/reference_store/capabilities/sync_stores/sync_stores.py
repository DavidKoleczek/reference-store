"""Syncing stores with GitHub when asked to, where it otherwise happens in the background."""

from reference_store.core import stores
from reference_store.core.remotes import sync
from reference_store.models import ReferenceStoreError, StoreSync


def sync_store(store: str | None) -> list[StoreSync]:
    """Syncs the store named, or every store that is kept on GitHub, and returns how each went."""
    if store is None:
        return [sync.run(each, asked=True) for each in stores.searched(None) if each.push or each.read_only]
    target = stores.find_store(store)
    if not (target.push or target.read_only):
        raise ReferenceStoreError(
            f"The store {target.name} is a folder that isn't pushed anywhere, so there is nothing to sync."
        )
    return [sync.run(target, asked=True)]
