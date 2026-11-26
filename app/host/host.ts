import {
  AppBridge,
  RESOURCE_MIME_TYPE,
  buildAllowAttribute,
  type McpUiResourcePermissions,
  type McpUiSandboxProxyReadyNotification,
  type McpUiTheme,
} from "@modelcontextprotocol/ext-apps/app-bridge";
import { EXTENSION_ID } from "@modelcontextprotocol/ext-apps/server";
import {
  Client,
  StreamableHTTPClientTransport,
} from "@modelcontextprotocol/client";

import { SERVER_RESTARTING } from "../src/lib/restart";
import { QuietPostMessageTransport } from "../src/lib/transport";

const HOST = { name: "Reference Store browser host", version: "1.0.0" };
const VIEW_URI = "ui://reference-store/app";
const SANDBOX_ATTRIBUTE = "allow-scripts allow-same-origin allow-forms";
const PROXY_READY: McpUiSandboxProxyReadyNotification["method"] =
  "ui/notifications/sandbox-proxy-ready";
const RESTART_CHECK_MS = 500;
// An update is downloaded before the server ends, so the wait for it to end is a long one.
const RESTART_PATIENCE_MS = 10 * 60 * 1000;

const darkScheme = window.matchMedia("(prefers-color-scheme: dark)");
const theme = (): McpUiTheme => (darkScheme.matches ? "dark" : "light");
const containerDimensions = () => ({
  width: window.innerWidth,
  height: window.innerHeight,
});

/** The port a page was served its sandbox on, which each run of the server picks anew. */
function sandboxPort(page: Document): string | null {
  const port = page
    .querySelector<HTMLMetaElement>('meta[name="reference-store-sandbox-port"]')
    ?.content.trim();
  return port && /^\d+$/.test(port) ? port : null;
}

function sandboxUrl(): URL {
  const port = sandboxPort(document);
  if (!port) {
    throw new Error(
      "This page was not served by `reference-store app`, so it has no sandbox to load the view in.",
    );
  }
  // Same hostname as this page, other port: a different origin, as the MCP Apps spec requires of a web host.
  return new URL(
    `${location.protocol}//${location.hostname}:${port}/sandbox.html`,
  );
}

async function readView(
  client: Client,
): Promise<{ html: string; permissions?: McpUiResourcePermissions }> {
  const { contents } = await client.readResource({ uri: VIEW_URI });
  const [content] = contents;
  if (contents.length !== 1 || content.mimeType !== RESOURCE_MIME_TYPE) {
    throw new Error(
      `${VIEW_URI} is not a single ${RESOURCE_MIME_TYPE} resource.`,
    );
  }
  const html = "blob" in content ? atob(content.blob) : content.text;
  const permissions = (
    content._meta?.ui as { permissions?: McpUiResourcePermissions } | undefined
  )?.permissions;
  return { html, permissions };
}

function loadSandbox(
  url: URL,
  permissions?: McpUiResourcePermissions,
): Promise<HTMLIFrameElement> {
  const iframe = document.createElement("iframe");
  iframe.title = "Reference Store";
  iframe.setAttribute("sandbox", SANDBOX_ATTRIBUTE);
  const allow = buildAllowAttribute(permissions);
  if (allow) {
    iframe.setAttribute("allow", allow);
  }
  const ready = new Promise<HTMLIFrameElement>((resolve) => {
    const listener = ({ source, data }: MessageEvent) => {
      if (source === iframe.contentWindow && data?.method === PROXY_READY) {
        window.removeEventListener("message", listener);
        resolve(iframe);
      }
    };
    window.addEventListener("message", listener);
  });
  iframe.src = url.href;
  document.body.append(iframe);
  return ready;
}

function createBridge(client: Client): AppBridge {
  const capabilities = client.getServerCapabilities();
  const bridge = new AppBridge(
    client,
    HOST,
    {
      openLinks: {},
      serverTools: capabilities?.tools,
      serverResources: capabilities?.resources,
    },
    {
      // No style variables, so the view keeps its own look in every host.
      hostContext: {
        theme: theme(),
        platform: "web",
        displayMode: "fullscreen",
        availableDisplayModes: ["fullscreen"],
        containerDimensions: containerDimensions(),
      },
    },
  );
  bridge.onopenlink = async ({ url }) => {
    window.open(url, "_blank", "noopener,noreferrer");
    return {};
  };
  // The view fills the window and scrolls itself, so its reported size changes nothing here.
  bridge.onsizechange = () => {};
  darkScheme.addEventListener("change", () =>
    bridge.sendHostContextChange({ theme: theme() }),
  );
  window.addEventListener("resize", () =>
    bridge.sendHostContextChange({
      containerDimensions: containerDimensions(),
    }),
  );
  return bridge;
}

function showStatus(text: string) {
  const status = document.getElementById("status")!;
  status.textContent = text;
  status.hidden = false;
}

/** Which run of the server answers now, by its sandbox port, or null when none answers. */
async function servingNow(): Promise<string | null> {
  try {
    const response = await fetch("/", { cache: "no-store" });
    const page = new DOMParser().parseFromString(
      await response.text(),
      "text/html",
    );
    return response.ok ? sandboxPort(page) : null;
  } catch {
    return null;
  }
}

/**
 * Loads the page again on the server that follows this one, once the view says this one is about to end, as it is
 * when the Windows app changes who may reach it or updates. The view's connection is to the server that ended.
 */
function reloadAfterRestart(iframe: HTMLIFrameElement) {
  const served = sandboxPort(document);
  let watching = false;
  const watch = async () => {
    const deadline = Date.now() + RESTART_PATIENCE_MS;
    let ended = false;
    while (Date.now() < deadline) {
      const now = await servingNow();
      if (now !== null && (ended || now !== served)) {
        location.reload();
        return;
      }
      if (now === null && !ended) {
        ended = true;
        iframe.style.display = "none";
        showStatus(
          "Reference Store isn't running right now. This page loads again once it is back.",
        );
      }
      await new Promise((resolve) => setTimeout(resolve, RESTART_CHECK_MS));
    }
    watching = false;
    if (ended) {
      showStatus(
        "Reference Store didn't come back. Open it from its shortcut, then reload this page.",
      );
    }
  };
  window.addEventListener("message", ({ source, data }) => {
    if (
      source === iframe.contentWindow &&
      data?.type === SERVER_RESTARTING &&
      !watching
    ) {
      watching = true;
      void watch();
    }
  });
}

async function main(): Promise<void> {
  const client = new Client(HOST, {
    capabilities: {
      extensions: { [EXTENSION_ID]: { mimeTypes: [RESOURCE_MIME_TYPE] } },
    },
  });
  await client.connect(
    new StreamableHTTPClientTransport(new URL("/mcp", location.href)),
  );
  const view = await readView(client);
  const iframe = await loadSandbox(sandboxUrl(), view.permissions);
  reloadAfterRestart(iframe);

  const bridge = createBridge(client);
  const initialized = new Promise<void>((resolve) => {
    bridge.oninitialized = () => resolve();
  });
  await bridge.connect(
    new QuietPostMessageTransport(iframe.contentWindow!, iframe.contentWindow!),
  );
  await bridge.sendSandboxResourceReady(view);
  await initialized;
  // The app fills the page, so keys reach it without a click into it first.
  iframe.focus();
}

main().catch((cause: unknown) => {
  showStatus(
    `Could not open the app. ${cause instanceof Error ? cause.message : String(cause)} Check that \`reference-store app\` is still running, then reload.`,
  );
  document.querySelector("iframe")?.remove();
});
