"""The tool's skill: what it tells an agent that is about to use it."""

from importlib.metadata import metadata, version
from pathlib import Path

DISTRIBUTION = "reference-store"
SKILL_FILE = "SKILL.md"


def tool_skill() -> str:
    """Returns the skill for the whole tool, as the SKILL.md file an agent keeps in its skills folder."""
    return (Path(__file__).resolve().parent / SKILL_FILE).read_text(encoding="utf-8")


def repository_url() -> str | None:
    """Returns the tool's repository, from the package metadata, or None when the package declares none."""
    for entry in metadata(DISTRIBUTION).get_all("Project-URL") or []:
        label, _, url = str(entry).partition(",")
        if label.strip().lower() == "repository":
            return url.strip()
    return None


def tool_version() -> str:
    """Returns the installed package's version, from its metadata."""
    return version(DISTRIBUTION)
