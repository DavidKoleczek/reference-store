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
# Inside its entry, so the entry still fits when it moves to a store with a longer path.
PATH_LIMIT = 150
# Windows' MAX_PATH is 260, and that counts the null that ends the path.
FULL_PATH_LIMIT = 259
# Windows makes a folder only when a file name of 8.3 characters still fits in it, with its backslash and the null.
FOLDER_PATH_LIMIT = 247


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
    problem = _problem(name) or _name_problem(name)
    if problem:
        raise ReferenceStoreError(f"{name!r} can't be the name of {of}, since {problem}.")


def slashed(path: str) -> str:
    """Returns a path in an entry with `/` between its parts and none around them, however it was written."""
    return path.strip().replace("\\", "/").strip("/")


def check_path(path: str) -> str:
    """Returns a path in an entry as `slashed` writes it, refusing one that breaks a rule.

    Each part follows the rules for names, but can start with a dot, as `.gitignore` does.

    Raises:
        ReferenceStoreError: The path is empty, has `.` or `..` in it, or breaks a rule.
    """
    cleaned = slashed(path)
    if not cleaned:
        raise ReferenceStoreError("A path in an entry can't be empty.")
    for part in cleaned.split("/"):
        if part in ("", ".", ".."):
            raise ReferenceStoreError(
                f"{path!r} can't be a path in an entry, since it has an empty part, . or .. in it."
            )
        problem = _problem(part)
        if problem:
            raise ReferenceStoreError(f"{cleaned!r} can't be a path in an entry, since in {part!r}, {problem}.")
    if len(cleaned) > PATH_LIMIT:
        raise ReferenceStoreError(
            f"{cleaned!r} can't be a path in an entry, since it is {len(cleaned)} characters, and a path in an entry "
            f"is at most {PATH_LIMIT}."
        )
    return cleaned


def _problem(name: str) -> str | None:
    """Returns why Windows wouldn't take `name` as a file's or a folder's name, or None when it would."""
    forbidden = sorted({character for character in name if character in FORBIDDEN}, key=FORBIDDEN.index)
    if forbidden:
        return f"it has {' '.join(forbidden)}, and a name can't have any of {' '.join(FORBIDDEN)}"
    if any(ord(character) < 32 for character in name):
        return "it has a control character"
    if name.endswith((".", " ")):
        return "it ends in a dot or a space"
    device = name.split(".")[0].rstrip(" ").upper()
    if device in RESERVED:
        return f"Windows keeps {device} for itself"
    return None


def _name_problem(name: str) -> str | None:
    """Returns why `name` can't be a store's or an entry's name, beyond what Windows refuses, or None."""
    if name.startswith("."):
        return "it starts with a dot, and only what the library keeps for itself does"
    if len(name) > NAME_LIMIT:
        return f"it is {len(name)} characters, and a name is at most {NAME_LIMIT}"
    return None


def check_full_path(path: Path, shorten: str) -> None:
    """Raises when most Windows programs couldn't open `path`, saying how much shorter `shorten` has to be.

    Raises:
        ReferenceStoreError: The path is too long.
    """
    _check_length(path, FULL_PATH_LIMIT, "most Windows programs can't open a path of more than", shorten)


def check_folder_path(folder: Path, shorten: str) -> None:
    """Raises when Windows couldn't make the folder `folder`, saying how much shorter `shorten` has to be.

    Raises:
        ReferenceStoreError: The path is too long.
    """
    _check_length(folder, FOLDER_PATH_LIMIT, "Windows can't make a folder with a path of more than", shorten)


def _check_length(path: Path, limit: int, refusal: str, shorten: str) -> None:
    length = len(str(path))
    if length > limit:
        raise ReferenceStoreError(
            f"That would make {path}, which is {length} characters, and {refusal} {limit}. Make {shorten} "
            f"{length - limit} character{'' if length - limit == 1 else 's'} shorter, or keep the store in a folder "
            "with a shorter path."
        )
