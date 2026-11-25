"""The command line. Each command parses its arguments, calls the library, and prints the result."""

from collections.abc import Generator
import contextlib
from datetime import datetime
from enum import StrEnum
from pathlib import Path
import time
from typing import Annotated

from pydantic import TypeAdapter
import typer

from reference_store import lib
from reference_store.models import (
    NOT_GIVEN,
    Entry,
    EntrySort,
    EntrySummary,
    NewFile,
    NewPreview,
    ReferenceStoreError,
    SiteCount,
    Store,
    TagCount,
)
from reference_store.skill.skill import DISTRIBUTION

JSON_HELP = "Print the result as JSON."
STORES = TypeAdapter(list[Store])
TAGS = TypeAdapter(list[TagCount])
SITES = TypeAdapter(list[SiteCount])
SIZE_UNITS = ("bytes", "KB", "MB", "GB", "TB")


class Clearable(StrEnum):
    """The fields `update-entry --clear` empties."""

    TITLE = "title"
    DESCRIPTION = "description"
    URL = "url"
    NOTES = "notes"
    RATING = "rating"
    PREVIEW = "preview"


class FileClearable(StrEnum):
    """The fields `update-file --clear` empties."""

    DESCRIPTION = "description"
    NOTES = "notes"


app = typer.Typer(
    name=DISTRIBUTION,
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


@contextlib.contextmanager
def _reported() -> Generator[None]:
    """Prints the message of a failure the caller can act on, in place of a traceback, and exits with 1."""
    try:
        yield
    except ReferenceStoreError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from None


def _describe_store(store: Store) -> str:
    marks = [
        mark
        for mark, shown in (
            ("project", store.priority_order == 0),
            ("default", store.default),
            ("not available", not store.available),
        )
        if shown
    ]
    flags = f" ({', '.join(marks)})" if marks else ""
    return f"{store.priority_order}. {store.name}{flags}: {store.path}"


def _print_stores(stores: list[Store], json: bool) -> None:
    if json:
        typer.echo(STORES.dump_json(stores, indent=2).decode())
    elif stores:
        for store in stores:
            typer.echo(_describe_store(store))
    else:
        typer.echo("No stores are registered. Add one with add-store.")


def _moment(text: str | None, option: str) -> datetime | None:
    if text is None:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        raise typer.BadParameter(
            f"{text!r} isn't a date or a time, such as 2026-01-05 or 2026-01-05T18:30:00Z.", param_hint=option
        ) from None


def _size(count: int) -> str:
    value, unit = float(count), 0
    while value >= 1024 and unit < len(SIZE_UNITS) - 1:
        value /= 1024
        unit += 1
    if unit == 0:
        return f"{count} byte" if count == 1 else f"{count} bytes"
    return f"{value:.1f} {SIZE_UNITS[unit]}" if value < 10 else f"{value:.0f} {SIZE_UNITS[unit]}"


def _describe_entry(entry: Entry) -> str:
    """The entry as a line for each field that has something in it, then a line for each file."""
    fields = [
        ("name", entry.name),
        ("title", entry.title),
        ("store", entry.store),
        ("folder", str(entry.folder)),
        ("description", entry.description),
        ("url", entry.url),
        ("tags", ", ".join(entry.tags)),
        ("notes", entry.notes),
        ("rating", None if entry.rating is None else str(entry.rating)),
        ("preview", str(entry.preview.path) if entry.preview else None),
        ("created", f"{entry.created.astimezone():%Y-%m-%d %H:%M}"),
        ("updated", f"{entry.updated.astimezone():%Y-%m-%d %H:%M}"),
        ("files", f"{entry.file_count}, {_size(entry.size)}" if entry.files else "none"),
    ]
    # Lines after the first of a value are indented, so a field written over several lines still reads as one.
    lines = [f"{field}: {value.replace('\n', '\n  ')}" for field, value in fields if value]
    for file in entry.files:
        tags = f"  [{', '.join(file.tags)}]" if file.tags else ""
        description = f"  {file.description}" if file.description else ""
        lines.append(f"  {file.path}  {_size(file.size)}{tags}{description}")
    return "\n".join(lines)


def _counted(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


def _describe_summary(entry: EntrySummary, sort: EntrySort) -> str:
    """The entry as one line: its name and title, then its store, a date, its files, its rating, and its tags."""
    moment = entry.updated if sort == "updated" else entry.created
    files = _counted(entry.file_count, "file", "files")
    facts = [
        entry.store,
        f"{moment.astimezone():%Y-%m-%d}",
        f"{files}, {_size(entry.size)}" if entry.file_count else files,
    ]
    if entry.rating is not None:
        facts.append(f"rated {entry.rating}")
    if entry.tags:
        facts.append(f"[{', '.join(entry.tags)}]")
    title = f" ({entry.title})" if entry.title else ""
    return "  ".join([f"{entry.name}{title}", *facts])


def _print_version(value: bool) -> None:
    if value:
        typer.echo(f"{DISTRIBUTION} {lib.version()}")
        raise typer.Exit()


@app.callback()
def cli(
    version: Annotated[
        bool,
        typer.Option("--version", "-V", is_eager=True, callback=_print_version, help="Print the version and exit."),
    ] = False,
) -> None:
    """A place to store various references and useful content."""


@app.command()
def add_store(
    name: Annotated[str, typer.Argument(help="What to call the store, such as main.")],
    location: Annotated[str, typer.Argument(help="The store's folder. One that doesn't exist yet is made.")],
    default: Annotated[
        bool, typer.Option("--default", help="Make it the default store, where new entries go.")
    ] = False,
    json: Annotated[bool, typer.Option("--json", help=JSON_HELP)] = False,
) -> None:
    """Register a store on this machine.

    An empty or missing folder becomes a new store, and one that already holds a store is connected as it is. A folder with other things in it becomes a store too, and they are left alone.

    A project's folder, one with a .reference-store store in it, registers that store. The first store added is the default.
    """
    with _reported():
        store = lib.add_store(name, location, default)
    typer.echo(store.model_dump_json(indent=2) if json else _describe_store(store))


@app.command()
def list_stores(json: Annotated[bool, typer.Option("--json", help=JSON_HELP)] = False) -> None:
    """List the stores in priority order, where 1 is the highest.

    Inside a project that has its own store, that store comes first, with priority 0.
    """
    with _reported():
        stores = lib.list_stores()
    _print_stores(stores, json)


@app.command()
def set_default_store(
    name: Annotated[str, typer.Argument(help="The store's name.")],
    json: Annotated[bool, typer.Option("--json", help=JSON_HELP)] = False,
) -> None:
    """Make a store the default, which is where entries are added when no store is given."""
    with _reported():
        store = lib.set_default_store(name)
    typer.echo(store.model_dump_json(indent=2) if json else _describe_store(store))


@app.command()
def set_store_priority(
    name: Annotated[str, typer.Argument(help="The store's name.")],
    priority_order: Annotated[int, typer.Argument(help="Its place in the order, where 1 is the highest.")],
    json: Annotated[bool, typer.Option("--json", help=JSON_HELP)] = False,
) -> None:
    """Give a store a place in the order, and list the stores. The others shift to make room."""
    with _reported():
        stores = lib.set_store_priority(name, priority_order)
    _print_stores(stores, json)


@app.command()
def remove_store(name: Annotated[str, typer.Argument(help="The store's name.")]) -> None:
    """Unregister a store. Nothing in it is deleted.

    When it was the default, the store with the highest priority left becomes the default.
    """
    with _reported():
        lib.remove_store(name)
    typer.echo(f"Removed the store {name}. Its files are left as they are.")


@app.command()
def add_entry(
    name: Annotated[str, typer.Argument(help="The entry's name, which is also its folder's name.")],
    title: Annotated[str | None, typer.Option(help="A title the name can't be, such as one with a colon.")] = None,
    description: Annotated[str, typer.Option(help="What the reference is.")] = "",
    url: Annotated[str | None, typer.Option(help="The reference's link.")] = None,
    tag: Annotated[list[str] | None, typer.Option(help="A tag. Repeat it for each one.")] = None,
    notes: Annotated[str, typer.Option(help="Anything else, such as why it was saved.")] = "",
    rating: Annotated[int | None, typer.Option(help="From 1 to 5, where 5 is the best.")] = None,
    preview: Annotated[Path | None, typer.Option(help="An image to copy in as the entry's preview.")] = None,
    preview_file: Annotated[
        str | None, typer.Option(help="One of the files added to make its preview, such as screenshots/menu.png.")
    ] = None,
    preview_url: Annotated[str | None, typer.Option(help="Where the preview image came from.")] = None,
    file: Annotated[
        list[Path] | None,
        typer.Option(help="A file or folder to copy in at the top of the entry. Repeat it for each one."),
    ] = None,
    created: Annotated[
        str | None, typer.Option(help="When it was first saved, such as 2026-01-05 or 2026-01-05T18:30:00Z.")
    ] = None,
    store: Annotated[
        str | None, typer.Option(help="The store to add it to. Without it, the project's store or the default.")
    ] = None,
    json: Annotated[bool, typer.Option("--json", help=JSON_HELP)] = False,
) -> None:
    """Add an entry: one reference, such as a repo, a website, or a game with its screenshots.

    It only saves what it is given, and never fetches anything. add-files puts files in other folders of the entry, and says what they are.
    """
    previewed = preview is not None or preview_file is not None or preview_url is not None
    new_preview = NewPreview(source=preview, file=preview_file, url=preview_url) if previewed else None
    files = [NewFile(source=source) for source in file or []]
    with _reported():
        entry = lib.add_entry(
            name, title, description, url, tag, notes, rating, new_preview, files, _moment(created, "--created"), store
        )
    typer.echo(entry.model_dump_json(indent=2) if json else _describe_entry(entry))


@app.command()
def get_entry(
    name: Annotated[str, typer.Argument(help="The entry's name.")],
    store: Annotated[
        str | None,
        typer.Option(help="The store it is in. Without it, the store with the highest priority that has it."),
    ] = None,
    json: Annotated[bool, typer.Option("--json", help=JSON_HELP)] = False,
) -> None:
    """Show an entry and its files, including files put in its folder by hand."""
    with _reported():
        entry = lib.get_entry(name, store)
    typer.echo(entry.model_dump_json(indent=2) if json else _describe_entry(entry))


@app.command()
def update_entry(
    name: Annotated[str, typer.Argument(help="The entry's name.")],
    title: Annotated[str | None, typer.Option(help="A title the name can't be, such as one with a colon.")] = None,
    description: Annotated[str | None, typer.Option(help="What the reference is.")] = None,
    url: Annotated[str | None, typer.Option(help="The reference's link.")] = None,
    notes: Annotated[str | None, typer.Option(help="Anything else, such as why it was saved.")] = None,
    rating: Annotated[int | None, typer.Option(help="From 1 to 5, where 5 is the best.")] = None,
    preview: Annotated[Path | None, typer.Option(help="An image to copy in as the entry's preview.")] = None,
    preview_file: Annotated[
        str | None, typer.Option(help="One of the entry's images to make its preview, such as screenshots/menu.png.")
    ] = None,
    preview_url: Annotated[
        str | None, typer.Option(help="Where the preview image came from. On its own, it keeps the image.")
    ] = None,
    add_tag: Annotated[list[str] | None, typer.Option(help="A tag to add. Repeat it for each one.")] = None,
    remove_tag: Annotated[list[str] | None, typer.Option(help="A tag to remove. Repeat it for each one.")] = None,
    clear: Annotated[
        list[Clearable] | None, typer.Option(help="A field to clear. Repeat it for each one.", show_default=False)
    ] = None,
    store: Annotated[
        str | None,
        typer.Option(help="The store it is in. Without it, the store with the highest priority that has it."),
    ] = None,
    json: Annotated[bool, typer.Option("--json", help=JSON_HELP)] = False,
) -> None:
    """Change an entry. Whatever is left out stays as it is.

    Tags are added and removed rather than replaced, so two callers tagging the same entry don't undo each other.
    """
    cleared = set(clear or [])
    for field, value in (
        ("title", title),
        ("description", description),
        ("url", url),
        ("notes", notes),
        ("rating", rating),
    ):
        if field in cleared and value is not None:
            raise typer.BadParameter(f"--{field} and --clear {field} can't both be given.", param_hint="--clear")
    previewed = preview is not None or preview_file is not None or preview_url is not None
    if "preview" in cleared and previewed:
        raise typer.BadParameter(
            "--clear preview can't go with --preview, --preview-file, or --preview-url.", param_hint="--clear"
        )
    with _reported():
        entry = lib.update_entry(
            name,
            title=None if "title" in cleared else NOT_GIVEN if title is None else title,
            description="" if "description" in cleared else NOT_GIVEN if description is None else description,
            url=None if "url" in cleared else NOT_GIVEN if url is None else url,
            notes="" if "notes" in cleared else NOT_GIVEN if notes is None else notes,
            rating=None if "rating" in cleared else NOT_GIVEN if rating is None else rating,
            preview=None
            if "preview" in cleared
            else NewPreview(source=preview, file=preview_file, url=preview_url)
            if previewed
            else NOT_GIVEN,
            add_tags=add_tag,
            remove_tags=remove_tag,
            store=store,
        )
    typer.echo(entry.model_dump_json(indent=2) if json else _describe_entry(entry))


@app.command()
def rename_entry(
    name: Annotated[str, typer.Argument(help="The entry's name.")],
    new_name: Annotated[str, typer.Argument(help="Its new name, which is also its folder's.")],
    store: Annotated[
        str | None,
        typer.Option(help="The store it is in. Without it, the store with the highest priority that has it."),
    ] = None,
    json: Annotated[bool, typer.Option("--json", help=JSON_HELP)] = False,
) -> None:
    """Rename an entry, and its folder with it. It keeps its id."""
    with _reported():
        entry = lib.rename_entry(name, new_name, store)
    typer.echo(entry.model_dump_json(indent=2) if json else _describe_entry(entry))


@app.command()
def move_entry(
    name: Annotated[str, typer.Argument(help="The entry's name.")],
    to_store: Annotated[str, typer.Argument(help="The store to move it to.")],
    store: Annotated[
        str | None,
        typer.Option(help="The store it is in. Without it, the store with the highest priority that has it."),
    ] = None,
    json: Annotated[bool, typer.Option("--json", help=JSON_HELP)] = False,
) -> None:
    """Move an entry and its files to another store. It keeps its name and its id."""
    with _reported():
        entry = lib.move_entry(name, to_store, store)
    typer.echo(entry.model_dump_json(indent=2) if json else _describe_entry(entry))


@app.command()
def delete_entry(
    name: Annotated[str, typer.Argument(help="The entry's name.")],
    store: Annotated[
        str | None,
        typer.Option(help="The store it is in. Without it, the store with the highest priority that has it."),
    ] = None,
) -> None:
    """Delete an entry and its files.

    When a file in it is open in a program that keeps it from being deleted, nothing is.
    """
    with _reported():
        lib.delete_entry(name, store)
    typer.echo(f"Deleted the entry {name} and its files.")


@app.command()
def list_entries(
    tag: Annotated[
        list[str] | None, typer.Option(help="Keep entries with this tag. Repeat it for each one, and they need all.")
    ] = None,
    file_tag: Annotated[
        list[str] | None,
        typer.Option(
            help="Keep entries with a file that has this tag. Repeat it for each one, and the file needs all."
        ),
    ] = None,
    any_: Annotated[
        bool, typer.Option("--any", help="One of the tags is enough, and one of the file tags on a file.")
    ] = False,
    min_rating: Annotated[int | None, typer.Option(help="Keep entries rated this or better, from 1 to 5.")] = None,
    site: Annotated[
        str | None,
        typer.Option(
            help="Keep entries that link to a site, such as github.com, or to a group on it, such as github.com/octocat."
        ),
    ] = None,
    store: Annotated[str | None, typer.Option(help="List only this store. Without it, every store.")] = None,
    sort: Annotated[
        EntrySort,
        typer.Option(help="What to order them by. Names, tags, and stores go from A. The rest start with the most."),
    ] = "created",
    descending: Annotated[
        bool | None, typer.Option("--descending/--ascending", help="Turn the order around.", show_default=False)
    ] = None,
    limit: Annotated[int, typer.Option(help="How many to list at once.")] = 100,
    after: Annotated[str | None, typer.Option(help="Carry on from the page that printed this.")] = None,
    json: Annotated[bool, typer.Option("--json", help=JSON_HELP)] = False,
) -> None:
    """List the entries a page at a time, newest first unless sorted otherwise.

    The title shows in brackets after the name, and the date is when the entry was added, or last changed with --sort updated.
    """
    with _reported():
        listing = lib.list_entries(
            tag, file_tag, "any" if any_ else "all", min_rating, site, store, sort, descending, limit, after
        )
    if json:
        typer.echo(listing.model_dump_json(indent=2))
        return
    if not listing.total:
        typer.echo("No entries match." if tag or file_tag or min_rating or site else "There are no entries.")
        return
    for entry in listing.entries:
        typer.echo(_describe_summary(entry, sort))
    shown = f"{len(listing.entries)} of {_counted(listing.total, 'entry', 'entries')}."
    typer.echo(f"{shown} For the next page: --after {listing.after}" if listing.after else shown)


@app.command()
def list_tags(
    store: Annotated[str | None, typer.Option(help="Count only this store. Without it, every store.")] = None,
    json: Annotated[bool, typer.Option("--json", help=JSON_HELP)] = False,
) -> None:
    """List each tag with how many entries and files have it, the most used first. Check it before making up a tag."""
    with _reported():
        tags = lib.list_tags(store)
    if json:
        typer.echo(TAGS.dump_json(tags, indent=2).decode())
        return
    if not tags:
        typer.echo("No entry or file has a tag yet.")
    for count in tags:
        counts = [
            _counted(number, one, many)
            for number, one, many in ((count.entries, "entry", "entries"), (count.files, "file", "files"))
            if number
        ]
        typer.echo(f"{count.tag}: {', '.join(counts)}")


@app.command()
def list_sites(
    store: Annotated[str | None, typer.Option(help="Count only this store. Without it, every store.")] = None,
    json: Annotated[bool, typer.Option("--json", help=JSON_HELP)] = False,
) -> None:
    """List each site the entries link to with how many do, the most first, and under it how many each group has.

    A group is a part of a site, such as an owner on GitHub, a user on X, or a subreddit. The sites with groups, and how to tell them, can be changed in config.json.
    """
    with _reported():
        sites = lib.list_sites(store)
    if json:
        typer.echo(SITES.dump_json(sites, indent=2).decode())
        return
    if not sites:
        typer.echo("No entry links to a site yet.")
    for site in sites:
        typer.echo(f"{site.site}: {_counted(site.entries, 'entry', 'entries')}")
        for group in site.groups:
            typer.echo(f"  {group.group}: {_counted(group.entries, 'entry', 'entries')}")


@app.command()
def add_files(
    name: Annotated[str, typer.Argument(help="The entry's name.")],
    source: Annotated[Path, typer.Argument(help="A file, or a folder to add with everything in it.")],
    path: Annotated[
        str | None,
        typer.Option(
            help="Where it goes in the entry, such as screenshots/menu.png. Ending in / puts it in that folder, and . "
            "puts what is in a folder at the top. Without it, the top, under its own name."
        ),
    ] = None,
    description: Annotated[str, typer.Option(help="What the file is. Not for a folder.")] = "",
    notes: Annotated[str, typer.Option(help="Anything else, such as what it is useful for. Not for a folder.")] = "",
    tag: Annotated[
        list[str] | None, typer.Option(help="A tag, which on a folder goes on every file. Repeat it for each one.")
    ] = None,
    move: Annotated[bool, typer.Option("--move", help="Move it in instead of copying it.")] = False,
    store: Annotated[
        str | None,
        typer.Option(help="The store it is in. Without it, the store with the highest priority that has it."),
    ] = None,
    json: Annotated[bool, typer.Option("--json", help=JSON_HELP)] = False,
) -> None:
    """Copy a file or a folder into an entry, or move it in with --move.

    A file that is already there is refused, and then nothing is added.
    """
    new = NewFile(source=source, path=path, description=description, notes=notes, tags=tag, move=move)
    with _reported():
        entry = lib.add_files(name, [new], store)
    typer.echo(entry.model_dump_json(indent=2) if json else _describe_entry(entry))


@app.command()
def update_file(
    name: Annotated[str, typer.Argument(help="The entry's name.")],
    path: Annotated[str, typer.Argument(help="The file in the entry, such as screenshots/menu.png, or a folder.")],
    description: Annotated[str | None, typer.Option(help="What the file is.")] = None,
    notes: Annotated[str | None, typer.Option(help="Anything else, such as what it is useful for.")] = None,
    add_tag: Annotated[list[str] | None, typer.Option(help="A tag to add. Repeat it for each one.")] = None,
    remove_tag: Annotated[list[str] | None, typer.Option(help="A tag to remove. Repeat it for each one.")] = None,
    clear: Annotated[
        list[FileClearable] | None,
        typer.Option(help="A field to clear. Repeat it for each one.", show_default=False),
    ] = None,
    store: Annotated[
        str | None,
        typer.Option(help="The store it is in. Without it, the store with the highest priority that has it."),
    ] = None,
    json: Annotated[bool, typer.Option("--json", help=JSON_HELP)] = False,
) -> None:
    """Change what is said about a file. Whatever is left out stays as it is.

    A folder only takes tags, and changes them on every file in it.
    """
    cleared = set(clear or [])
    for field, value in (("description", description), ("notes", notes)):
        if field in cleared and value is not None:
            raise typer.BadParameter(f"--{field} and --clear {field} can't both be given.", param_hint="--clear")
    with _reported():
        entry = lib.update_file(
            name,
            path,
            description="" if "description" in cleared else NOT_GIVEN if description is None else description,
            notes="" if "notes" in cleared else NOT_GIVEN if notes is None else notes,
            add_tags=add_tag,
            remove_tags=remove_tag,
            store=store,
        )
    typer.echo(entry.model_dump_json(indent=2) if json else _describe_entry(entry))


@app.command()
def rename_file(
    name: Annotated[str, typer.Argument(help="The entry's name.")],
    path: Annotated[str, typer.Argument(help="The file or folder in the entry.")],
    new_path: Annotated[str, typer.Argument(help="Its new path in the entry. Ending in /, a folder to move it into.")],
    store: Annotated[
        str | None,
        typer.Option(help="The store it is in. Without it, the store with the highest priority that has it."),
    ] = None,
    json: Annotated[bool, typer.Option("--json", help=JSON_HELP)] = False,
) -> None:
    """Rename a file or a folder in an entry, or move it to another folder there.

    What was said about it, and the preview, go with it.
    """
    with _reported():
        entry = lib.rename_file(name, path, new_path, store)
    typer.echo(entry.model_dump_json(indent=2) if json else _describe_entry(entry))


@app.command()
def delete_file(
    name: Annotated[str, typer.Argument(help="The entry's name.")],
    path: Annotated[str, typer.Argument(help="The file or folder in the entry.")],
    store: Annotated[
        str | None,
        typer.Option(help="The store it is in. Without it, the store with the highest priority that has it."),
    ] = None,
    json: Annotated[bool, typer.Option("--json", help=JSON_HELP)] = False,
) -> None:
    """Delete a file from an entry, or a folder and everything in it."""
    with _reported():
        entry = lib.delete_file(name, path, store)
    typer.echo(entry.model_dump_json(indent=2) if json else _describe_entry(entry))


@app.command()
def skill() -> None:
    """Print the tool's skill, which tells an agent how to use it."""
    typer.echo(lib.skill())


@app.command("app")
def app_(
    port: Annotated[int | None, typer.Option(help="The port to bind; a free one is chosen when omitted.")] = None,
) -> None:
    """Serve the app in a browser page on this machine and print its URL.

    Keeps serving until Ctrl+C.
    """
    app_server = lib.app_server()
    with _reported():
        typer.echo(app_server.open(port).url)
    with contextlib.suppress(KeyboardInterrupt):
        while True:
            time.sleep(1)
    app_server.close()


def main() -> None:
    """Runs the command line."""
    app()
