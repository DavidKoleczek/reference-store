"""Adding files to an entry, and describing, renaming, and deleting them, from the CLI."""

from collections.abc import Callable
import errno
import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from reference_store.cli import app
from reference_store.core import disk

runner = CliRunner()


def run(*args: str) -> Any:
    result = runner.invoke(app, [*args, "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


def refused(*args: str) -> str:
    result = runner.invoke(app, list(args))
    assert (result.exit_code, bool(result.stderr)) == (1, True), args
    return result.stderr


def on_disk(folder: Path) -> list[str]:
    return sorted(path.relative_to(folder).as_posix() for path in folder.rglob("*"))


def said(entry: dict[str, Any]) -> dict[str, tuple[str, list[str]]]:
    return {file["path"]: (file["description"], file["tags"]) for file in entry["files"]}


def make_inbox(inbox: Path) -> None:
    (inbox / "captures").mkdir(parents=True)
    for number in (1, 2, 3):
        (inbox / "captures" / f"level-{number}.png").write_bytes(b"level")
    (inbox / "extra" / "docs").mkdir(parents=True)
    (inbox / "extra" / "trailer.txt").write_text("trailer", encoding="utf-8")
    (inbox / "extra" / "docs" / "readme.md").write_text("# Readme", encoding="utf-8")
    (inbox / "menu.png").write_bytes(b"menu")
    (inbox / "notes.md").write_text("# Notes", encoding="utf-8")


def test_files_are_added_described_renamed_and_deleted_with_what_was_said_about_them(workspace: Path) -> None:
    run("add-store", "main", "main")
    inbox = workspace / "inbox"
    make_inbox(inbox)
    run("add-entry", "game-1")
    folder = workspace / "main" / "game-1"

    run(
        "add-files", "game-1", str(inbox / "menu.png"), "--path", "screenshots/menu.png",
        "--description", "The pause menu.", "--tag", "ux",
    )  # fmt: skip
    run("add-files", "game-1", str(inbox / "captures"), "--path", "SCREENSHOTS/", "--tag", "gameplay")
    run("add-files", "game-1", str(inbox / "notes.md"), "--move")
    entry = run("add-files", "game-1", str(inbox / "extra"), "--path", ".", "--move")
    assert said(entry) == {
        "docs/readme.md": ("", []),
        "notes.md": ("", []),
        "screenshots/captures/level-1.png": ("", ["gameplay"]),
        "screenshots/captures/level-2.png": ("", ["gameplay"]),
        "screenshots/captures/level-3.png": ("", ["gameplay"]),
        "screenshots/menu.png": ("The pause menu.", ["ux"]),
        "trailer.txt": ("", []),
    }
    assert on_disk(inbox) == ["captures", "captures/level-1.png", "captures/level-2.png", "captures/level-3.png",
                              "menu.png"]  # fmt: skip

    long_store = workspace / ("d" * (217 - len(str(workspace)) - 1))
    run("add-store", "deep", str(long_store))
    run("add-entry", "g", "--store", "deep")
    # The entry's folder is 219 characters, so a folder in it can have a name of 27 and a file one of 39.
    before = on_disk(workspace)
    for refusal in [
        ["add-files", "game-1", str(inbox / "menu.png"), "--path", "screenshots/menu.png"],
        ["add-files", "game-1", str(inbox / "menu.png"), "--path", "SCREENSHOTS/MENU.PNG"],
        ["add-files", "game-1", str(inbox / "menu.png"), "--path", "notes.md/menu.png"],
        ["add-files", "game-1", str(inbox / "menu.png"), "--path", ".entry.json"],
        ["add-files", "game-1", str(inbox / "menu.png"), "--path", "../menu.png"],
        ["add-files", "game-1", str(inbox / "menu.png"), "--path", "a:b.png"],
        ["add-files", "game-1", str(inbox / "captures"), "--description", "Levels."],
        ["add-files", "game-1", str(inbox / "missing.png")],
        ["add-files", "game-1", str(folder / "notes.md"), "--path", "notes-2.md"],
        ["add-files", "game-1", str(workspace / "main")],
        ["add-files", "g", str(inbox / "menu.png"), "--path", f"{'s' * 28}/menu.png", "--store", "deep"],
        ["add-files", "g", str(inbox / "menu.png"), "--path", f"{'m' * 36}.png", "--store", "deep"],
        ["add-entry", "game-2", "--file", str(inbox / "menu.png"), "--preview-file", "nope.png"],
        ["update-file", "game-1", "screenshots", "--description", "Shots."],
        ["update-file", "game-1", "nope.png", "--add-tag", "ux"],
        ["rename-file", "game-1", "screenshots", "screenshots/old/"],
        ["rename-file", "game-1", "notes.md", "screenshots/menu.png"],
        ["rename-file", "game-1", "notes.md", ".preview.png"],
        ["delete-file", "game-1", ".entry.json"],
    ]:
        refused(*refusal)
    assert on_disk(workspace) == before
    run("add-files", "g", str(inbox / "menu.png"), "--path", f"{'s' * 27}/menu.png", "--store", "deep")
    run("add-files", "g", str(inbox / "menu.png"), "--path", f"{'m' * 35}.png", "--store", "deep")

    added = run("add-entry", "game-2", "--file", str(inbox / "menu.png"), "--preview-file", "MENU.png")
    assert (Path(added["preview"]["path"]), added["file_count"]) == (workspace / "main" / "game-2" / "menu.png", 1)

    run("update-entry", "game-1", "--preview-file", "screenshots/menu.png")
    run("update-file", "game-1", "SCREENSHOTS/CAPTURES", "--add-tag", "levels", "--remove-tag", "GAMEPLAY")
    run("update-file", "game-1", "notes.md", "--description", "What to look at.", "--notes", "Read first.")
    run("update-file", "game-1", "notes.md", "--clear", "notes")
    entry = run("rename-file", "game-1", "screenshots/menu.png", "ui/pause-menu.png")
    assert Path(entry["preview"]["path"]) == folder / "ui" / "pause-menu.png"
    entry = run("rename-file", "game-1", "screenshots/captures", ".")
    assert said(entry) == {
        "captures/level-1.png": ("", ["levels"]),
        "captures/level-2.png": ("", ["levels"]),
        "captures/level-3.png": ("", ["levels"]),
        "docs/readme.md": ("", []),
        "notes.md": ("What to look at.", []),
        "trailer.txt": ("", []),
        "ui/pause-menu.png": ("The pause menu.", ["ux"]),
    }
    assert not (folder / "screenshots").exists()

    (folder / "ui" / "pause-menu.png").rename(folder / "ui" / "menu.png")
    entry = run("get-entry", "game-1")
    assert (entry["preview"], said(entry)["ui/menu.png"]) == (None, ("", []))
    run("delete-file", "game-1", "captures")
    entry = run("delete-file", "game-1", "ui/menu.png")
    assert [file["path"] for file in entry["files"]] == ["docs/readme.md", "notes.md", "trailer.txt"]
    # What was said about the file renamed by hand stays, for when it is renamed back.
    saved = json.loads((folder / ".entry.json").read_text(encoding="utf-8"))
    assert (saved["preview"]["file"], list(saved["files"])) == ("ui/pause-menu.png", ["notes.md", "ui/pause-menu.png"])
    assert on_disk(folder) == [".entry.json", "docs", "docs/readme.md", "notes.md", "trailer.txt"]


def test_moving_from_another_drive_copies_and_a_failed_add_puts_everything_back(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run("add-store", "main", "main")
    run("add-entry", "game-1")
    inbox = workspace / "inbox"
    make_inbox(inbox)
    rename = disk.rename

    def failing(when: Callable[[int], OSError | None]) -> None:
        calls: list[Path] = []

        def renamed(source: Path, target: Path) -> None:
            calls.append(source)
            error = when(len(calls))
            if error is not None:
                raise error
            rename(source, target)

        monkeypatch.setattr(disk, "rename", renamed)

    failing(lambda _: OSError(errno.EXDEV, "Not the same device"))
    entry = run("add-files", "game-1", str(inbox / "extra"), "--move")
    assert [file["path"] for file in entry["files"]] == ["extra/docs/readme.md", "extra/trailer.txt"]
    assert not (inbox / "extra").exists()

    before = on_disk(workspace)
    failing(lambda call: OSError(errno.EACCES, "Access is denied") if call == 3 else None)
    assert "Nothing was added" in refused("add-files", "game-1", str(inbox / "captures"), "--path", "shots/", "--move")
    assert on_disk(workspace) == before
