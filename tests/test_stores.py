"""Registering stores on a machine and finding a project's own store, from the CLI."""

import json
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


def order() -> list[tuple[str, int, bool, bool]]:
    """Each store's name, priority, whether it is the default, and whether it is available, in order."""
    return [
        (store["name"], store["priority_order"], store["default"], store["available"]) for store in run("list-stores")
    ]


def test_stores_are_registered_ordered_and_removed(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = workspace / "game-project"
    (project / ".reference-store").mkdir(parents=True)
    (project / "src").mkdir()
    monkeypatch.chdir(project / "src")
    assert order() == [("game-project", 0, False, True)]
    monkeypatch.chdir(workspace)
    assert order() == []

    main = run("add-store", "main", "stores/main")
    assert Path(main["path"]) == workspace / "stores" / "main"
    assert [path.name for path in (workspace / "stores" / "main").iterdir()] == [".store.json"]
    (workspace / "notes").mkdir()
    (workspace / "notes" / "todo.md").write_text("Read later.", encoding="utf-8")
    run("add-store", "notes", "notes")
    assert sorted(path.name for path in (workspace / "notes").iterdir()) == [".store.json", "todo.md"]
    refs = run("add-store", "refs", str(project))
    assert Path(refs["path"]) == project / ".reference-store"
    assert order() == [("main", 1, True, True), ("notes", 2, False, True), ("refs", 3, False, True)]

    monkeypatch.chdir(project)
    assert order() == [("refs", 0, False, True), ("main", 1, True, True), ("notes", 2, False, True)]
    monkeypatch.chdir(workspace)

    run("set-store-priority", "REFS", "1")
    run("set-default-store", "notes")
    assert order() == [("refs", 1, False, True), ("main", 2, False, True), ("notes", 3, True, True)]

    (workspace / "stores" / "main").rename(workspace / "stores" / "away")
    assert order()[1] == ("main", 2, False, False)
    (workspace / "stores" / "away").rename(workspace / "stores" / "main")

    config = (workspace.parent / "home" / "config.json").read_text(encoding="utf-8")
    for refusal in [
        ["add-store", "Main", "elsewhere"],
        ["add-store", "again", "stores/main"],
        ["add-store", "bad:name", "elsewhere"],
        ["add-store", "file", "notes/todo.md"],
        ["set-default-store", "nope"],
        ["set-store-priority", "main", "4"],
        ["remove-store", "nope"],
    ]:
        result = runner.invoke(app, refusal)
        assert (result.exit_code, bool(result.stderr)) == (1, True), refusal
    assert (workspace.parent / "home" / "config.json").read_text(encoding="utf-8") == config
    assert not (workspace / "elsewhere").exists()

    runner.invoke(app, ["remove-store", "notes"])
    assert order() == [("refs", 1, True, True), ("main", 2, False, True)]
    runner.invoke(app, ["remove-store", "refs"])
    assert order() == [("main", 1, True, True)]
    assert (workspace / "notes" / ".store.json").is_file()
    run("add-store", "notes-again", "notes")
    assert order() == [("main", 1, True, True), ("notes-again", 2, False, True)]


def test_processes_registering_stores_at_once_all_keep_their_change(workspace: Path) -> None:
    command = [sys.executable, "-c", "from reference_store.cli import main; main()", "add-store"]
    processes = [
        subprocess.Popen(
            [*command, f"store-{number}", f"stores/{number}"],
            cwd=workspace,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        for number in range(8)
    ]
    for process in processes:
        _, error = process.communicate(timeout=120)
        assert process.returncode == 0, error
    stores = run("list-stores")
    assert sorted(store["name"] for store in stores) == [f"store-{number}" for number in range(8)]
    assert sorted(store["priority_order"] for store in stores) == list(range(1, 9))
