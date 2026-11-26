import type { EntryFilters, SiteCount, Store, TagCount } from "@/lib/api";
import type { EntryGroup } from "@/lib/arrange";
import { hasTag, siteKey, tagKey, type Filters } from "@/lib/filters";
import { TEXT } from "@/lib/text";

/** A group of entries: its header, and what narrows the entries to those in it, beyond the filters. */
export type GroupSpec = {
  key: string;
  title: string;
  /** How many there are by the counts in the filters pane, which count everything. */
  count: number | null;
  filters: EntryFilters;
};

/**
 * The groups of entries `group` makes, each a listing of its own: the tags, stores, or sites with their counts for
 * headers, and one for the entries with none. Null for no groups.
 */
export function groupSpecs(
  group: EntryGroup,
  filters: Filters,
  stores: Store[],
  tags: TagCount[],
  sites: SiteCount[],
): GroupSpec[] | null {
  switch (group) {
    case "tag": {
      // With `any`, an entry is in the groups of the tags picked; with `all`, it has every tag picked and the group's.
      const any = filters.tagMatch === "any" && filters.tags.length > 0;
      const shown = tags.filter(
        (each) =>
          each.entries > 0 &&
          (!any || hasTag(filters.tags, each.tag)) &&
          (any || !hasTag(filters.tags, each.tag)),
      );
      const specs: GroupSpec[] = shown.map((each) => ({
        key: `tag:${tagKey(each.tag)}`,
        title: each.tag,
        count: each.entries,
        filters: {
          tags: any ? [each.tag] : [...filters.tags, each.tag],
          tag_match: "all",
        },
      }));
      if (filters.tags.length === 0) {
        specs.push({
          key: "tag:",
          title: TEXT.list.noTags,
          count: null,
          filters: { without_tags: true },
        });
      }
      return specs;
    }
    case "store":
      return stores
        .filter(
          (store) =>
            store.available &&
            (filters.store === null || filters.store === store.name),
        )
        .map((store) => ({
          key: `store:${store.name}`,
          title: store.name,
          count: null,
          filters: { store: store.name },
        }));
    case "site": {
      const picked = filters.sites;
      const specs: GroupSpec[] =
        picked.length > 0
          ? picked.map((site) => ({
              key: `site:${site}`,
              title: site,
              count: null,
              filters: { sites: [site] },
            }))
          : sites.map((each) => ({
              key: `site:${siteKey(each.site)}`,
              title: each.site,
              count: each.entries,
              filters: { sites: [each.site] },
            }));
      if (picked.length === 0) {
        specs.push({
          key: "site:",
          title: TEXT.list.noLink,
          count: null,
          filters: { without_site: true },
        });
      }
      return specs;
    }
    default:
      return null;
  }
}
