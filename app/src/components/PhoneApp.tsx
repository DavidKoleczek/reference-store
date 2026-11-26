import { useEffect, useState } from "react";

import { EntryCover, WallRow } from "@/components/Grids";
import { loaderRow } from "@/components/rows";
import { TagsEditor } from "@/components/TagsEditor";
import { Viewer } from "@/components/Viewer";
import { Windowed, type WindowRow } from "@/components/Windowed";
import { Wordmark } from "@/components/Wordmark";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Input, Label } from "@/components/ui/field";
import { Icon } from "@/components/ui/icon";
import { LoadingMark } from "@/components/ui/loading-mark";
import { Notice } from "@/components/ui/notice";
import { ProgressBar } from "@/components/ui/progress-bar";
import { Rating } from "@/components/ui/rating";
import { Tag } from "@/components/ui/tag";
import {
  addEntry,
  listEntries,
  searchEntries,
  type EntryRef,
  type EntrySummary,
  type NewFile,
} from "@/lib/api";
import { describe } from "@/lib/errors";
import { toggleTag } from "@/lib/filters";
import { shownName, siteOf } from "@/lib/format";
import { app } from "@/lib/host";
import { shownKey, wallLayout, type Shown } from "@/lib/layout";
import { useCounts, useEntry } from "@/lib/library";
import { cleanName, isLink, suggestName } from "@/lib/names";
import { usePaged, useRefreshOnFocus } from "@/lib/paging";
import { startingStore } from "@/lib/stores";
import { TEXT } from "@/lib/text";
import { chooseFiles, sendFiles, type Outgoing } from "@/lib/uploads";
import { cn } from "@/lib/utils";

const ROW_HEIGHT = 76;
const WALL_ROW = 112;

/** An entry as a row of the phone's list: its image, its name, and where it links. */
function EntryRow({
  entry,
  onOpen,
}: {
  entry: EntrySummary;
  onOpen: () => void;
}) {
  const facts = [
    entry.url && siteOf(entry.url),
    entry.file_count > 0 && TEXT.count.files(entry.file_count),
  ].filter(Boolean);
  return (
    <button
      type="button"
      onClick={onOpen}
      className="flex size-full items-center gap-3 border-b border-line px-3 text-left outline-none active:bg-hover"
    >
      <span className="size-14 shrink-0 overflow-hidden rounded-md border border-line bg-field">
        <EntryCover entry={entry} />
      </span>
      <span className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="truncate font-medium">{shownName(entry)}</span>
        <span className="truncate mono-annotation text-ink-muted">
          {facts.join("  ") || entry.store}
        </span>
        {entry.tags.length > 0 && (
          <span className="truncate text-caption text-ink-muted">
            {entry.tags.join(", ")}
          </span>
        )}
      </span>
      {entry.rating !== null && <Rating value={entry.rating} />}
    </button>
  );
}

/** One entry over the whole screen: its image, what is said about it, and its files to look at. */
function EntryScreen({
  entry: ref,
  revision,
  onBack,
}: {
  entry: EntryRef;
  revision: number;
  onBack: () => void;
}) {
  const { read, error } = useEntry(ref, revision);
  const [viewer, setViewer] = useState<{
    files: Shown[];
    index: number;
  } | null>(null);
  const entry = read?.entry ?? null;
  const files: Shown[] = entry
    ? entry.files.map((file) => ({
        file: { ...file, store: entry.store, entry: entry.name },
        dimensions: read?.sizes[file.path] ?? null,
      }))
    : [];
  const url = entry?.url ?? null;
  const rows = (width: number): WindowRow[] =>
    wallLayout(files, width, WALL_ROW).map((row, index) => ({
      key: `${index}:${shownKey(row.tiles[0].shown)}`,
      height: row.height,
      render: () => (
        <WallRow
          row={row}
          isSelected={() => false}
          onSelect={(shown) =>
            setViewer({ files, index: files.indexOf(shown) })
          }
          onOpen={() => {}}
          onMenu={() => {}}
        />
      ),
    }));
  return (
    <div className="flex h-full flex-col">
      <header className="flex h-12 shrink-0 items-center gap-2 border-b border-line bg-panel px-2">
        <Button icon aria-label={TEXT.common.back} onClick={onBack}>
          <Icon name="chevron" className="rotate-90" size={20} />
        </Button>
        <h1 className="min-w-0 flex-1 truncate text-label">
          {entry ? shownName(entry) : ref.name}
        </h1>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {error ? (
          <Notice className="m-3">{error}</Notice>
        ) : entry === null ? (
          <div className="grid h-40 place-items-center">
            <LoadingMark size={24} />
          </div>
        ) : (
          <div className="flex flex-col gap-4 pb-6">
            {(entry.preview || entry.files.length > 0) && (
              <div className="aspect-video w-full overflow-hidden border-b border-line bg-field">
                <EntryCover
                  entry={entry}
                  size="large"
                  className="object-contain"
                />
              </div>
            )}
            <div className="flex flex-col gap-3 px-3">
              <div>
                <h2 className="text-title">{shownName(entry)}</h2>
                <p className="mono-annotation text-ink-muted">
                  {[entry.title && entry.name, entry.store]
                    .filter(Boolean)
                    .join("  ")}
                </p>
              </div>
              {entry.rating !== null && <Rating value={entry.rating} />}
              {url && (
                <div>
                  <Button
                    variant="secondary"
                    size="lg"
                    onClick={() => void app.openLink({ url })}
                  >
                    <Icon name="link-out" />
                    {TEXT.common.openSite(siteOf(url))}
                  </Button>
                </div>
              )}
              {entry.description && (
                <p className="whitespace-pre-wrap">{entry.description}</p>
              )}
              {entry.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {entry.tags.map((tag) => (
                    <Tag key={tag} tag={tag} />
                  ))}
                </div>
              )}
              {entry.notes && (
                <p className="whitespace-pre-wrap text-ink-muted">
                  {entry.notes}
                </p>
              )}
            </div>
            {files.length > 0 && (
              <section className="px-3">
                <h3 className="mb-2 text-label text-ink-muted">
                  {TEXT.count.files(files.length)}
                </h3>
                <Windowed rows={rows} />
              </section>
            )}
          </div>
        )}
      </div>
      {viewer && (
        <Viewer
          files={viewer.files}
          index={viewer.index}
          onIndex={(index) => setViewer({ ...viewer, index })}
          onClose={() => setViewer(null)}
        />
      )}
    </div>
  );
}

/** Adds a reference from the phone: a link, a name, tags, and photos taken or picked. */
function PhoneAdd({
  store,
  known,
  onAdded,
  onClose,
}: {
  store: string | null;
  known: { tag: string; count: number }[];
  onAdded: (entry: EntryRef) => void;
  onClose: () => void;
}) {
  const [url, setUrl] = useState("");
  const [name, setName] = useState<string | null>(null);
  const [tags, setTags] = useState<string[]>([]);
  const [photos, setPhotos] = useState<Outgoing[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const suggested = isLink(url)
    ? suggestName(url)
    : photos.length > 0
      ? cleanName(photos[0].path.replace(/\.[^.]+$/, ""))
      : "";
  const shown = name ?? suggested;
  const ready =
    store !== null &&
    shown.trim() !== "" &&
    (url.trim() === "" || isLink(url)) &&
    (url.trim() !== "" || photos.length > 0) &&
    !busy;
  const add = async () => {
    if (!ready || store === null) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const sources = photos.length > 0 ? await sendFiles(photos) : [];
      const entry = await addEntry({
        name: shown.trim(),
        url: url.trim() || undefined,
        tags: tags.length > 0 ? tags : undefined,
        files:
          sources.length > 0
            ? sources.map((source): NewFile => ({ source, move: true }))
            : undefined,
        store,
      });
      onAdded({ store: entry.store, name: entry.name });
      onClose();
    } catch (cause) {
      setBusy(false);
      setError(describe(cause));
    }
  };
  return (
    <Dialog open onOpenChange={(open) => !open && !busy && onClose()}>
      <DialogContent title={TEXT.common.addReference}>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void add();
          }}
          className="flex flex-col gap-4 overflow-y-auto p-4"
        >
          <div>
            <Label htmlFor="phone-link">{TEXT.fields.link.label}</Label>
            <Input
              id="phone-link"
              type="url"
              inputMode="url"
              value={url}
              placeholder={TEXT.fields.link.placeholder}
              onChange={(event) => setUrl(event.target.value)}
              className="h-9"
            />
          </div>
          <div>
            <Label htmlFor="phone-name">{TEXT.fields.name.label}</Label>
            <Input
              id="phone-name"
              value={shown}
              placeholder={TEXT.fields.name.example}
              onChange={(event) => setName(event.target.value)}
              className="h-9"
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
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="secondary"
              size="lg"
              onClick={() =>
                void chooseFiles("image/*").then((more) =>
                  setPhotos((was) => [...was, ...more]),
                )
              }
            >
              <Icon name="image" />
              {TEXT.narrow.photos}
            </Button>
            {photos.length > 0 && (
              <>
                <span className="text-ink-muted">
                  {TEXT.count.photos(photos.length)}
                </span>
                <Button onClick={() => setPhotos([])}>
                  {TEXT.common.clear}
                </Button>
              </>
            )}
          </div>
          {store === null && <Notice>{TEXT.stores.noneToAddTo}</Notice>}
          {busy && <ProgressBar />}
          {error && <Notice>{error}</Notice>}
          <button type="submit" hidden />
        </form>
        <DialogFooter>
          <span className="flex-1" />
          <Button size="lg" onClick={onClose} disabled={busy}>
            {TEXT.common.cancel}
          </Button>
          <Button
            variant="primary"
            size="lg"
            disabled={!ready}
            onClick={() => void add()}
          >
            {TEXT.common.add}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * The app on a phone: one column with the search box and the entries, an entry over the whole screen, and Add. It adds
 * and it views; changing things is for the wide layout.
 */
export function PhoneApp() {
  const [query, setQuery] = useState("");
  const [opened, setOpened] = useState<EntryRef | null>(null);
  const [adding, setAdding] = useState(false);
  const [revision, setRevision] = useState(0);
  const counts = useCounts(null, revision);
  const text = query.trim();
  const lists = usePaged<EntrySummary>(JSON.stringify({ text }), {
    all: async (after, limit) => {
      const page = text
        ? await searchEntries(text, {}, limit, after)
        : await listEntries({}, "created", true, limit, after);
      return { items: page.entries, total: page.total, after: page.after };
    },
  });
  const list = lists.list("all");
  useEffect(() => {
    lists.open("all");
  });
  useRefreshOnFocus(() => {
    setRevision((was) => was + 1);
    lists.refresh();
  });

  if (opened) {
    return (
      <div className="h-dvh bg-canvas text-ink">
        <EntryScreen
          entry={opened}
          revision={revision}
          onBack={() => setOpened(null)}
        />
      </div>
    );
  }
  const rows = (): WindowRow[] => [
    ...list.items.map((entry) => ({
      key: `${entry.store}/${entry.name}`,
      height: ROW_HEIGHT,
      render: () => (
        <EntryRow
          entry={entry}
          onOpen={() => setOpened({ store: entry.store, name: entry.name })}
        />
      ),
    })),
    ...(list.after !== null || list.loading || list.total === null || list.error
      ? [
          loaderRow(
            "all",
            list.loading || list.total === null,
            list.error,
            () => lists.more("all"),
            lists.refresh,
          ),
        ]
      : []),
  ];
  return (
    <div className="flex h-dvh flex-col bg-canvas text-ink">
      <header className="flex shrink-0 flex-col gap-2 border-b border-line bg-panel px-3 pt-2.5 pb-2">
        <div className="flex h-8 items-center justify-between">
          <Wordmark />
          <Button variant="primary" onClick={() => setAdding(true)}>
            <Icon name="add" />
            {TEXT.common.add}
          </Button>
        </div>
        <label className="flex h-9 items-center gap-2 rounded-sm border border-line-control bg-field px-2 focus-within:border-ink focus-within:bg-panel">
          <Icon name="search" className="text-ink-muted" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={TEXT.common.search}
            aria-label={TEXT.common.search}
            className="min-w-0 flex-1 bg-transparent outline-none placeholder:text-ink-muted"
          />
        </label>
      </header>
      <div className={cn("min-h-0 flex-1 overflow-y-auto bg-panel")}>
        {list.total === 0 ? (
          <div className="p-3">
            <EmptyState
              tile={<Icon name={text ? "search" : "folder"} size={24} />}
              tileClassName="bg-pastel-butter"
              title={text ? TEXT.list.nothingMatches : TEXT.list.nothingYet}
            />
          </div>
        ) : (
          <Windowed rows={rows} />
        )}
      </div>
      {adding && (
        <PhoneAdd
          store={startingStore(counts.stores)}
          known={counts.tags
            .filter((each) => each.entries > 0)
            .map(({ tag, entries }) => ({ tag, count: entries }))}
          onAdded={(entry) => {
            setRevision((was) => was + 1);
            lists.refresh();
            setOpened(entry);
          }}
          onClose={() => setAdding(false)}
        />
      )}
    </div>
  );
}
