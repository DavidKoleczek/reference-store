import { useSyncExternalStore } from "react";

import { readAppSettings, saveAppSettings } from "@/lib/api";
import {
  ENTRY_GROUPS,
  ENTRY_SORTS,
  FILE_SORTS,
  IN_ENTRY_GROUPS,
  IN_ENTRY_SORTS,
  type Choice,
  type EntryArrangement,
  type FileArrangement,
  type InEntryArrangement,
} from "@/lib/arrange";
import { setThemePreference, type ThemePreference } from "@/lib/theme";

export type PaneSettings = { open: boolean; size: number };

/** Where the app was: the entry that was open, kept so a reload stays in it. */
export type Place = { store: string; name: string } | null;

/** What the app remembers from one run to the next, on the server, since the view's address changes. */
export type Settings = {
  theme: ThemePreference;
  filtersPane: PaneSettings;
  detailsPane: PaneSettings;
  /** The preview sits beside the details rather than above them. */
  beside: boolean;
  view: "entries" | "files";
  entries: EntryArrangement;
  files: FileArrangement;
  inEntry: InEntryArrangement;
  /** The widths given to the columns of the lists, by list and column. */
  widths: Record<string, number>;
  /** Which sections of the filters pane are open. */
  sections: Record<"stores" | "sites" | "tags" | "fileTags", boolean>;
  place: Place;
};

export const DEFAULTS: Settings = {
  theme: "system",
  filtersPane: { open: true, size: 232 },
  detailsPane: { open: true, size: 360 },
  beside: false,
  view: "entries",
  entries: {
    layout: "icons",
    sort: "created",
    descending: true,
    group: "none",
  },
  files: { layout: "icons", sort: "path", descending: false },
  inEntry: {
    layout: "icons",
    sort: "name",
    descending: false,
    group: "folder",
  },
  widths: {},
  sections: { stores: true, sites: true, tags: true, fileTags: true },
  place: null,
};

// Long enough that dragging a pane saves once it stops, not on every step.
const SAVE_AFTER_MS = 500;

let settings: Settings = DEFAULTS;
const listeners = new Set<() => void>();
let timer: ReturnType<typeof setTimeout> | null = null;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** What was kept, where it has the shape of what the defaults hold, and the default where it hasn't. */
function kept<Value>(value: unknown, fallback: Value): Value {
  if (isRecord(fallback)) {
    if (!isRecord(value)) {
      return fallback;
    }
    // A record the defaults leave empty, such as the widths, keeps whatever numbers it holds.
    if (Object.keys(fallback).length === 0) {
      return Object.fromEntries(
        Object.entries(value).filter(([, each]) => typeof each === "number"),
      ) as Value;
    }
    return Object.fromEntries(
      Object.entries(fallback).map(([key, each]) => [
        key,
        kept(value[key], each),
      ]),
    ) as Value;
  }
  if (fallback === null) {
    return (
      isRecord(value) &&
      typeof value.store === "string" &&
      typeof value.name === "string"
        ? { store: value.store, name: value.name }
        : null
    ) as Value;
  }
  return typeof value === typeof fallback ? (value as Value) : fallback;
}

function oneOf<Value extends string>(
  value: Value,
  choices: Choice<Value>[],
  fallback: Value,
): Value {
  return choices.some((choice) => choice.value === value) ? value : fallback;
}

function checked(value: unknown): Settings {
  const read = kept(value, DEFAULTS);
  return {
    ...read,
    theme: ["system", "light", "dark"].includes(read.theme)
      ? read.theme
      : DEFAULTS.theme,
    view: read.view === "files" ? "files" : "entries",
    entries: {
      ...read.entries,
      layout: read.entries.layout === "details" ? "details" : "icons",
      sort: oneOf(read.entries.sort, ENTRY_SORTS, DEFAULTS.entries.sort),
      group: oneOf(read.entries.group, ENTRY_GROUPS, DEFAULTS.entries.group),
    },
    files: {
      ...read.files,
      layout: read.files.layout === "details" ? "details" : "icons",
      sort: oneOf(read.files.sort, FILE_SORTS, DEFAULTS.files.sort),
    },
    inEntry: {
      ...read.inEntry,
      layout: read.inEntry.layout === "details" ? "details" : "icons",
      sort: oneOf(read.inEntry.sort, IN_ENTRY_SORTS, DEFAULTS.inEntry.sort),
      group: oneOf(read.inEntry.group, IN_ENTRY_GROUPS, DEFAULTS.inEntry.group),
    },
  };
}

/** Reads what the app remembers, before it is first drawn. What can't be read leaves the defaults. */
export async function loadSettings() {
  try {
    settings = checked(await readAppSettings());
  } catch {
    settings = DEFAULTS;
  }
  setThemePreference(settings.theme);
}

/** Changes what the app remembers, and saves it once changes stop for a moment. */
export function changeSettings(
  change: Partial<Settings> | ((now: Settings) => Partial<Settings>),
) {
  const next = {
    ...settings,
    ...(typeof change === "function" ? change(settings) : change),
  };
  if (next.theme !== settings.theme) {
    setThemePreference(next.theme);
  }
  settings = next;
  for (const listener of listeners) {
    listener();
  }
  if (timer !== null) {
    clearTimeout(timer);
  }
  timer = setTimeout(() => {
    timer = null;
    // Lost when the server is gone, which only costs a layout.
    saveAppSettings(settings).catch(() => {});
  }, SAVE_AFTER_MS);
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** What the app remembers, rerendering when it changes. */
export function useSettings(): Settings {
  return useSyncExternalStore(subscribe, () => settings);
}
