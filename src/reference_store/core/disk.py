"""Reading, writing, and moving files and folders, so that another process never sees half of one."""

from collections.abc import Callable
import contextlib
import errno
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import stat
import sys
import time

from reference_store.models import ReferenceStoreError

# On Windows a file can't be replaced while another process has it open, and readers hold it only briefly.
ATTEMPTS = 50
PAUSE_SECONDS = 0.02
# As long as `.entry.json`, `.store.json`, and `config.json`, so writing one never makes a longer path than the file.
TEMPORARY = re.compile(r"\.[0-9a-f]{6}\.tmp")
LONG_PREFIX = "\\\\?\\"


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


def copy_file(source: Path, target: Path) -> None:
    """Copies a file to `target` the way `write_text` writes one, so a reader sees the old file or the new one.

    The copy keeps when the file was last modified.
    """
    written = _new_file_beside(target)
    try:
        shutil.copyfile(source, written)
        info = source.stat()
        os.utime(written, ns=(info.st_atime_ns, info.st_mtime_ns))
        _retried(lambda: written.replace(target))
    except BaseException:
        written.unlink(missing_ok=True)
        raise


def move_folder(source: Path, target: Path) -> None:
    """Moves a folder and everything in it to `target`, which doesn't exist yet.

    On another drive it is copied beside `target` under a temporary name and then renamed, so `target` is never half
    there, and the source is deleted last.

    Raises:
        OSError: It couldn't be moved, such as when a file in it is open in a program that keeps it from moving.
        ReferenceStoreError: It was copied, but some of the source couldn't be deleted.
    """
    try:
        rename(source, target)
        return
    except OSError as error:
        if error.errno != errno.EXDEV:
            raise
    copy = _new_name_beside(target)
    try:
        shutil.copytree(_long(source), _long(copy))
        rename(copy, target)
    except BaseException:
        shutil.rmtree(_long(copy), ignore_errors=True)
        raise
    delete_folder(source)


def rename(source: Path, target: Path) -> None:
    """Renames a file or a folder, waiting while another process has it open for a moment.

    Raises:
        OSError: It couldn't be renamed, such as when `target` is on another drive, where the error's errno is EXDEV.
    """
    _retried(lambda: source.rename(target))


def make_folders(folder: Path, path: str) -> list[Path]:
    """Makes the folders inside `folder` that `path`, a path inside it, goes through and that aren't there yet.

    Returns:
        The folders it made, outermost first.
    """
    made: list[Path] = []
    for inside in reversed(PurePosixPath(path).parents[:-1]):
        each = folder / inside
        if not each.is_dir():
            each.mkdir()
            made.append(each)
    return made


def delete_empty(folders: list[Path]) -> None:
    """Deletes each folder that is empty, in the order given, and leaves the rest."""
    for each in folders:
        with contextlib.suppress(OSError):
            each.rmdir()


def delete_file(path: Path) -> None:
    """Deletes a file, even a read-only one.

    Raises:
        OSError: It couldn't be deleted, such as when it is open in a program that keeps it from being deleted.
    """
    try:
        _retried(path.unlink)
    except PermissionError as error:
        _made_writable_and_retried(os.unlink, str(path), error)


def delete_folder(folder: Path) -> None:
    """Deletes a folder and everything in it.

    It is renamed out of the way first, so it is either all there or gone from its name, even when something in it is
    open and can't be deleted. What can't be deleted is left under the new name, which starts with a dot.

    Raises:
        OSError: It couldn't be renamed, such as when a file in it is open in a program that keeps it from moving.
        ReferenceStoreError: Some of it couldn't be deleted.
    """
    doomed = _new_name_beside(folder)
    rename(folder, doomed)
    try:
        shutil.rmtree(_long(doomed), onexc=_made_writable_and_retried)
    except OSError as error:
        raise ReferenceStoreError(
            f"{folder} is gone, but {doomed} is left with what couldn't be deleted: {error.strerror or error}. Delete "
            "it once no program has it open."
        ) from None


def is_temporary(name: str) -> bool:
    """Returns whether a file is one `write_text` writes on the way to the file it is writing."""
    return TEMPORARY.fullmatch(name) is not None


def _new_file_beside(path: Path) -> Path:
    """Makes an empty file beside `path` under a temporary name, and returns it in the form `_long` gives."""
    while True:
        candidate = Path(_long(path.with_name(f".{secrets.token_hex(3)}.tmp")))
        try:
            candidate.touch(exist_ok=False)
        except FileExistsError:
            continue
        return candidate


def _new_name_beside(path: Path) -> Path:
    while True:
        candidate = path.with_name(f".{secrets.token_hex(3)}.tmp")
        if not candidate.exists():
            return candidate


def _long(path: Path) -> str:
    """Returns the path in a form Windows takes at any length.

    A file or folder under a temporary name can be longer than the 260 characters most of Windows allows, when its own
    name is shorter than the temporary one.
    """
    # Windows takes such a path as it is, so `..` has to be gone from it first.
    full = str(path.resolve())
    if sys.platform != "win32" or full.startswith(LONG_PREFIX):
        return full
    if full.startswith("\\\\"):
        return f"{LONG_PREFIX}UNC\\{full[2:]}"
    return f"{LONG_PREFIX}{full}"


def _made_writable_and_retried(action: Callable[[str], object], path: str, error: BaseException) -> None:
    """Deletes a read-only file, which Windows otherwise refuses to delete."""
    if not isinstance(error, PermissionError):
        raise error
    Path(path).chmod(stat.S_IWRITE)
    _retried(lambda: action(path))
