"""What the app remembers, such as its theme, pane sizes, and sorts, kept in `app.json` in the configuration folder,
since the view's address changes from one run to the next and the browser would forget it."""

import json
from typing import Any

from reference_store.core import config, disk
from reference_store.models import ReferenceStoreError

SETTINGS_FILE = "app.json"
# Far past what the view keeps, and short of filling the disk.
MAX_BYTES = 256 * 1024


def read_settings() -> dict[str, Any]:
    """Returns what the app remembers, which is empty before it saves anything or once the file can't be read.

    The view fills in what is missing, so a view from another version reads it too.
    """
    text = disk.read_text(config.home() / SETTINGS_FILE)
    try:
        settings = json.loads(text) if text is not None else {}
    except json.JSONDecodeError:
        return {}
    return settings if isinstance(settings, dict) else {}


def save_settings(settings: dict[str, Any]) -> None:
    """Keeps what the app remembers, in place of what it kept before.

    Raises:
        ReferenceStoreError: It is larger than the app keeps.
    """
    text = json.dumps(settings, indent=2) + "\n"
    if len(text.encode()) > MAX_BYTES:
        raise ReferenceStoreError(f"The app's settings are larger than {MAX_BYTES // 1024} KB, so they weren't kept.")
    disk.write_text(config.home() / SETTINGS_FILE, text)
