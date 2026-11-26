import { useState, type ReactNode } from "react";

import {
  DetailsTable,
  type Column,
  type Section,
} from "@/components/DetailsTable";
import { GroupHeader, WallRow } from "@/components/Grids";
import { Picture } from "@/components/Picture";
import { Windowed, type WindowRow } from "@/components/Windowed";
import { Icon } from "@/components/ui/icon";
import { thumbnailUri } from "@/lib/api";
import type { Layout } from "@/lib/arrange";
import {
  dimensions,
  fileFolder,
  fileName,
  fileType,
  formatKilobytes,
  formatSize,
  formatTime,
  isImage,
} from "@/lib/format";
import {
  GROUP_HEADER_HEIGHT,
  shownKey,
  wallLayout,
  type Shown,
} from "@/lib/layout";
import { TEXT } from "@/lib/text";
import { cn } from "@/lib/utils";

/** Files under a header, or with none, and the row that reads more of them. */
export type FileSection = {
  key: string;
  /** None shows the files with nothing above them. */
  title: string | null;
  count?: string;
  aside?: ReactNode;
  items: Shown[];
  loader?: WindowRow;
};

/** What a column of the list of files sorts by: the library's sort across entries, or the open entry's own. */
export type FileColumnSort =
  "path" | "name" | "modified" | "type" | "size" | "tags";

const THUMB = "size-4.5 shrink-0 rounded-[2px]";

function NameCell({ shown }: { shown: Shown }) {
  const { file } = shown;
  const icon = (
    <span className={cn(THUMB, "grid place-items-center text-ink-muted")}>
      <Icon name="file" className="size-3.5" />
    </span>
  );
  return (
    <span className="flex min-w-0 items-center gap-2">
      <span className={cn(THUMB, "overflow-hidden")}>
        <Picture
          uri={isImage(file) ? thumbnailUri(file, "small") : null}
          fallback={icon}
          className={cn(THUMB, "border border-line bg-field object-cover")}
        />
      </span>
      <span className="truncate">{fileName(file)}</span>
    </span>
  );
}

function fileColumns(inEntry: boolean): Column<Shown, FileColumnSort>[] {
  return [
    {
      key: "name",
      label: TEXT.columns.name,
      sort: "name",
      width: 300,
      cell: (shown) => <NameCell shown={shown} />,
    },
    {
      key: "modified",
      label: TEXT.columns.date,
      sort: "modified",
      width: 150,
      mono: true,
      cell: ({ file }) => formatTime(file.modified),
    },
    {
      key: "type",
      label: TEXT.columns.type,
      sort: "type",
      width: 90,
      cell: ({ file }) => fileType(file),
    },
    {
      key: "size",
      label: TEXT.columns.size,
      sort: "size",
      width: 90,
      align: "right",
      mono: true,
      cell: ({ file }) => formatKilobytes(file.size),
    },
    {
      key: "tags",
      label: TEXT.columns.tags,
      // Across entries the library sorts, and it has no sort by a file's tags.
      sort: inEntry ? "tags" : undefined,
      width: 170,
      cell: ({ file }) => file.tags.join(", "),
    },
    {
      key: "dimensions",
      label: TEXT.columns.dimensions,
      width: 110,
      mono: true,
      cell: (shown) => (shown.dimensions ? dimensions(shown.dimensions) : ""),
    },
    inEntry
      ? {
          key: "folder",
          label: TEXT.columns.folder,
          width: 140,
          cell: ({ file }) => fileFolder(file),
        }
      : {
          key: "entry",
          label: TEXT.columns.entry,
          sort: "path",
          width: 200,
          cell: ({ file }) => file.entry,
        },
  ];
}

function fileTip({ file, dimensions: size }: Shown): string {
  return [
    file.description,
    TEXT.columns.tip.type(fileType(file)),
    size && TEXT.columns.tip.dimensions(dimensions(size)),
    TEXT.columns.tip.size(formatSize(file.size)),
  ]
    .filter(Boolean)
    .join("\n");
}

/** Files as a wall of pictures or as a list with columns, in sections that open and close. */
export function FilesView({
  sections,
  layout,
  inEntry,
  rowHeight,
  sort,
  descending,
  onSort,
  widths,
  onWidth,
  isSelected,
  onSelect,
  onOpen,
  onMenu,
}: {
  sections: FileSection[];
  layout: Layout;
  /** The files are all of the entry that is open, so nothing has to say which entry each is in. */
  inEntry: boolean;
  /** How tall a row of the wall is before it stretches to fill its width. */
  rowHeight: number;
  sort: FileColumnSort;
  descending: boolean;
  onSort: (sort: FileColumnSort) => void;
  widths: Record<string, number>;
  onWidth: (column: string, width: number | null) => void;
  isSelected: (shown: Shown) => boolean;
  onSelect: (shown: Shown) => void;
  onOpen: (shown: Shown) => void;
  onMenu: (shown: Shown) => void;
}) {
  const [closed, setClosed] = useState<string[]>([]);
  const toggle = (key: string) =>
    setClosed((was) =>
      was.includes(key) ? was.filter((each) => each !== key) : [...was, key],
    );

  if (layout === "details") {
    const tableSections: Section<Shown>[] = sections.map((section) => {
      const open = !closed.includes(section.key);
      return {
        key: section.key,
        header:
          section.title === null
            ? undefined
            : {
                title: section.title,
                count: section.count ?? `${section.items.length}`,
                open,
                onToggle: () => toggle(section.key),
                aside: section.aside,
              },
        items: section.items,
        loader: section.loader,
      };
    });
    return (
      <DetailsTable
        label={TEXT.list.files}
        columns={fileColumns(inEntry)}
        widths={widths}
        onWidth={onWidth}
        sections={tableSections}
        sort={sort}
        descending={descending}
        onSort={onSort}
        itemKey={shownKey}
        isSelected={isSelected}
        tip={fileTip}
        onSelect={onSelect}
        onOpen={onOpen}
        onMenu={onMenu}
      />
    );
  }

  const rows = (width: number): WindowRow[] =>
    sections.flatMap((section) => {
      const open = section.title === null || !closed.includes(section.key);
      const made: WindowRow[] = [];
      if (section.title !== null) {
        const title = section.title;
        made.push({
          key: `header:${section.key}`,
          height: GROUP_HEADER_HEIGHT,
          render: () => (
            <GroupHeader
              title={title}
              count={section.count ?? `${section.items.length}`}
              open={open}
              onToggle={() => toggle(section.key)}
              aside={section.aside}
              className="mt-1.5"
            />
          ),
        });
      }
      if (!open) {
        return made;
      }
      wallLayout(section.items, width, rowHeight).forEach((row, index) =>
        made.push({
          key: `${section.key}:${index}:${shownKey(row.tiles[0].shown)}`,
          height: row.height,
          render: () => (
            <WallRow
              row={row}
              isSelected={isSelected}
              onSelect={onSelect}
              onOpen={onOpen}
              onMenu={onMenu}
            />
          ),
        }),
      );
      if (section.loader) {
        made.push(section.loader);
      }
      return made;
    });
  return (
    <div className="p-3">
      <Windowed rows={rows} />
    </div>
  );
}
