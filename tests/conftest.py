from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """An empty folder each test runs in, with a configuration folder of its own beside it, so no test reads or writes
    the configuration of whoever runs it."""
    monkeypatch.setenv("REFERENCE_STORE_HOME", str(tmp_path / "home"))
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    return work
