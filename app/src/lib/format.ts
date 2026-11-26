import type { EntryFile, EntrySummary } from "@/lib/api";

/** Compares names as a file manager orders them: whatever their case, and with `2` before `10`. */
export const names = new Intl.Collator(undefined, {
  numeric: true,
  sensitivity: "base",
});

/** What an entry shows as its name: its title when it has one. */
export function shownName(entry: EntrySummary): string {
  return entry.title ?? entry.name;
}

const TEXT_SUFFIXES = [
  ".md",
  ".txt",
  ".json",
  ".csv",
  ".log",
  ".yaml",
  ".yml",
  ".toml",
];
// What the server makes thumbnails of.
const IMAGE_SUFFIXES = [
  ".png",
  ".jpg",
  ".jpeg",
  ".webp",
  ".gif",
  ".bmp",
  ".tif",
  ".tiff",
  ".avif",
  ".svg",
];

function hasSuffix(path: string, suffixes: string[]): boolean {
  const lower = path.toLowerCase();
  return suffixes.some((suffix) => lower.endsWith(suffix));
}

/** Whether a file can be shown as text. */
export function isText(file: Pick<EntryFile, "path">): boolean {
  return hasSuffix(file.path, TEXT_SUFFIXES);
}

/** Whether the server makes a thumbnail of a file. */
export function isImage(file: Pick<EntryFile, "path">): boolean {
  return hasSuffix(file.path, IMAGE_SUFFIXES);
}

export function fileName(file: Pick<EntryFile, "path">): string {
  return file.path.slice(file.path.lastIndexOf("/") + 1);
}

/** The folder a file is in within its entry, with nothing for the top. */
export function fileFolder(file: Pick<EntryFile, "path">): string {
  return file.path.slice(0, Math.max(0, file.path.lastIndexOf("/")));
}

/** The kind of file, as a file manager names it from its extension: `JPG File`. */
export function fileType(file: Pick<EntryFile, "path">): string {
  const name = fileName(file);
  const dot = name.lastIndexOf(".");
  return dot > 0 ? `${name.slice(dot + 1).toUpperCase()} File` : "File";
}

const UNITS = ["B", "KB", "MB", "GB", "TB"];

/** A file size with its unit, such as `1.4 MB`. */
export function formatSize(bytes: number): string {
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < UNITS.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${unit === 0 || value >= 100 ? Math.round(value) : value.toFixed(1)} ${UNITS[unit]}`;
}

const thousands = new Intl.NumberFormat();

/** A size in whole kilobytes, as a file manager's list shows it, such as `1,002 KB`. */
export function formatKilobytes(bytes: number): string {
  return `${thousands.format(Math.ceil(bytes / 1024))} KB`;
}

/** A number with its thousands marked, such as `10,000`. */
export function formatCount(count: number): string {
  return thousands.format(count);
}

/** A width and height in pixels, with the multiplication sign between them. */
export function dimensions([width, height]: [number, number]): string {
  return `${width} × ${height}`;
}

const days = new Intl.DateTimeFormat(undefined, { dateStyle: "medium" });

export function formatDay(time: string): string {
  const date = new Date(time);
  return Number.isNaN(date.getTime()) ? time : days.format(date);
}

const times = new Intl.DateTimeFormat(undefined, {
  year: "numeric",
  month: "numeric",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

/** A day and time as a file manager's list shows it, such as `7/15/2018 4:19 PM`. */
export function formatTime(time: string): string {
  const date = new Date(time);
  return Number.isNaN(date.getTime())
    ? time
    : times.format(date).replace(",", "");
}

const ago = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
const STEPS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["second", 60],
  ["minute", 60],
  ["hour", 24],
  ["day", 30],
  ["month", 12],
  ["year", Infinity],
];

/** How long ago a time was, such as `5 minutes ago`. */
export function formatAgo(time: string): string {
  let value = (new Date(time).getTime() - Date.now()) / 1000;
  for (const [unit, size] of STEPS) {
    if (Math.abs(value) < size) {
      return ago.format(Math.round(value), unit);
    }
    value /= size;
  }
  return formatDay(time);
}

/** A count with its noun, such as `1 file` or `3 entries`. */
export function plural(count: number, one: string, many = `${one}s`): string {
  return `${formatCount(count)} ${count === 1 ? one : many}`;
}

/** How many of something show, out of how many there are when some are left out. */
export function shownOf(shown: number, all: number): string {
  return shown < all
    ? `${formatCount(shown)} of ${formatCount(all)}`
    : formatCount(all);
}

/** `text` cut to `length` characters, with dots where the rest was. */
export function clipped(text: string, length: number): string {
  return text.length > length ? `${text.slice(0, length - 3)}...` : text;
}

/** The site a link is on, without `www.`; the link itself when it is not a URL. */
export function siteOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

const PASTELS = [
  "bg-pastel-blue",
  "bg-pastel-lilac",
  "bg-pastel-rose",
  "bg-pastel-peach",
  "bg-pastel-butter",
  "bg-pastel-mint",
  "bg-pastel-sage",
  "bg-pastel-stone",
];

/** The pastel a name is labeled with: the same one every time, whatever its case. */
export function pastelOf(name: string): string {
  let hash = 0;
  for (const character of name.toLowerCase()) {
    hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
  }
  return PASTELS[hash % PASTELS.length];
}
