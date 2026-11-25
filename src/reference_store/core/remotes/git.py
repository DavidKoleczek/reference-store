"""Running `git`, which is how a store kept on GitHub is cloned, committed, pulled, and pushed.

`git` signs in as the machine is set up to, such as through a credential manager. A command never waits at a prompt and
never opens a window, since most of them run where no one would see it.
"""

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys

LOCAL_SECONDS = 10 * 60
# A clone, fetch, or push moves whole files, which takes as long as the files are large.
NETWORK_SECONDS = 60 * 60
SETTINGS = (
    # Files go in and come out byte for byte. Git for Windows otherwise changes the line endings of text, such as a
    # saved page's.
    "core.autocrlf=false",
    "core.longpaths=true",
    # Paths are printed as they are, and not escaped when they have letters outside ASCII.
    "core.quotepath=false",
    "core.askPass=",
    # A transfer that stops moving is given up on after a minute, so it doesn't hold a store's sync forever.
    "http.lowSpeedLimit=1000",
    "http.lowSpeedTime=60",
)
QUIET = {"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}
PROMPTS = ("GIT_ASKPASS", "SSH_ASKPASS")
# Who commits are made as on a machine where `git` is set up for no one.
NOBODY = {
    "GIT_AUTHOR_NAME": "Reference Store",
    "GIT_AUTHOR_EMAIL": "reference-store@localhost",
    "GIT_COMMITTER_NAME": "Reference Store",
    "GIT_COMMITTER_EMAIL": "reference-store@localhost",
}


class GitError(Exception):
    """A `git` command failed. Its message is what `git` said."""


@dataclass(frozen=True)
class Result:
    """How a `git` command ended."""

    worked: bool
    out: str
    said: str  # what it gave as the reason, when it failed


def call(
    folder: Path | None,
    *arguments: str,
    seconds: int = LOCAL_SECONDS,
    given: str | None = None,
    env: dict[str, str] | None = None,
) -> Result:
    """Runs `git` with these arguments in a folder, and returns how it ended. `given` is what it reads on stdin.

    Raises:
        GitError: `git` isn't installed, or it ran for longer than `seconds`.
    """
    command = ["git", *(part for setting in SETTINGS for part in ("-c", setting)), *arguments]
    environment = {name: value for name, value in os.environ.items() if name not in PROMPTS}
    try:
        done = subprocess.run(
            command,
            cwd=folder,
            env={**environment, **QUIET, **(env or {})},
            input=None if given is None else given.encode(),
            stdin=subprocess.DEVNULL if given is None else None,
            capture_output=True,
            timeout=seconds,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            check=False,
        )
    except FileNotFoundError:
        raise GitError("git isn't installed, or isn't on PATH. A store kept on GitHub needs it.") from None
    except subprocess.TimeoutExpired:
        raise GitError(f"git {arguments[0]} took longer than {seconds // 60} minutes, and was stopped.") from None
    out = done.stdout.decode("utf-8", errors="replace")
    said = " ".join(line.strip() for line in done.stderr.decode("utf-8", errors="replace").splitlines() if line.strip())
    return Result(done.returncode == 0, out, said or f"git {arguments[0]} failed.")


def run(
    folder: Path | None,
    *arguments: str,
    seconds: int = LOCAL_SECONDS,
    given: str | None = None,
    env: dict[str, str] | None = None,
) -> str:
    """Runs `git` with these arguments in a folder, and returns what it printed.

    Raises:
        GitError: It failed.
    """
    result = call(folder, *arguments, seconds=seconds, given=given, env=env)
    if not result.worked:
        raise GitError(result.said)
    return result.out


def commit(root: Path, *arguments: str) -> None:
    """Commits what is staged in a clone, as whoever `git` is set up for there.

    Raises:
        GitError: The commit failed.
    """
    run(root, "commit", "--quiet", *arguments, env=committer(root))


def committer(root: Path) -> dict[str, str] | None:
    """Returns the environment a command that commits in a clone needs, which is None where `git` knows who commits."""
    known = call(root, "config", "user.email").worked and call(root, "config", "user.name").worked
    return None if known else NOBODY


def head(root: Path) -> str | None:
    """Returns the commit a clone is at, or None before its first one."""
    result = call(root, "rev-parse", "--verify", "--quiet", "HEAD")
    return result.out.strip() if result.worked else None


def branch(root: Path) -> str:
    """Returns the branch a clone is on.

    Raises:
        GitError: It is on no branch, such as when a commit was checked out by hand.
    """
    result = call(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    if not result.worked:
        raise GitError(f"The clone in {root} is on no branch. Check out its branch again.")
    return result.out.strip()
