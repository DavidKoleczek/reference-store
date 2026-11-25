"""The process that syncs stores with GitHub in the background: `python -m reference_store.core.remotes.job <store>...`."""

import contextlib
import sys

from reference_store.core import stores
from reference_store.core.remotes import sync
from reference_store.models import ReferenceStoreError


def main() -> None:
    """Syncs the stores named. One that is gone or out of reach by now is left for the next sync."""
    for name in sys.argv[1:]:
        with contextlib.suppress(ReferenceStoreError, OSError):
            store = stores.find_store(name)
            if store.push or store.read_only:
                sync.run(store, asked=False)


if __name__ == "__main__":
    main()
