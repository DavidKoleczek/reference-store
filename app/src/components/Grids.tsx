import type { ReactNode } from "react";

import { Picture } from "@/components/Picture";
import { Icon } from "@/components/ui/icon";
import { Rating } from "@/components/ui/rating";
import {
  coverUri,
  coverVersion,
  fileVersion,
  thumbnailUri,
  type EntrySummary,
} from "@/lib/api";
import {
  fileName,
  hasThumbnail,
  pastelOf,
  shownName,
  siteOf,
} from "@/lib/format";
import { shownKey, type Shown, type WallRowLayout } from "@/lib/layout";
import { TEXT } from "@/lib/text";
import { cn } from "@/lib/utils";

const SELECTED = "border-accent-ink shadow-[0_0_0_1px_var(--accent-ink)]";

/** The line a group is under: its name and how many it holds, and a click that opens and closes it. */
export function GroupHeader({
  title,
  count,
  open,
  onToggle,
  aside,
  className,
}: {
  title: string;
  count: string;
  open: boolean;
  onToggle: () => void;
  aside?: ReactNode;
  className?: string;
}) {
  return (
    <header className={cn("flex h-6 items-center gap-2", className)}>
      <button
        type="button"
        aria-expanded={open}
        onClick={onToggle}
        className="-ml-1 flex h-full min-w-0 cursor-default items-center gap-1 rounded-sm px-1 text-left text-label outline-none focus-visible:focus-ring"
      >
        <Icon
          name="chevron"
          className={cn(
            "text-ink-muted transition-transform",
            !open && "-rotate-90",
          )}
        />
        <span className="truncate">{title}</span>
      </button>
      <span className="shrink-0 mono-annotation text-ink-muted">{count}</span>
      <span aria-hidden className="h-px min-w-4 flex-1 bg-line" />
      {aside}
    </header>
  );
}

/** The image that stands for an entry, or its pastel with what kind of entry it is. */
export function EntryCover({
  entry,
  size = "small",
  compact = false,
  className,
}: {
  entry: EntrySummary;
  size?: "small" | "large";
  /** It stands beside a name in a row, where its icon is small. */
  compact?: boolean;
  className?: string;
}) {
  const fallback = (
    <span
      className={cn(
        "grid size-full place-items-center text-on-pastel",
        pastelOf(entry.name),
      )}
    >
      <Icon
        name={entry.url ? "link-out" : "file"}
        size={24}
        className={cn(compact && "size-3")}
      />
    </span>
  );
  return (
    <Picture
      uri={
        entry.preview || entry.file_count > 0
          ? coverUri(entry.store, entry.name, size)
          : null
      }
      version={coverVersion(entry)}
      kind={size}
      fallback={fallback}
      // A preview is often the top of a page, so that is the part kept.
      className={cn("size-full object-cover object-top", className)}
    />
  );
}

export function EntryCard({
  entry,
  imageHeight,
  selected,
  showStore,
  onSelect,
  onOpen,
  onMenu,
}: {
  entry: EntrySummary;
  imageHeight: number;
  selected: boolean;
  showStore: boolean;
  onSelect: () => void;
  onOpen: () => void;
  /** It was right clicked, before the menu for it opens. */
  onMenu: () => void;
}) {
  const facts = [
    entry.url && siteOf(entry.url),
    entry.file_count > 0 && TEXT.count.files(entry.file_count),
  ].filter(Boolean);
  return (
    <button
      type="button"
      aria-pressed={selected}
      title={entry.description || undefined}
      onClick={onSelect}
      onDoubleClick={onOpen}
      onContextMenu={onMenu}
      onKeyDown={(event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          onOpen();
        }
      }}
      className={cn(
        "flex min-w-0 cursor-default flex-col overflow-hidden rounded-lg border bg-panel text-left outline-none focus-visible:focus-ring",
        selected ? SELECTED : "border-line hover:border-line-control",
      )}
    >
      <span
        style={{ height: imageHeight }}
        className="block w-full shrink-0 overflow-hidden border-b border-line bg-field"
      >
        <EntryCover entry={entry} />
      </span>
      <span className="flex h-14 min-w-0 flex-col justify-center gap-0.5 px-2.5">
        <span className="flex min-w-0 items-center gap-2">
          <span className="min-w-0 flex-1 truncate font-medium">
            {shownName(entry)}
          </span>
          {entry.rating !== null && <Rating value={entry.rating} />}
        </span>
        <span className="flex min-w-0 gap-2 mono-annotation text-ink-muted">
          <span className="min-w-0 flex-1 truncate">{facts.join("  ")}</span>
          {showStore && <span className="shrink-0">{entry.store}</span>}
        </span>
      </span>
    </button>
  );
}

export function FileTile({
  shown,
  width,
  imageHeight,
  selected,
  onSelect,
  onOpen,
  onMenu,
}: {
  shown: Shown;
  width: number;
  imageHeight: number;
  selected: boolean;
  onSelect: () => void;
  onOpen: () => void;
  onMenu: () => void;
}) {
  const { file } = shown;
  return (
    <button
      type="button"
      aria-pressed={selected}
      title={file.description || file.path}
      onClick={onSelect}
      onDoubleClick={onOpen}
      onContextMenu={onMenu}
      onKeyDown={(event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          onOpen();
        }
      }}
      style={{ width }}
      className="group/tile flex shrink-0 cursor-default flex-col text-left outline-none"
    >
      <span
        style={{ height: imageHeight }}
        className={cn(
          "block w-full overflow-hidden rounded-sm border bg-field group-focus-visible/tile:focus-ring",
          selected
            ? SELECTED
            : "border-line group-hover/tile:border-line-control",
        )}
      >
        <Picture
          uri={hasThumbnail(file) ? thumbnailUri(file, "small") : null}
          version={fileVersion(file)}
          alt={file.description}
          fallback={
            <span className="grid size-full place-items-center bg-panel text-ink-muted">
              <Icon name="file" size={24} />
            </span>
          }
          className="size-full object-cover"
        />
      </span>
      <span
        className={cn(
          "mt-1 block w-full truncate mono-annotation",
          selected ? "text-ink" : "text-ink-muted",
        )}
      >
        {fileName(file)}
      </span>
    </button>
  );
}

/** One row of a wall of files. */
export function WallRow({
  row,
  isSelected,
  onSelect,
  onOpen,
  onMenu,
}: {
  row: WallRowLayout;
  isSelected: (shown: Shown) => boolean;
  onSelect: (shown: Shown) => void;
  onOpen: (shown: Shown) => void;
  onMenu: (shown: Shown) => void;
}) {
  return (
    <div className="flex gap-x-2">
      {row.tiles.map(({ shown, width }) => (
        <FileTile
          key={shownKey(shown)}
          shown={shown}
          width={width}
          imageHeight={row.imageHeight}
          selected={isSelected(shown)}
          onSelect={() => onSelect(shown)}
          onOpen={() => onOpen(shown)}
          onMenu={() => onMenu(shown)}
        />
      ))}
    </div>
  );
}
