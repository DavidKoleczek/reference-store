import type { ReactNode } from "react";

import { Document } from "@/components/Document";
import { Picture } from "@/components/Picture";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icon";
import { Tooltip } from "@/components/ui/tooltip";
import {
  coverUri,
  thumbnailUri,
  type EntryFile,
  type EntrySummary,
} from "@/lib/api";
import {
  dimensions,
  formatSize,
  isImage,
  isText,
  pastelOf,
  siteOf,
} from "@/lib/format";
import { app } from "@/lib/host";
import { usePicture } from "@/lib/pictures";
import { TEXT } from "@/lib/text";
import { cn } from "@/lib/utils";

const FITTED = "absolute inset-0 size-full object-contain p-3";

/**
 * An image as large as its box allows. The small copy a list already read shows until the large one is in, and
 * `fallback` when there is none.
 */
function Fitted({
  small,
  large,
  fallback,
}: {
  small: string;
  large: string;
  fallback: ReactNode;
}) {
  const read = usePicture(large, "large");
  if (read.failed) {
    return fallback;
  }
  return read.url === null ? (
    <Picture key={small} uri={small} className={FITTED} />
  ) : (
    <img
      key={large}
      src={read.url}
      alt=""
      draggable={false}
      className={FITTED}
    />
  );
}

/** Where an entry's image comes from: its preview and the link that has, or the first of its own images. */
function Source({ entry }: { entry: EntrySummary }) {
  const preview = entry.preview;
  if (preview === null) {
    return entry.file_count > 0 ? TEXT.preview.firstImage : TEXT.preview.none;
  }
  if (preview.url === null) {
    return TEXT.preview.preview;
  }
  const url = preview.url;
  return (
    <>
      {TEXT.preview.from}{" "}
      <a
        href={url}
        onClick={(event) => {
          event.preventDefault();
          void app.openLink({ url });
        }}
        className="text-accent-ink underline underline-offset-2"
      >
        {siteOf(url)}
      </a>
    </>
  );
}

/**
 * What is picked, shown as large as the room allows: an image, a text file as it reads, or the image that stands for
 * an entry. A line under it says what it is.
 */
export function Preview({
  entry,
  file,
  size,
  onView,
}: {
  entry: EntrySummary;
  /** The file picked in `entry`, if one is. */
  file: EntryFile | null;
  /** The file's width and height, when it is an image whose size is known. */
  size: [number, number] | null;
  /** Shows the file over the whole app. */
  onView: () => void;
}) {
  const of = file && { store: entry.store, entry: entry.name, path: file.path };
  const image = of
    ? isImage(of)
      ? { small: thumbnailUri(of, "small"), large: thumbnailUri(of, "large") }
      : null
    : entry.preview || entry.file_count > 0
      ? {
          small: coverUri(entry.store, entry.name, "small"),
          large: coverUri(entry.store, entry.name, "large"),
        }
      : null;
  const text = of !== null && isText(of);
  const tile = (
    <div className="absolute inset-0 grid place-items-center">
      <span
        className={cn(
          "grid size-16 place-items-center rounded-xl text-on-pastel",
          pastelOf(entry.name),
        )}
      >
        <Icon
          name={file === null && entry.url ? "link-out" : "file"}
          size={24}
        />
      </span>
    </div>
  );
  return (
    <div className="flex h-full min-h-0 min-w-0 flex-col bg-canvas">
      <div className="relative min-h-0 flex-1">
        {image !== null ? (
          <Fitted small={image.small} large={image.large} fallback={tile} />
        ) : of !== null && text ? (
          <div className="absolute inset-0 overflow-y-auto bg-panel px-4 py-3">
            <Document file={of} />
          </div>
        ) : (
          tile
        )}
      </div>
      <footer className="flex h-7 shrink-0 items-center gap-3 border-t border-line bg-panel pr-1 pl-3 mono-annotation text-ink-muted">
        <span className="flex min-w-0 flex-1 gap-3 truncate">
          {file === null ? (
            <span className="truncate">
              <Source entry={entry} />
            </span>
          ) : (
            <>
              {size && <span>{dimensions(size)}</span>}
              <span>{formatSize(file.size)}</span>
            </>
          )}
        </span>
        {file !== null && (image !== null || text) && (
          <Tooltip content={TEXT.preview.viewLargeTip} side="top">
            <Button
              size="sm"
              icon
              aria-label={TEXT.preview.viewLarge}
              onClick={onView}
            >
              <Icon name="expand" />
            </Button>
          </Tooltip>
        )}
      </footer>
    </div>
  );
}
