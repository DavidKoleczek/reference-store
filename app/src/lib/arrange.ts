import type { Entry, EntryFile, EntrySort, FileSort } from "@/lib/api";
import { fileFolder, fileName, fileType, names } from "@/lib/format";
import { tagKey } from "@/lib/filters";
import { TEXT } from "@/lib/text";

/** How entries or files are laid out: as pictures, or as a list with a column for each fact. */
export type Layout = "icons" | "details";

export type EntryGroup = "none" | "tag" | "store" | "site";

/** How the files of the entry that is open are sorted, all of them being at hand. */
export type InEntrySort = "name" | "modified" | "type" | "size" | "tags";

export type InEntryGroup = "none" | "folder" | "type" | "tag";

export type EntryArrangement = {
  layout: Layout;
  sort: EntrySort;
  descending: boolean;
  group: EntryGroup;
};

/** The Files view across every entry, which the library sorts. */
export type FileArrangement = {
  layout: Layout;
  sort: FileSort;
  descending: boolean;
};

export type InEntryArrangement = {
  layout: Layout;
  sort: InEntrySort;
  descending: boolean;
  group: InEntryGroup;
};

export type Choice<Value extends string> = { value: Value; label: string };

/** Each choice as the Sort menu names it. */
function choices<Value extends string>(
  values: Value[],
  labels: Record<Value, string>,
): Choice<Value>[] {
  return values.map((value) => ({ value, label: labels[value] }));
}

export const ENTRY_SORTS = choices<EntrySort>(
  ["name", "created", "published", "files", "size", "tags", "rating", "store"],
  TEXT.sort.by,
);

export const ENTRY_GROUPS = choices<EntryGroup>(
  ["none", "tag", "store", "site"],
  TEXT.sort.groups,
);

export const FILE_SORTS = choices<FileSort>(
  ["path", "name", "modified", "type", "size"],
  TEXT.sort.by,
);

export const IN_ENTRY_SORTS = choices<InEntrySort>(
  ["name", "modified", "type", "size", "tags"],
  TEXT.sort.by,
);

export const IN_ENTRY_GROUPS = choices<InEntryGroup>(
  ["none", "folder", "type", "tag"],
  TEXT.sort.groups,
);

/** What a sort starts as when it is picked: the newest, largest, and best rated first, and names from A. */
export function startsDescending(sort: string): boolean {
  return [
    "created",
    "updated",
    "published",
    "modified",
    "size",
    "files",
    "rating",
  ].includes(sort);
}

/** The arrangement after a column's header is clicked: sorted by it, or the other way round when it already is. */
export function resorted<
  Arrangement extends { sort: string; descending: boolean },
>(arrangement: Arrangement, sort: Arrangement["sort"]): Arrangement {
  return {
    ...arrangement,
    sort,
    descending:
      arrangement.sort === sort
        ? !arrangement.descending
        : startsDescending(sort),
  };
}

export type Group<Item> = { key: string; title: string; items: Item[] };

const FILE_ORDERS: Record<InEntrySort, (a: EntryFile, b: EntryFile) => number> =
  {
    name: (a, b) => names.compare(fileName(a), fileName(b)),
    modified: (a, b) => a.modified.localeCompare(b.modified),
    type: (a, b) => names.compare(fileType(a), fileType(b)),
    size: (a, b) => a.size - b.size,
    tags: (a, b) => names.compare(a.tags.join(", "), b.tags.join(", ")),
  };

function sortFiles(
  files: EntryFile[],
  sort: InEntrySort,
  descending: boolean,
): EntryFile[] {
  return [...files].sort(
    (a, b) =>
      (descending ? -1 : 1) * FILE_ORDERS[sort](a, b) ||
      names.compare(a.path, b.path),
  );
}

/** Items under each name `namesOf` gives them, in the order of those names. One with two names is in both groups. */
function grouped<Item>(
  items: Item[],
  namesOf: (item: Item) => string[],
  none: string,
  largestFirst = false,
): Group<Item>[] {
  const groups = new Map<string, Group<Item>>();
  const without: Item[] = [];
  for (const item of items) {
    const titles = namesOf(item);
    if (titles.length === 0) {
      without.push(item);
    }
    for (const title of titles) {
      const group = groups.get(tagKey(title));
      if (group) {
        group.items.push(item);
      } else {
        groups.set(tagKey(title), { key: tagKey(title), title, items: [item] });
      }
    }
  }
  const sorted = [...groups.values()].sort(
    (a, b) =>
      (largestFirst ? b.items.length - a.items.length : 0) ||
      names.compare(a.title, b.title),
  );
  return without.length > 0
    ? [...sorted, { key: "", title: none, items: without }]
    : sorted;
}

const TOP = TEXT.list.topOfEntry;

/** The files of the entry that is open, under what `group` names, each group in the order `sort` gives. */
export function groupInEntry(
  files: EntryFile[],
  { sort, descending, group }: InEntryArrangement,
): Group<EntryFile>[] {
  const sorted = sortFiles(files, sort, descending);
  switch (group) {
    case "folder":
      return grouped(sorted, (file) => [fileFolder(file) || TOP], "").sort(
        (a, b) => Number(b.title === TOP) - Number(a.title === TOP),
      );
    case "type":
      return grouped(sorted, (file) => [fileType(file)], "");
    case "tag":
      return grouped(sorted, (file) => file.tags, TEXT.list.noTags, true);
    default:
      return [{ key: "all", title: "", items: sorted }];
  }
}

/** The tags an entry's files have, each with how many of them have it, most first. */
export function fileTagsOf(entry: Entry): { tag: string; count: number }[] {
  const counts = new Map<string, { tag: string; count: number }>();
  for (const file of entry.files) {
    for (const tag of file.tags) {
      const kept = counts.get(tagKey(tag));
      if (kept) {
        kept.count += 1;
      } else {
        counts.set(tagKey(tag), { tag, count: 1 });
      }
    }
  }
  return [...counts.values()].sort(
    (a, b) => b.count - a.count || names.compare(a.tag, b.tag),
  );
}
