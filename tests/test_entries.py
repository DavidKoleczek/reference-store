"""Adding entries and reading them back with their files, from the CLI."""

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest
from typer.testing import CliRunner

from reference_store.cli import app

runner = CliRunner()


def run(*args: str) -> Any:
    result = runner.invoke(app, [*args, "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


def refused(*args: str) -> None:
    result = runner.invoke(app, list(args))
    assert (result.exit_code, bool(result.stderr)) == (1, True), args


def test_an_entry_is_kept_as_plain_files_and_read_back_with_the_files_put_there_by_hand(workspace: Path) -> None:
    run("add-store", "main", "main")
    cover = workspace / "cover.png"
    cover.write_bytes(b"an image")
    added = run(
        "add-entry", "game-1",
        "--title", "Game 1: The First One",
        "--description", "A co-op puzzle game.",
        "--url", "https://example.com/game-1",
        "--tag", "game", "--tag", " Puzzle ", "--tag", "puzzle",
        "--notes", "Good menus.",
        "--rating", "4",
        "--preview", str(cover),
        "--preview-url", "https://example.com/game-1/cover.png",
        "--created", "2026-01-05T18:30:00Z",
        "--source-published-at", "2024-03-05T09:15:00+01:00",
    )  # fmt: skip
    folder = workspace / "main" / "game-1"
    assert Path(added["folder"]) == folder
    saved = json.loads((folder / ".entry.json").read_text(encoding="utf-8"))
    assert list(saved) == [
        "id", "title", "description", "url", "tags", "notes", "rating", "preview", "source_published_at", "created",
        "updated", "files",
    ]  # fmt: skip
    assert saved | {"id": None, "updated": None} == {
        "id": None,
        "title": "Game 1: The First One",
        "description": "A co-op puzzle game.",
        "url": "https://example.com/game-1",
        "tags": ["game", "Puzzle"],
        "notes": "Good menus.",
        "rating": 4,
        "preview": {"file": ".preview.png", "url": "https://example.com/game-1/cover.png"},
        "source_published_at": "2024-03-05T08:15:00Z",
        "created": "2026-01-05T18:30:00Z",
        "updated": None,
        "files": {},
    }
    assert (folder / ".preview.png").read_bytes() == b"an image"
    assert (added["file_count"], added["files"]) == (0, [])

    for path, text in [
        ("notes.md", "# Notes"),
        ("shots/menu.png", "menu"),
        ("shots-old/menu.png", "old"),
        (".gitignore", "*"),
    ]:
        (folder / path).parent.mkdir(exist_ok=True)
        (folder / path).write_text(text, encoding="utf-8")
    saved["files"] = {"SHOTS/menu.png": {"description": "The pause menu.", "notes": "", "tags": ["ux"]}}
    (folder / ".entry.json").write_text(json.dumps(saved), encoding="utf-8")

    entry = run("get-entry", "GAME-1")
    assert entry["name"] == "game-1"
    assert (entry["id"], entry["source_published_at"]) == (added["id"], "2024-03-05T08:15:00Z")
    assert [file["path"] for file in entry["files"]] == [
        ".gitignore",
        "notes.md",
        "shots/menu.png",
        "shots-old/menu.png",
    ]
    assert (entry["file_count"], entry["size"]) == (4, 1 + 7 + 4 + 3)
    menu = entry["files"][2]
    assert (menu["description"], menu["tags"], Path(menu["full_path"])) == (
        "The pause menu.",
        ["ux"],
        folder / "shots" / "menu.png",
    )
    assert Path(entry["preview"]["path"]) == folder / ".preview.png"

    (folder / ".preview.png").unlink()
    assert run("get-entry", "game-1")["preview"] is None
    text = runner.invoke(app, ["get-entry", "game-1"]).stdout
    assert "title: Game 1: The First One\n" in text
    assert "\npublished: 2024-03-0" in text
    assert "  shots/menu.png  4 bytes  [ux]  The pause menu.\n" in text


def test_entries_go_to_the_right_store_and_are_found_in_priority_order(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    refused("add-entry", "game-1")
    run("add-store", "first", "first")
    run("add-store", "second", "second")

    assert run("add-entry", "game-1")["store"] == "first"
    assert run("add-entry", "game-1", "--store", "SECOND")["store"] == "second"
    assert run("get-entry", "game-1")["store"] == "first"
    assert run("get-entry", "game-1", "--store", "second")["store"] == "second"
    run("set-store-priority", "second", "1")
    assert run("get-entry", "game-1")["store"] == "second"

    project = workspace / "game-project"
    (project / ".reference-store").mkdir(parents=True)
    monkeypatch.chdir(project)
    assert run("add-entry", "game-1")["store"] == "game-project"
    assert (project / ".reference-store" / ".store.json").is_file()
    assert run("get-entry", "game-1")["store"] == "game-project"
    monkeypatch.chdir(workspace)
    assert run("get-entry", "game-1")["store"] == "second"

    by_hand = workspace / "first" / "by-hand"
    by_hand.mkdir()
    (by_hand / ".entry.json").write_text('{"tags": ["made by hand"]}', encoding="utf-8")
    first_read = run("get-entry", "by-hand")
    assert first_read["tags"] == ["made by hand"]
    assert run("get-entry", "by-hand")["id"] == first_read["id"]
    assert json.loads((by_hand / ".entry.json").read_text(encoding="utf-8"))["id"] == first_read["id"]

    (workspace / "first" / "plain").mkdir()
    (workspace / "image.txt").write_text("not an image", encoding="utf-8")
    deep = workspace / ("d" * (217 - len(str(workspace)) - 1))
    deep.mkdir()
    run("add-store", "deep", str(deep))
    before = sorted(path.relative_to(workspace) for path in workspace.rglob("*"))
    for refusal in [
        ["add-entry", "GAME-1", "--store", "first"],
        ["add-entry", "plain", "--store", "first"],
        ["add-entry", "bad:name"],
        ["add-entry", "game-2", "--rating", "6"],
        ["add-entry", "game-2", "--preview", "missing.png"],
        ["add-entry", "game-2", "--preview", "image.txt"],
        ["add-entry", "game-2", "--store", "nope"],
        ["add-entry", "a" * 31, "--store", "deep"],
        ["get-entry", "nope"],
        ["get-entry", "by-hand", "--store", "second"],
    ]:
        refused(*refusal)
    assert sorted(path.relative_to(workspace) for path in workspace.rglob("*")) == before
    run("add-entry", "a" * 29, "--store", "deep")

    (workspace / "second").rename(workspace / "away")
    refused("get-entry", "game-1", "--store", "second")
    assert run("get-entry", "game-1")["store"] == "first"


def test_what_is_printed_to_a_pipe_keeps_every_character(workspace: Path) -> None:
    run("add-store", "main", "main")
    star = chr(0x2605)
    run("add-entry", "game-1", "--description", f"A co-op puzzle game. {star}")
    command = [sys.executable, "-c", "from reference_store.cli import main; main()"]
    # The code page Windows gives a pipe, which has no star.
    on_windows = {**os.environ, "PYTHONIOENCODING": "cp1252"}

    shown = subprocess.run([*command, "get-entry", "game-1"], env=on_windows, capture_output=True, check=False)
    assert shown.returncode == 0, shown.stderr
    assert f"description: A co-op puzzle game. {star}" in shown.stdout.decode("utf-8")
    missing = subprocess.run([*command, "get-entry", f"game-{star}"], env=on_windows, capture_output=True, check=False)
    assert (missing.returncode, f"game-{star}" in missing.stderr.decode("utf-8")) == (1, True)
