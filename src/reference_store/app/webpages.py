"""Pictures of the HTML files in entries, for their thumbnails, drawn by a browser on this machine without a window.

The browser shows the page in a sandboxed frame, so none of its scripts run, and is pointed at a proxy that isn't
there, so it loads nothing from the network. Its own switch for turning scripts off leaves it with no picture to take.
Each picture starts a browser of its own, with a profile of its own that is deleted after, in about half a second.
"""

import html
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading

from reference_store.models import ReferenceStoreError

SUFFIXES = {".html", ".htm"}
# A desktop browser's window, as tall as the view's tiles for a page are for their width, so the picture fills one.
WIDTH, HEIGHT = 1024, 1280
TIMEOUT_SECONDS = 30
# Each picture is a browser, so only a few are drawn at once however many the view asks for.
AT_ONCE = threading.Semaphore(2)
# Nothing listens there, so every request fails at once. Loopback is sent there too, or it would skip the proxy.
NO_NETWORK = ["--proxy-server=127.0.0.1:9", "--proxy-bypass-list=<-loopback>"]
QUIET = [
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-sync",
    "--mute-audio",
]
# The picture is taken once the page loads, which now and then is before the page in its frame is drawn. Waiting for
# virtual time costs little, since it passes at once while nothing is left to load.
SETTLE = "--virtual-time-budget=1000"
# A page with a dark mode would follow this machine's, whichever theme the app is in. A picture is kept and shown in
# both, so it is drawn as the page looks in light mode, as nearly every page looks.
SCHEME = "light"
FRAME = (
    "<!doctype html><style>:root, iframe {{ color-scheme: {scheme}; }} html, body, iframe {{ margin: 0; border: 0; "
    'width: 100%; height: 100%; display: block; }}</style><iframe sandbox scrolling="no" src="{page}"></iframe>'
)
NAMES = ["chrome", "google-chrome", "chromium", "chromium-browser", "msedge", "microsoft-edge"]
MAC_APPS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]
# Where Windows installs them, under the folders these variables name. Edge comes with Windows.
WINDOWS_APPS = [
    ("PROGRAMFILES", "Google/Chrome/Application/chrome.exe"),
    ("PROGRAMFILES(X86)", "Google/Chrome/Application/chrome.exe"),
    ("LOCALAPPDATA", "Google/Chrome/Application/chrome.exe"),
    ("PROGRAMFILES(X86)", "Microsoft/Edge/Application/msedge.exe"),
    ("PROGRAMFILES", "Microsoft/Edge/Application/msedge.exe"),
]


def is_page(path: Path) -> bool:
    """Returns whether a file is an HTML file, which has a picture of its page for a thumbnail."""
    return path.suffix.lower() in SUFFIXES


def browser() -> Path | None:
    """Returns the Chrome, Edge, or Chromium on this machine that draws pages, or None when there is none."""
    for name in NAMES:
        if found := shutil.which(name):
            return Path(found)
    places = [Path(app) for app in MAC_APPS] + [
        Path(folder) / inside for variable, inside in WINDOWS_APPS if (folder := os.environ.get(variable))
    ]
    return next((place for place in places if place.is_file()), None)


def screenshot(path: Path) -> bytes:
    """Returns a PNG of the top of the page in the HTML file at `path`.

    Raises:
        ReferenceStoreError: There is no browser to draw it, or it couldn't be drawn.
    """
    found = browser()
    if found is None:
        raise ReferenceStoreError(
            f"{path.name} has no picture, since there is no Chrome, Edge, or Chromium to draw it."
        )
    with AT_ONCE, tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as scratch:
        folder = Path(scratch)
        frame = folder / "frame.html"
        frame.write_text(FRAME.format(scheme=SCHEME, page=html.escape(path.as_uri())), encoding="utf-8")
        shot = folder / "shot.png"
        command = [
            str(found), "--headless", "--disable-gpu", "--hide-scrollbars", f"--window-size={WIDTH},{HEIGHT}",
            f"--user-data-dir={folder / 'profile'}", *NO_NETWORK, *QUIET, SETTLE, f"--screenshot={shot}",
            frame.as_uri(),
        ]  # fmt: skip
        try:
            subprocess.run(
                command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=TIMEOUT_SECONDS, check=False
            )
            return shot.read_bytes()
        except subprocess.TimeoutExpired:
            raise ReferenceStoreError(f"{path.name} took longer than {TIMEOUT_SECONDS} seconds to draw.") from None
        except OSError as error:
            raise ReferenceStoreError(
                f"{path.name} couldn't be drawn by {found.name}: {error.strerror or error}."
            ) from None
