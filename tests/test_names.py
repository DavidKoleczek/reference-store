"""The rules for names, which follow Windows on every system."""

import re

import pytest

from reference_store.core import names
from reference_store.models import ReferenceStoreError


@pytest.mark.parametrize(
    "name",
    ["game-1", "Concept Art", "Mario & Luigi (2024)", "v1.2 notes", "CONSOLE", "con-1", "NULL.txt", "a" * 64],
)
def test_a_name_that_follows_the_rules_is_taken(name: str) -> None:
    names.check_name(name, "an entry")


@pytest.mark.parametrize(
    ("name", "reason"),
    [
        ("", "can't be empty"),
        ("game:1", "it has :"),
        ("a/b\\c", "it has \\ /"),
        ('say "hi"', 'it has "'),
        ("tab\there", "control character"),
        ("ends.", "ends in a dot or a space"),
        ("ends ", "ends in a dot or a space"),
        (".hidden", "starts with a dot"),
        ("con", "keeps CON"),
        ("Nul.txt", "keeps NUL"),
        ("aux .md", "keeps AUX"),
        ("COM0", "keeps COM0"),
        ("lpt" + chr(0xB9), "keeps LPT" + chr(0xB9)),
        ("a" * 65, "65 characters"),
    ],
)
def test_a_name_that_breaks_a_rule_is_refused_with_the_reason(name: str, reason: str) -> None:
    with pytest.raises(ReferenceStoreError, match=re.escape(reason)):
        names.check_name(name, "an entry")


@pytest.mark.parametrize(
    ("path", "cleaned"),
    [
        ("menu.png", "menu.png"),
        ("screenshots\\menu.png", "screenshots/menu.png"),
        (" /screenshots/captures/ ", "screenshots/captures"),
        (".gitignore", ".gitignore"),
        ("docs/.notes/con-1.md", "docs/.notes/con-1.md"),
        ("a" * 150, "a" * 150),
    ],
)
def test_a_path_in_an_entry_is_taken_with_slashes_between_its_parts(path: str, cleaned: str) -> None:
    assert names.check_path(path) == cleaned


@pytest.mark.parametrize(
    ("path", "reason"),
    [
        ("", "can't be empty"),
        ("/", "can't be empty"),
        ("a//b.png", "an empty part"),
        ("./b.png", ". or .."),
        ("a/../b.png", ". or .."),
        ("shots/a:b.png", "it has :"),
        ("shots./a.png", "ends in a dot or a space"),
        ("aux/a.png", "keeps AUX"),
        ("a" * 151, "151 characters"),
    ],
)
def test_a_path_that_breaks_a_rule_is_refused_with_the_reason(path: str, reason: str) -> None:
    with pytest.raises(ReferenceStoreError, match=re.escape(reason)):
        names.check_path(path)
