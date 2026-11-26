"""The browser pages that show the app: the host page, and the sandbox it loads the view in."""

from html import escape
from pathlib import Path
import socket
import threading
from urllib.parse import urlencode

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse, Response
from mcp.server import Server
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send
import uvicorn

from reference_store.app import network
from reference_store.models import ReferenceStoreError
from reference_store.skill.skill import repository_url, tool_version

STATIC = Path(__file__).parent / "static"
VIEW = STATIC / "view" / "mcp_app.html"
HOST_STATIC = STATIC / "host"
BUILD_COMMAND = "uv run build-app.py"
HOST = "127.0.0.1"
# Every IPv4 address of the machine, so devices on the local network reach it.
EVERY_ADDRESS = "0.0.0.0"
STOP_TIMEOUT_SECONDS = 5
# How long a device keeps the key once it has visited with it: the longest a browser keeps a cookie.
KEY_SECONDS = 400 * 24 * 60 * 60
# The spec's restrictive default for a view that declares no `ui.csp`, with frames, objects, and base URIs locked down
# as in its example host. The view is written into a frame of the sandbox page, so it inherits this policy.
VIEW_CSP = (
    "default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
    "font-src 'self'; media-src 'self' data:; connect-src 'none'; frame-src 'none'; object-src 'none'; "
    "base-uri 'self'"
)


class Pages:
    """The pages while they are served: where to open the app in a browser, on this machine and on the network."""

    def __init__(
        self,
        url: str,
        lan_url: str | None,
        machine: network.Machine | None,
        servers: list[uvicorn.Server],
        threads: list[threading.Thread],
    ) -> None:
        self.url = url
        self.lan_url = lan_url
        # This machine's addresses when the pages are on the local network, and None when only it can reach them.
        self.machine = machine
        self._servers = servers
        self._threads = threads

    def stop(self) -> None:
        """Disconnects every page and stops serving."""
        for server in self._servers:
            server.should_exit = True
        for thread in self._threads:
            thread.join(STOP_TIMEOUT_SECONDS)


def view() -> str:
    """Returns the view's HTML, with the tool's version and where its docs are.

    Raises:
        ReferenceStoreError: The view is not compiled.
    """
    if not VIEW.is_file():
        raise ReferenceStoreError(
            f"The app's view is not compiled: {VIEW} does not exist. Run `{BUILD_COMMAND}` from the repository root."
        )
    html = VIEW.read_text(encoding="utf-8")
    return html.replace("{{version}}", escape(tool_version())).replace("{{repository}}", escape(repository_url() or ""))


def serve_pages(server: Server, port: int | None = None, lan: bool = False) -> Pages:
    """Serves the host page for `server`'s view from daemon threads, and returns once both ports listen.

    With `lan`, both ports listen on every IPv4 address, and only devices on the local network with the key are
    answered, as `network.judge` says.

    Raises:
        ReferenceStoreError: The port is held by something else.
    """
    address = EVERY_ADDRESS if lan else HOST
    # Bound and listening before this returns, so the URL answers at once and a held port is a named failure.
    host_sock = _bind(address, port)
    try:
        sandbox_sock = _bind(address, None)
    except ReferenceStoreError:
        host_sock.close()
        raise
    host_port = int(host_sock.getsockname()[1])
    sandbox_port = int(sandbox_sock.getsockname()[1])
    here = network.machine() if lan else None
    apis: tuple[ASGIApp, ASGIApp] = (
        _create_host_api(server, sandbox_port, here),
        _create_sandbox_api(host_port),
    )
    lan_url = None
    if here is not None:
        key = network.key()
        apis = (Guard(apis[0], key, here), Guard(apis[1], key, here))
        address_on_lan = network.lan_address()
        if address_on_lan is not None:
            lan_url = f"http://{address_on_lan}:{host_port}/?{urlencode({network.KEY_PARAMETER: key})}"
    servers: list[uvicorn.Server] = []
    threads: list[threading.Thread] = []
    for api, sock in zip(apis, (host_sock, sandbox_sock), strict=True):
        uvicorn_server = uvicorn.Server(uvicorn.Config(api, log_config=None, log_level="warning"))
        thread = threading.Thread(target=uvicorn_server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        servers.append(uvicorn_server)
        threads.append(thread)
    return Pages(f"http://{HOST}:{host_port}", lan_url, here, servers, threads)


class Guard:
    """Answers a request only when `network.judge` lets it in, and keeps a key given in the URL as a cookie."""

    def __init__(self, app: ASGIApp, key: str, here: network.Machine) -> None:
        self._app = app
        self._key = key
        self._here = here

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        request = Request(scope)
        verdict = network.judge(
            request.client.host if request.client else None,
            request.headers.get("host"),
            request.cookies.get(network.KEY_COOKIE),
            request.query_params.get(network.KEY_PARAMETER),
            self._key,
            self._here,
        )
        if not verdict.allowed:
            await PlainTextResponse(verdict.reason, status_code=403)(scope, receive, send)
            return
        if verdict.keep_key and request.method == "GET":
            # The key leaves the address bar, and the browser keeps it, so the page can be bookmarked without it.
            rest = {name: value for name, value in request.query_params.items() if name != network.KEY_PARAMETER}
            target = request.url.path + (f"?{urlencode(rest)}" if rest else "")
            response = RedirectResponse(target, status_code=303)
            response.set_cookie(
                network.KEY_COOKIE, self._key, max_age=KEY_SECONDS, httponly=True, samesite="lax", path="/"
            )
            await response(scope, receive, send)
            return
        await self._app(scope, receive, send)


def _create_host_api(server: Server, sandbox_port: int, here: network.Machine | None) -> FastAPI:
    # The SDK guards `/mcp` against DNS rebinding for a loopback host by default, so only this machine's pages reach it.
    # On the local network it is told this machine's own names, which `Guard` checks for the pages too.
    security = (
        None
        if here is None
        else TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[f"{name}:*" for name in here.names],
            allowed_origins=[f"http://{name}:*" for name in here.names],
        )
    )
    mcp_api = server.streamable_http_app(host=HOST, transport_security=security)
    # FastAPI runs only its own lifespan, never a mounted app's, and the session manager must be running to serve.
    api = FastAPI(lifespan=lambda _: server.session_manager.run(), docs_url=None, redoc_url=None, openapi_url=None)
    api.router.routes.extend(mcp_api.routes)

    @api.get("/{page_path:path}", include_in_schema=False)
    def page(page_path: str) -> Response:
        index = HOST_STATIC / "index.html"
        if not index.is_file():
            return _not_compiled()
        candidate = (HOST_STATIC / page_path).resolve()
        if candidate.is_relative_to(HOST_STATIC.resolve()) and candidate.is_file() and candidate.suffix != ".html":
            return FileResponse(candidate)
        return HTMLResponse(index.read_text(encoding="utf-8").replace("{{sandbox_port}}", str(sandbox_port)))

    return api


def _create_sandbox_api(host_port: int) -> FastAPI:
    """The sandbox page, on its own origin as the MCP Apps spec requires of a web host, with the view's CSP."""
    api = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @api.get("/sandbox.html", include_in_schema=False)
    def sandbox() -> Response:
        page = HOST_STATIC / "sandbox.html"
        if not page.is_file():
            return _not_compiled()
        return HTMLResponse(
            page.read_text(encoding="utf-8").replace("{{host_port}}", str(host_port)),
            headers={"Content-Security-Policy": VIEW_CSP, "Cache-Control": "no-store"},
        )

    @api.get("/assets/{asset}", include_in_schema=False)
    def asset(asset: str) -> Response:
        assets = (HOST_STATIC / "assets").resolve()
        candidate = (assets / asset).resolve()
        if candidate.is_relative_to(assets) and candidate.is_file():
            return FileResponse(candidate)
        return PlainTextResponse("Not found.", status_code=404)

    return api


def _not_compiled() -> Response:
    return PlainTextResponse(
        f"The app is not compiled. Run `{BUILD_COMMAND}` from the repository root.", status_code=503
    )


def _bind(address: str, port: int | None) -> socket.socket:
    # SO_REUSEADDR stays off: on Windows it lets a second app bind a port the first still holds.
    sock = socket.socket(socket.AF_INET)
    try:
        sock.bind((address, port or 0))
    except OSError as error:
        sock.close()
        raise ReferenceStoreError(
            f"The app could not bind {address}:{port}: {error.strerror or error}. "
            "Omit the port to have a free one chosen, or pass one nothing else holds."
        ) from error
    sock.listen()
    return sock
