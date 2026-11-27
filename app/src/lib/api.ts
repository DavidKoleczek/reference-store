/**
 * The app's tools and resources, with what they take and return. Each library tool has the name and arguments of the
 * function in `reference_store.lib`, and answers with its model, as `docs/01-library.md` has them.
 */
import type { CallToolResult } from "@modelcontextprotocol/client";

import { app } from "@/lib/host";
import { gotNoAnswer } from "@/lib/restart";
import { TEXT } from "@/lib/text";

export type Store = {
  name: string;
  kind: "directory" | "github";
  location: string;
  /** Where its files are on the machine the app runs on. */
  path: string;
  default: boolean;
  /** 1 is the highest, and 0 is the project's store. */
  priority_order: number;
  /** False when it can't be reached, such as a NAS that is offline. */
  available: boolean;
  push: boolean;
  /** A clone of a repository that isn't pushed to, which can't be changed. */
  read_only: boolean;
  /** When it was last in step with GitHub, ISO 8601. */
  synced: string | null;
  sync_error: string | null;
};

export type StoreSync = {
  store: string;
  pulled: number;
  pushed: number;
  left_out: string[];
  error: string | null;
};

export type Preview = { path: string; url: string | null };

export type EntryFile = {
  /** Its path in the entry, with forward slashes. */
  path: string;
  full_path: string;
  size: number;
  /** ISO 8601. */
  modified: string;
  description: string;
  notes: string;
  tags: string[];
};

export type EntrySummary = {
  id: string;
  name: string;
  /** Shown in place of the name. */
  title: string | null;
  store: string;
  description: string;
  url: string | null;
  tags: string[];
  notes: string;
  /** 1 to 5. */
  rating: number | null;
  preview: Preview | null;
  file_count: number;
  size: number;
  /** When the reference itself was first published, as far as is known. ISO 8601. */
  source_published_at: string | null;
  created: string;
  updated: string;
};

export type Entry = EntrySummary & { folder: string; files: EntryFile[] };

/** An entry, by the store it is in and its name, which together tell it from every other. */
export type EntryRef = { store: string; name: string };

export function sameEntry(a: EntryRef | null, b: EntryRef | null): boolean {
  return (
    a !== null &&
    b !== null &&
    a.store === b.store &&
    a.name.toLowerCase() === b.name.toLowerCase()
  );
}

export type TagMatch = "all" | "any";
export type EntrySort =
  | "name"
  | "created"
  | "updated"
  | "published"
  | "rating"
  | "size"
  | "files"
  | "tags"
  | "store";
export type FileSort = "path" | "name" | "modified" | "size" | "type";

export type EntryListing = {
  entries: EntrySummary[];
  total: number;
  after: string | null;
};

export type TagCount = { tag: string; entries: number; files: number };

export type SiteCount = {
  site: string;
  entries: number;
  groups: { group: string; entries: number }[];
};

export type GrepField =
  | "name"
  | "title"
  | "description"
  | "url"
  | "tags"
  | "notes"
  | "file_descriptions"
  | "file_notes"
  | "file_tags"
  | "file_contents";

export type GrepListing = {
  results: { entry: EntrySummary; match_count: number }[];
  total: number;
  after: string | null;
};

export type FileMatch = EntryFile & { entry: string; store: string };

export type FileListing = {
  files: FileMatch[];
  total: number;
  after: string | null;
};

export type NewFile = {
  /** What `upload_file` returned for it. */
  source: string;
  path?: string;
  description?: string;
  notes?: string;
  tags?: string[];
  move?: boolean;
};

export type NewPreview = { source?: string; file?: string; url?: string };

/** The filters `list_entries`, `grep_entries`, and `glob_files` share. */
export type EntryFilters = {
  tags?: string[];
  file_tags?: string[];
  tag_match?: TagMatch;
  min_rating?: number;
  sites?: string[];
  without_tags?: boolean;
  without_site?: boolean;
  store?: string;
};

/** A tool's failure, with the library's message, which says what went wrong and what to do. */
export class ToolError extends Error {}

async function call<Result>(
  name: string,
  args: Record<string, unknown> = {},
): Promise<Result> {
  let result: CallToolResult;
  try {
    result = await app.callServerTool({ name, arguments: args });
  } catch (cause) {
    gotNoAnswer();
    throw cause;
  }
  if (result.isError) {
    const text = result.content.find((each) => each.type === "text");
    throw new ToolError(text?.text ?? TEXT.errors.toolFailed(name));
  }
  const structured = result.structuredContent as { result: Result } | undefined;
  if (!structured) {
    throw new ToolError(TEXT.errors.noResult(name));
  }
  return structured.result;
}

/** Leaves out what is undefined, so the library's own default holds for it. */
function given(args: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(args).filter(([, value]) => value !== undefined),
  );
}

export const listStores = () => call<Store[]>("list_stores");

export const addStore = (
  name: string,
  location: string,
  isDefault = false,
  push = false,
) => call<Store>("add_store", { name, location, default: isDefault, push });

export const removeStore = (name: string) =>
  call<null>("remove_store", { name });

export const setDefaultStore = (name: string) =>
  call<Store>("set_default_store", { name });

export const setStorePriority = (name: string, priorityOrder: number) =>
  call<Store[]>("set_store_priority", { name, priority_order: priorityOrder });

export const syncStore = (store?: string) =>
  call<StoreSync[]>("sync_store", given({ store }));

export const listEntries = (
  filters: EntryFilters,
  sort: EntrySort,
  descending: boolean,
  limit: number,
  after: string | null,
) =>
  call<EntryListing>(
    "list_entries",
    given({ ...filters, sort, descending, limit, after: after ?? undefined }),
  );

/** Every field but the files' contents, which would read every text file in every store. */
const SEARCHED: GrepField[] = [
  "name",
  "title",
  "description",
  "url",
  "tags",
  "notes",
  "file_descriptions",
  "file_notes",
  "file_tags",
];

/** The entries that have `text` in a field, whatever its case, sorted by name. */
export async function searchEntries(
  text: string,
  filters: EntryFilters,
  limit: number,
  after: string | null,
): Promise<EntryListing> {
  const found = await call<GrepListing>(
    "grep_entries",
    given({
      pattern: escapeRegex(text),
      fields: SEARCHED,
      ignore_case: true,
      matches_per_entry: 1,
      ...filters,
      limit,
      after: after ?? undefined,
    }),
  );
  return {
    entries: found.results.map((result) => result.entry),
    total: found.total,
    after: found.after,
  };
}

export const listTags = (store?: string) =>
  call<TagCount[]>("list_tags", given({ store }));

export const listSites = (store?: string) =>
  call<SiteCount[]>("list_sites", given({ store }));

export const getEntry = (name: string, store: string) =>
  call<Entry>("get_entry", { name, store });

export const addEntry = (args: {
  name: string;
  title?: string;
  description?: string;
  url?: string;
  tags?: string[];
  notes?: string;
  rating?: number;
  preview?: NewPreview;
  files?: NewFile[];
  store?: string;
}) => call<Entry>("add_entry", given(args));

/** What can change about an entry. Left out keeps it, and null clears it. */
export type EntryChange = {
  title?: string | null;
  description?: string;
  url?: string | null;
  notes?: string;
  rating?: number | null;
  preview?: NewPreview | null;
  source_published_at?: string | null;
  add_tags?: string[];
  remove_tags?: string[];
};

export const updateEntry = (name: string, store: string, change: EntryChange) =>
  call<Entry>("update_entry", given({ name, store, ...change }));

export const renameEntry = (name: string, store: string, newName: string) =>
  call<Entry>("rename_entry", { name, store, new_name: newName });

export const moveEntry = (name: string, store: string, toStore: string) =>
  call<Entry>("move_entry", { name, store, to_store: toStore });

export const deleteEntry = (name: string, store: string) =>
  call<null>("delete_entry", { name, store });

export const addFiles = (name: string, store: string, files: NewFile[]) =>
  call<Entry>("add_files", { name, store, files });

export type FileChange = {
  description?: string;
  notes?: string;
  add_tags?: string[];
  remove_tags?: string[];
};

export const updateFile = (
  name: string,
  store: string,
  path: string,
  change: FileChange,
) => call<Entry>("update_file", given({ name, store, path, ...change }));

export const renameFile = (
  name: string,
  store: string,
  path: string,
  newPath: string,
) => call<Entry>("rename_file", { name, store, path, new_path: newPath });

export const deleteFile = (name: string, store: string, path: string) =>
  call<Entry>("delete_file", { name, store, path });

export const globFiles = (
  pattern: string,
  filters: EntryFilters,
  sort: FileSort,
  descending: boolean,
  limit: number,
  after: string | null,
) =>
  call<FileListing>(
    "glob_files",
    given({
      pattern,
      ...filters,
      sort,
      descending,
      limit,
      after: after ?? undefined,
    }),
  );

/** One of an entry's files, as the app's own tools and resources name it. */
export type FileOf = { store: string; entry: string; path: string };

/** The width and height of each file, or null for one that isn't an image. */
export async function imageSizes(
  files: FileOf[],
): Promise<([number, number] | null)[]> {
  return (
    await call<{ sizes: ([number, number] | null)[] }>("image_sizes", { files })
  ).sizes;
}

export const uploadPiece = (
  upload: string,
  path: string,
  offset: number,
  data: string,
) =>
  call<{ source: string; received: number }>("upload_file", {
    upload,
    path,
    offset,
    data,
  });

export const showInFileManager = (
  store: string,
  entry?: string,
  path?: string,
) => call<null>("show_in_file_manager", given({ store, entry, path }));

export async function readAppSettings(): Promise<Record<string, unknown>> {
  return (
    await call<{ settings: Record<string, unknown> }>("read_app_settings")
  ).settings;
}

export const saveAppSettings = (settings: Record<string, unknown>) =>
  call<null>("save_app_settings", { settings });

/** The two sizes the server makes of an image: small for cards, walls, and rows, large for the preview pane. */
export type ThumbnailSize = "small" | "large";

const segments = (...parts: string[]) =>
  parts
    .flatMap((part) => part.split("/"))
    .map(encodeURIComponent)
    .join("/");

export const fileUri = ({ store, entry, path }: FileOf) =>
  `reference-store://files/${segments(store, entry, path)}`;

export const thumbnailUri = (
  { store, entry, path }: FileOf,
  size: ThumbnailSize,
) => `reference-store://thumbnails/${size}/${segments(store, entry, path)}`;

/** The image that stands for an entry: its preview, or the first of its images when it has none. */
export const coverUri = (store: string, entry: string, size: ThumbnailSize) =>
  `reference-store://covers/${size}/${segments(store, entry)}`;

/** What changes when a file does, so a copy of it the view kept is read again. Times are to the second. */
export const fileVersion = (file: Pick<EntryFile, "modified" | "size">) =>
  `${file.modified} ${file.size}`;

/**
 * What changes when the image that stands for an entry may have. A preview copied in keeps its path, so the entry says
 * so: the library moves `updated` whenever it changes the entry or its files, and a file changed by hand changes its
 * size.
 */
export const coverVersion = (entry: Pick<EntrySummary, "updated" | "size">) =>
  `${entry.updated} ${entry.size}`;

/** A resource's bytes and type, as the server sends them. */
export async function readResource(
  uri: string,
): Promise<{ base64: string; mimeType: string }> {
  const result = await app.readServerResource({ uri });
  const content = result.contents[0];
  if (!content || !("blob" in content)) {
    throw new ToolError(TEXT.errors.noFile(uri));
  }
  return {
    base64: content.blob,
    mimeType: content.mimeType ?? "application/octet-stream",
  };
}

/** A text file of an entry, read as UTF-8. */
export async function readText(file: FileOf): Promise<string> {
  const { base64 } = await readResource(fileUri(file));
  const binary = atob(base64);
  const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

function escapeRegex(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Text a glob pattern matches as it is written, with its wildcards each in brackets. */
export function escapeGlob(text: string): string {
  return text.replace(/[*?[]/g, "[$&]");
}

/** Where the page is, and on this machine with the app on the local network, how other devices on it open it. */
export type AppNetwork = {
  this_machine: boolean;
  lan_url: string | null;
  /** `lan_url` as a QR code, a data URL of an SVG. */
  qr_code: string | null;
};

export const readAppNetwork = () => call<AppNetwork>("read_app_network");

/** The Windows app by the clock, when it is what runs the server, which keeps the settings a server can't. */
export type WindowsApp = {
  version: string;
  /** The newer version there is to update to. */
  update: string | null;
  updating: boolean;
  /** Whether the server is started on the local network. */
  lan: boolean;
  start_at_sign_in: boolean;
  /** Its Agent Skill, when it is installed. */
  skill: {
    /** The agents it is for, as the skills CLI names them. */
    agents: string[];
    mode: SkillMode;
  } | null;
};

/** An agent the skills CLI knows, which the Agent Skill can be installed for. */
export type SkillAgent = {
  id: string;
  name: string;
  /** Where it reads its skills from. */
  folder: string;
  /** Whether it reads the shared folder, which always has the skill. */
  shares: boolean;
  /** Whether it is on this computer. */
  detected: boolean;
};

export type SkillAgents = {
  /** The user's folder, which the agents' folders are in. */
  home: string;
  shared: string;
  agents: SkillAgent[];
  /** The ids of the agents on this computer that have the skill. */
  installed: string[];
};

/** How an agent with a folder of its own gets the skill: a link to the shared copy, or a copy of its own. */
export type SkillMode = "symlink" | "copy";

/** Null when the server was started any other way. Only a page on the machine itself may ask. */
export async function readWindowsApp(): Promise<WindowsApp | null> {
  return (await call<{ windows_app: WindowsApp | null }>("read_windows_app"))
    .windows_app;
}

/** Changing `lan` starts the server again a moment after this answers. */
export const changeWindowsApp = (changes: {
  lan?: boolean;
  start_at_sign_in?: boolean;
}) => call<WindowsApp>("change_windows_app", changes);

export const checkForUpdate = () => call<WindowsApp>("check_for_update");

/** Ends the server once the newer version is downloaded, and starts the new one on the same port. */
export const installUpdate = () => call<WindowsApp>("install_update");

/** The first time, the Windows app gets the skills CLI first, which can take a minute. */
export const listSkillAgents = () => call<SkillAgents>("list_skill_agents");

/** Installs the skill in the shared folder and for these agents, and takes it from the others. */
export const installSkill = (agents: string[], mode: SkillMode) =>
  call<WindowsApp>("install_skill", { agents, mode });

export const removeSkill = () => call<WindowsApp>("remove_skill");
