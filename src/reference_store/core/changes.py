"""What follows a change to an entry, whichever call made it."""

from reference_store.core.catalog import catalog
from reference_store.core.remotes import background
from reference_store.models import Store


def made(store: Store, name: str) -> None:
    """Tells the index that the entry with that name in a store was added, changed, or removed, and starts the sync of
    a store that is pushed to GitHub."""
    catalog.changed(store, name)
    background.changed(store)
