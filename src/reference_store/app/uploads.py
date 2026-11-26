"""Files sent to the app from the view, which can't hand over a path. Each upload waits in a folder of its own in the
configuration folder until a library function adds it to an entry."""

import base64
import binascii
from pathlib import Path, PurePosixPath
import re
import shutil
import time

from pydantic import BaseModel

from reference_store.core import config
from reference_store.models import ReferenceStoreError

UPLOADS = "uploads"
UPLOAD_ID = re.compile(r"[0-9a-f]{16,64}")
# An upload nothing took, such as one whose app was closed halfway, is cleared by the next app to start once it is
# this old.
LIFETIME_SECONDS = 24 * 60 * 60
# Far past any one reference, and short of an offset that would fill the disk.
MAX_BYTES = 4 * 1024 * 1024 * 1024


class Received(BaseModel):
    """How much of a file has arrived, and what to pass a library function as its `source` once it all has."""

    source: Path  # the file, or the folder at the top of the path it was sent under
    received: int


def folder() -> Path:
    """Returns the folder uploads wait in."""
    return config.home() / UPLOADS


def receive(upload: str, path: str, offset: int, data: str) -> Received:
    """Writes a piece of a file at `offset`. A piece sent again lands where it did, so a lost answer can be retried.

    `path` is the file's name, or its path in a folder that was sent, which an upload can hold several files of.

    Raises:
        ReferenceStoreError: The id or the path can't be one, the piece isn't base64, or it can't be written.
    """
    parts = PurePosixPath(path.replace("\\", "/")).parts
    if not parts or any(part in ("", ".", "..") or ":" in part for part in parts) or path.startswith(("/", "\\")):
        raise ReferenceStoreError(
            f"{path!r} can't be a file's path in an upload. Send its name, or its path in a folder."
        )
    try:
        piece = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        raise ReferenceStoreError(f"The piece of {path} didn't arrive as base64. Send the file again.") from None
    if offset < 0 or offset + len(piece) > MAX_BYTES:
        raise ReferenceStoreError(f"{path} is larger than the app takes, {MAX_BYTES // 1024**3} GB.")
    top = _folder_of(upload)
    target = top.joinpath(*parts)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("r+b" if target.exists() else "wb") as file:
            file.seek(offset)
            file.write(piece)
        received = target.stat().st_size
    except OSError as error:
        raise ReferenceStoreError(f"Could not keep the upload {path}: {error}. Send it again.") from None
    return Received(source=top / parts[0], received=received)


def upload_of(source: Path) -> str | None:
    """Returns the upload `source` is in, or None when it isn't in one."""
    try:
        inside = source.resolve().relative_to(folder().resolve())
    except ValueError:
        return None
    upload = inside.parts[0] if len(inside.parts) > 1 else None
    return upload if upload is not None and UPLOAD_ID.fullmatch(upload) else None


def clear(upload: str) -> None:
    """Deletes an upload and whatever is left of it."""
    shutil.rmtree(_folder_of(upload), ignore_errors=True)


def clear_old() -> None:
    """Deletes the uploads that are past their lifetime."""
    now = time.time()
    try:
        waiting = list(folder().iterdir())
    except OSError:
        return
    for each in waiting:
        try:
            old = now - each.stat().st_mtime > LIFETIME_SECONDS
        except OSError:
            continue
        if old:
            shutil.rmtree(each, ignore_errors=True)


def _folder_of(upload: str) -> Path:
    if not UPLOAD_ID.fullmatch(upload):
        raise ReferenceStoreError(f"{upload!r} isn't an upload's id, which is 16 to 64 lowercase hex digits.")
    return folder() / upload
