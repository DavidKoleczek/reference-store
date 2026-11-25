"""The command line. Each command parses its arguments, calls the library, and prints the result."""

from collections.abc import Generator
import contextlib
from datetime import datetime
from pathlib import Path
import time
from typing import Annotated

from pydantic import TypeAdapter
import typer

from reference_store import lib
from reference_store.models import Entry, NewPreview, ReferenceStoreError, Store
from reference_store.skill.skill import DISTRIBUTION

JSON_HELP = "Print the result as JSON."
STORES = TypeAdapter(list[Store])
SIZE_UNITS = ("bytes", "KB", "MB", "GB", "TB")

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
    preview_url: Annotated[str | None, typer.Option(help="Where the preview image came from.")] = None,
    created: Annotated[
        str | None, typer.Option(help="When it was first saved, such as 2026-01-05 or 2026-01-05T18:30:00Z.")
    ] = None,
    store: Annotated[
        str | None, typer.Option(help="The store to add it to. Without it, the project's store or the default.")
    ] = None,
    json: Annotated[bool, typer.Option("--json", help=JSON_HELP)] = False,
) -> None:
    """Add an entry: one reference, such as a repo, a website, or a game with its screenshots.

    It only saves what it is given, and never fetches anything.
    """
    new_preview = NewPreview(source=preview, url=preview_url) if preview or preview_url else None
    with _reported():
        entry = lib.add_entry(
            name, title, description, url, tag, notes, rating, new_preview, _moment(created, "--created"), store
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
