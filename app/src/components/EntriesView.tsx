import { useEffect } from "react";

import {
  DetailsTable,
  type Column,
  type Section,
} from "@/components/DetailsTable";
import { EntryCard, EntryCover, GroupHeader } from "@/components/Grids";
import { loaderRow } from "@/components/rows";
import { Windowed, type WindowRow } from "@/components/Windowed";
import { Rating } from "@/components/ui/rating";
import {
  sameEntry,
  type EntryRef,
  type EntrySort,
  type EntrySummary,
} from "@/lib/api";
import type { EntryArrangement } from "@/lib/arrange";
import { cardLayout, GROUP_HEADER_HEIGHT } from "@/lib/layout";
import {
  formatCount,
  formatKilobytes,
  formatSize,
  formatTime,
  shownName,
} from "@/lib/format";
import type { Paged } from "@/lib/paging";
import { TEXT } from "@/lib/text";
import { cn } from "@/lib/utils";

/** A group of entries: its header, and the list it reads once it is opened. No groups is one list with no header. */
export type EntryGroupSpec = {
  key: string;
  title: string;
  /** How many there are by the counts in the filters pane, until the group's own list says. */
  count: number | null;
};

export type EntryLists = {
  list: (key: string) => Paged<EntrySummary>;
  open: (key: string) => void;
  more: (key: string) => void;
  refresh: () => void;
};

const NAME_THUMB = "size-4.5 shrink-0 overflow-hidden rounded-[2px]";

/** The columns of the list of entries. `onRate` is told the rating picked in a row. */
function entryColumns(
  onRate: (entry: EntrySummary, rating: number | null) => void,
  canChange: (entry: EntrySummary) => boolean,
): Column<EntrySummary, EntrySort>[] {
  return [
    {
      key: "name",
      label: TEXT.columns.name,
      sort: "name",
      width: 300,
      cell: (entry) => (
        <span className="flex min-w-0 items-center gap-2">
          <span
            className={cn(
              NAME_THUMB,
              entry.preview && "border border-line bg-field",
            )}
          >
            <EntryCover entry={entry} compact />
          </span>
          <span className="truncate">{shownName(entry)}</span>
        </span>
      ),
    },
    {
      key: "created",
      label: TEXT.columns.date,
      sort: "created",
      width: 150,
      mono: true,
      cell: (entry) => formatTime(entry.created),
    },
    {
      key: "published",
      label: TEXT.columns.published,
      sort: "published",
      width: 150,
      mono: true,
      cell: (entry) =>
        entry.source_published_at === null
          ? ""
          : formatTime(entry.source_published_at),
    },
    {
      key: "files",
      label: TEXT.columns.files,
      sort: "files",
      width: 80,
      align: "right",
      mono: true,
      cell: (entry) =>
        entry.file_count === 0 ? "" : formatCount(entry.file_count),
    },
    {
      key: "size",
      label: TEXT.columns.size,
      sort: "size",
      width: 100,
      align: "right",
      mono: true,
      cell: (entry) =>
        entry.file_count > 0 ? formatKilobytes(entry.size) : "",
    },
    {
      key: "tags",
      label: TEXT.columns.tags,
      sort: "tags",
      width: 180,
      cell: (entry) => entry.tags.join(", "),
    },
    {
      key: "rating",
      label: TEXT.columns.rating,
      sort: "rating",
      width: 124,
      cell: (entry) =>
        canChange(entry) ? (
          // The squares of an entry with no rating show while the pointer is on its row, to rate it there.
          <span
            onClick={(event) => event.stopPropagation()}
            onDoubleClick={(event) => event.stopPropagation()}
            className={cn(
              "flex",
              entry.rating === null &&
                "opacity-0 group-focus-within/row:opacity-100 group-hover/row:opacity-100",
            )}
          >
            <Rating
              value={entry.rating}
              onChange={(rating) => onRate(entry, rating)}
              className="-ml-1"
            />
          </span>
        ) : (
          entry.rating !== null && <Rating value={entry.rating} />
        ),
    },
    {
      key: "store",
      label: TEXT.columns.store,
      sort: "store",
      width: 110,
      cell: (entry) => entry.store,
    },
  ];
}

function entryTip(entry: EntrySummary): string {
  return [
    entry.title && entry.name,
    entry.description,
    entry.file_count > 0 &&
      TEXT.columns.tip.files(formatCount(entry.file_count)),
    entry.file_count > 0 && TEXT.columns.tip.size(formatSize(entry.size)),
    entry.url && TEXT.columns.tip.link(entry.url),
  ]
    .filter(Boolean)
    .join("\n");
}

function groupCount(spec: EntryGroupSpec, paged: Paged<EntrySummary>): string {
  const count = paged.total ?? spec.count;
  return count === null ? "" : formatCount(count);
}

/** Entries, a page at a time, as cards or as a list with columns, in groups that each read their own pages. */
export function EntriesView({
  lists,
  groups,
  opened,
  onToggleGroup,
  arrangement,
  sortable,
  onSort,
  widths,
  onWidth,
  selected,
  showStore,
  canChange,
  onSelect,
  onOpen,
  onMenu,
  onRate,
}: {
  lists: EntryLists;
  /** The groups, or null for one list with no headers. */
  groups: EntryGroupSpec[] | null;
  /** The keys of the groups that are open. */
  opened: string[];
  onToggleGroup: (key: string) => void;
  arrangement: EntryArrangement;
  /** Whether the list can be sorted, which it can't while it shows what was searched for. */
  sortable: boolean;
  /** A column's header was clicked. */
  onSort: (sort: EntrySort) => void;
  widths: Record<string, number>;
  onWidth: (column: string, width: number | null) => void;
  selected: EntryRef | null;
  showStore: boolean;
  canChange: (entry: EntrySummary) => boolean;
  onSelect: (entry: EntrySummary) => void;
  onOpen: (entry: EntrySummary) => void;
  onMenu: (entry: EntrySummary) => void;
  onRate: (entry: EntrySummary, rating: number | null) => void;
}) {
  const specs = groups ?? [{ key: "all", title: "", count: null }];
  const isOpen = (key: string) => groups === null || opened.includes(key);
  const shownKeys = specs
    .filter((spec) => isOpen(spec.key))
    .map((spec) => spec.key);

  useEffect(() => {
    for (const key of shownKeys) {
      lists.open(key);
    }
  });

  const loader = (key: string, paged: Paged<EntrySummary>) =>
    paged.after !== null ||
    paged.loading ||
    paged.error !== null ||
    paged.total === null
      ? loaderRow(
          key,
          paged.loading || paged.total === null,
          paged.error,
          () => lists.more(key),
          lists.refresh,
        )
      : undefined;

  if (arrangement.layout === "details") {
    const sections: Section<EntrySummary>[] = specs.map((spec) => {
      const paged = lists.list(spec.key);
      const open = isOpen(spec.key);
      return {
        key: spec.key,
        header:
          groups === null
            ? undefined
            : {
                title: spec.title,
                count: groupCount(spec, paged),
                open,
                onToggle: () => onToggleGroup(spec.key),
              },
        items: open ? paged.items : [],
        loader: open ? loader(spec.key, paged) : undefined,
      };
    });
    return (
      <DetailsTable
        label={TEXT.list.entries}
        columns={entryColumns(onRate, canChange)}
        widths={widths}
        onWidth={onWidth}
        sections={sections}
        sort={sortable ? arrangement.sort : "name"}
        descending={sortable ? arrangement.descending : false}
        onSort={onSort}
        itemKey={(entry) => `${entry.store}/${entry.name}`}
        isSelected={(entry) => sameEntry(entry, selected)}
        tip={entryTip}
        onSelect={onSelect}
        onOpen={onOpen}
        onMenu={onMenu}
      />
    );
  }

  const rows = (width: number): WindowRow[] => {
    const { columns, imageHeight, rowHeight } = cardLayout(width);
    return specs.flatMap((spec) => {
      const paged = lists.list(spec.key);
      const open = isOpen(spec.key);
      const made: WindowRow[] = [];
      if (groups !== null) {
        made.push({
          key: `header:${spec.key}`,
          height: GROUP_HEADER_HEIGHT,
          render: () => (
            <GroupHeader
              title={spec.title}
              count={groupCount(spec, paged)}
              open={open}
              onToggle={() => onToggleGroup(spec.key)}
              className="mt-1.5"
            />
          ),
        });
      }
      if (!open) {
        return made;
      }
      for (let start = 0; start < paged.items.length; start += columns) {
        const cards = paged.items.slice(start, start + columns);
        made.push({
          key: `${spec.key}:${cards[0].store}/${cards[0].name}`,
          height: rowHeight,
          render: () => (
            <div
              className="grid gap-3"
              style={{
                gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`,
              }}
            >
              {cards.map((entry) => (
                <EntryCard
                  key={`${entry.store}/${entry.name}`}
                  entry={entry}
                  imageHeight={imageHeight}
                  selected={sameEntry(entry, selected)}
                  showStore={showStore}
                  onSelect={() => onSelect(entry)}
                  onOpen={() => onOpen(entry)}
                  onMenu={() => onMenu(entry)}
                />
              ))}
            </div>
          ),
        });
      }
      const more = loader(spec.key, paged);
      if (more) {
        made.push(more);
      }
      return made;
    });
  };
  return (
    <div className="p-3">
      <Windowed rows={rows} />
    </div>
  );
}
