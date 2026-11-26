"""The tool's Agent Skill."""

from pathlib import Path
import re
import tomllib

from reference_store import lib

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def test_the_skill_is_the_version_of_the_tool_it_comes_with() -> None:
    with PYPROJECT.open("rb") as file:
        version = tomllib.load(file)["project"]["version"]
    frontmatter = lib.skill().split("---")[1]
    found = re.search(r'^metadata:\n  version: "([^"]+)"$', frontmatter, re.MULTILINE)
    assert found is not None, "The skill's frontmatter has no metadata.version."
    assert found[1] == version, f"Set metadata.version in SKILL.md to {version}, the version in pyproject.toml."
