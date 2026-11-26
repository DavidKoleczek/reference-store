"""Thumbnails and sizes of the images in entries. They are the app's, not the library's, and are kept in `cache/` in the
configuration folder by each image's path, size, and when it last changed, so the folder can be deleted at any time."""

import contextlib
import hashlib
from io import BytesIO
import os
from pathlib import Path
import sqlite3
import uuid

from PIL import Image, ImageOps, UnidentifiedImageError

from reference_store.core import config
from reference_store.models import ReferenceStoreError

CACHE = "cache"
THUMBNAILS = "thumbnails"
SIZES = "sizes.sqlite"
# The longest side of each size: small for cards, walls, and rows, large for the preview pane.
EDGES = {"small": 480, "large": 1600}
QUALITY = 80
# What Pillow reads. An SVG is drawn at any size by the browser, so it is sent as it is.
RASTER = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".avif"}
SVG = ".svg"
# What a browser shows by itself, so the large viewer shows the file and not a thumbnail of it.
BROWSER_SHOWS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".avif", SVG}
# EXIF orientations that turn an image a quarter, so its width and height swap.
QUARTER_TURNS = {5, 6, 7, 8}
ORIENTATION = 0x0112
# How many paths go in one query, well under SQLite's limit on parameters.
CHUNK = 500


def is_image(path: Path) -> bool:
    """Returns whether a file has a thumbnail."""
    return path.suffix.lower() in RASTER or path.suffix.lower() == SVG


def thumbnail(path: Path, size: str) -> tuple[bytes, str]:
    """Returns a WebP of the image at `path` that fits a square of the size's edge, made once and kept, and its MIME
    type. An SVG is returned as it is.

    Raises:
        ReferenceStoreError: The size isn't one, or the file can't be read as an image.
    """
    if size not in EDGES:
        raise ReferenceStoreError(f"There is no thumbnail size {size}. It is one of: {', '.join(EDGES)}.")
    suffix = path.suffix.lower()
    if suffix == SVG:
        return _read(path), "image/svg+xml"
    if suffix not in RASTER:
        raise ReferenceStoreError(f"{path.name} isn't an image the app makes thumbnails of.")
    info = _stat(path)
    key = hashlib.sha256(f"{path}|{info.st_size}|{info.st_mtime_ns}|{EDGES[size]}".encode()).hexdigest()[:40]
    kept = config.home() / CACHE / THUMBNAILS / f"{key}.webp"
    with contextlib.suppress(OSError):
        return kept.read_bytes(), "image/webp"
    made = _make(path, EDGES[size])
    kept.parent.mkdir(parents=True, exist_ok=True)
    # Written beside it and put in place, so a thumbnail being made by another call is never read half done.
    beside = kept.with_name(f"{kept.stem}.{uuid.uuid4().hex[:8]}.tmp")
    beside.write_bytes(made)
    try:
        beside.replace(kept)
    except OSError:
        beside.unlink(missing_ok=True)
    return made, "image/webp"


def sizes(paths: list[Path]) -> list[tuple[int, int] | None]:
    """Returns the width and height of each image, as it shows once turned as its camera recorded, or None for a file
    that isn't one. Each is read once and kept."""
    found: list[tuple[int, int] | None] = [None] * len(paths)
    stats = [_stat_or_none(path) if path.suffix.lower() in RASTER else None for path in paths]
    database = config.home() / CACHE / SIZES
    database.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.closing(sqlite3.connect(database, timeout=10)) as connection:
        connection.execute(
            "create table if not exists sizes (path text primary key, size integer, modified integer, "
            "width integer, height integer)"
        )
        kept: dict[str, tuple[int, int, int | None, int | None]] = {}
        wanted = [str(path) for path, info in zip(paths, stats, strict=True) if info is not None]
        for start in range(0, len(wanted), CHUNK):
            chunk = wanted[start : start + CHUNK]
            rows = connection.execute(
                f"select path, size, modified, width, height from sizes where path in ({','.join('?' * len(chunk))})",
                chunk,
            )
            kept.update({row[0]: row[1:] for row in rows})
        new: list[tuple[str, int, int, int | None, int | None]] = []
        for index, (path, info) in enumerate(zip(paths, stats, strict=True)):
            if info is None:
                continue
            row = kept.get(str(path))
            if row is not None and row[0] == info.st_size and row[1] == info.st_mtime_ns:
                width, height = row[2], row[3]
            else:
                read = _read_size(path)
                width, height = read if read is not None else (None, None)
                new.append((str(path), info.st_size, info.st_mtime_ns, width, height))
            found[index] = (width, height) if width is not None and height is not None else None
        if new:
            with connection:
                connection.executemany("insert or replace into sizes values (?, ?, ?, ?, ?)", new)
    return found


def _make(path: Path, edge: int) -> bytes:
    try:
        with Image.open(BytesIO(_read(path))) as image:
            # A JPEG decodes at a fraction of its size that still covers the edge, so a wall of photos fills in fast.
            image.draft("RGB", (edge, edge))
            small = ImageOps.exif_transpose(image)
            small.thumbnail((edge, edge))
            if small.mode not in ("RGB", "RGBA"):
                small = small.convert("RGBA" if small.has_transparency_data else "RGB")
            buffer = BytesIO()
            small.save(buffer, format="WEBP", quality=QUALITY)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as error:
        raise ReferenceStoreError(f"{path.name} can't be read as an image: {error}") from None
    return buffer.getvalue()


def _read_size(path: Path) -> tuple[int, int] | None:
    try:
        with Image.open(path) as image:
            width, height = image.size
            if image.getexif().get(ORIENTATION) in QUARTER_TURNS:
                width, height = height, width
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        return None
    return width, height


def _read(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as error:
        raise ReferenceStoreError(f"{path.name} can't be read: {error.strerror or error}.") from None


def _stat(path: Path) -> os.stat_result:
    try:
        return path.stat()
    except OSError as error:
        raise ReferenceStoreError(f"{path.name} can't be read: {error.strerror or error}.") from None


def _stat_or_none(path: Path) -> os.stat_result | None:
    try:
        return path.stat()
    except OSError:
        return None
