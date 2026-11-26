import { useEffect, useState } from "react";

import {
  getEntry,
  imageSizes,
  listEntries,
  listSites,
  listStores,
  listTags,
  type Entry,
  type SiteCount,
  type Store,
  type TagCount,
} from "@/lib/api";
import { describe } from "@/lib/errors";
import { isImage } from "@/lib/format";

/** What the filters pane counts: the stores and their entries, and the sites and tags of the store picked. */
export type Counts = {
  stores: Store[];
  /** Entries by store name, and in all under the empty name. */
  totals: Record<string, number>;
  tags: TagCount[];
  sites: SiteCount[];
  error: string | null;
};

const NO_COUNTS: Counts = {
  stores: [],
  totals: {},
  tags: [],
  sites: [],
  error: null,
};

/** Reads the stores, tags, and sites, again whenever `revision` changes. */
export function useCounts(store: string | null, revision: number): Counts {
  const [counts, setCounts] = useState<Counts>(NO_COUNTS);
  useEffect(() => {
    let current = true;
    const total = (name?: string) =>
      listEntries({ store: name }, "name", false, 1, null).then(
        (page) => page.total,
        () => null,
      );
    (async () => {
      const stores = await listStores();
      const [tags, sites, all, each] = await Promise.all([
        listTags(store ?? undefined),
        listSites(store ?? undefined),
        total(),
        Promise.all(
          stores.map((one) =>
            one.available ? total(one.name) : Promise.resolve(null),
          ),
        ),
      ]);
      const totals: Record<string, number> = {};
      if (all !== null) {
        totals[""] = all;
      }
      stores.forEach((one, index) => {
        const count = each[index];
        if (count !== null) {
          totals[one.name] = count;
        }
      });
      return { stores, totals, tags, sites, error: null };
    })().then(
      (read) => current && setCounts(read),
      (cause: unknown) =>
        current && setCounts((was) => ({ ...was, error: describe(cause) })),
    );
    return () => {
      current = false;
    };
  }, [store, revision]);
  return counts;
}

/** An entry with its files, and the width and height of each of its images by path. */
export type Read = {
  entry: Entry;
  sizes: Record<string, [number, number]>;
};

/** Reads an entry, and the sizes of its images so a wall of them is laid out before they arrive. */
export async function readEntry(name: string, store: string): Promise<Read> {
  const entry = await getEntry(name, store);
  const images = entry.files.filter(isImage);
  const found = images.length
    ? await imageSizes(
        images.map((file) => ({ store, entry: entry.name, path: file.path })),
      )
    : [];
  const sizes: Record<string, [number, number]> = {};
  images.forEach((file, index) => {
    const size = found[index];
    if (size) {
      sizes[file.path] = size;
    }
  });
  return { entry, sizes };
}

/** An entry read with its files, again whenever `revision` changes; null while it is read, or with no entry. */
export function useEntry(
  ref: { store: string; name: string } | null,
  revision: number,
): { read: Read | null; error: string | null; set: (read: Read) => void } {
  const store = ref?.store ?? null;
  const name = ref?.name ?? null;
  const [state, setState] = useState<{
    key: string;
    read: Read | null;
    error: string | null;
  } | null>(null);
  const key = `${store}/${name}`;
  useEffect(() => {
    if (store === null || name === null) {
      return;
    }
    let current = true;
    readEntry(name, store).then(
      (read) => current && setState({ key, read, error: null }),
      (cause: unknown) =>
        current && setState({ key, read: null, error: describe(cause) }),
    );
    return () => {
      current = false;
    };
  }, [store, name, key, revision]);
  const mine = state?.key === key ? state : null;
  return {
    read: store === null ? null : (mine?.read ?? null),
    error: mine?.error ?? null,
    set: (read) =>
      setState({
        key: `${read.entry.store}/${read.entry.name}`,
        read,
        error: null,
      }),
  };
}
