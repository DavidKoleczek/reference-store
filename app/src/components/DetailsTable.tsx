import { useRef, type PointerEvent, type ReactNode } from "react";

import { GroupHeader } from "@/components/Grids";
import { Windowed, type WindowRow } from "@/components/Windowed";
import { Icon } from "@/components/ui/icon";
import { GROUP_HEADER_HEIGHT } from "@/lib/layout";
import { TEXT } from "@/lib/text";
import { cn } from "@/lib/utils";

export type Column<Item, Sort extends string> = {
  key: string;
  label: string;
  /** What a click on its header sorts by; none for a column that cannot be sorted by. */
  sort?: Sort;
  /** How wide it starts, in pixels. */
  width: number;
  align?: "right";
  /** Its cells are numbers or times, set in mono so they line up. */
  mono?: boolean;
  cell: (item: Item) => ReactNode;
};

/** A group of rows, under a line with its name when it has a header, and the row that reads more of it. */
export type Section<Item> = {
  key: string;
  header?: {
    title: string;
    count: string;
    open: boolean;
    onToggle: () => void;
    aside?: ReactNode;
  };
  items: Item[];
  loader?: WindowRow;
};

const NARROWEST = 56;
const ROW_HEIGHT = 28;

function HeaderCell<Item, Sort extends string>({
  column,
  width,
  sorted,
  descending,
  onSort,
  onWidth,
}: {
  column: Column<Item, Sort>;
  width: number;
  sorted: boolean;
  descending: boolean;
  onSort: (sort: Sort) => void;
  onWidth: (width: number | null) => void;
}) {
  const drag = useRef<{ x: number; width: number } | null>(null);
  const sort = column.sort;
  return (
    <div
      role="columnheader"
      aria-sort={sorted ? (descending ? "descending" : "ascending") : undefined}
      className="relative flex min-w-0 border-r border-line"
    >
      <button
        type="button"
        disabled={sort === undefined}
        onClick={() => sort !== undefined && onSort(sort)}
        className={cn(
          "flex h-full min-w-0 flex-1 cursor-default items-center px-2 outline-none select-none focus-visible:focus-ring enabled:hover:bg-hover enabled:hover:text-ink",
          column.align === "right" && "justify-end",
          sorted && "text-ink",
        )}
      >
        <span className="truncate">{column.label}</span>
      </button>
      {sorted && (
        // Over the middle of the header, as a file manager marks the column a list is sorted by.
        <Icon
          name="chevron"
          className={cn(
            "pointer-events-none absolute -top-0.5 left-1/2 size-3 -translate-x-1/2 text-ink-muted",
            !descending && "rotate-180",
          )}
        />
      )}
      <span
        role="separator"
        aria-orientation="vertical"
        aria-label={TEXT.columns.resize(column.label)}
        title={TEXT.columns.resizeHint}
        onPointerDown={(event: PointerEvent<HTMLSpanElement>) => {
          event.preventDefault();
          event.currentTarget.setPointerCapture(event.pointerId);
          drag.current = { x: event.clientX, width };
        }}
        onPointerMove={(event) => {
          if (drag.current) {
            onWidth(
              Math.max(
                NARROWEST,
                drag.current.width + event.clientX - drag.current.x,
              ),
            );
          }
        }}
        onPointerUp={(event) => {
          drag.current = null;
          event.currentTarget.releasePointerCapture(event.pointerId);
        }}
        onDoubleClick={() => onWidth(null)}
        className="absolute top-0 -right-1 z-10 h-full w-2 cursor-col-resize touch-none"
      />
    </div>
  );
}

/**
 * Things as a list with a column for each fact, as a file manager's details view has it. A click on a column's header
 * sorts by it, and another turns the order around. Columns are resized by the line after them. A click on a row picks
 * it, and a double click opens it. Only the rows near the screen are in the page.
 */
export function DetailsTable<Item, Sort extends string>({
  label,
  columns,
  widths,
  onWidth,
  sections,
  sort,
  descending,
  onSort,
  itemKey,
  isSelected,
  tip,
  onSelect,
  onOpen,
  onMenu,
}: {
  label: string;
  columns: Column<Item, Sort>[];
  /** The widths the person gave columns, by key. */
  widths: Record<string, number>;
  /** A column's new width, or null to put it back to how it started. */
  onWidth: (column: string, width: number | null) => void;
  sections: Section<Item>[];
  sort: Sort | null;
  descending: boolean;
  onSort: (sort: Sort) => void;
  itemKey: (item: Item) => string;
  isSelected: (item: Item) => boolean;
  /** What shows when the pointer rests on a row. */
  tip: (item: Item) => string;
  onSelect: (item: Item) => void;
  onOpen: (item: Item) => void;
  /** A row was right clicked, before the menu for it opens. */
  onMenu: (item: Item) => void;
}) {
  const sized = columns.map((column) => widths[column.key] ?? column.width);
  const template = {
    gridTemplateColumns: sized.map((width) => `${width}px`).join(" "),
  };
  const row = (item: Item): WindowRow => ({
    key: itemKey(item),
    height: ROW_HEIGHT,
    render: () => {
      const selected = isSelected(item);
      return (
        <div
          role="row"
          tabIndex={0}
          aria-selected={selected}
          title={tip(item)}
          onClick={() => onSelect(item)}
          onDoubleClick={() => onOpen(item)}
          onContextMenu={() => onMenu(item)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              onOpen(item);
            }
          }}
          style={template}
          className={cn(
            "group/row grid h-7 cursor-default items-center outline-none select-none focus-visible:focus-ring",
            selected ? "bg-accent-soft" : "hover:bg-hover",
          )}
        >
          {columns.map((column, index) => (
            <div
              key={column.key}
              role="cell"
              className={cn(
                "min-w-0 truncate px-2",
                index > 0 && "text-ink-muted",
                column.align === "right" && "text-right",
                column.mono && "mono-annotation",
              )}
            >
              {column.cell(item)}
            </div>
          ))}
        </div>
      );
    },
  });
  const rows = (): WindowRow[] =>
    sections.flatMap((section) => {
      const made: WindowRow[] = [];
      const header = section.header;
      if (header) {
        made.push({
          key: `header:${section.key}`,
          height: GROUP_HEADER_HEIGHT,
          render: () => (
            <GroupHeader
              title={header.title}
              count={header.count}
              open={header.open}
              onToggle={header.onToggle}
              aside={header.aside}
              className="sticky left-0 mt-1.5 h-7 pr-2 pl-3"
            />
          ),
        });
      }
      if (!header || header.open) {
        made.push(...section.items.map(row));
        if (section.loader) {
          made.push(section.loader);
        }
      }
      return made;
    });
  return (
    <div
      role="table"
      aria-label={label}
      style={{ minWidth: sized.reduce((sum, width) => sum + width, 0) }}
      className="pb-2"
    >
      <div
        role="row"
        style={template}
        className="sticky top-0 z-10 grid h-7 border-b border-line bg-panel text-label text-ink-muted"
      >
        {columns.map((column, index) => (
          <HeaderCell
            key={column.key}
            column={column}
            width={sized[index]}
            sorted={column.sort !== undefined && column.sort === sort}
            descending={descending}
            onSort={onSort}
            onWidth={(width) => onWidth(column.key, width)}
          />
        ))}
      </div>
      <Windowed rows={rows} />
    </div>
  );
}
