import { useState } from "react";

import { TagsEditor } from "@/components/TagsEditor";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { CropMarks } from "@/components/ui/empty-state";
import { Input, Label, Textarea } from "@/components/ui/field";
import { Icon } from "@/components/ui/icon";
import { Notice } from "@/components/ui/notice";
import { ProgressBar } from "@/components/ui/progress-bar";
import { Select } from "@/components/ui/select";
import type { Store } from "@/lib/api";
import { describe } from "@/lib/errors";
import { toggleTag } from "@/lib/filters";
import { formatSize } from "@/lib/format";
import { cleanName, isLink, suggestName } from "@/lib/names";
import { startingStore } from "@/lib/stores";
import { TEXT } from "@/lib/text";
import { dropped, type Outgoing } from "@/lib/uploads";

/** What the Add dialog was given, for the app to add. */
export type Adding = {
  name: string;
  url: string;
  title: string;
  description: string;
  tags: string[];
  store: string;
  files: Outgoing[];
};

/**
 * Adds a reference from a link, files, or both. Its name is suggested from the link or the files and can be changed.
 * Nothing is fetched: what the link is stays to be filled in.
 */
export function AddDialog({
  link,
  stores,
  known,
  onAdd,
  onClose,
}: {
  /** The link it starts with, such as one pasted onto the app. */
  link: string;
  stores: Store[];
  /** The tags in use, to pick from. */
  known: { tag: string; count: number }[];
  /** Adds it, telling how much of its files went up. */
  onAdd: (
    adding: Adding,
    onProgress: (sent: number, total: number) => void,
  ) => Promise<void>;
  onClose: () => void;
}) {
  const [url, setUrl] = useState(link);
  const [name, setName] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [store, setStore] = useState(startingStore(stores) ?? "");
  const [files, setFiles] = useState<Outgoing[]>([]);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const suggested = isLink(url)
    ? suggestName(url)
    : files.length > 0
      ? cleanName(files[0].path.split("/")[0].replace(/\.[^.]+$/, ""))
      : "";
  const shownName = name ?? suggested;
  const ready =
    shownName.trim() !== "" &&
    store !== "" &&
    (url.trim() === "" || isLink(url)) &&
    progress === null;
  const add = () => {
    if (!ready) {
      return;
    }
    setProgress(0);
    setError(null);
    onAdd(
      {
        name: shownName.trim(),
        url: url.trim(),
        title: title.trim(),
        description: description.trim(),
        tags,
        store,
        files,
      },
      (sent, total) => setProgress(total > 0 ? sent / total : 1),
    ).then(onClose, (cause: unknown) => {
      setProgress(null);
      setError(describe(cause));
    });
  };
  const size = files.reduce((sum, each) => sum + each.file.size, 0);
  return (
    <Dialog
      open
      onOpenChange={(open) => !open && progress === null && onClose()}
    >
      <DialogContent title={TEXT.common.addReference} className="sm:max-w-120">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            add();
          }}
          className="flex flex-col gap-4 overflow-y-auto px-5 py-4"
        >
          <div>
            <Label htmlFor="add-link">{TEXT.fields.link.label}</Label>
            <Input
              id="add-link"
              autoFocus={!link}
              value={url}
              placeholder={TEXT.fields.link.placeholder}
              aria-invalid={url.trim() !== "" && !isLink(url)}
              onChange={(event) => setUrl(event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="add-name">{TEXT.fields.name.label}</Label>
            <Input
              id="add-name"
              autoFocus={Boolean(link)}
              value={shownName}
              placeholder={TEXT.fields.name.placeholder}
              onChange={(event) => setName(event.target.value)}
            />
            <p className="mt-1.5 text-caption text-ink-muted">
              {TEXT.fields.name.help}
            </p>
          </div>
          <div>
            <Label htmlFor="add-title">{TEXT.fields.title.label}</Label>
            <Input
              id="add-title"
              value={title}
              placeholder={TEXT.fields.title.help}
              onChange={(event) => setTitle(event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="add-description">
              {TEXT.fields.description.label}
            </Label>
            <Textarea
              id="add-description"
              value={description}
              placeholder={TEXT.fields.description.help}
              onChange={(event) => setDescription(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
                  add();
                }
              }}
            />
          </div>
          <div>
            <Label>{TEXT.fields.tags.label}</Label>
            <TagsEditor
              tags={tags}
              known={known}
              active={[]}
              locked={null}
              onAdd={(tag) => setTags([...tags, tag])}
              onRemove={(tag) => setTags(toggleTag(tags, tag))}
            />
          </div>
          <div>
            <Label>{TEXT.fields.store.label}</Label>
            <Select
              label={TEXT.fields.store.label}
              value={store}
              onChange={setStore}
              items={stores.map((each) => ({
                value: each.name,
                label: each.name,
                aside:
                  each.priority_order === 0
                    ? TEXT.stores.project
                    : each.default
                      ? TEXT.stores.default
                      : undefined,
                disabled: !each.available
                  ? TEXT.stores.unreachable
                  : each.read_only
                    ? TEXT.stores.isReadOnly
                    : undefined,
              }))}
            />
          </div>
          <div
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              void dropped(event.dataTransfer).then((more) =>
                setFiles((was) => [...was, ...more]),
              );
            }}
            className="relative flex items-center justify-center gap-2 bg-canvas px-4 py-5 text-ink-muted"
          >
            <CropMarks />
            <Icon name="import" />
            {files.length > 0 ? (
              <>
                <span>
                  {TEXT.count.filesAndSize(files.length, formatSize(size))}
                </span>
                <Button size="sm" onClick={() => setFiles([])}>
                  {TEXT.common.clear}
                </Button>
              </>
            ) : (
              TEXT.dialogs.add.drop
            )}
          </div>
          {progress !== null && files.length > 0 && <ProgressBar />}
          {error && <Notice>{error}</Notice>}
          <button type="submit" hidden />
        </form>
        <DialogFooter>
          <span className="flex-1" />
          <Button onClick={onClose} disabled={progress !== null}>
            {TEXT.common.cancel}
          </Button>
          <Button variant="primary" disabled={!ready} onClick={add}>
            {TEXT.common.add}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
