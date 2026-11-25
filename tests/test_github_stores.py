"""Stores kept on GitHub: one that is pushed and shared by two devices, and one that is only read.

Bare repositories in a temp folder stand in for GitHub, and each device is a configuration folder of its own.
"""

from collections.abc import Callable, Generator
import contextlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any

import pytest
from typer.testing import CliRunner

from reference_store.cli import app
from reference_store.core import disk
from reference_store.core.remotes import background

runner = CliRunner()
SHARED = "https://github.com/owner-1/store-1"
PROJECT = "https://github.com/owner-1/project-1"
TOO_LARGE = 100 * 1024 * 1024 + 1


def run(*args: str) -> Any:
    result = runner.invoke(app, [*args, "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


def run_failing(*args: str) -> Any:
    result = runner.invoke(app, [*args, "--json"])
    assert result.exit_code == 1, result.output
    return json.loads(result.stdout)


def refused(*args: str) -> str:
    result = runner.invoke(app, list(args))
    assert result.exit_code == 1, result.output
    return result.stderr


def git(folder: Path, *arguments: str) -> str:
    who = {"GIT_AUTHOR_NAME": "Sam", "GIT_AUTHOR_EMAIL": "sam@example.com"}
    who |= {"GIT_COMMITTER_NAME": "Sam", "GIT_COMMITTER_EMAIL": "sam@example.com"}
    done = subprocess.run(
        ["git", "-c", "core.autocrlf=false", *arguments],
        cwd=folder,
        env={**os.environ, **who},
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return done.stdout


@pytest.fixture
def github(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """The folder that stands in for GitHub: `git` reads and writes `https://github.com/<owner>/<repository>` there."""
    if shutil.which("git") is None:
        pytest.skip("git isn't installed")
    remotes = tmp_path / "github"
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", f"url.{remotes.as_uri()}/.insteadOf")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "https://github.com/")
    for name in ("store-1", "project-1"):
        bare = remotes / "owner-1" / name
        bare.mkdir(parents=True)
        git(bare, "init", "--quiet", "--bare", "--initial-branch", "main")
        git(bare, "config", "uploadpack.allowFilter", "true")
        git(bare, "config", "uploadpack.allowAnySHA1InWant", "true")
    return remotes


@pytest.fixture
def device(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Callable[[int], Path]:
    """Makes the commands that follow run on a device, and returns its configuration folder."""

    def use(number: int) -> Path:
        home = tmp_path / f"home-{number}"
        monkeypatch.setenv("REFERENCE_STORE_HOME", str(home))
        return home

    return use


@contextlib.contextmanager
def offline(remotes: Path) -> Generator[None]:
    """Keeps every device from reaching GitHub while the block runs, the syncs in the background included."""
    away = remotes.with_name("away")
    waited_until = time.monotonic() + 60
    while True:
        try:
            remotes.rename(away)
            break
        except PermissionError:
            # A sync in the background is reading from it just now.
            assert time.monotonic() < waited_until
            time.sleep(0.1)
    try:
        yield
    finally:
        away.rename(remotes)


def on_github(remotes: Path, repository: str) -> list[str]:
    bare = remotes / "owner-1" / repository
    return git(bare, "ls-tree", "-r", "--name-only", "main").splitlines()


def synced(store: str = "shared") -> dict[str, Any]:
    [result] = run("sync-store", "--store", store)
    assert result["error"] is None, result
    return result


def entry(name: str = "game-1") -> tuple[list[str], str, int | None, list[str]]:
    found = run("get-entry", name)
    return found["tags"], found["description"], found["rating"], [file["path"] for file in found["files"]]


def test_two_devices_share_a_store_that_is_pushed(workspace: Path, github: Path, device: Callable[[int], Path]) -> None:
    (workspace / "notes.md").write_text("Notes.\r\n", encoding="utf-8", newline="")
    (workspace / "big.bin").open("wb").truncate(TOO_LARGE)

    # The first device makes the empty repository a store, and what it adds is on GitHub after a sync.
    first = device(1)
    store = run("add-store", "shared", SHARED, "--push")
    clone = first / "stores" / "shared"
    assert (store["kind"], store["push"], store["read_only"], Path(store["path"])) == ("github", True, False, clone)
    assert on_github(github, "store-1") == [".store.json"]
    run("add-entry", "game-1", "--tag", "game", "--file", str(workspace / "notes.md"))
    synced()
    assert on_github(github, "store-1") == [".store.json", "game-1/.entry.json", "game-1/notes.md"]
    assert "can't go in the store shared" in refused("add-files", "game-1", str(workspace / "big.bin"))

    # The second device has a clone of its own making, in a folder it picked, and pushes that.
    device(2)
    mine = workspace / "mine"
    git(workspace, "clone", "--quiet", SHARED, str(mine))
    assert (mine / "game-1" / "notes.md").read_bytes() == b"Notes.\r\n"
    store = run("add-store", "shared", "mine", "--push")
    assert (store["kind"], store["push"], Path(store["path"])) == ("directory", True, mine)
    assert entry() == (["game"], "", None, ["notes.md"])

    # Both change the same entry with no way to sync, and once there is one each keeps what the other changed.
    with offline(github):
        run("update-entry", "game-1", "--add-tag", "second", "--description", "From the second.")
        run("add-files", "game-1", str(workspace / "notes.md"), "--path", "more/notes.md", "--tag", "ux")
        (mine / "game-1" / "clash.txt").write_text("second", encoding="utf-8")
        [failed] = run_failing("sync-store")
        assert failed["error"]
        assert run("list-stores")[0]["sync_error"] == failed["error"]
        device(1)
        run("update-entry", "game-1", "--add-tag", "first", "--remove-tag", "game", "--rating", "4")
        run("update-file", "game-1", "notes.md", "--description", "From the first.")
        (clone / "game-1" / "clash.txt").write_text("first", encoding="utf-8")
    device(2)
    synced()
    device(1)
    synced()
    merged = (["first", "second"], "From the second.", 4, ["clash.txt", "more/notes.md", "notes.md"])
    assert entry() == merged
    files = {file["path"]: file for file in run("get-entry", "game-1")["files"]}
    assert (files["notes.md"]["description"], files["more/notes.md"]["tags"]) == ("From the first.", ["ux"])
    device(2)
    synced()
    assert entry() == merged
    # A file both added is one or the other's, and the same on both.
    clashes = [(each / "game-1" / "clash.txt").read_text(encoding="utf-8") for each in (clone, mine)]
    assert clashes in (["first", "first"], ["second", "second"])
    assert run("list-entries")["total"] == 1

    # An entry moves out to a folder and back in, and GitHub follows. One with a file too large can't move in.
    device(1)
    run("add-store", "local", "local")
    assert run("move-entry", "game-1", "local")["store"] == "local"
    synced()
    assert on_github(github, "store-1") == [".store.json"]
    run("add-entry", "game-2", "--store", "local")
    (workspace / "local" / "game-2" / "big.bin").open("wb").truncate(TOO_LARGE)
    assert "can't go in the store shared" in refused("move-entry", "game-2", "shared")
    assert run("move-entry", "game-1", "shared")["store"] == "shared"
    synced()
    assert "game-1/more/notes.md" in on_github(github, "store-1")
    assert not (workspace / "local" / "game-1").exists()
    device(2)
    synced()
    assert entry() == merged

    # What can't be pushed is left out and said, and the rest still goes.
    device(1)
    (clone / "game-1" / "big.bin").open("wb").truncate(TOO_LARGE)
    git(clone / "game-1", "init", "--quiet", "vendor")
    (clone / "game-1" / "vendor" / "readme.md").write_text("Theirs.", encoding="utf-8")
    (clone / "game-1" / ".gitignore").write_text("*.log\n", encoding="utf-8")
    (clone / "game-1" / "run.log").write_text("ignored by git, and a file of the entry all the same", encoding="utf-8")
    assert synced()["left_out"] == ["game-1/big.bin", "game-1/vendor/"]
    assert {"game-1/.gitignore", "game-1/run.log"} <= set(on_github(github, "store-1"))
    assert not {"game-1/big.bin", "game-1/vendor/readme.md"} & set(on_github(github, "store-1"))

    # Removing the store deletes the clone the library made, once nothing in it is only there.
    assert "can't be pushed" in refused("remove-store", "shared")
    (clone / "game-1" / "big.bin").unlink()
    disk.delete_folder(clone / "game-1" / "vendor")
    (clone / "game-1" / "late.txt").write_text("late", encoding="utf-8")
    assert "aren't committed yet" in refused("remove-store", "shared")
    synced()
    assert runner.invoke(app, ["remove-store", "shared"]).exit_code == 0
    assert not clone.exists()
    device(2)
    synced()
    assert runner.invoke(app, ["remove-store", "shared"]).exit_code == 0
    assert (mine / "game-1" / "late.txt").is_file()


def test_a_repository_that_isnt_pushed_is_only_read(
    workspace: Path, github: Path, device: Callable[[int], Path]
) -> None:
    # A project's repository, with code and a store of its own, as whoever works on it pushed it.
    device(1)
    project = workspace / "project-1"
    git(workspace, "clone", "--quiet", PROJECT, str(project))
    (project / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (project / ".reference-store").mkdir()
    assert "nothing but a store" in refused("add-store", "pushed", "project-1", "--push")
    assert "isn't a clone" in refused("add-store", "pushed", "elsewhere", "--push")
    run("add-store", "project", "project-1")
    run("add-entry", "game-1", "--store", "project", "--description", "First.")
    git(project, "add", "--all")
    git(project, "commit", "--quiet", "--message", "First")
    git(project, "push", "--quiet", "origin", "HEAD:main")

    # Another device reads it from its URL, with only the store downloaded, and can't change it.
    home = device(2)
    assert "nothing but a store" in refused("add-store", "code", PROJECT, "--push")
    assert "holds no store" in refused("add-store", "code", "https://github.com/owner-1/store-1")
    assert not (home / "stores").exists() or not list((home / "stores").iterdir())
    store = run("add-store", "code", PROJECT)
    clone = home / "stores" / "code"
    assert (store["push"], store["read_only"], Path(store["path"])) == (False, True, clone / ".reference-store")
    run("add-store", "local", "local")
    assert not (clone / "main.py").exists()
    assert [each["description"] for each in run("list-entries")["entries"]] == ["First."]
    for change in (
        ["add-entry", "game-2", "--store", "code"],
        ["update-entry", "game-1", "--rating", "5"],
        ["delete-entry", "game-1"],
        ["add-files", "game-1", str(project / "main.py")],
        ["move-entry", "game-1", "local"],
    ):
        assert "can only be read" in refused(*change), change
    assert git(clone, "status", "--porcelain") == ""

    # What is pushed from the project shows after a sync, or by itself once the last sync is old.
    device(1)
    run("update-entry", "game-1", "--description", "Second.")
    run("add-entry", "game-2", "--store", "project")
    git(project, "add", "--all")
    git(project, "commit", "--quiet", "--message", "Second")
    git(project, "push", "--quiet", "origin", "HEAD:main")
    device(2)
    assert [each["description"] for each in run("list-entries")["entries"]] == ["First."]
    kept = clone / ".git" / "reference-store.json"
    old = json.loads(kept.read_text(encoding="utf-8")) | {"synced": time.time() - 2 * background.SYNC_EVERY_SECONDS}
    kept.write_text(json.dumps(old), encoding="utf-8")
    waited_until = time.monotonic() + 60
    while [each["name"] for each in run("list-entries", "--sort", "name")["entries"]] != ["game-1", "game-2"]:
        assert time.monotonic() < waited_until, "The sync a read starts never finished."
        time.sleep(0.2)
    assert run("get-entry", "game-1")["description"] == "Second."
    assert run("list-stores")[0]["sync_error"] is None
    assert runner.invoke(app, ["remove-store", "code"]).exit_code == 0
    assert not clone.exists()


def test_a_change_is_pushed_without_being_asked(github: Path, device: Callable[[int], Path]) -> None:
    device(1)
    run("add-store", "shared", SHARED, "--push")
    run("add-entry", "game-1")
    waited_until = time.monotonic() + 60
    while "game-1/.entry.json" not in on_github(github, "store-1"):
        assert time.monotonic() < waited_until, "The sync a change starts never finished."
        time.sleep(0.2)
