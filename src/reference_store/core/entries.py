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


def at(folder: Path, path: str) -> Path | None:
    """Returns what is at a path in the entry, spelled as it is on disk, whatever the case of the path given."""
    found: Path | None = folder
    for part in path.split("/"):
        found = child(found, part) if found is not None else None
    return found


def spelled(folder: Path, path: str) -> tuple[str, Path | None]:
    """Returns a path in the entry with each folder on its way that is there already spelled as it is on disk, and what
    is at the path now, whatever its case.

    Raises:
        ReferenceStoreError: A file is where the path needs a folder.
    """
    *folders, last = path.split("/")
    current = folder
    for index, part in enumerate(folders):
        found = child(current, part)
        if found is None:
            return "/".join([*current.relative_to(folder).parts, *folders[index:], last]), None
        if not found.is_dir():
            raise ReferenceStoreError(
                f"{folder.name} has a file at {found.relative_to(folder).as_posix()}, so {path} can't go in it."
            )
        current = found
    return "/".join([*current.relative_to(folder).parts, last]), child(current, last)


def files_of(folder: Path, record: EntryRecord) -> list[EntryFile]:
    """Returns every file in the entry's folder but the library's own, in the order of their paths."""
    said = {names.key(path): about for path, about in record.files.items()}
    files: list[EntryFile] = []
    for root, folder_names, file_names in folder.walk():
        folder_names[:] = [each for each in folder_names if not disk.is_temporary(each)]
        for file_name in file_names:
            full_path = root / file_name
            path = full_path.relative_to(folder).as_posix()
            if is_the_librarys(path):
                continue
            try:
                info = full_path.stat()
            except OSError:
                continue
            if not stat.S_ISREG(info.st_mode):
                continue
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
    return sorted(files, key=lambda file: path_order(file.path))


def path_order(path: str) -> list[str]:
    """Returns what paths in an entry are sorted by, folder by folder, so a folder's files stay together."""
    return [names.key(part) for part in path.split("/")]


def said_about(record: EntryRecord, path: str) -> FileRecord:
    """Returns what was said about a file, whatever the case `.entry.json` has its path in."""
    return next(
        (about for each, about in record.files.items() if names.key(each) == names.key(path)), FileRecord()
    ).model_copy(deep=True)


def say_about(record: EntryRecord, path: str, about: FileRecord) -> None:
    """Sets what is said about the file at `path`, spelled as it is on disk, leaving it out when nothing is."""
    kept = {each: said for each, said in record.files.items() if names.key(each) != names.key(path)}
    if about != FileRecord():
        kept[path] = about
    record.files = dict(sorted(kept.items(), key=lambda item: path_order(item[0])))


def tag_changes(add_tags: list[str] | None, remove_tags: list[str] | None) -> tuple[list[str], list[str]]:
    """Returns the tags to add and to remove, as `clean_tags` leaves them.

    Raises:
        ReferenceStoreError: A tag is empty, or both added and removed.
    """
    adding = clean_tags(add_tags or [])
    removing = clean_tags(remove_tags or [])
    removed = {names.key(tag) for tag in removing}
    both = next((tag for tag in adding if names.key(tag) in removed), None)
    if both is not None:
        raise ReferenceStoreError(f"The tag {both} can't be both added and removed.")
    return adding, removing


def retagged(tags: list[str], adding: list[str], removing: list[str]) -> list[str]:
    """Returns the tags without those removed and with those added, keeping the spelling of a tag already there."""
    removed = {names.key(tag) for tag in removing}
    kept = [tag for tag in tags if names.key(tag) not in removed]
    held = {names.key(tag) for tag in kept}
    return kept + [tag for tag in adding if names.key(tag) not in held]


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


def check_file_path(path: str) -> str:
    """Returns a path for a file or folder in an entry as `names.check_path` does, refusing one the library keeps.

    Raises:
        ReferenceStoreError: The path breaks a rule, or the library keeps it for itself.
    """
    cleaned = names.check_path(path)
    if is_the_librarys(cleaned):
        raise ReferenceStoreError(
            f"{cleaned} can't be a file in an entry, since the library keeps that name for itself."
        )
    return cleaned


def is_the_librarys(path: str) -> bool:
    """Returns whether a path in an entry is one the library keeps for itself, rather than one of the entry's files:
    `.entry.json` or a copied-in preview at the top, or a file it is writing anywhere."""
    parts = path.split("/")
    if any(disk.is_temporary(part) for part in parts):
        return True
    return len(parts) == 1 and (names.key(path) == ENTRY_FILE or is_copied_preview(path))
