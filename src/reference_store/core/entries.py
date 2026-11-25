"""An entry on disk: a folder in a store with an `.entry.json`, what that says about it, and the files in it."""

from collections.abc import Generator, Iterator
import contextlib
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any
import uuid

from pydantic import BaseModel, Field, ValidationError, field_validator

from reference_store.core import config, disk, names, stores
from reference_store.models import Entry, EntryFile, EntrySummary, Preview, ReferenceStoreError, Store

ENTRY_FILE = ".entry.json"
# A preview copied in is `.preview` with the image's extension, at the top of the entry.
PREVIEW_STEM = ".preview"
PREVIEW_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif", ".bmp", ".svg")
# What an `.entry.json` written by hand may leave out, and the library fills in the first time it reads it.
FILLED_IN = ("id", "created", "updated")


class PreviewRecord(BaseModel):
    """An entry's preview, as `.entry.json` has it."""

    file: str  # inside the entry, such as .preview.png or screenshots/menu.png
    url: str | None = None


class FileRecord(BaseModel):
    """What was said about one of an entry's files, as `.entry.json` has it."""

    description: str = ""
    notes: str = ""
    tags: list[str] = []


class EntryRecord(BaseModel):
    """What `.entry.json` holds: everything about the entry but its name, and what was said about its files."""

    id: str
    title: str | None = None
    description: str = ""
    url: str | None = None
    tags: list[str] = []
    notes: str = ""
    rating: int | None = Field(default=None, ge=1, le=5)
    preview: PreviewRecord | None = None
    created: datetime
    updated: datetime
    files: dict[str, FileRecord] = {}

    @field_validator("created", "updated")
    @classmethod
    def _in_utc(cls, moment: datetime) -> datetime:
        return in_utc(moment)


def find(name: str, store: str | None) -> tuple[Store, Path]:
    """Returns the entry's store and folder: in the store named, or the store with the highest priority that has it.

    Raises:
        ReferenceStoreError: No store searched has an entry with that name, or the store named can't be used.
    """
    searched = stores.searched(store)
    for each in searched:
        folder = child(each.path, name)
        if folder is not None and (folder / ENTRY_FILE).is_file():
            return each, folder
    where = f"the store {searched[0].name}" if store is not None else "any store"
    raise ReferenceStoreError(f"There is no entry named {name} in {where}.")


def entries_in(store: Store) -> Iterator[Entry]:
    """Yields each entry in the store, in the order of their names.

    An entry whose `.entry.json` can't be read is left out, so one broken by hand or removed while it is read doesn't
    hide the rest. `get_entry` says what is wrong with it.
    """
    try:
        with os.scandir(store.path) as found:
            # A name can't start with a dot, so such a folder is the library's own, such as one being deleted.
            folders = sorted(
                (Path(item.path) for item in found if item.is_dir() and not item.name.startswith(".")),
                key=lambda path: names.key(path.name),
            )
    except OSError:
        return
    for folder in folders:
        if not (folder / ENTRY_FILE).is_file():
            continue
        try:
            record = read(folder)
        except (ReferenceStoreError, OSError):
            continue
        yield entry_of(store, folder, record)


def read(folder: Path) -> EntryRecord:
    """Returns what an entry's `.entry.json` says, first filling in and saving what the library keeps for every entry
    when it was written without it.

    Raises:
        ReferenceStoreError: The `.entry.json` can't be read as an entry.
    """
    path = folder / ENTRY_FILE
    data = _load(path)
    if all(data.get(key) for key in FILLED_IN):
        return _parsed(path, data)
    with locked(folder):
        data = _load(path)
        written = in_utc(datetime.fromtimestamp(path.stat().st_mtime, UTC))
        filled: dict[str, Any] = {"id": str(uuid.uuid4()), "created": written, "updated": written}
        for key in FILLED_IN:
            if not data.get(key):
                data[key] = filled[key]
        record = _parsed(path, data)
        write(folder, record)
        return record


def write(folder: Path, record: EntryRecord) -> None:
    """Saves an entry's `.entry.json`. Hold the entry's lock while reading what to change and writing it."""
    disk.write_text(folder / ENTRY_FILE, record.model_dump_json(indent=2) + "\n")


def entry_of(store: Store, folder: Path, record: EntryRecord) -> Entry:
    """Returns the entry, with the files that are in its folder now."""
    files = files_of(folder, record)
    return Entry(
        id=record.id,
        name=folder.name,
        title=record.title,
        store=store.name,
        description=record.description,
        url=record.url,
        tags=record.tags,
        notes=record.notes,
        rating=record.rating,
        preview=_preview(folder, record),
        file_count=len(files),
        size=sum(file.size for file in files),
        created=record.created,
        updated=record.updated,
        folder=folder,
        files=files,
    )


def summary_of(entry: Entry) -> EntrySummary:
    """Returns the entry without its files."""
    return EntrySummary(**{field: getattr(entry, field) for field in EntrySummary.model_fields})


@contextlib.contextmanager
def locked(*folders: Path) -> Generator[None]:
    """Holds the lock of each entry folder, so only one process changes an entry at a time.

    A folder is locked by its store and its name whatever its case, so a name can be locked before anything has it.
    The locks are taken in one order, so two processes that each want two of them never wait on each other.
    """
    identities = {f"{os.path.normcase(folder.parent)}/{names.key(folder.name)}" for folder in folders}
    with contextlib.ExitStack() as held:
        for identity in sorted(identities):
            held.enter_context(config.locked(f"entry-{hashlib.sha256(identity.encode()).hexdigest()[:32]}"))
        yield


def in_utc(moment: datetime) -> datetime:
    """Returns the moment in UTC, to the second. A moment with no time zone is taken as local time."""
    return moment.astimezone(UTC).replace(microsecond=0)


def clean_tags(tags: list[str]) -> list[str]:
    """Returns the tags without spaces around them, and with only the first of those that differ only by case.

    Raises:
        ReferenceStoreError: A tag is empty.
    """
    kept: dict[str, str] = {}
    for tag in tags:
        trimmed = tag.strip()
        if not trimmed:
            raise ReferenceStoreError("A tag can't be empty.")
        kept.setdefault(names.key(trimmed), trimmed)
    return list(kept.values())


def check_rating(rating: int | None) -> None:
    """Raises when a rating is outside 1 to 5.

    Raises:
        ReferenceStoreError: The rating is outside 1 to 5.
    """
    if rating is not None and not 1 <= rating <= 5:
        raise ReferenceStoreError(f"A rating goes from 1 to 5, where 5 is the best, so it can't be {rating}.")


def what_is(path: Path) -> str:
    """Returns what is at a path in a store, such as `an entry`, to say what has taken a name."""
    return "an entry" if (path / ENTRY_FILE).is_file() else "a folder" if path.is_dir() else "a file"


def child(folder: Path, name: str) -> Path | None:
    """Returns what is in the folder under that name, whatever its case, or None when there is nothing."""
    try:
        with os.scandir(folder) as found:
            match = next((item.name for item in found if names.key(item.name) == names.key(name)), None)
    except OSError:
        return None
    return None if match is None else folder / match


def files_of(folder: Path, record: EntryRecord) -> list[EntryFile]:
    """Returns every file in the entry's folder but the library's own, in the order of their paths."""
    said = {names.key(path): about for path, about in record.files.items()}
    files: list[EntryFile] = []
    for root, _, file_names in folder.walk():
        if root == folder:
            file_names = [each for each in file_names if not _is_the_librarys(each)]
        for file_name in file_names:
            full_path = root / file_name
            try:
                info = full_path.stat()
            except OSError:
                continue
            if not stat.S_ISREG(info.st_mode):
                continue
            path = full_path.relative_to(folder).as_posix()
            about = said.get(names.key(path), FileRecord())
            files.append(
                EntryFile(
                    path=path,
                    full_path=full_path,
                    size=info.st_size,
                    modified=in_utc(datetime.fromtimestamp(info.st_mtime, UTC)),
                    description=about.description,
                    notes=about.notes,
                    tags=about.tags,
                )
            )
    return sorted(files, key=lambda file: [names.key(part) for part in file.path.split("/")])


def _load(path: Path) -> dict[str, Any]:
    text = disk.read_text(path)
    if text is None:
        raise ReferenceStoreError(f"{path} is gone, so its folder is no longer an entry.")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ReferenceStoreError(
            f"{path} isn't JSON: {error}. Fix it, or delete it to make the folder plain files."
        ) from None
    if not isinstance(data, dict):
        raise ReferenceStoreError(
            f"{path} has to hold a JSON object. Fix it, or delete it to make the folder plain files."
        )
    return data


def _parsed(path: Path, data: dict[str, Any]) -> EntryRecord:
    try:
        return EntryRecord.model_validate(data)
    except ValidationError as error:
        raise ReferenceStoreError(
            f"{path} can't be read as an entry. Fix it, or delete it to make the folder plain files.\n{error}"
        ) from None


def _preview(folder: Path, record: EntryRecord) -> Preview | None:
    """Returns the entry's preview, or None when its image is no longer where `.entry.json` says."""
    if record.preview is None:
        return None
    path = folder / record.preview.file
    if not path.is_file() or not path.resolve().is_relative_to(folder.resolve()):
        return None
    return Preview(path=path, url=record.preview.url)


def is_copied_preview(path: str) -> bool:
    """Returns whether a path in an entry is a preview copied in, rather than one of the entry's files."""
    stem, _, suffix = names.key(path).rpartition(".")
    return stem == PREVIEW_STEM and f".{suffix}" in PREVIEW_SUFFIXES


def _is_the_librarys(name: str) -> bool:
    """Returns whether a file at the top of an entry is one the library keeps there, rather than one of its files."""
    return names.key(name) == ENTRY_FILE or disk.is_temporary(name) or is_copied_preview(name)
