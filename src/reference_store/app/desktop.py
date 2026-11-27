"""Showing a file or a folder in this machine's file manager."""

from pathlib import Path
import subprocess
import sys

from reference_store.models import ReferenceStoreError


def show(path: Path) -> None:
    """Opens the file manager with a file picked in its folder, or a folder open.

    Raises:
        ReferenceStoreError: It isn't there, or the file manager couldn't be started.
    """
    if not path.exists():
        raise ReferenceStoreError(f"{path} isn't there any more.")
    is_file = path.is_file()
    command: str | list[str]
    if sys.platform == "win32":
        # Explorer can't read `/select,` inside quotes, and opens Documents instead. A list would quote the whole
        # argument when the path has a space, so only the path is quoted. A Windows path can't hold a quote to end it.
        command = f'explorer /select,"{path}"' if is_file else ["explorer", str(path)]
    elif sys.platform == "darwin":
        command = ["open", "-R", str(path)] if is_file else ["open", str(path)]
    else:
        command = ["xdg-open", str(path.parent if is_file else path)]
    try:
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as error:
        raise ReferenceStoreError(f"The file manager couldn't be opened: {error.strerror or error}.") from None
