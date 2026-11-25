"""Starting a process that goes on after this one ends, for work a call shouldn't wait for."""

import os
import subprocess
import sys

from reference_store.core import config


def start(module: str, arguments: list[str]) -> None:
    """Runs a module of the library with these arguments in a process of its own, and returns at once.

    The process has the same configuration as this one. When it can't be started, nothing is raised, since whoever
    asked has what they came for either way and the work is asked for again later.
    """
    command = [sys.executable, "-m", module, *arguments]
    try:
        if sys.platform == "win32":
            # A console of its own with no window. With no console at all, the Python a virtual environment's
            # python.exe starts opens one that shows on the desktop.
            apart = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
            try:
                # Out of the job this process is in, which can end every process in it once its first one is done.
                _started(command, apart | subprocess.CREATE_BREAKAWAY_FROM_JOB)
            except OSError:
                _started(command, apart)
        else:
            _started(command, 0)
    except OSError:
        return


def _started(command: list[str], creation_flags: int) -> None:
    # It runs from the configuration's folder, so it doesn't keep the folder this process runs in from being deleted,
    # and finds the same configuration from there.
    home = config.home()
    home.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(
        command,
        cwd=home,
        env={**os.environ, config.HOME_VARIABLE: str(home)},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags,
        start_new_session=sys.platform != "win32",
    )
