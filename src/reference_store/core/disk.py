"""Reading and writing the library's own files, so that another process never sees half of one."""

from collections.abc import Callable
import os
from pathlib import Path
import re
import secrets
import sys
import time

# On Windows a file can't be replaced while another process has it open, and readers hold it only briefly.
ATTEMPTS = 50
PAUSE_SECONDS = 0.02
# As long as `.entry.json`, `.store.json`, and `config.json`, so writing one never makes a longer path than the file.
TEMPORARY = re.compile(r"\.[0-9a-f]{6}\.tmp")


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

    The file beside it is named as `TEMPORARY` says. It starts with a dot, so programs that skip the library's files
    skip it too.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    written = _new_file_beside(path)
    try:
        with written.open("w", encoding="utf-8", newline="\n") as file:
            file.write(text)
            file.flush()
            os.fsync(file.fileno())
        _retried(lambda: written.replace(path))
    except BaseException:
        written.unlink(missing_ok=True)
        raise


def is_temporary(name: str) -> bool:
    """Returns whether a file is one `write_text` writes on the way to the file it is writing."""
    return TEMPORARY.fullmatch(name) is not None


def _new_file_beside(path: Path) -> Path:
    while True:
        candidate = path.with_name(f".{secrets.token_hex(3)}.tmp")
        try:
            candidate.touch(exist_ok=False)
        except FileExistsError:
            continue
        return candidate
