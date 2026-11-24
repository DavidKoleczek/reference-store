"""The command line. Each command parses its arguments, calls the library, and prints the result."""

import contextlib
import time
from typing import Annotated

import typer

from reference_store import lib
from reference_store.models import ReferenceStoreError
from reference_store.skill.skill import DISTRIBUTION

app = typer.Typer(
    name=DISTRIBUTION,
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


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
    try:
        typer.echo(app_server.open(port).url)
    except ReferenceStoreError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from None
    with contextlib.suppress(KeyboardInterrupt):
        while True:
            time.sleep(1)
    app_server.close()


def main() -> None:
    """Runs the command line."""
    app()
