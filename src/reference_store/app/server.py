"""The app's server: the view as an MCP App, the tools and resources it reads and changes the stores through, and the
browser pages that show it."""

import asyncio
import json
import threading
from typing import Any

from mcp import MCPError
from mcp.server import Server, ServerRequestContext
from mcp.server.apps import APP_MIME_TYPE, EXTENSION_ID
from mcp.types import (
    INVALID_PARAMS,
    CallToolRequestParams,
    CallToolResult,
    ListResourcesResult,
    ListResourceTemplatesResult,
    ListToolsResult,
    PaginatedRequestParams,
    ReadResourceRequestParams,
    ReadResourceResult,
    Resource,
    TextContent,
    TextResourceContents,
)
from pydantic import ValidationError

from reference_store.app import network, resources, uploads
from reference_store.app.known import Known
from reference_store.app.own_tools import own_tools
from reference_store.app.pages import Pages, serve_pages, view
from reference_store.app.tools import VIEW_URI, AppTool, library_tools
from reference_store.models import App, ReferenceStoreError

VIEW = Resource(uri=VIEW_URI, name="Reference Store app", mime_type=APP_MIME_TYPE)


class AppServer:
    """The app's server. Nothing listens until `open` is called.

    The view is an MCP App, so `server` is an MCP server that offers it as a resource, with the tools and resources
    the view calls. The browser pages reach that server to show the view.
    """

    def __init__(self, server_name: str, version: str) -> None:
        self._lock = threading.Lock()
        self._pages: Pages | None = None
        self._known = Known()
        self._tools: dict[str, AppTool] = {
            tool.name: tool for tool in [*library_tools(self._known), *own_tools(self._known, self._lan_url)]
        }
        self.server = Server(
            server_name,
            version=version,
            on_list_tools=self._list_tools,
            on_call_tool=self._call_tool,
            on_list_resources=self._list_resources,
            on_list_resource_templates=self._list_resource_templates,
            on_read_resource=self._read_resource,
        )
        self.server.extensions[EXTENSION_ID] = {}

    def open(self, port: int | None = None, lan: bool = False) -> App:
        """Serves the app in a browser page, unless it already is, and returns once it listens.

        Without `port` a free one is picked. It listens on `127.0.0.1` only, unless `lan` is set, which lets devices
        on the local network reach it with its key.

        Raises:
            ReferenceStoreError: The port is held by something else.
        """
        with self._lock:
            if self._pages is None:
                uploads.clear_old()
                self._pages = serve_pages(self.server, port, lan)
            return App(url=self._pages.url, lan_url=self._pages.lan_url)

    def close(self) -> None:
        """Stops serving the app, if it was opened."""
        with self._lock:
            if self._pages is not None:
                self._pages.stop()
                self._pages = None

    async def _list_tools(
        self, ctx: ServerRequestContext[Any], params: PaginatedRequestParams | None
    ) -> ListToolsResult:
        return ListToolsResult(tools=[tool.tool for tool in self._tools.values()])

    async def _call_tool(self, ctx: ServerRequestContext[Any], params: CallToolRequestParams) -> CallToolResult:
        tool = self._tools.get(params.name)
        if tool is None:
            return _failed(f"There is no tool {params.name}. The tools are: {', '.join(self._tools)}.")
        here = self._from_this_machine(ctx)
        if tool.local_only and not here:
            return _failed(f"{params.name} is about this machine's disk, so only a page on this machine can use it.")
        # Copied into the thread the tool runs in, for the tools that say where they were asked from.
        network.FROM_THIS_MACHINE.set(here)
        try:
            result = await asyncio.to_thread(tool.call, params.arguments or {})
        except ReferenceStoreError as error:
            return _failed(str(error))
        except ValidationError as error:
            return _failed(_invalid(params.name, error))
        # Structured content is an object, so a list or nothing goes under `result`.
        structured = {"result": result}
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result))], structured_content=structured
        )

    def _lan_url(self) -> str | None:
        pages = self._pages
        return pages.lan_url if pages is not None else None

    def _from_this_machine(self, ctx: ServerRequestContext[Any]) -> bool:
        """Whether a request came from this machine. Without `lan` nothing else can reach the server."""
        pages = self._pages
        if pages is None or pages.machine is None:
            return True
        address = getattr(getattr(ctx.request, "client", None), "host", None)
        return isinstance(address, str) and network.is_this_machine(address, pages.machine)

    async def _list_resources(
        self, ctx: ServerRequestContext[Any], params: PaginatedRequestParams | None
    ) -> ListResourcesResult:
        return ListResourcesResult(resources=[VIEW])

    async def _list_resource_templates(
        self, ctx: ServerRequestContext[Any], params: PaginatedRequestParams | None
    ) -> ListResourceTemplatesResult:
        return ListResourceTemplatesResult(resource_templates=resources.TEMPLATES)

    async def _read_resource(
        self, ctx: ServerRequestContext[Any], params: ReadResourceRequestParams
    ) -> ReadResourceResult:
        try:
            if params.uri == VIEW_URI:
                contents = TextResourceContents(uri=VIEW_URI, mime_type=APP_MIME_TYPE, text=view())
                return ReadResourceResult(contents=[contents])
            if resources.is_resource(params.uri):
                return ReadResourceResult(contents=[await asyncio.to_thread(resources.read, params.uri, self._known)])
        except ReferenceStoreError as error:
            raise MCPError(INVALID_PARAMS, str(error)) from None
        raise MCPError(
            INVALID_PARAMS,
            f"'{params.uri}' is not a resource of this server. It has {VIEW_URI}, and "
            f"{', '.join(template.uri_template for template in resources.TEMPLATES)}.",
        )


def _failed(message: str) -> CallToolResult:
    return CallToolResult(content=[TextContent(type="text", text=message)], is_error=True)


def _invalid(name: str, error: ValidationError) -> str:
    problems = "; ".join(
        f"{'.'.join(str(part) for part in problem['loc']) or 'the arguments'}: {problem['msg']}"
        for problem in error.errors()
    )
    return f"{name} can't take those arguments. {problems}."
