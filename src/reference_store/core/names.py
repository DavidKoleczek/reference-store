"""The rules for names. Windows is the strictest about files, so its rules apply on every system."""

from pathlib import Path

from reference_store.models import ReferenceStoreError

FORBIDDEN = '\\/:*?"<>|'
# Windows also reads the superscript digits as digits here.
RESERVED = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "CONIN$",
        "CONOUT$",
        *(f"{device}{digit}" for device in ("COM", "LPT") for digit in "0123456789\u00b9\u00b2\u00b3"),
    }
)
NAME_LIMIT = 64
# Windows' MAX_PATH is 260, and that counts the null that ends the path.
FULL_PATH_LIMIT = 259


def key(name: str) -> str:
    """Returns what two names are compared by, since names that differ only by case count as the same."""
    return name.casefold()


def check_name(name: str, of: str) -> None:
    """Raises when `name` can't be the name of `of`, such as "a store", saying which rule it breaks.

    Raises:
        ReferenceStoreError: The name breaks a rule.
    """
    if not name:
        raise ReferenceStoreError(f"The name of {of} can't be empty.")
    problem = _problem(name)
    if problem:
        raise ReferenceStoreError(f"{name!r} can't be the name of {of}, since {problem}.")


def _problem(name: str) -> str | None:
    forbidden = sorted({character for character in name if character in FORBIDDEN}, key=FORBIDDEN.index)
    if forbidden:
        return f"it has {' '.join(forbidden)}, and a name can't have any of {' '.join(FORBIDDEN)}"
    if any(ord(character) < 32 for character in name):
        return "it has a control character"
    if name.endswith((".", " ")):
        return "it ends in a dot or a space"
    if name.startswith("."):
        return "it starts with a dot, and only what the library keeps for itself does"
    device = name.split(".")[0].rstrip(" ").upper()
    if device in RESERVED:
        return f"Windows keeps {device} for itself"
    if len(name) > NAME_LIMIT:
        return f"it is {len(name)} characters, and a name is at most {NAME_LIMIT}"
    return None


def check_full_path(path: Path, shorten: str) -> None:
    """Raises when most Windows programs couldn't open `path`, saying how much shorter `shorten` has to be.

    Raises:
        ReferenceStoreError: The path is too long.
    """
    length = len(str(path))
    if length > FULL_PATH_LIMIT:
        raise ReferenceStoreError(
            f"That would make {path}, which is {length} characters, and most Windows programs can't open a path of "
            f"more than {FULL_PATH_LIMIT}. Make {shorten} {length - FULL_PATH_LIMIT} characters shorter, or keep the "
            "store in a folder with a shorter path."
        )
