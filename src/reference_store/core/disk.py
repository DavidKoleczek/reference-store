"""Reading and writing the library's own files, so that another process never sees half of one."""

from collections.abc import Callable
import os
from pathlib import Path
import sys
import tempfile
import time

# On Windows a file can't be replaced while another process has it open, and readers hold it only briefly.
ATTEMPTS = 50
PAUSE_SECONDS = 0.02


def _retried[T](action: Callable[[], T]) -> T:
    attempts = ATTEMPTS if sys.platform == "win32" else 1
    for _ in range(attempts - 1):
        try:
            return action()
        except PermissionError:
            time.sleep(PAUSE_SECONDS)
    return action()


def read_text(path: Path) -> str | None:
    """Returns the text of a UTF-8 file, or None when there is no such file."""
    try:
        return _retried(lambda: path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def write_text(path: Path, text: str) -> None:
    """Writes UTF-8 text with `\\n` line endings, by writing a file beside `path` and then putting it in its place.

    The file beside it starts with a dot, so programs that skip the library's files skip it too.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as file:
        file.write(text)
        file.flush()
        os.fsync(file.fileno())
    written = Path(file.name)
    try:
        _retried(lambda: written.replace(path))
    except BaseException:
        written.unlink(missing_ok=True)
        raise
