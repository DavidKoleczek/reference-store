"""Entries: the folders in a store that have an `.entry.json`, what it says about them, and the files in them."""

from collections.abc import Generator
import contextlib
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
from typing import Any
import uuid

from pydantic import BaseModel, Field, ValidationError, field_validator

from reference_store.core import config, disk, names, stores
from reference_store.models import Entry, EntryFile, NewPreview, Preview, ReferenceStoreError, Store

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


def add_entry(
    name: str,
    title: str | None,
    description: str,
    url: str | None,
    tags: list[str] | None,
    notes: str,
    rating: int | None,
    preview: NewPreview | None,
    created: datetime | None,
    store: str | None,
) -> Entry:
    """Adds an entry with what it is given, to the store named, the project's, or the default."""
    names.check_name(name, "an entry")
    check_rating(rating)
    target = _store_to_add_to(store)
    folder = target.path / name
    names.check_full_path(folder / ENTRY_FILE, "the entry's name")
    image = _preview_image(preview)
    now = in_utc(datetime.now(UTC))
    record = EntryRecord(
        id=str(uuid.uuid4()),
        title=title or None,
        description=description,
        url=url or None,
        tags=clean_tags(tags or []),
        notes=notes,
        rating=rating,
        created=in_utc(created) if created else now,
        updated=now,
    )
    if image is not None:
        record.preview = PreviewRecord(
            file=f"{PREVIEW_STEM}{image.suffix.lower()}", url=preview.url if preview else None
        )
        names.check_full_path(folder / record.preview.file, "the entry's name")
    with locked(folder):
        taken = _child(target.path, name)
        if taken is not None:
            kind = "an entry" if (taken / ENTRY_FILE).is_file() else "a folder" if taken.is_dir() else "a file"
            raise ReferenceStoreError(
                f"The store {target.name} already has {kind} named {taken.name}. Pick another name, or another store."
            )
        if target.priority_order == 0:
            stores.make_store(target.path)
        folder.mkdir()
        try:
            if image is not None and record.preview is not None:
                shutil.copyfile(image, folder / record.preview.file)
            write(folder, record)
        except BaseException:
            shutil.rmtree(folder, ignore_errors=True)
            raise
    return entry_of(target, folder, record)


def get_entry(name: str, store: str | None) -> Entry:
    """Returns the entry with that name, from the store named, or the one with the highest priority that has it."""
    target, folder = find(name, store)
    return entry_of(target, folder, read(folder))


def find(name: str, store: str | None) -> tuple[Store, Path]:
    """Returns the entry's store and folder: in the store named, or the store with the highest priority that has it.

    Raises:
        ReferenceStoreError: No store searched has an entry with that name, or the store named can't be used.
    """
    searched = [stores.find_store(store)] if store is not None else [s for s in stores.list_stores() if s.available]
    for each in searched:
        folder = _child(each.path, name)
        if folder is not None and (folder / ENTRY_FILE).is_file():
            return each, folder
    where = f"the store {searched[0].name}" if store is not None else "any store"
    raise ReferenceStoreError(f"There is no entry named {name} in {where}.")


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
    files = _files(folder, record)
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


@contextlib.contextmanager
def locked(folder: Path) -> Generator[None]:
    """Holds the entry's lock, so only one process changes it at a time."""
    identity = f"{os.path.normcase(folder.parent)}/{names.key(folder.name)}"
    with config.locked(f"entry-{hashlib.sha256(identity.encode()).hexdigest()[:32]}"):
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


def _store_to_add_to(store: str | None) -> Store:
    if store is not None:
        return stores.find_store(store)
    listed = stores.list_stores()
    target = next((each for each in listed if each.priority_order == 0), None) or next(
        (each for each in listed if each.default), None
    )
    if target is None:
        raise ReferenceStoreError("There is no store to add it to. Register one first.")
    if not target.available:
        raise ReferenceStoreError(
            f"The default store {target.name} is not available, since {target.path} can't be reached. Name another "
            "store to add it to."
        )
    return target


def _preview_image(preview: NewPreview | None) -> Path | None:
    """Returns the image to copy in as the preview, refusing a preview that can't be one."""
    if preview is None:
        return None
    if preview.source is not None and preview.file is not None:
        raise ReferenceStoreError("A preview is a source or a file, not both.")
    if preview.file is not None:
        raise ReferenceStoreError(f"{preview.file} isn't one of the entry's files, so it can't be its preview.")
    if preview.source is None:
        raise ReferenceStoreError("A preview needs a source, an image to copy in.")
    image = preview.source.expanduser().resolve()
    if not image.is_file():
        raise ReferenceStoreError(f"There is no image at {image}.")
    if image.suffix.lower() not in PREVIEW_SUFFIXES:
        raise ReferenceStoreError(
            f"{image.name} can't be a preview. A preview is an image: {', '.join(PREVIEW_SUFFIXES)}."
        )
    return image


def _child(folder: Path, name: str) -> Path | None:
    """Returns what is in the folder under that name, whatever its case, or None when there is nothing."""
    try:
        with os.scandir(folder) as found:
            match = next((item.name for item in found if names.key(item.name) == names.key(name)), None)
    except OSError:
        return None
    return None if match is None else folder / match


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


def _files(folder: Path, record: EntryRecord) -> list[EntryFile]:
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


def _preview(folder: Path, record: EntryRecord) -> Preview | None:
    """Returns the entry's preview, or None when its image is no longer where `.entry.json` says."""
    if record.preview is None:
        return None
    path = folder / record.preview.file
    if not path.is_file() or not path.resolve().is_relative_to(folder.resolve()):
        return None
    return Preview(path=path, url=record.preview.url)


def _is_the_librarys(name: str) -> bool:
    """Returns whether a file at the top of an entry is one the library keeps there, rather than one of its files."""
    key = names.key(name)
    stem, _, suffix = key.rpartition(".")
    return key == ENTRY_FILE or disk.is_temporary(name) or (stem == PREVIEW_STEM and f".{suffix}" in PREVIEW_SUFFIXES)
