import type { EntryFilters, TagMatch } from "@/lib/api";

/** What narrows the entries and files shown. */
export type Filters = {
  /** One store by name, or every store. */
  store: string | null;
  /** Entries have every one of these, or one of them when `tagMatch` is `any`. */
  tags: string[];
  /** Files have every one of these, or one of them when `tagMatch` is `any`. */
  fileTags: string[];
  tagMatch: TagMatch;
  /** Entries link to one of these: a site such as `github.com`, or a group on it, such as `github.com/octocat`. */
  sites: string[];
  /** Found by `grep_entries`, or in the Files view, in the files' names. */
  query: string;
};

export const NO_FILTERS: Filters = {
  store: null,
  tags: [],
  fileTags: [],
  tagMatch: "all",
  sites: [],
  query: "",
};

/** The filters as the library takes them. */
export function libraryFilters(filters: Filters): EntryFilters {
  return {
    store: filters.store ?? undefined,
    tags: filters.tags.length > 0 ? filters.tags : undefined,
    file_tags: filters.fileTags.length > 0 ? filters.fileTags : undefined,
    tag_match: filters.tagMatch,
    sites: filters.sites.length > 0 ? filters.sites : undefined,
  };
}

/** Whether anything narrows the entries. */
export function isFiltered(filters: Filters): boolean {
  return (
    filters.store !== null ||
    filters.tags.length > 0 ||
    filters.fileTags.length > 0 ||
    filters.sites.length > 0 ||
    filters.query.trim() !== ""
  );
}

/** What tells a tag from another: tags that differ only by case are the same tag. */
export function tagKey(tag: string): string {
  return tag.toLowerCase();
}

export function hasTag(tags: string[], tag: string): boolean {
  return tags.some((each) => tagKey(each) === tagKey(tag));
}

export function toggleTag(tags: string[], tag: string): string[] {
  return hasTag(tags, tag)
    ? tags.filter((each) => tagKey(each) !== tagKey(tag))
    : [...tags, tag];
}

/**
 * The tags picked after a click on `tag`. A plain click picks it alone, or nothing when it was the only one picked.
 * With `several`, as Ctrl does, it joins or leaves the ones picked.
 */
export function pickTag(
  tags: string[],
  tag: string,
  several: boolean,
): string[] {
  if (several) {
    return toggleTag(tags, tag);
  }
  return tags.length === 1 && hasTag(tags, tag) ? [] : [tag];
}

/** The keys held with a click, as a file manager reads them: Ctrl picks one more, and Shift picks a range. */
export type Click = { more: boolean; range: boolean };

/**
 * What is picked in a list after a click on `item`. A plain click picks it alone. With Ctrl it joins or leaves the
 * ones picked. With Shift everything from `anchor`, the last item clicked without Shift, through `item` is picked.
 */
export function pickFrom(
  picked: string[],
  /** The list in the order it shows. */
  listed: string[],
  item: string,
  anchor: string | null,
  click: Click,
): string[] {
  if (click.range && anchor !== null) {
    const from = listed.findIndex((each) => tagKey(each) === tagKey(anchor));
    const to = listed.findIndex((each) => tagKey(each) === tagKey(item));
    if (from >= 0 && to >= 0) {
      const range = listed.slice(Math.min(from, to), Math.max(from, to) + 1);
      // With Ctrl too, the range adds to what is picked.
      return click.more
        ? [...picked, ...range.filter((each) => !hasTag(picked, each))]
        : range;
    }
  }
  return pickTag(picked, item, click.more);
}

/** How a filter names a site, or one group on it. */
export function siteKey(site: string, group: string | null = null): string {
  return (group === null ? site : `${site}/${group}`).toLowerCase();
}
