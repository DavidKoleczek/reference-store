"""Listing entries, tags, and sites across stores, from the CLI."""

import json
from pathlib import Path
import shutil
from typing import Any

from typer.testing import CliRunner

from reference_store.cli import app

runner = CliRunner()


def run(*args: str) -> Any:
    result = runner.invoke(app, [*args, "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


def listed(*args: str) -> list[str]:
    """The entries listed, each as its store and name, from every page."""
    shown: list[str] = []
    after: list[str] = []
    while True:
        page = run("list-entries", *args, *after)
        shown.extend(f"{entry['store']}/{entry['name']}" for entry in page["entries"])
        if page["after"] is None:
            return shown
        after = ["--after", page["after"]]


def test_entries_are_listed_filtered_sorted_and_paged_across_stores(workspace: Path) -> None:
    run("add-store", "alpha", "alpha")
    run("add-store", "beta", "beta")
    run(
        "add-entry", "game-1", "--title", "Game 1: The First One", "--tag", "game", "--tag", "puzzle",
        "--rating", "4", "--url", "https://www.github.com/Some-Org/game-1", "--created", "2026-01-01",
    )  # fmt: skip
    run(
        "add-entry", "game-2", "--tag", "Game", "--rating", "2", "--url", "https://twitter.com/someone/status/1",
        "--created", "2026-01-02",
    )  # fmt: skip
    run("add-entry", "notes", "--url", "https://example.com/a", "--created", "2026-01-03")
    run(
        "add-entry", "game-1", "--store", "beta", "--tag", "game", "--url", "https://github.com/some-org/other",
        "--created", "2026-01-04",
    )  # fmt: skip
    by_hand = workspace / "beta" / "by-hand"
    (by_hand / "shots").mkdir(parents=True)
    (by_hand / "shots" / "menu.png").write_bytes(b"12345")
    (by_hand / "shots" / "map.png").write_bytes(b"123")
    (by_hand / ".entry.json").write_text(
        json.dumps(
            {"tags": ["photos"], "created": "2025-12-31T12:00:00Z", "files": {"shots/menu.png": {"tags": ["UX"]}}}
        ),
        encoding="utf-8",
    )
    (workspace / "beta" / "broken").mkdir()
    (workspace / "beta" / "broken" / ".entry.json").write_text("{", encoding="utf-8")
    (workspace / "beta" / "plain folder").mkdir()

    newest_first = ["beta/game-1", "alpha/notes", "alpha/game-2", "alpha/game-1", "beta/by-hand"]
    everything = run("list-entries")
    assert ([f"{e['store']}/{e['name']}" for e in everything["entries"]], everything["total"]) == (newest_first, 5)
    assert "files" not in everything["entries"][0]
    assert listed("--limit", "2") == newest_first
    assert listed("--ascending", "--limit", "3") == newest_first[::-1]

    first = run("list-entries", "--limit", "2")
    shutil.rmtree(workspace / "alpha" / "notes")
    rest = run("list-entries", "--limit", "2", "--after", first["after"])
    assert ([entry["name"] for entry in rest["entries"]], rest["total"]) == (["game-2", "game-1"], 4)
    run("add-entry", "notes", "--url", "https://example.com/a", "--created", "2026-01-03")

    assert listed("--tag", "GAME") == ["beta/game-1", "alpha/game-2", "alpha/game-1"]
    assert listed("--tag", "game", "--tag", "puzzle") == ["alpha/game-1"]
    assert listed("--tag", "puzzle", "--tag", "photos", "--any") == ["alpha/game-1", "beta/by-hand"]
    assert listed("--file-tag", "ux") == ["beta/by-hand"]
    assert listed("--file-tag", "ux", "--file-tag", "photos") == []
    assert listed("--min-rating", "3") == ["alpha/game-1"]
    assert listed("--site", "github.com/SOME-ORG") == ["beta/game-1", "alpha/game-1"]
    assert listed("--site", "x.com") == ["alpha/game-2"]
    assert listed("--site", "x.com", "--site", "example.com") == ["alpha/notes", "alpha/game-2"]
    assert listed("--without-tags") == ["alpha/notes"]
    assert listed("--without-site") == ["beta/by-hand"]
    assert listed("--store", "beta", "--sort", "files") == ["beta/by-hand", "beta/game-1"]

    # The title counts as the name, and ties go by name, then by store.
    assert listed("--sort", "name") == ["beta/by-hand", "alpha/game-1", "beta/game-1", "alpha/game-2", "alpha/notes"]
    assert listed("--sort", "store", "--limit", "1") == [
        "alpha/game-1", "alpha/game-2", "alpha/notes", "beta/by-hand", "beta/game-1",
    ]  # fmt: skip
    # An entry with nothing to sort by comes last either way.
    unrated = ["beta/by-hand", "beta/game-1", "alpha/notes"]
    assert listed("--sort", "rating") == ["alpha/game-1", "alpha/game-2", *unrated]
    assert listed("--sort", "rating", "--ascending") == ["alpha/game-2", "alpha/game-1", *unrated]
    assert listed("--sort", "tags") == ["beta/game-1", "alpha/game-2", "alpha/game-1", "beta/by-hand", "alpha/notes"]

    text = runner.invoke(app, ["list-entries", "--store", "alpha", "--sort", "name", "--limit", "2"])
    lines = text.stdout.splitlines()
    assert lines[:2] == [
        "game-1 (Game 1: The First One)  alpha  2026-01-01  0 files  rated 4  [game, puzzle]",
        "game-2  alpha  2026-01-02  0 files  rated 2  [Game]",
    ]
    after = run("list-entries", "--store", "alpha", "--sort", "name", "--limit", "2")["after"]
    assert lines[2] == f"2 of 3 entries. For the next page: --after {after}"

    assert run("list-tags") == [
        {"tag": "game", "entries": 3, "files": 0},
        {"tag": "photos", "entries": 1, "files": 0},
        {"tag": "puzzle", "entries": 1, "files": 0},
        {"tag": "UX", "entries": 0, "files": 1},
    ]
    assert run("list-sites") == [
        {"site": "github.com", "entries": 2, "groups": [{"group": "Some-Org", "entries": 2}]},
        {"site": "example.com", "entries": 1, "groups": []},
        {"site": "x.com", "entries": 1, "groups": [{"group": "someone", "entries": 1}]},
    ]
    assert run("list-sites", "--store", "beta") == [
        {"site": "github.com", "entries": 1, "groups": [{"group": "some-org", "entries": 1}]},
    ]

    for args in (
        ["--sort", "size", "--after", after],
        ["--limit", "0"],
        ["--site", "example.com/a"],
        ["--tag", "game", "--without-tags"],
        ["--site", "x.com", "--without-site"],
        ["--store", "nope"],
    ):
        result = runner.invoke(app, ["list-entries", *args])
        assert (result.exit_code, bool(result.stderr)) == (1, True), args
    assert "isn't JSON" in runner.invoke(app, ["get-entry", "broken"]).stderr

    # Sites in config.json add groups, or turn off the library's, and the library keeps them when it saves the file.
    config_file = workspace.parent / "home" / "config.json"
    configured = {"example.com": {"pattern": r"example\.com/(?P<group>[^/]+)"}, "x.com": None}
    config_file.write_text(json.dumps(json.loads(config_file.read_text(encoding="utf-8")) | {"sites": configured}))
    run("add-store", "gamma", "gamma")
    assert json.loads(config_file.read_text(encoding="utf-8"))["sites"] == configured
    assert run("list-sites")[1:] == [
        {"site": "example.com", "entries": 1, "groups": [{"group": "a", "entries": 1}]},
        {"site": "twitter.com", "entries": 1, "groups": []},
    ]
    assert listed("--site", "example.com/A") == ["alpha/notes"]
    configured["example.com"] = {"pattern": "(unclosed"}
    config_file.write_text(json.dumps({"stores": [], "sites": configured}))
    assert "isn't a regular expression" in runner.invoke(app, ["list-sites"]).stderr
    assert run("list-entries")["total"] == 0
