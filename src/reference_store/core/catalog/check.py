"""The process a read starts once a day: `python -m reference_store.core.catalog.check <store folder>...`."""

import contextlib
from pathlib import Path
import sys

from reference_store.core.catalog import index, upkeep


def main() -> None:
    """Checks the stores in the folders given against the index. One that can't be read is left for the next check."""
    with contextlib.closing(index.connect()) as connection:
        for folder in sys.argv[1:]:
            with contextlib.suppress(OSError):
                upkeep.check_store(connection, Path(folder))


if __name__ == "__main__":
    main()
