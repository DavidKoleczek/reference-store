"""Adding entries and reading them back one at a time."""

from datetime import UTC, datetime
from pathlib import Path
import shutil
import uuid

from reference_store.core import entries, names, stores
from reference_store.core.entries import ENTRY_FILE, EntryRecord, PreviewRecord
from reference_store.models import Entry, NewPreview, ReferenceStoreError, Store


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
        record.preview = PreviewRecord(
            file=f"{entries.PREVIEW_STEM}{image.suffix.lower()}", url=preview.url if preview else None
        )
        names.check_full_path(folder / record.preview.file, "the entry's name")
    with entries.locked(folder):
        taken = entries.child(target.path, name)
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
            entries.write(folder, record)
        except BaseException:
            shutil.rmtree(folder, ignore_errors=True)
            raise
    return entries.entry_of(target, folder, record)


def get_entry(name: str, store: str | None) -> Entry:
    """Returns the entry with that name, from the store named, or the one with the highest priority that has it."""
    target, folder = entries.find(name, store)
    return entries.entry_of(target, folder, entries.read(folder))


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
    if image.suffix.lower() not in entries.PREVIEW_SUFFIXES:
        raise ReferenceStoreError(
            f"{image.name} can't be a preview. A preview is an image: {', '.join(entries.PREVIEW_SUFFIXES)}."
        )
    return image
