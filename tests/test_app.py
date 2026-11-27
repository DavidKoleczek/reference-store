"""The app's tools and resources, through an MCP client connected to its server."""

import base64
from io import BytesIO
from pathlib import Path
from typing import Any

from mcp import Client, MCPError
from mcp.types import BlobResourceContents, TextContent
from PIL import Image
import pytest

from reference_store import lib
from reference_store.app import webpages
from reference_store.models import NewFile

UPLOAD = "0123456789abcdef0123456789abcdef"


async def call(client: Client, tool: str, **arguments: Any) -> Any:
    result = await client.call_tool(tool, arguments)
    assert not result.is_error, result.content
    assert result.structured_content is not None
    return result.structured_content["result"]


async def refused(client: Client, tool: str, **arguments: Any) -> str:
    result = await client.call_tool(tool, arguments)
    assert result.is_error
    message = result.content[0]
    assert isinstance(message, TextContent)
    return message.text


async def read(client: Client, uri: str) -> bytes:
    contents = (await client.read_resource(uri)).contents[0]
    assert isinstance(contents, BlobResourceContents)
    return base64.b64decode(contents.blob)


def png(width: int, height: int) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), "teal").save(buffer, format="PNG")
    return buffer.getvalue()


async def upload(client: Client, path: str, content: bytes) -> str:
    """Sends a file in two pieces, as the view sends a large one, and returns its source."""
    half = len(content) // 2
    for offset, piece in ((0, content[:half]), (half, content[half:])):
        sent = await call(
            client, "upload_file", upload=UPLOAD, path=path, offset=offset, data=base64.b64encode(piece).decode()
        )
    assert sent["received"] == len(content)
    return sent["source"]


async def test_the_app_lists_adds_changes_and_deletes_through_its_tools(workspace: Path) -> None:
    async with Client(lib.app_server().server) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        assert tools["list_entries"].meta == {"ui": {"resourceUri": "ui://reference-store/app", "visibility": ["app"]}}
        assert "without_tags" in tools["list_entries"].input_schema["properties"]

        await call(client, "add_store", name="main", location=str(workspace / "main"))
        shots = await upload(client, "shots/menu.png", png(1000, 500))
        assert await upload(client, "notes.md", b"# Notes\n") == str(Path(shots).parent / "notes.md")
        added = await call(
            client, "add_entry", name="game-1", title="Game 1: The First", tags=["game"],
            files=[{"source": shots, "move": True}, {"source": str(Path(shots).parent / "notes.md"), "move": True}],
            preview={"file": "shots/menu.png"},
        )  # fmt: skip
        assert [file["path"] for file in added["files"]] == ["notes.md", "shots/menu.png"]
        assert (workspace / "main" / "game-1" / "shots" / "menu.png").is_file()
        assert not Path(shots).parent.exists()

        listing = await call(client, "list_entries", without_site=True)
        assert (listing["total"], listing["entries"][0]["title"]) == (1, "Game 1: The First")
        entry = await call(client, "get_entry", name="game-1")
        assert entry["files"][1]["full_path"] == str(workspace / "main" / "game-1" / "shots" / "menu.png")

        thumbnail = Image.open(
            BytesIO(await read(client, "reference-store://thumbnails/small/main/game-1/shots/menu.png"))
        )
        assert (thumbnail.format, thumbnail.size) == ("WEBP", (480, 240))
        preview = Image.open(BytesIO(await read(client, "reference-store://covers/large/main/game-1")))
        assert preview.size == (1000, 500)
        assert await read(client, "reference-store://files/main/game-1/notes.md") == b"# Notes\n"
        sizes = await call(
            client, "image_sizes",
            files=[{"store": "main", "entry": "game-1", "path": path} for path in ("shots/menu.png", "notes.md")],
        )  # fmt: skip
        assert sizes == {"sizes": [[1000, 500], None]}

        changed = await call(client, "update_entry", name="game-1", rating=4, add_tags=["puzzle"])
        assert (changed["title"], changed["rating"], changed["tags"]) == ("Game 1: The First", 4, ["game", "puzzle"])
        assert (await call(client, "update_entry", name="game-1", title=None))["title"] is None
        await call(client, "update_file", name="game-1", path="notes.md", description="What to look at")
        renamed = await call(client, "rename_entry", name="game-1", new_name="game-one")
        assert renamed["files"][0]["description"] == "What to look at"
        assert await read(client, "reference-store://files/main/game-one/notes.md") == b"# Notes\n"

        await call(client, "save_app_settings", settings={"theme": "dark"})
        assert await call(client, "read_app_settings") == {"settings": {"theme": "dark"}}

        (workspace / "secret.txt").write_text("not for the app", encoding="utf-8")
        assert "wasn't sent to the app" in await refused(
            client, "add_files", name="game-one", files=[{"source": str(workspace / "secret.txt")}]
        )
        with pytest.raises(MCPError, match="has no file"):
            await read(client, "reference-store://files/main/game-one/../../secret.txt")
        assert "can't take those arguments" in await refused(client, "list_entries", tag="game")
        assert "There is no entry" in await refused(client, "get_entry", name="game-1")

        await call(client, "delete_entry", name="game-one")
        assert not (workspace / "main" / "game-one").exists()
        assert (await call(client, "list_entries"))["total"] == 0


@pytest.mark.skipif(webpages.browser() is None, reason="Pages are drawn by Chrome, Edge, or Chromium.")
async def test_an_html_file_has_a_picture_of_its_page_drawn_once_light_and_without_its_scripts(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The browser is in dark mode, as it is on a machine that is, and the page has a dark mode of its own.
    monkeypatch.setattr(webpages, "QUIET", [*webpages.QUIET, "--force-dark-mode"])
    page = workspace / "page.html"
    page.write_text(
        "<!doctype html><style>body { background: #d33 } @media (prefers-color-scheme: dark) { body { background: "
        "#000 } }</style><body><script>document.body.style.background = '#36c'</script>",
        encoding="utf-8",
    )
    lib.add_store("main", str(workspace / "main"))
    lib.add_entry(name="saved", files=[NewFile(source=page)], store="main")
    uri = "reference-store://thumbnails/small/main/saved/page.html"
    async with Client(lib.app_server().server) as client:
        picture = Image.open(BytesIO(await read(client, uri)))
        assert (picture.format, picture.size) == ("WEBP", (384, 480))
        pixel = picture.convert("RGB").getpixel((192, 400))
        assert isinstance(pixel, tuple)
        red, _, blue = pixel
        assert red > 200
        assert blue < 100

        def drawn_again(path: Path) -> bytes:
            raise AssertionError(f"{path.name} was drawn again")

        monkeypatch.setattr(webpages, "screenshot", drawn_again)
        assert Image.open(BytesIO(await read(client, uri))).size == (384, 480)


async def test_an_html_file_has_no_picture_without_a_browser(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(webpages, "browser", lambda: None)
    page = workspace / "page.html"
    page.write_text("<!doctype html><p>A page", encoding="utf-8")
    lib.add_store("main", str(workspace / "main"))
    lib.add_entry(name="saved", files=[NewFile(source=page)], store="main")
    async with Client(lib.app_server().server) as client:
        with pytest.raises(MCPError, match="no Chrome, Edge, or Chromium"):
            await read(client, "reference-store://thumbnails/small/main/saved/page.html")
