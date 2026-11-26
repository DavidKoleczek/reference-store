"""The Windows app's settings and updates, through the app's tools, with a stand-in for the app by the clock."""

from collections.abc import Iterator
import json
import socket
import threading
from typing import Any

from mcp import Client
from mcp.types import TextContent
import pytest

from reference_store import lib
from reference_store.app import windows_app
from reference_store.app.known import Known
from reference_store.app.own_tools import own_tools

TOKEN = "0f1e2d3c4b5a"
STATE = {"version": "0.1.0", "update": None, "updating": False, "lan": False, "start_at_sign_in": False, "skill": None}
TOOLS = [
    "read_windows_app",
    "change_windows_app",
    "check_for_update",
    "install_update",
    "list_skill_agents",
    "install_skill",
    "remove_skill",
]
AGENTS = {
    "home": "C:\\Users\\me",
    "shared": "C:\\Users\\me\\.agents\\skills",
    "agents": [
        {"id": "codex", "name": "Codex", "folder": "C:\\Users\\me\\.agents\\skills", "shares": True, "detected": True},
        {
            "id": "claude-code",
            "name": "Claude Code",
            "folder": "C:\\Users\\me\\.claude\\skills",
            "shares": False,
            "detected": True,
        },
    ],
    "installed": ["codex"],
}


class StandIn:
    """Listens as the Windows app does, keeps what it was asked, and answers with `answer`."""

    def __init__(self) -> None:
        self.asked: list[dict[str, Any]] = []
        self.answer: Any = {"ok": True, "state": STATE}
        self._listener = socket.create_server(("127.0.0.1", 0))
        self.port = int(self._listener.getsockname()[1])
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self) -> None:
        while True:
            try:
                connection, _ = self._listener.accept()
            except OSError:
                return
            with connection, connection.makefile("rwb") as lines:
                self.asked.append(json.loads(lines.readline()))
                answer = self.answer if isinstance(self.answer, str) else json.dumps(self.answer)
                lines.write(answer.encode() + b"\n")

    def close(self) -> None:
        self._listener.close()


@pytest.fixture
def stand_in(monkeypatch: pytest.MonkeyPatch) -> Iterator[StandIn]:
    app = StandIn()
    monkeypatch.setenv(windows_app.PORT_VARIABLE, str(app.port))
    monkeypatch.setenv(windows_app.TOKEN_VARIABLE, TOKEN)
    yield app
    app.close()


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


async def test_a_server_started_any_other_way_has_no_windows_app(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(windows_app.PORT_VARIABLE, raising=False)
    monkeypatch.delenv(windows_app.TOKEN_VARIABLE, raising=False)
    async with Client(lib.app_server().server) as client:
        assert await call(client, "read_windows_app") == {"windows_app": None}
        for tool in TOOLS[1:]:
            arguments = {"agents": [], "mode": "symlink"} if tool == "install_skill" else {}
            assert "isn't what started this server" in await refused(client, tool, **arguments)


async def test_the_windows_app_is_read_and_changed_with_its_token(stand_in: StandIn) -> None:
    async with Client(lib.app_server().server) as client:
        assert await call(client, "read_windows_app") == {"windows_app": STATE}

        stand_in.answer = {"ok": True, "state": {**STATE, "lan": True}}
        assert (await call(client, "change_windows_app", lan=True))["lan"] is True
        await call(client, "change_windows_app", start_at_sign_in=False)

        stand_in.answer = {"ok": True, "state": {**STATE, "update": "0.2.0"}}
        assert (await call(client, "check_for_update"))["update"] == "0.2.0"
        stand_in.answer = {"ok": True, "state": {**STATE, "update": "0.2.0", "updating": True}}
        assert (await call(client, "install_update"))["updating"] is True

    # A setting that isn't given isn't sent, so the Windows app leaves it as it is.
    assert stand_in.asked == [
        {"token": TOKEN, "do": "state"},
        {"token": TOKEN, "do": "set", "lan": True},
        {"token": TOKEN, "do": "set", "start_at_sign_in": False},
        {"token": TOKEN, "do": "check_for_update"},
        {"token": TOKEN, "do": "install_update"},
    ]


async def test_the_agent_skill_is_installed_for_the_agents_listed(stand_in: StandIn) -> None:
    async with Client(lib.app_server().server) as client:
        stand_in.answer = {"ok": True, "agents": AGENTS}
        assert await call(client, "list_skill_agents") == AGENTS

        skill = {"agents": ["Claude Code", "Codex"], "mode": "copy"}
        stand_in.answer = {"ok": True, "state": {**STATE, "skill": skill}}
        assert (await call(client, "install_skill", agents=["claude-code"], mode="copy"))["skill"] == skill
        stand_in.answer = {"ok": True, "state": STATE}
        assert (await call(client, "remove_skill"))["skill"] is None

        # Only the two ways the skills CLI installs a skill.
        assert (await client.call_tool("install_skill", {"agents": [], "mode": "hardlink"})).is_error

    assert stand_in.asked == [
        {"token": TOKEN, "do": "list_agents"},
        {"token": TOKEN, "do": "install_skill", "agents": ["claude-code"], "mode": "copy"},
        {"token": TOKEN, "do": "remove_skill"},
    ]


async def test_a_list_of_agents_that_cant_be_read_is_said(stand_in: StandIn) -> None:
    stand_in.answer = {"ok": True, "agents": {"agents": "all"}}
    async with Client(lib.app_server().server) as client:
        assert "couldn't be read" in await refused(client, "list_skill_agents")


async def test_what_the_windows_app_cant_do_is_said_in_its_words(stand_in: StandIn) -> None:
    stand_in.answer = {"ok": False, "error": "There is no newer version to update to."}
    async with Client(lib.app_server().server) as client:
        assert await refused(client, "install_update") == "There is no newer version to update to."


@pytest.mark.parametrize("answer", ["", "not json", "[]", '{"ok": true}', '{"ok": true, "state": {"version": 1}}'])
async def test_an_answer_that_isnt_the_windows_apps_is_said(stand_in: StandIn, answer: str) -> None:
    stand_in.answer = answer
    async with Client(lib.app_server().server) as client:
        assert "couldn't be read" in await refused(client, "read_windows_app")


async def test_a_windows_app_that_is_gone_is_said(stand_in: StandIn) -> None:
    stand_in.close()
    async with Client(lib.app_server().server) as client:
        assert "didn't answer" in await refused(client, "check_for_update")


def test_only_a_page_on_this_machine_reaches_the_windows_app() -> None:
    tools = {tool.name: tool for tool in own_tools(Known(), lambda: None)}
    assert all(tools[name].local_only for name in TOOLS)
