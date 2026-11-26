import { useState } from "react";

import { TagsEditor } from "@/components/TagsEditor";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/field";
import { Icon } from "@/components/ui/icon";
import { Notice } from "@/components/ui/notice";
import { ProgressBar } from "@/components/ui/progress-bar";
import { describe } from "@/lib/errors";
import { toggleTag } from "@/lib/filters";
import { formatSize } from "@/lib/format";
import { TEXT } from "@/lib/text";
import type { Outgoing } from "@/lib/uploads";

/** One file or folder going in, by its name at the top of what was dropped, and what to say about it. */
export type GoingIn = { top: string; description: string; tags: string[] };

type Top = { top: string; folder: boolean; count: number; size: number };

function topsOf(outgoing: Outgoing[]): Top[] {
  const tops = new Map<string, Top>();
  for (const { file, path } of outgoing) {
    const [top, ...rest] = path.split("/");
    const kept = tops.get(top) ?? {
      top,
      folder: rest.length > 0,
      count: 0,
      size: 0,
    };
    kept.count += 1;
    kept.size += file.size;
    tops.set(top, kept);
  }
  return [...tops.values()];
}

/**
 * Files and folders going into an entry, each of which can be given tags, and a file a description, as it goes in.
 * Tags on a folder go on every file in it.
 */
export function AddFilesDialog({
  entry,
  outgoing,
  known,
  onAdd,
  onClose,
}: {
  /** The entry's name, as the title says it. */
  entry: string;
  outgoing: Outgoing[];
  known: { tag: string; count: number }[];
  onAdd: (
    goingIn: GoingIn[],
    onProgress: (sent: number, total: number) => void,
  ) => Promise<void>;
  onClose: () => void;
}) {
  const tops = topsOf(outgoing);
  const [said, setSaid] = useState<Record<string, GoingIn>>({});
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const about = (top: string): GoingIn =>
    said[top] ?? { top, description: "", tags: [] };
  const change = (top: string, next: Partial<GoingIn>) =>
    setSaid((was) => ({ ...was, [top]: { ...about(top), ...next } }));
  const add = () => {
    setProgress(0);
    setError(null);
    onAdd(
      tops.map(({ top }) => about(top)),
      (sent, total) => setProgress(total > 0 ? sent / total : 1),
    ).then(onClose, (cause: unknown) => {
      setProgress(null);
      setError(describe(cause));
    });
  };
  return (
    <Dialog
      open
      onOpenChange={(open) => !open && progress === null && onClose()}
    >
      <DialogContent
        title={TEXT.dialogs.addFiles.title(entry)}
        className="sm:max-w-140"
      >
        <div className="flex flex-col gap-3 overflow-y-auto px-5 py-4">
          {tops.map((top) => (
            <div
              key={top.top}
              className="flex flex-col gap-2 border-b border-line pb-3"
            >
              <p className="flex items-center gap-2">
                <Icon
                  name={top.folder ? "folder" : "file"}
                  className="text-ink-muted"
                />
                <span className="min-w-0 flex-1 truncate">{top.top}</span>
                <span className="mono-annotation text-ink-muted">
                  {top.folder
                    ? TEXT.count.filesAndSize(top.count, formatSize(top.size))
                    : formatSize(top.size)}
                </span>
              </p>
              {!top.folder && (
                <Input
                  aria-label={TEXT.dialogs.addFiles.descriptionOf(top.top)}
                  value={about(top.top).description}
                  placeholder={TEXT.fields.description.fileHelp}
                  onChange={(event) =>
                    change(top.top, { description: event.target.value })
                  }
                />
              )}
              <TagsEditor
                tags={about(top.top).tags}
                known={known}
                active={[]}
                locked={null}
                onAdd={(tag) =>
                  change(top.top, { tags: [...about(top.top).tags, tag] })
                }
                onRemove={(tag) =>
                  change(top.top, { tags: toggleTag(about(top.top).tags, tag) })
                }
              />
            </div>
          ))}
          {progress !== null && <ProgressBar />}
          {error && <Notice>{error}</Notice>}
        </div>
        <DialogFooter>
          <span className="flex-1" />
          <Button onClick={onClose} disabled={progress !== null}>
            {TEXT.common.cancel}
          </Button>
          <Button
            variant="primary"
            disabled={progress !== null || tops.length === 0}
            onClick={add}
          >
            {TEXT.dialogs.addFiles.action(outgoing.length)}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
