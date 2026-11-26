import {
  useCallback,
  useEffect,
  useEffectEvent,
  useLayoutEffect,
  useRef,
  useState,
} from "react";

import { describe } from "@/lib/errors";

/** A page of what the library listed, and where the next one starts. */
export type Page<Item> = { items: Item[]; total: number; after: string | null };

export type Fetch<Item> = (
  after: string | null,
  limit: number,
) => Promise<Page<Item>>;

export type Paged<Item> = {
  items: Item[];
  /** How many there are in all; null before the first page is in. */
  total: number | null;
  after: string | null;
  loading: boolean;
  error: string | null;
};

const EMPTY: Paged<never> = {
  items: [],
  total: null,
  after: null,
  loading: false,
  error: null,
};

export const PAGE = 100;
// A refresh reads again as many as were shown, so nothing jumps, up to this many.
const MOST_ON_REFRESH = 2000;

/**
 * Lists that are read a page at a time: one for each group that is open, or one with no groups. Changing `query`,
 * which says what the lists are, starts them over. `fetchers` has what reads each list, by its key.
 */
export function usePaged<Item>(
  query: string,
  fetchers: Record<string, Fetch<Item>>,
) {
  const [lists, setLists] = useState<{
    query: string;
    paged: Record<string, Paged<Item>>;
  }>({ query, paged: {} });
  // What the reads see, kept up to date before any effect asks for a page.
  const current = useRef({ query, fetchers, lists });
  useLayoutEffect(() => {
    current.current = { query, fetchers, lists };
  });
  const paged = lists.query === query ? lists.paged : {};

  const read = useCallback((key: string, from: "start" | "next" | "again") => {
    const { query: asked, fetchers: known, lists: now } = current.current;
    const fetch = known[key];
    const before: Paged<Item> =
      (now.query === asked ? now.paged[key] : undefined) ?? EMPTY;
    if (!fetch || before.loading) {
      return;
    }
    // A page that failed is read again by a refresh, not each time its row shows.
    if (from === "next" && (before.after === null || before.error !== null)) {
      return;
    }
    const limit =
      from === "again"
        ? Math.min(MOST_ON_REFRESH, Math.max(PAGE, before.items.length))
        : PAGE;
    const set = (change: (state: Paged<Item>) => Paged<Item>) =>
      setLists((was) => {
        if (current.current.query !== asked) {
          return was;
        }
        const base = was.query === asked ? was.paged : {};
        return {
          query: asked,
          paged: { ...base, [key]: change(base[key] ?? EMPTY) },
        };
      });
    set((state) => ({ ...state, loading: true, error: null }));
    fetch(from === "next" ? before.after : null, limit).then(
      (page) =>
        set((state) => ({
          items: from === "next" ? [...state.items, ...page.items] : page.items,
          total: page.total,
          after: page.after,
          loading: false,
          error: null,
        })),
      (cause: unknown) =>
        set((state) => ({ ...state, loading: false, error: describe(cause) })),
    );
  }, []);

  /** Reads a list's first page, unless it was read. */
  const open = useCallback(
    (key: string) => {
      const { query: asked, lists: now } = current.current;
      const state = now.query === asked ? now.paged[key] : undefined;
      if (!state || (state.total === null && !state.loading && !state.error)) {
        read(key, "start");
      }
    },
    [read],
  );

  /** Reads a list's next page, unless it is being read or there is none. */
  const more = useCallback((key: string) => read(key, "next"), [read]);

  /** Reads every list that was read again, as much of it as was shown. */
  const refresh = useCallback(() => {
    const { query: asked, lists: now } = current.current;
    if (now.query !== asked) {
      return;
    }
    for (const key of Object.keys(now.paged)) {
      read(key, "again");
    }
  }, [read]);

  /**
   * Changes items where they are, without reading the lists again, so a changed item stays in its place until the
   * next refresh. `change` returns the item as it is now, or null for one that is gone.
   */
  const patch = useCallback((change: (item: Item) => Item | null) => {
    setLists((was) => ({
      query: was.query,
      paged: Object.fromEntries(
        Object.entries(was.paged).map(([key, state]) => {
          const items = state.items.flatMap((item) => {
            const now = change(item);
            return now === null ? [] : [now];
          });
          const gone = state.items.length - items.length;
          return [
            key,
            {
              ...state,
              items,
              total: state.total === null ? null : state.total - gone,
            },
          ];
        }),
      ),
    }));
  }, []);

  return {
    lists: paged,
    list: (key: string): Paged<Item> => paged[key] ?? EMPTY,
    open,
    more,
    refresh,
    patch,
  };
}

/** Calls `refresh` when the window gets the focus back, which is when agents may have changed the stores. */
export function useRefreshOnFocus(refresh: () => void) {
  const onRefresh = useEffectEvent(refresh);
  useEffect(() => {
    const onFocus = () => onRefresh();
    const onVisible = () => {
      if (document.visibilityState === "visible") {
        onRefresh();
      }
    };
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, []);
}
