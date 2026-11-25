"""Finding entries by what they say and what their files hold, and files by their paths, from the CLI."""

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


def refused(*args: str) -> None:
    result = runner.invoke(app, list(args))
    assert (result.exit_code, bool(result.stderr)) == (1, True), args


def paged(command: str, *args: str) -> list[Any]:
    """Every result or file listed, from every page of two."""
    shown: list[Any] = []
    after: list[str] = []
    while True:
        page = run(command, *args, "--limit", "2", *after)
        shown.extend(page["results" if command == "grep-entries" else "files"])
        if page["after"] is None:
            return shown
        after = ["--after", page["after"]]


def found(*args: str) -> dict[str, list[str]]:
    """The entries grep finds, each as its store and name, with its matches as the CLI's text shows them."""
    return {
        f"{result['entry']['store']}/{result['entry']['name']}": [
            f"{match['path']}:{match['line']}: {match['text']}"
            if match["line"]
            else f"{match['path'] or ''} {match['field']}: {match['text']}".strip()
            for match in result["matches"]
        ]
        for result in paged("grep-entries", *args)
    }


def test_entries_are_found_by_what_they_say_and_files_by_their_paths(workspace: Path) -> None:
    run("add-store", "alpha", "alpha")
    run("add-store", "beta", "beta")
    inbox = workspace / "inbox"
    (inbox / "notes").mkdir(parents=True)
    (inbox / "notes" / "review.md").write_text("# Review\nThe assist mode helps.\nNothing else.\n", encoding="utf-8")
    (inbox / "menu.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00assist mode")
    (inbox / "legacy.txt").write_bytes(b"assist mode in caf\xe9")
    (inbox / "page.html").write_text(f"<p>{'x' * 1000} assist mode {'y' * 1000}</p>", encoding="utf-8")
    run(
        "add-entry", "game-1", "--title", "Game 1: The First One", "--description", "A puzzle game.\nHas an assist mode.",
        "--tag", "game", "--tag", "puzzle", "--rating", "4", "--store", "alpha",
        "--file", str(inbox / "notes"), "--file", str(inbox / "legacy.txt"), "--file", str(inbox / "page.html"),
    )  # fmt: skip
    run(
        "add-files", "game-1", str(inbox / "menu.png"), "--path", "screenshots/", "--tag", "ux",
        "--description", "The pause menu, with assist mode.", "--store", "alpha",
    )  # fmt: skip
    run("add-entry", "game-3", "--description", "ASSIST MODE", "--store", "alpha")
    (inbox / "notes.md").write_text("assist mode? no.\n", encoding="utf-8")
    run("add-entry", "game-1", "--tag", "game", "--store", "beta", "--file", str(inbox / "notes.md"))
    run("add-entry", "game-2", "--description", "Nothing here.", "--store", "beta")

    # The long line is cut to 300 characters, starting 100 before the match.
    cut = f"...{'x' * 99} assist mode {'y' * 188}..."
    assert found("assist mode") == {
        "alpha/game-1": [
            "description: Has an assist mode.",
            "screenshots/menu.png file_descriptions: The pause menu, with assist mode.",
            "notes/review.md:2: The assist mode helps.",
            f"page.html:1: {cut}",
        ],
        "beta/game-1": ["notes.md:1: assist mode? no."],
    }
    assert list(found("assist mode", "--ignore-case")) == ["alpha/game-1", "beta/game-1", "alpha/game-3"]
    assert found("assist", "--field", "file_contents", "--glob", "**/*.MD") == {
        "alpha/game-1": ["notes/review.md:2: The assist mode helps."],
        "beta/game-1": ["notes.md:1: assist mode? no."],
    }
    assert found("assist", "--file-tag", "ux", "--field", "file_contents", "--field", "file_descriptions") == {
        "alpha/game-1": ["screenshots/menu.png file_descriptions: The pause menu, with assist mode."],
    }
    assert list(found("game", "--field", "tags", "--tag", "puzzle", "--min-rating", "4")) == ["alpha/game-1"]
    first = run("grep-entries", "assist mode", "--matches-per-entry", "1")["results"][0]
    assert (len(first["matches"]), first["match_count"]) == (1, 4)

    def paths(*args: str) -> list[str]:
        return [f"{file['store']}/{file['entry']}/{file['path']}" for file in paged("glob-files", *args)]

    assert paths("**") == [
        "alpha/game-1/legacy.txt",
        "alpha/game-1/notes/review.md",
        "alpha/game-1/page.html",
        "alpha/game-1/screenshots/menu.png",
        "beta/game-1/notes.md",
    ]
    assert paths("GAME-1/*.md") == ["beta/game-1/notes.md"]
    assert paths("**", "--descending") == paths("**")[::-1]
    assert paths("**", "--sort", "size") == [
        "alpha/game-1/page.html",
        "alpha/game-1/notes/review.md",
        "alpha/game-1/screenshots/menu.png",
        "alpha/game-1/legacy.txt",
        "beta/game-1/notes.md",
    ]
    # Ties go in the order of the paths.
    assert paths("**", "--sort", "type") == [
        "alpha/game-1/page.html",
        "alpha/game-1/notes/review.md",
        "beta/game-1/notes.md",
        "alpha/game-1/screenshots/menu.png",
        "alpha/game-1/legacy.txt",
    ]
    assert [path.rsplit("/", 1)[-1] for path in paths("**", "--sort", "name", "--descending")] == [
        "review.md", "page.html", "notes.md", "menu.png", "legacy.txt",
    ]  # fmt: skip
    assert paths("**", "--file-tag", "ux") == ["alpha/game-1/screenshots/menu.png"]
    assert paths("**/*.md", "--tag", "puzzle") == ["alpha/game-1/notes/review.md"]

    after = run("glob-files", "**", "--limit", "1")["after"]
    for refusal in [
        ["grep-entries", "assist ("],
        ["grep-entries", "assist", "--matches-per-entry", "-1"],
        ["grep-entries", "assist", "--after", after],
        ["glob-files", " "],
        ["glob-files", "**", "--sort", "size", "--after", after],
    ]:
        refused(*refusal)
    assert runner.invoke(app, ["grep-entries", "assist", "--field", "nope"]).exit_code == 2

    # Run as a command, a pattern reaches the library as it was typed, even where files here match it.
    command = [sys.executable, "-c", "from reference_store.cli import main; main()", "glob-files", "*/*.md", "--json"]
    printed = subprocess.run(command, cwd=workspace, capture_output=True, text=True, check=True).stdout
    assert [file["path"] for file in json.loads(printed)["files"]] == ["notes.md"]
