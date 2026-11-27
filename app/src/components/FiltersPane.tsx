import { Fragment, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icon";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuTrigger,
} from "@/components/ui/menu";
import { Section } from "@/components/ui/section";
import { Segmented } from "@/components/ui/segmented";
import { TagSwatch } from "@/components/ui/tag";
import { Tooltip } from "@/components/ui/tooltip";
import type { SiteCount, Store, TagCount, TagMatch } from "@/lib/api";
import {
  hasTag,
  pickFrom,
  siteKey,
  type Click,
  type Filters,
} from "@/lib/filters";
import { formatCount } from "@/lib/format";
import { storeState } from "@/lib/stores";
import { TEXT } from "@/lib/text";
import { cn } from "@/lib/utils";

function Row({
  selected,
  onClick,
  lead,
  count,
  indent = false,
  muted = false,
  title,
  children,
}: {
  selected: boolean;
  /** Told which keys were held, which pick more than one. */
  onClick: (click: Click) => void;
  lead: ReactNode;
  count: number | null;
  /** It is under the row above it. */
  indent?: boolean;
  muted?: boolean;
  title?: string;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      title={title}
      onClick={(event) =>
        onClick({
          more: event.ctrlKey || event.metaKey,
          range: event.shiftKey,
        })
      }
      className={cn(
        "flex h-7 w-full cursor-default items-center gap-2 rounded-sm px-2 text-left outline-none select-none focus-visible:focus-ring",
        selected ? "bg-accent-soft" : "hover:bg-hover",
        indent && "pl-6",
        muted && "text-ink-muted",
      )}
    >
      <span className="grid size-4 shrink-0 place-items-center">{lead}</span>
      <span className="flex min-w-0 flex-1 items-baseline gap-1.5">
        {children}
      </span>
      {count !== null && (
        <span className="mono-annotation text-ink-muted">
          {formatCount(count)}
        </span>
      )}
    </button>
  );
}

/**
 * What a click on an item of a list picks, given the list in the order it shows: the item alone, one more with Ctrl,
 * or with Shift the range from the item clicked before.
 */
function usePicker(
  listed: string[],
  picked: string[],
  onPick: (picked: string[]) => void,
): (item: string, click: Click) => void {
  const [anchor, setAnchor] = useState<string | null>(null);
  return (item, click) => {
    onPick(pickFrom(picked, listed, item, anchor, click));
    if (!click.range) {
      setAnchor(item);
    }
  };
}

function TagRows({
  counts,
  picked,
  onPick,
}: {
  counts: { tag: string; count: number }[];
  picked: string[];
  onPick: (tags: string[]) => void;
}) {
  const pick = usePicker(
    counts.map(({ tag }) => tag),
    picked,
    onPick,
  );
  if (counts.length === 0) {
    return <p className="px-1 text-ink-muted">{TEXT.filters.noneYet}</p>;
  }
  return counts.map(({ tag, count }) => {
    const selected = hasTag(picked, tag);
    return (
      <Row
        key={tag}
        selected={selected}
        onClick={(click) => pick(tag, click)}
        lead={
          selected ? (
            <Icon name="check" className="text-accent-ink" />
          ) : (
            <TagSwatch tag={tag} />
          )
        }
        count={count}
      >
        <span className="truncate">{tag}</span>
      </Row>
    );
  });
}

function Clear({ shown, onClick }: { shown: boolean; onClick: () => void }) {
  return (
    shown && (
      <Button size="sm" onClick={onClick} className="text-ink-muted">
        {TEXT.common.clear}
      </Button>
    )
  );
}

/** All or any of the tags picked, which the library's `tag_match` says. */
function MatchSwitch({
  value,
  onChange,
}: {
  value: TagMatch;
  onChange: (value: TagMatch) => void;
}) {
  return (
    <Segmented
      label={TEXT.filters.match}
      size="sm"
      value={value}
      onChange={onChange}
      options={[
        { value: "all", label: TEXT.filters.all },
        { value: "any", label: TEXT.filters.any },
      ]}
    />
  );
}

/** What narrows the view: one store or all of them, sites, tags on entries, and tags on files. */
export function FiltersPane({
  stores,
  totals,
  sites,
  tags,
  filters,
  onFilters,
  onStore,
  sections,
  onSections,
  closedSites,
  onClosedSites,
  onManageStores,
  storeMenu,
}: {
  stores: Store[];
  /** How many entries each store has, by name, and in all under the empty name. */
  totals: Record<string, number>;
  sites: SiteCount[];
  /** The tags of the store picked, or of every store. */
  tags: TagCount[];
  filters: Filters;
  onFilters: (filters: Filters) => void;
  /** Picks a store, or every store with null, even the one picked already, which is a way back to its list. */
  onStore: (store: string | null) => void;
  sections: Record<"stores" | "sites" | "tags" | "fileTags", boolean>;
  onSections: (
    sections: Record<"stores" | "sites" | "tags" | "fileTags", boolean>,
  ) => void;
  /** The sites whose groups are hidden, by name. */
  closedSites: string[];
  onClosedSites: (sites: string[]) => void;
  /** Opens the list of stores, to change their order or add one. */
  onManageStores: () => void;
  storeMenu: (store: Store) => ReactNode;
}) {
  // A group picked stays in sight while its site is closed, so no filter in use is hidden.
  const shownSites = sites.map(({ site, entries, groups }) => ({
    site,
    entries,
    hasGroups: groups.length > 0,
    open: !closedSites.includes(site),
    groups: closedSites.includes(site)
      ? groups.filter((each) =>
          filters.sites.includes(siteKey(site, each.group)),
        )
      : groups,
  }));
  const nested = shownSites.some((each) => each.hasGroups);
  const pickSite = usePicker(
    shownSites.flatMap(({ site, groups }) => [
      siteKey(site),
      ...groups.map((each) => siteKey(site, each.group)),
    ]),
    filters.sites,
    (picked) => onFilters({ ...filters, sites: picked }),
  );
  const entryTags = tags
    .filter((each) => each.entries > 0)
    .map(({ tag, entries }) => ({ tag, count: entries }));
  const fileTags = tags
    .filter((each) => each.files > 0)
    .sort((a, b) => b.files - a.files)
    .map(({ tag, files }) => ({ tag, count: files }));
  const match = (
    <MatchSwitch
      value={filters.tagMatch}
      onChange={(tagMatch) => onFilters({ ...filters, tagMatch })}
    />
  );
  return (
    <aside className="flex h-full min-w-0 flex-col bg-panel">
      <header className="flex h-10 shrink-0 items-center border-b border-line pr-2 pl-3">
        <h2 className="flex-1 truncate text-label">{TEXT.panes.filters}</h2>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <Section
          title={TEXT.filters.stores}
          open={sections.stores}
          onOpenChange={(stores) => onSections({ ...sections, stores })}
          aside={
            <Tooltip content={TEXT.filters.manageStores}>
              <Button
                size="sm"
                icon
                aria-label={TEXT.filters.manageStores}
                onClick={onManageStores}
                className="text-ink-muted"
              >
                <Icon name="more" />
              </Button>
            </Tooltip>
          }
        >
          <div className="-mx-1">
            <Row
              selected={filters.store === null}
              onClick={() => onStore(null)}
              lead={<Icon name="grid" className="text-ink-muted" />}
              count={totals[""] ?? null}
            >
              <span className="truncate">{TEXT.filters.allStores}</span>
            </Row>
            {stores.map((store) => {
              const { note, title } = storeState(store);
              return (
                <ContextMenu key={store.name}>
                  <ContextMenuTrigger>
                    <Row
                      selected={filters.store === store.name}
                      onClick={() => onStore(store.name)}
                      lead={
                        <Icon
                          name={store.available ? "folder" : "warning"}
                          className="text-ink-muted"
                        />
                      }
                      count={totals[store.name] ?? null}
                      muted={!store.available}
                      title={title}
                    >
                      <span className="truncate">{store.name}</span>
                      {note && (
                        <span
                          className={cn(
                            "shrink-0 mono-annotation",
                            store.sync_error ? "text-danger" : "text-ink-muted",
                          )}
                        >
                          {note}
                        </span>
                      )}
                    </Row>
                  </ContextMenuTrigger>
                  <ContextMenuContent>{storeMenu(store)}</ContextMenuContent>
                </ContextMenu>
              );
            })}
          </div>
        </Section>
        {sites.length > 0 && (
          <Section
            title={TEXT.filters.sites}
            open={sections.sites}
            onOpenChange={(open) => onSections({ ...sections, sites: open })}
            aside={
              <Clear
                shown={filters.sites.length > 0}
                onClick={() => onFilters({ ...filters, sites: [] })}
              />
            }
          >
            <div className="-mx-1">
              {shownSites.map(({ site, entries, hasGroups, open, groups }) => {
                const picked = filters.sites.includes(siteKey(site));
                return (
                  <Fragment key={site}>
                    <div className="flex">
                      {hasGroups ? (
                        <button
                          type="button"
                          aria-label={TEXT.filters.groupsOf(site)}
                          aria-expanded={open}
                          onClick={() =>
                            onClosedSites(
                              open
                                ? [...closedSites, site]
                                : closedSites.filter((each) => each !== site),
                            )
                          }
                          className="grid h-7 w-5 shrink-0 cursor-default place-items-center rounded-sm text-ink-muted outline-none hover:text-ink focus-visible:focus-ring"
                        >
                          <Icon
                            name="chevron"
                            className={cn(
                              "transition-transform",
                              !open && "-rotate-90",
                            )}
                          />
                        </button>
                      ) : (
                        nested && <span className="w-5 shrink-0" />
                      )}
                      <div className="min-w-0 flex-1">
                        <Row
                          selected={picked}
                          onClick={(click) => pickSite(siteKey(site), click)}
                          lead={
                            <Icon
                              name={picked ? "check" : "globe"}
                              className={
                                picked ? "text-accent-ink" : "text-ink-muted"
                              }
                            />
                          }
                          count={entries}
                        >
                          <span className="truncate">{site}</span>
                        </Row>
                      </div>
                    </div>
                    {groups.map((each) => {
                      const key = siteKey(site, each.group);
                      const one = filters.sites.includes(key);
                      return (
                        <div key={key} className="pl-5">
                          <Row
                            indent
                            selected={one}
                            onClick={(click) => pickSite(key, click)}
                            lead={
                              one && (
                                <Icon
                                  name="check"
                                  className="text-accent-ink"
                                />
                              )
                            }
                            count={each.entries}
                          >
                            <span className="truncate">{each.group}</span>
                          </Row>
                        </div>
                      );
                    })}
                  </Fragment>
                );
              })}
            </div>
          </Section>
        )}
        <Section
          title={TEXT.filters.tags}
          open={sections.tags}
          onOpenChange={(open) => onSections({ ...sections, tags: open })}
          aside={
            <>
              {filters.tags.length > 1 && match}
              <Clear
                shown={filters.tags.length > 0}
                onClick={() => onFilters({ ...filters, tags: [] })}
              />
            </>
          }
        >
          <div className="-mx-1">
            <TagRows
              counts={entryTags}
              picked={filters.tags}
              onPick={(picked) => onFilters({ ...filters, tags: picked })}
            />
          </div>
        </Section>
        <Section
          title={TEXT.filters.fileTags}
          open={sections.fileTags}
          onOpenChange={(open) => onSections({ ...sections, fileTags: open })}
          aside={
            <>
              {filters.fileTags.length > 1 && filters.tags.length < 2 && match}
              <Clear
                shown={filters.fileTags.length > 0}
                onClick={() => onFilters({ ...filters, fileTags: [] })}
              />
            </>
          }
        >
          <div className="-mx-1">
            <TagRows
              counts={fileTags}
              picked={filters.fileTags}
              onPick={(picked) => onFilters({ ...filters, fileTags: picked })}
            />
          </div>
        </Section>
      </div>
    </aside>
  );
}
