import { useEffect } from "react";

import { CopyPath } from "@/components/CopyPath";
import { Document, HtmlPage } from "@/components/Document";
import { Picture } from "@/components/Picture";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Icon } from "@/components/ui/icon";
import { Markdown } from "@/components/ui/markdown";
import { Tag } from "@/components/ui/tag";
import { fileUri, fileVersion, thumbnailUri, type FileOf } from "@/lib/api";
import {
  dimensions,
  fileName,
  formatSize,
  isHtml,
  isImage,
  isText,
} from "@/lib/format";
import type { Shown } from "@/lib/layout";
import { appNetwork } from "@/lib/network";
import { readAhead, type PictureKind } from "@/lib/pictures";
import { TEXT } from "@/lib/text";

// What a browser shows by itself, so the viewer shows the file and not a thumbnail of it.
const SHOWN_AS_IS = [
  ".png",
  ".jpg",
  ".jpeg",
  ".webp",
  ".gif",
  ".bmp",
  ".avif",
  ".svg",
];

/** The copy of an image the viewer shows: the file itself where the browser can show it, else the large thumbnail. */
function largest(file: FileOf): { uri: string; kind: PictureKind } {
  const lower = file.path.toLowerCase();
  return SHOWN_AS_IS.some((suffix) => lower.endsWith(suffix))
    ? { uri: fileUri(file), kind: "file" }
    : { uri: thumbnailUri(file, "large"), kind: "large" };
}

/** One file shown large over the app, with the files around it a key away. */
export function Viewer({
  files,
  index,
  onIndex,
  onClose,
}: {
  /** The files it steps through, in the order they showed. */
  files: Shown[];
  index: number;
  onIndex: (index: number) => void;
  onClose: () => void;
}) {
  const shown = files[index];
  const last = files.length - 1;
  useEffect(() => {
    const step = (event: KeyboardEvent) => {
      if (event.key === "ArrowLeft" && index > 0) {
        onIndex(index - 1);
      } else if (event.key === "ArrowRight" && index < last) {
        onIndex(index + 1);
      }
    };
    // On the way down, since the dialog keeps key presses in it from reaching the window on the way up.
    window.addEventListener("keydown", step, true);
    return () => window.removeEventListener("keydown", step, true);
  }, [index, last, onIndex]);
  useEffect(() => {
    const next = files[index + 1];
    if (next && isImage(next.file)) {
      const { uri, kind } = largest(next.file);
      readAhead(uri, kind, fileVersion(next.file));
    }
  }, [files, index]);
  if (!shown) {
    return null;
  }
  const { file } = shown;
  const facts = [
    file.entry,
    shown.dimensions ? dimensions(shown.dimensions) : null,
    formatSize(file.size),
  ].filter(Boolean);
  const image = isImage(file) ? largest(file) : null;
  const version = fileVersion(file);
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        title={fileName(file)}
        subtitle={facts.join("  ")}
        className="h-full sm:max-w-350"
      >
        <div className="relative min-h-0 flex-1 bg-canvas">
          {image ? (
            <>
              <Picture
                key={`small:${file.path}`}
                uri={thumbnailUri(file, "small")}
                version={version}
                className="absolute inset-0 size-full object-contain p-4 blur-[1px]"
              />
              <Picture
                key={image.uri}
                uri={image.uri}
                version={version}
                kind={image.kind}
                alt={file.description}
                className="absolute inset-0 size-full bg-canvas object-contain p-4"
              />
            </>
          ) : isText(file) ? (
            <div className="absolute inset-0 overflow-y-auto">
              <div className="mx-auto max-w-180 px-6 py-5">
                <Document file={file} version={version} />
              </div>
            </div>
          ) : isHtml(file) ? (
            <HtmlPage file={file} version={version} />
          ) : (
            <p className="absolute inset-0 grid place-items-center text-ink-muted">
              {TEXT.viewer.noPreview}
            </p>
          )}
        </div>
        {(file.description || file.tags.length > 0 || file.notes) && (
          <div className="flex shrink-0 flex-col gap-1.5 border-t border-line px-5 py-3">
            {file.description && <p>{file.description}</p>}
            {file.notes && (
              <Markdown breaks className="text-ink-muted">
                {file.notes}
              </Markdown>
            )}
            {file.tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {file.tags.map((tag) => (
                  <Tag key={tag} tag={tag} />
                ))}
              </div>
            )}
          </div>
        )}
        <DialogFooter>
          <Button
            variant="secondary"
            icon
            aria-label={TEXT.viewer.previous}
            disabled={index === 0}
            onClick={() => onIndex(index - 1)}
          >
            <Icon name="chevron" className="rotate-90" />
          </Button>
          <Button
            variant="secondary"
            icon
            aria-label={TEXT.viewer.next}
            disabled={index === last}
            onClick={() => onIndex(index + 1)}
          >
            <Icon name="chevron" className="-rotate-90" />
          </Button>
          <span className="mono-annotation text-ink-muted">
            {TEXT.count.place(index + 1, files.length)}
          </span>
          <span className="flex-1" />
          {/* A path on the machine the stores are on says nothing to another device. */}
          {appNetwork().this_machine && <CopyPath path={file.full_path} />}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
