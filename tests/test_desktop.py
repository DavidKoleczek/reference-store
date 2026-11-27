"""Showing a file or a folder in the file manager."""

from pathlib import Path
import subprocess
import sys

import pytest

from reference_store.app import desktop


@pytest.mark.skipif(sys.platform != "win32", reason="Explorer is the file manager on Windows only.")
def test_explorer_picks_a_file_whose_path_has_spaces(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    shot = workspace / "an entry" / "a shot.png"
    shot.parent.mkdir()
    shot.write_bytes(b"")
    started: list[str | list[str]] = []
    monkeypatch.setattr(subprocess, "Popen", lambda command, **_: started.append(command))

    desktop.show(shot)
    desktop.show(shot.parent)

    assert started == [f'explorer /select,"{shot}"', ["explorer", str(shot.parent)]]
