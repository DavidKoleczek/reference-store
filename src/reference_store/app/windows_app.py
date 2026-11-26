"""The Windows app, when it is what started this server: the icon by the clock that keeps the server running, and
keeps the settings a server can't keep for itself, such as whether it is on the local network at all.

It tells the server it starts where it listens on this machine and a token, in two environment variables. It is asked
in one line of JSON that has the token, and answers in one line.
"""

import json
import os
import socket
from typing import Any

from pydantic import BaseModel, ValidationError

from reference_store.models import ReferenceStoreError

PORT_VARIABLE = "REFERENCE_STORE_WINDOWS_APP_PORT"
TOKEN_VARIABLE = "REFERENCE_STORE_WINDOWS_APP_TOKEN"
HOST = "127.0.0.1"
CONNECT_SECONDS = 5
# Looking for an update takes as long as GitHub does to answer, and the app gives up on it before this does.
ANSWER_SECONDS = 150
# Far past the longest answer there is.
MAX_ANSWER_BYTES = 64 * 1024


class WindowsApp(BaseModel):
    """What the Windows app is like now."""

    version: str
    update: str | None  # the newer version there is to update to
    updating: bool
    lan: bool  # whether the server is started on the local network
    start_at_sign_in: bool


def state() -> WindowsApp | None:
    """Returns what the Windows app is like, or None when it isn't what started this server.

    Raises:
        ReferenceStoreError: It started this server and doesn't answer.
    """
    return _ask("state") if _address() is not None else None


def change(lan: bool | None = None, start_at_sign_in: bool | None = None) -> WindowsApp:
    """Changes the settings that are given, and returns what the Windows app is like after.

    Changing `lan` has it start this server again a moment later, on the same port.

    Raises:
        ReferenceStoreError: The Windows app isn't what started this server, or it couldn't change them.
    """
    changes = {"lan": lan, "start_at_sign_in": start_at_sign_in}
    return _ask("set", **{name: value for name, value in changes.items() if value is not None})


def check_for_update() -> WindowsApp:
    """Has the Windows app look for a newer version, and returns what it is like after, with the version in `update`.

    Raises:
        ReferenceStoreError: The Windows app isn't what started this server, or it couldn't look.
    """
    return _ask("check_for_update")


def install_update() -> WindowsApp:
    """Has the Windows app start installing the newer version, which ends this server and starts the new one.

    Raises:
        ReferenceStoreError: The Windows app isn't what started this server, or there is no newer version.
    """
    return _ask("install_update")


def _address() -> tuple[int, str] | None:
    """The port the Windows app listens on and its token, or None when it didn't start this server."""
    port, token = os.environ.get(PORT_VARIABLE, ""), os.environ.get(TOKEN_VARIABLE, "")
    return (int(port), token) if port.isdecimal() and token else None


def _ask(do: str, **more: Any) -> WindowsApp:
    address = _address()
    if address is None:
        raise ReferenceStoreError(
            "This is for the Windows app, which isn't what started this server. Install it from the repository's "
            "releases, and open the app from its shortcut."
        )
    port, token = address
    try:
        with socket.create_connection((HOST, port), timeout=CONNECT_SECONDS) as connection:
            connection.settimeout(ANSWER_SECONDS)
            connection.sendall((json.dumps({"token": token, "do": do, **more}) + "\n").encode())
            with connection.makefile("rb") as answered:
                line = answered.readline(MAX_ANSWER_BYTES)
    except OSError as error:
        raise ReferenceStoreError(f"The Windows app didn't answer: {error.strerror or error}.") from None
    try:
        answer = json.loads(line)
        if not answer["ok"]:
            raise ReferenceStoreError(str(answer["error"]))
        return WindowsApp.model_validate(answer["state"])
    except (ValueError, KeyError, TypeError, ValidationError):
        raise ReferenceStoreError("The Windows app's answer couldn't be read. It may be another version.") from None
