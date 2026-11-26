"""The files of entries and their thumbnails as MCP resources, named by store, entry, and path in the entry."""

import base64
import mimetypes
from pathlib import Path
from urllib.parse import unquote

from mcp.types import BlobResourceContents, ResourceTemplate

from reference_store.app import images
from reference_store.app.known import Known
from reference_store.models import ReferenceStoreError

FILES = "reference-store://files/"
THUMBNAILS = "reference-store://thumbnails/"
COVERS = "reference-store://covers/"
TEMPLATES = [
    ResourceTemplate(
        name="file",
        uri_template=f"{FILES}{{store}}/{{entry}}/{{+path}}",
        description="One of an entry's files as it is.",
    ),
    ResourceTemplate(
        name="thumbnail",
        uri_template=f"{THUMBNAILS}{{size}}/{{store}}/{{entry}}/{{+path}}",
        description="One of an entry's images as a WebP that fits the size, small or large.",
        mime_type="image/webp",
    ),
    ResourceTemplate(
        name="cover",
        uri_template=f"{COVERS}{{size}}/{{store}}/{{entry}}",
        description="The image that stands for an entry, its preview or else the first of its images, as a WebP that "
        "fits the size, small or large.",
        mime_type="image/webp",
    ),
]
# Types the browser reads by their MIME type that Python's table may not have.
TYPES = {".webp": "image/webp", ".avif": "image/avif", ".md": "text/markdown", ".svg": "image/svg+xml"}


def is_resource(uri: str) -> bool:
    return uri.startswith((FILES, THUMBNAILS, COVERS))


def read(uri: str, known: Known) -> BlobResourceContents:
    """Returns the file or thumbnail `uri` names.

    Raises:
        ReferenceStoreError: It names no file of an entry the library has, or the file can't be read.
    """
    if uri.startswith(FILES):
        path = known.file(*_parts(uri, FILES, 3))
        return _contents(uri, _bytes(path), _type(path))
    if uri.startswith(THUMBNAILS):
        size, store, entry, file = _parts(uri, THUMBNAILS, 4)
        content, mime_type = images.thumbnail(known.file(store, entry, file), size)
        return _contents(uri, content, mime_type)
    size, store, entry = _parts(uri, COVERS, 3, False)
    content, mime_type = images.thumbnail(known.cover(store, entry), size)
    return _contents(uri, content, mime_type)


def _parts(uri: str, prefix: str, count: int, path_last: bool = True) -> list[str]:
    """The parts of the URI after its prefix, each decoded, the last holding the rest when it is a path."""
    pieces = uri.removeprefix(prefix).split("/", count - 1 if path_last else -1)
    if len(pieces) != count or not all(pieces):
        raise ReferenceStoreError(f"{uri} isn't a resource of the app. They are: {_templates()}.")
    return [unquote(piece) for piece in pieces]


def _templates() -> str:
    return ", ".join(template.uri_template for template in TEMPLATES)


def _contents(uri: str, content: bytes, mime_type: str) -> BlobResourceContents:
    return BlobResourceContents(uri=uri, mime_type=mime_type, blob=base64.b64encode(content).decode("ascii"))


def _type(path: Path) -> str:
    suffix = path.suffix.lower()
    return TYPES.get(suffix) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def _bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as error:
        raise ReferenceStoreError(f"{path.name} can't be read: {error.strerror or error}.") from None
