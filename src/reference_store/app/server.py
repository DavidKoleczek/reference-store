"""The app's server: the view as an MCP App, and the browser pages that show it."""

import threading
from typing import Any

from mcp import MCPError
from mcp.server import Server, ServerRequestContext
from mcp.server.apps import APP_MIME_TYPE, EXTENSION_ID
from mcp.types import (
    INVALID_PARAMS,
    ListResourcesResult,
    PaginatedRequestParams,
    ReadResourceRequestParams,
    ReadResourceResult,
    Resource,
    TextResourceContents,
)

from reference_store.app.pages import Pages, serve_pages, view
from reference_store.models import App, ReferenceStoreError

VIEW_URI = "ui://reference-store/app"
VIEW = Resource(uri=VIEW_URI, name="Reference Store app", mime_type=APP_MIME_TYPE)


class AppServer:
    """The app's server. Nothing listens until `open` is called.

    The view is an MCP App, so `server` is an MCP server that offers it as a resource. The browser pages reach that
    server to show the view.
    """

    def __init__(self, server_name: str, version: str) -> None:
        self._lock = threading.Lock()
        self._pages: Pages | None = None
        self.server = Server(
            server_name,
            version=version,
            on_list_resources=self._list_resources,
            on_read_resource=self._read_resource,
        )
        self.server.extensions[EXTENSION_ID] = {}

    def open(self, port: int | None = None, lan: bool = False) -> App:
        """Serves the app in a browser page, unless it already is, and returns once it listens.

        Without `port` a free one is picked. It listens on `127.0.0.1` only, unless `lan` is set, which lets devices
        on the local network reach it.

        Raises:
            ReferenceStoreError: The port is held by something else.
        """
        if lan:
            raise NotImplementedError
        with self._lock:
            if self._pages is None:
                self._pages = serve_pages(self.server, port)
            return App(url=self._pages.url)

    def close(self) -> None:
        """Stops serving the app, if it was opened."""
        with self._lock:
            if self._pages is not None:
                self._pages.stop()
                self._pages = None

    async def _list_resources(
        self, ctx: ServerRequestContext[Any], params: PaginatedRequestParams | None
    ) -> ListResourcesResult:
        return ListResourcesResult(resources=[VIEW])

    async def _read_resource(
        self, ctx: ServerRequestContext[Any], params: ReadResourceRequestParams
    ) -> ReadResourceResult:
        if params.uri != VIEW_URI:
            raise MCPError(INVALID_PARAMS, f"'{params.uri}' is not a resource of this server. It has {VIEW_URI}.")
        try:
            contents = TextResourceContents(uri=VIEW_URI, mime_type=APP_MIME_TYPE, text=view())
        except ReferenceStoreError as error:
            raise MCPError(INVALID_PARAMS, str(error)) from None
        return ReadResourceResult(contents=[contents])
