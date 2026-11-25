"""The command line. Each command parses its arguments, calls the library, and prints the result."""

from collections.abc import Generator
import contextlib
import time
from typing import Annotated

from pydantic import TypeAdapter
import typer

from reference_store import lib
from reference_store.models import ReferenceStoreError, Store
from reference_store.skill.skill import DISTRIBUTION

JSON_HELP = "Print the result as JSON."
STORES = TypeAdapter(list[Store])

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
