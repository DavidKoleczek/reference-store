"""The index that listing and search read: what it keeps up with at once, and what waits for a check or a rebuild."""

import contextlib
import json
from pathlib import Path
import shutil
import sqlite3
import time
from typing import Any

from typer.testing import CliRunner

from reference_store.cli import app
from reference_store.core import config, filters
from reference_store.core.catalog import index, upkeep
from reference_store.core.catalog.indexed import Indexed
from reference_store.core.catalog.scanned import Scanned
from reference_store.models import FileMatch

runner = CliRunner()


def run(*args: str) -> Any:
    result = runner.invoke(app, [*args, "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


def entries() -> list[str]:
    """Every entry listed, as its name, how many files it has, and its description."""
    listed = run("list-entries", "--sort", "name")["entries"]
    return [f"{entry['name']} {entry['file_count']} {entry['description']}".strip() for entry in listed]


def files(pattern: str = "**") -> list[str]:
    return [f"{file['entry']}/{file['path']}" for file in run("glob-files", pattern)["files"]]


def in_order(found: list[FileMatch]) -> list[FileMatch]:
    return sorted(found, key=lambda file: (file.store, file.entry, file.path))


def index_is_what_the_folders_hold() -> None:
    """The catalog read from the index gives what the one read from the folders does."""
    scanned = Scanned()
    narrowed = filters.filters(["game"], ["ux"], "any", 2, None)
    with contextlib.closing(index.connect()) as connection:
        indexed = Indexed(connection)
        for keep in (filters.EVERYTHING, narrowed):
            assert indexed.summaries(keep, None) == scanned.summaries(keep, None)
            assert list(indexed.entries(keep, None)) == list(scanned.entries(keep, None))
            for wanted in (lambda entry, path: True, lambda entry, path: path.endswith(".png")):
                # Files come in no order, since what lists them sorts them.
                assert in_order(indexed.files(keep, None, wanted)) == in_order(scanned.files(keep, None, wanted))
        assert list(indexed.tags(None)) == list(scanned.tags(None))


def test_the_index_keeps_up_with_the_library_and_catches_up_with_changes_by_hand(workspace: Path) -> None:
    run("add-store", "alpha", "alpha")
    run("add-store", "beta", "beta")
    inbox = workspace / "inbox"
    inbox.mkdir()
    (inbox / "menu.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (inbox / "notes.md").write_text("Notes.\n", encoding="utf-8")
    run("add-entry", "game-1", "--tag", "game", "--rating", "4", "--preview", str(inbox / "menu.png"))
    run("add-files", "game-1", str(inbox / "menu.png"), "--path", "screenshots/", "--tag", "ux")
    run("add-entry", "game-2", "--description", "Second.", "--file", str(inbox / "notes.md"))
    run("add-entry", "game-1", "--store", "beta", "--tag", "game", "--file", str(inbox / "notes.md"))

    assert entries() == ["game-1 1", "game-1 1", "game-2 1 Second."]
    assert (config.home() / "index" / "index.sqlite").is_file()
    index_is_what_the_folders_hold()

    # What the library changes shows in the next read.
    run("update-entry", "game-2", "--description", "Changed.", "--add-tag", "game")
    run("update-file", "game-2", "notes.md", "--add-tag", "ux")
    run("rename-entry", "game-2", "Game-2")
    run("add-files", "Game-2", str(inbox / "menu.png"), "--path", "art/")
    run("rename-file", "Game-2", "art/menu.png", "art/title.png")
    run("add-entry", "game-3", "--file", str(inbox / "notes.md"))
    run("delete-file", "game-3", "notes.md")
    run("move-entry", "game-3", "beta")
    assert entries() == ["game-1 1", "game-1 1", "Game-2 2 Changed.", "game-3 0"]
    assert files("game-2/**") == ["Game-2/art/title.png", "Game-2/notes.md"]
    assert [tag["tag"] for tag in run("list-tags")] == ["game", "ux"]
    assert [entry["store"] for entry in run("list-entries", "--sort", "name")["entries"]][-1] == "beta"
    index_is_what_the_folders_hold()
    assert runner.invoke(app, ["delete-entry", "game-3"]).exit_code == 0
    assert entries() == ["game-1 1", "game-1 1", "Game-2 2 Changed."]

    # So does an entry added, renamed, or removed by hand.
    by_hand = workspace / "alpha" / "by-hand"
    by_hand.mkdir()
    (by_hand / ".entry.json").write_text('{"description": "Written by hand."}', encoding="utf-8")
    (by_hand / "page.html").write_text("<p>Hello.</p>", encoding="utf-8")
    assert entries() == ["by-hand 1 Written by hand.", "game-1 1", "game-1 1", "Game-2 2 Changed."]
    by_hand.rename(workspace / "alpha" / "renamed")
    shutil.rmtree(workspace / "beta" / "game-1")
    assert entries() == ["game-1 1", "Game-2 2 Changed.", "renamed 1 Written by hand."]
    index_is_what_the_folders_hold()

    # A file added by hand, and an `.entry.json` saved in place, wait: for the entry to be read by itself,
    game_1 = workspace / "alpha" / "game-1"
    shutil.copy(inbox / "menu.png", game_1 / "screenshots" / "pause.png")
    shutil.copy(inbox / "notes.md", game_1 / "notes.md")
    assert files("game-1/**") == ["game-1/screenshots/menu.png"]
    assert run("get-entry", "game-1")["file_count"] == 3
    assert files("game-1/**") == ["game-1/notes.md", "game-1/screenshots/menu.png", "game-1/screenshots/pause.png"]

    # for the check of everything in the store,
    record = json.loads((game_1 / ".entry.json").read_text(encoding="utf-8"))
    (game_1 / ".entry.json").write_text(json.dumps({**record, "description": "Edited in place."}), encoding="utf-8")
    (game_1 / "screenshots" / "pause.png").unlink()
    (workspace / "alpha" / "renamed" / ".entry.json").unlink()
    assert entries() == ["game-1 3", "Game-2 2 Changed.", "renamed 1 Written by hand."]
    with contextlib.closing(index.connect()) as connection:
        upkeep.check_store(connection, workspace / "alpha")
    assert entries() == ["game-1 2 Edited in place.", "Game-2 2 Changed."]
    index_is_what_the_folders_hold()

    # or for a rebuild.
    (game_1 / "notes.md").unlink()
    assert entries() == ["game-1 2 Edited in place.", "Game-2 2 Changed."]
    result = runner.invoke(app, ["rebuild-index"])
    assert (result.exit_code, result.stdout) == (0, "Rebuilt the index.\n")
    assert entries() == ["game-1 1 Edited in place.", "Game-2 2 Changed."]

    # The index is made again when it is deleted, or isn't a database.
    shutil.rmtree(config.home() / "index")
    assert entries() == ["game-1 1 Edited in place.", "Game-2 2 Changed."]
    (config.home() / "index" / "index.sqlite").write_text("Not a database.", encoding="utf-8")
    for leftover in (config.home() / "index").glob("index.sqlite-*"):
        leftover.unlink()
    assert entries() == ["game-1 1 Edited in place.", "Game-2 2 Changed."]
    index_is_what_the_folders_hold()


def test_a_read_starts_the_check_of_everything_once_the_last_one_is_a_day_old(workspace: Path) -> None:
    run("add-store", "alpha", "alpha")
    (workspace / "menu.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    run("add-entry", "game-1")
    run("add-files", "game-1", str(workspace / "menu.png"), "--path", "screenshots/")
    assert files() == ["game-1/screenshots/menu.png"]
    shutil.copy(workspace / "menu.png", workspace / "alpha" / "game-1" / "screenshots" / "pause.png")

    def stores() -> list[tuple[float, float | None]]:
        with contextlib.closing(sqlite3.connect(index.location())) as connection:
            return connection.execute("select checked, started from stores").fetchall()

    # Within the day, a read starts nothing.
    assert files() == ["game-1/screenshots/menu.png"]
    assert [started for _, started in stores()] == [None]

    with contextlib.closing(sqlite3.connect(index.location())) as connection, connection:
        connection.execute("update stores set checked = checked - 2 * ?", (upkeep.CHECK_EVERY_SECONDS,))
    # The read that starts the check doesn't wait for it, and reads from then on find what it found.
    files()
    assert [started is not None for _, started in stores()] == [True]
    waited_until = time.monotonic() + 60
    while files() != ["game-1/screenshots/menu.png", "game-1/screenshots/pause.png"]:
        assert time.monotonic() < waited_until, "The check never finished."
        time.sleep(0.2)
    checked, _ = stores()[0]
    assert time.time() - checked < 60
