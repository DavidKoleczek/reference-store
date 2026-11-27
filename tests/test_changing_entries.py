"""Changing, renaming, moving, and deleting entries, from the CLI."""

import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from typer.testing import CliRunner

from reference_store.cli import app

runner = CliRunner()


def run(*args: str) -> Any:
    result = runner.invoke(app, [*args, "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


def done(*args: str) -> str:
    result = runner.invoke(app, list(args))
    assert result.exit_code == 0, result.output
    return result.stdout


def refused(*args: str) -> None:
    result = runner.invoke(app, list(args))
    assert (result.exit_code, bool(result.stderr)) == (1, True), args


def on_disk(folder: Path) -> list[str]:
    return sorted(path.relative_to(folder).as_posix() for path in folder.rglob("*"))


def test_an_entry_is_changed_renamed_moved_and_deleted_with_what_is_in_it(workspace: Path) -> None:
    run("add-store", "main", "main")
    deep = workspace / ("d" * (217 - len(str(workspace)) - 1))
    run("add-store", "deep", str(deep))
    (workspace / "cover.png").write_bytes(b"cover")
    (workspace / "photo.webp").write_bytes(b"photo")
    added = run(
        "add-entry", "game-1", "--description", "A game.", "--url", "https://example.com/game-1", "--tag", "game",
        "--tag", "Puzzle", "--rating", "3", "--preview", "cover.png", "--preview-url", "https://example.com/cover.png",
    )  # fmt: skip
    folder = workspace / "main" / "game-1"
    (folder / "shots").mkdir()
    (folder / "shots" / "menu.png").write_bytes(b"menu")
    (folder / "notes.md").write_text("# Notes", encoding="utf-8")

    changed = run(
        "update-entry", "GAME-1", "--title", "Game 1: The First One", "--rating", "5", "--add-tag", "PUZZLE",
        "--add-tag", "ux", "--remove-tag", "GAME", "--clear", "url", "--source-published-at", "2024-03-05T09:15:00+01:00",
    )  # fmt: skip
    kept = ("id", "title", "description", "url", "tags", "rating", "source_published_at", "created")
    assert {key: changed[key] for key in kept} == {
        "id": added["id"],
        "title": "Game 1: The First One",
        "description": "A game.",
        "url": None,
        "tags": ["Puzzle", "ux"],
        "rating": 5,
        "source_published_at": "2024-03-05T08:15:00Z",
        "created": added["created"],
    }
    saved = (folder / ".entry.json").read_bytes()
    run(
        "update-entry", "game-1", "--add-tag", "UX", "--remove-tag", "game", "--source-published-at",
        "2024-03-05T08:15:00Z",
    )  # fmt: skip
    assert (folder / ".entry.json").read_bytes() == saved

    def preview() -> Any:
        return json.loads((folder / ".entry.json").read_text(encoding="utf-8"))["preview"]

    run("update-entry", "game-1", "--preview-file", "SHOTS/MENU.PNG")
    assert (preview(), on_disk(folder)) == (
        {"file": "shots/menu.png", "url": None},
        [".entry.json", "notes.md", "shots", "shots/menu.png"],
    )
    run("update-entry", "game-1", "--preview-url", "https://example.com/menu")
    assert preview() == {"file": "shots/menu.png", "url": "https://example.com/menu"}
    run("update-entry", "game-1", "--preview", "photo.webp")
    assert (folder / ".preview.webp").read_bytes() == b"photo"
    run("update-entry", "game-1", "--preview", "cover.png")
    assert (preview(), (folder / ".preview.png").is_file(), (folder / ".preview.webp").exists()) == (
        {"file": ".preview.png", "url": None},
        True,
        False,
    )
    cleared = run(
        "update-entry", "game-1", "--clear", "preview", "--clear", "description", "--clear", "source_published_at"
    )
    assert (cleared["preview"], cleared["description"], cleared["source_published_at"], cleared["file_count"]) == (
        None,
        "",
        None,
        2,
    )
    assert on_disk(folder) == [".entry.json", "notes.md", "shots", "shots/menu.png"]

    run("add-entry", "game-2")
    run("add-entry", "game-1", "--store", "deep")
    before = on_disk(workspace)
    for refusal in [
        ["update-entry", "game-1", "--rating", "6"],
        ["update-entry", "game-1", "--add-tag", "ux", "--remove-tag", "UX"],
        ["update-entry", "game-1", "--preview-file", "notes.md"],
        ["update-entry", "game-1", "--preview-file", "missing.png"],
        ["update-entry", "game-1", "--preview-url", "https://example.com/cover.png"],
        ["update-entry", "nope", "--rating", "1"],
        ["rename-entry", "game-1", "bad:name"],
        ["rename-entry", "game-1", "GAME-2"],
        ["move-entry", "game-1", "main"],
        ["move-entry", "game-1", "nope"],
        ["move-entry", "game-1", "deep"],
    ]:
        refused(*refusal)
    for misused in [
        ["--url", "https://example.com", "--clear", "url"],
        ["--source-published-at", "2024-03-05", "--clear", "source_published_at"],
        ["--source-published-at", "last week"],
    ]:
        assert runner.invoke(app, ["update-entry", "game-1", *misused]).exit_code == 2, misused
    assert on_disk(workspace) == before

    renamed = run("rename-entry", "game-1", "Game-One")
    assert (renamed["id"], renamed["name"], on_disk(workspace / "main")) == (
        added["id"],
        "Game-One",
        [".store.json", "Game-One", "Game-One/.entry.json", "Game-One/notes.md", "Game-One/shots",
         "Game-One/shots/menu.png", "game-2", "game-2/.entry.json"],
    )  # fmt: skip
    assert run("rename-entry", "game-one", "game-one")["name"] == "game-one"
    assert [path.name for path in (workspace / "main").iterdir()] == [".store.json", "game-2", "game-one"]

    assert done("delete-entry", "game-1", "--store", "deep") == "Deleted the entry game-1 and its files.\n"
    moved = run("move-entry", "game-one", "deep")
    assert (moved["id"], moved["store"], moved["file_count"]) == (added["id"], "deep", 2)
    assert on_disk(workspace / "main") == [".store.json", "game-2", "game-2/.entry.json"]
    # The longest path in the entry, shots/menu.png, has to stay within 259 characters.
    longest_name = 259 - len(str(deep)) - len("//shots/menu.png")
    refused("rename-entry", "game-one", "g" * (longest_name + 1))
    run("rename-entry", "game-one", "g" * longest_name)

    done("delete-entry", "g" * longest_name)
    refused("get-entry", "g" * longest_name)
    assert on_disk(deep) == [".store.json"]


def test_processes_changing_one_entry_at_once_all_keep_their_change(workspace: Path) -> None:
    run("add-store", "main", "main")
    run("add-entry", "game-1")
    command = [sys.executable, "-c", "from reference_store.cli import main; main()", "update-entry", "game-1"]
    processes = [
        subprocess.Popen(
            [*command, "--add-tag", f"tag-{number}"],
            cwd=workspace,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        for number in range(8)
    ]
    for process in processes:
        _, error = process.communicate(timeout=120)
        assert process.returncode == 0, error
    assert sorted(run("get-entry", "game-1")["tags"]) == [f"tag-{number}" for number in range(8)]
