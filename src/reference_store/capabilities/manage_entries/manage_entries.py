"""Adding, reading, changing, and deleting entries one at a time."""

from datetime import UTC, datetime
from pathlib import Path
import shutil
import uuid

from reference_store.core import disk, entries, names, new_files, stores
from reference_store.core.entries import ENTRY_FILE, EntryRecord, PreviewRecord
from reference_store.models import Entry, NewFile, NewPreview, NotGiven, ReferenceStoreError, Store


def add_entry(
    name: str,
    title: str | None,
    description: str,
    url: str | None,
    tags: list[str] | None,
    notes: str,
    rating: int | None,
    preview: NewPreview | None,
    files: list[NewFile] | None,
    created: datetime | None,
    store: str | None,
) -> Entry:
    """Adds an entry with what it is given, to the store named, the project's, or the default."""
    names.check_name(name, "an entry")
    entries.check_rating(rating)
    target = _store_to_add_to(store)
    folder = target.path / name
    names.check_full_path(folder / ENTRY_FILE, "the entry's name")
    image = _preview_image(preview)
    now = entries.in_utc(datetime.now(UTC))
    record = EntryRecord(
        id=str(uuid.uuid4()),
        title=title or None,
        description=description,
        url=url or None,
        tags=entries.clean_tags(tags or []),
        notes=notes,
        rating=rating,
        created=entries.in_utc(created) if created else now,
        updated=now,
    )
    if image is not None:
        record.preview = PreviewRecord(file=_copied_name(image), url=preview.url if preview else None)
        names.check_full_path(folder / record.preview.file, "the entry's name")
    with entries.locked(folder):
        taken = entries.child(target.path, name)
        if taken is not None:
            raise ReferenceStoreError(
                f"The store {target.name} already has {entries.what_is(taken)} named {taken.name}. Pick another name, "
                "or another store."
            )
        placings = new_files.planned(folder, files or [])
        new_files.describe(record, placings)
        if preview is not None and preview.file is not None:
            paths = [placing.path for placing in placings]
            record.preview = PreviewRecord(file=_own_image(name, paths, preview.file), url=preview.url or None)
        if target.priority_order == 0:
            stores.make_store(target.path)
        folder.mkdir()
        try:
            with new_files.placed(folder, placings):
                if image is not None and record.preview is not None:
                    shutil.copyfile(image, folder / record.preview.file)
                entries.write(folder, record)
        except BaseException:
            shutil.rmtree(folder, ignore_errors=True)
            raise
        new_files.finish_moves(placings)
    return entries.entry_of(target, folder, record)


def get_entry(name: str, store: str | None) -> Entry:
    """Returns the entry with that name, from the store named, or the one with the highest priority that has it."""
    target, folder = entries.find(name, store)
    return entries.entry_of(target, folder, entries.read(folder))


def update_entry(
    name: str,
    title: str | NotGiven | None,
    description: str | NotGiven,
    url: str | NotGiven | None,
    notes: str | NotGiven,
    rating: int | NotGiven | None,
    preview: NewPreview | NotGiven | None,
    add_tags: list[str] | None,
    remove_tags: list[str] | None,
    store: str | None,
) -> Entry:
    """Changes what is given, keeps what is left out, and clears what is given None.

    `updated` only moves when something changed, so a call that changes nothing leaves the entry as it was.
    """
    if not isinstance(rating, NotGiven):
        entries.check_rating(rating)
    adding, removing = entries.tag_changes(add_tags, remove_tags)
    target, folder = entries.find(name, store)
    image = None
    if isinstance(preview, NewPreview):
        if preview.source is not None and preview.file is not None:
            raise ReferenceStoreError("A preview is a source or a file, not both.")
        if preview.source is not None:
            image = _source_image(preview.source)
            names.check_full_path(folder / _copied_name(image), "the entry's name")
    with entries.locked(folder):
        record = entries.read(folder)
        before = record.model_copy(deep=True)
        if not isinstance(title, NotGiven):
            record.title = title or None
        if not isinstance(description, NotGiven):
            record.description = description
        if not isinstance(url, NotGiven):
            record.url = url or None
        if not isinstance(notes, NotGiven):
            record.notes = notes
        if not isinstance(rating, NotGiven):
            record.rating = rating
        record.tags = entries.retagged(record.tags, adding, removing)
        old_copy = before.preview.file if before.preview and entries.is_copied_preview(before.preview.file) else None
        if not isinstance(preview, NotGiven):
            record.preview = _changed_preview(folder, record, preview, image)
        if image is not None and record.preview is not None:
            disk.copy_file(image, folder / record.preview.file)
        if record != before or image is not None:
            record.updated = entries.in_utc(datetime.now(UTC))
            entries.write(folder, record)
        # A copied-in preview is the library's own file, so it goes once nothing uses it.
        if old_copy is not None and (record.preview is None or names.key(record.preview.file) != names.key(old_copy)):
            (folder / old_copy).unlink(missing_ok=True)
    return entries.entry_of(target, folder, record)


def delete_entry(name: str, store: str | None) -> None:
    """Deletes the entry's folder and everything in it."""
    target, folder = entries.find(name, store)
    with entries.locked(folder):
        if not (folder / ENTRY_FILE).is_file():
            raise ReferenceStoreError(f"There is no entry named {folder.name} in the store {target.name} anymore.")
        try:
            disk.delete_folder(folder)
        except OSError as error:
            raise ReferenceStoreError(
                f"Couldn't delete {folder.name} from the store {target.name}: {error.strerror or error}. A file in it "
                "may be open in another program. Close it and try again. Nothing was deleted."
            ) from None


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
    """Returns the image a new entry copies in as its preview, or None for one of its files, refusing a preview that
    can't be one."""
    if preview is None:
        return None
    if preview.source is not None and preview.file is not None:
        raise ReferenceStoreError("A preview is a source or a file, not both.")
    if preview.file is not None:
        return None
    if preview.source is None:
        raise ReferenceStoreError("A preview needs an image: a source to copy in, or one of the entry's files.")
    return _source_image(preview.source)


def _source_image(source: Path) -> Path:
    image = source.expanduser().resolve()
    if not image.is_file():
        raise ReferenceStoreError(f"There is no image at {image}.")
    if image.suffix.lower() not in entries.PREVIEW_SUFFIXES:
        raise ReferenceStoreError(
            f"{image.name} can't be a preview. A preview is an image: {', '.join(entries.PREVIEW_SUFFIXES)}."
        )
    return image


def _copied_name(image: Path) -> str:
    return f"{entries.PREVIEW_STEM}{image.suffix.lower()}"


def _changed_preview(
    folder: Path, record: EntryRecord, preview: NewPreview | None, image: Path | None
) -> PreviewRecord | None:
    """Returns the preview `.entry.json` gets: a copied-in image, one of the entry's files, or the same image with
    another `url` when the preview names neither."""
    if preview is None:
        return None
    url = preview.url or None
    if image is not None:
        return PreviewRecord(file=_copied_name(image), url=url)
    if preview.file is not None:
        paths = [file.path for file in entries.files_of(folder, record)]
        return PreviewRecord(file=_own_image(folder.name, paths, preview.file), url=url)
    if record.preview is None:
        raise ReferenceStoreError(
            f"{folder.name} has no preview for that url to be about. Give the image too, as a source or a file."
        )
    return PreviewRecord(file=record.preview.file, url=url)


def _own_image(name: str, paths: list[str], path: str) -> str:
    """Returns the one of the entry's paths that `path` names, refusing one that isn't there or isn't an image."""
    wanted = names.key(names.slashed(path))
    found = next((each for each in paths if names.key(each) == wanted), None)
    if found is None:
        raise ReferenceStoreError(f"{path} isn't one of {name}'s files, so it can't be its preview.")
    if Path(found).suffix.lower() not in entries.PREVIEW_SUFFIXES:
        raise ReferenceStoreError(
            f"{found} can't be a preview. A preview is an image: {', '.join(entries.PREVIEW_SUFFIXES)}."
        )
    return found
