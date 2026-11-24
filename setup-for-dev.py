"""
Cross-platform script to set up a development environment for the project.
It assumes that you have installed all the prerequisites listed in CONTRIBUTING.md.
"""

from pathlib import Path
import shlex
import shutil
import subprocess

REFERENCE_ROOT = Path(__file__).parent / "reference"
REFERENCES = [
    "https://github.com/DavidKoleczek/3d-modeling-smart-tool",
    "https://github.com/agentskills/agentskills",
    "https://github.com/openai/codex",
    "https://github.com/modelcontextprotocol/ext-tasks",
    "https://github.com/DavidKoleczek/image-design-smart-tool",
    "https://github.com/modelcontextprotocol/modelcontextprotocol",
    "https://github.com/vercel-labs/skills",
    "https://github.com/astral-sh/uv",
    "https://github.com/DavidKoleczek/my-design-systems",
]


def run(command: str) -> None:
    """Run a command, forwarding its output to this process's stdout and stderr."""
    subprocess.run(shlex.split(command), check=True)


def clone_missing_references() -> None:
    """Clone every reference repository that is absent; they are gitignored, so a fresh clone has none."""
    for repository in REFERENCES:
        destination = REFERENCE_ROOT / repository.rsplit("/", 1)[-1]
        if destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--single-branch",
                repository,
                str(destination),
            ],
            check=True,
        )


def install_app_dependencies() -> None:
    """Only when pnpm is present; the compiled app is committed, so Node is needed only to change it."""
    pnpm = shutil.which("pnpm")
    if pnpm is None:
        print("pnpm not found; skipping the app's dependencies. Install Node 22+ and pnpm to change the frontend.")
        return
    subprocess.run([pnpm, "--dir", "app", "install", "--frozen-lockfile"], check=True)


def main() -> None:
    run("uv --version")
    run("prek --version")
    run("uv sync --frozen --all-groups")
    run("prek install")
    clone_missing_references()
    install_app_dependencies()


if __name__ == "__main__":
    main()
