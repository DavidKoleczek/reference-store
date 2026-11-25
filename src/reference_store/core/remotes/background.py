"""Starting the sync of a store with GitHub in a process of its own, so that no call waits for the network.

A change to a store that is pushed starts one. So does a read of a store whose last sync is old or failed, which is
how a device that only reads sees what the others pushed, and how what was changed with no network gets pushed.
"""

import time

from reference_store.core import detached
from reference_store.core.remotes import status
from reference_store.models import Store

SYNC_EVERY_SECONDS = 3 * 60 * 60
# A sync a read started that didn't finish, such as with no network, is started again only after this long, so that
# not every read starts one.
ASK_AGAIN_SECONDS = 30 * 60
JOB_MODULE = "reference_store.core.remotes.job"


def changed(store: Store) -> None:
    """Starts the sync of a store that is pushed, after a change to it."""
    if store.push:
        detached.start(JOB_MODULE, [store.name])


def read(stores: list[Store]) -> None:
    """Starts the sync of each of these stores that is due one."""
    due: list[str] = []
    now = time.time()
    for store in stores:
        if not (store.push or store.read_only) or not is_due(store, now):
            continue
        root = status.root_of(store.path)
        kept = status.read(root)
        if now - (kept.asked or 0) > ASK_AGAIN_SECONDS:
            status.write(root, kept.model_copy(update={"asked": now}))
            due.append(store.name)
    if due:
        detached.start(JOB_MODULE, due)


def is_due(store: Store, now: float) -> bool:
    """Returns whether a store should sync with GitHub without anything new to push: its last sync is old, or failed,
    such as with no network."""
    return store.synced is None or store.sync_error is not None or now - store.synced.timestamp() > SYNC_EVERY_SECONDS
