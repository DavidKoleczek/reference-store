import {
  useEffect,
  useRef,
  useState,
  type DragEvent,
  type ReactNode,
} from "react";
import {
  Group as PanelGroup,
  Panel,
  usePanelRef,
} from "react-resizable-panels";

import {
  EntryActions,
  FileActions,
  StoreActions,
  type Doing,
} from "@/components/Actions";
import { AddDialog, type Adding } from "@/components/AddDialog";
import { AddFilesDialog, type GoingIn } from "@/components/AddFilesDialog";
import { DetailsPane } from "@/components/DetailsPane";
import {
  AddStoreDialog,
  ConfirmDialog,
  MoveDialog,
  MoveFileDialog,
  StoreOrderDialog,
  TextDialog,
} from "@/components/Dialogs";
import { EntriesView } from "@/components/EntriesView";
import { EntryPage } from "@/components/EntryPage";
import { FiltersPane } from "@/components/FiltersPane";
import {
  FilesView,
  type FileColumnSort,
  type FileSection,
} from "@/components/FilesView";
import { loaderRow } from "@/components/rows";
import { SortMenu } from "@/components/SortMenu";
import { StatusBar } from "@/components/StatusBar";
import { TopBar, type Pane } from "@/components/TopBar";
import { Viewer } from "@/components/Viewer";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Icon } from "@/components/ui/icon";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuTrigger,
  MenuItem,
} from "@/components/ui/menu";
import { Notice } from "@/components/ui/notice";
import { LoadingMark } from "@/components/ui/loading-mark";
import { ResizeHandle } from "@/components/ui/resizable";
import { Segmented } from "@/components/ui/segmented";
import { Tooltip } from "@/components/ui/tooltip";
import {
  addEntry,
  addFiles,
  addStore,
  deleteEntry,
  deleteFile,
  escapeGlob,
  globFiles,
  imageSizes,
  listEntries,
  moveEntry,
  removeStore,
  renameEntry,
  renameFile,
  sameEntry,
  searchEntries,
  setDefaultStore,
  setStorePriority,
  showInFileManager,
  syncStore,
  updateEntry,
  updateFile,
  type Entry,
  type EntryChange,
  type EntryFile,
  type EntryFilters,
  type EntryRef,
  type EntrySummary,
  type FileChange,
  type NewFile,
  type Store,
} from "@/lib/api";
import {
  ENTRY_GROUPS,
  ENTRY_SORTS,
  FILE_SORTS,
  fileTagsOf,
  groupInEntry,
  IN_ENTRY_GROUPS,
  IN_ENTRY_SORTS,
  resorted,
  startsDescending,
  type InEntrySort,
  type Layout,
} from "@/lib/arrange";
import { describe } from "@/lib/errors";
import {
  hasTag,
  isFiltered,
  libraryFilters,
  NO_FILTERS,
  pickTag,
  type Filters,
} from "@/lib/filters";
import {
  fileName,
  formatCount,
  isImage,
  shownName,
  shownOf,
} from "@/lib/format";
import { groupSpecs } from "@/lib/groups";
import type { Shown } from "@/lib/layout";
import { isLink } from "@/lib/names";
import { lockedBecause as lockedOf } from "@/lib/stores";
import { app } from "@/lib/host";
import { useCounts, useEntry, type Read } from "@/lib/library";
import { usePaged, useRefreshOnFocus, type Page } from "@/lib/paging";
import { usePlaces } from "@/lib/places";
import { changeSettings, useSettings } from "@/lib/settings";
import { TEXT } from "@/lib/text";
import { chooseFiles, dropped, sendFiles, type Outgoing } from "@/lib/uploads";
import { cn } from "@/lib/utils";

const FILTERS = { min: 180 };
// `beside` is how wide Details is made when its preview goes beside its details and it is narrower.
const DETAILS = { min: 260, beside: 720 };
const MIDDLE_MIN = 360;
const SAID_FOR = 3500;
// How tall a row of pictures is: across every entry, and inside one, where there are fewer to get through.
const WALL_ROW = 148;
const ENTRY_ROW = 168;
const SEARCH_AFTER_MS = 250;

/** `value` once it has stayed the same for `ms`. */
function useSettled<Value>(value: Value, ms: number): Value {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), ms);
    return () => clearTimeout(timer);
  }, [value, ms]);
  return settled;
}

/** What is picked: an entry, or one of its files, with what is known of them until the entry is read. */
type Selection = {
  entry: EntryRef;
  summary: EntrySummary | null;
  file: string | null;
  /** The file as a list across entries had it. */
  shown: Shown | null;
};

/** What the right click menu is for. */
type MenuOn =
  | { kind: "entry"; entry: EntrySummary }
  | { kind: "file"; entry: EntryRef; file: EntryFile }
  | null;

/** A line the app says for a moment: something done, or something it couldn't do. */
type Said = { text: string; done: boolean };

type DialogState =
  | { kind: "add"; link: string }
  | { kind: "add-files"; entry: EntryRef; outgoing: Outgoing[] }
  | { kind: "rename"; entry: EntryRef }
  | { kind: "move"; entry: EntryRef }
  | { kind: "delete"; entry: EntryRef; title: string }
  | { kind: "rename-file"; entry: EntryRef; file: EntryFile }
  | { kind: "move-file"; entry: EntryRef; file: EntryFile }
  | { kind: "delete-file"; entry: EntryRef; file: EntryFile }
  | { kind: "remove-store"; store: Store }
  | { kind: "stores" }
  | { kind: "add-store" };

const LAYOUTS: { value: Layout; label: string; icon: "grid" | "list" }[] = [
  { value: "icons", label: TEXT.list.icons, icon: "grid" },
  { value: "details", label: TEXT.list.details, icon: "list" },
];

function typing(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable ||
      ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))
  );
}

function asShown(entry: Entry, file: EntryFile, read: Read | null): Shown {
  return {
    file: { ...file, store: entry.store, entry: entry.name },
    dimensions: read?.sizes[file.path] ?? null,
  };
}

/** Whether a file passes the file tags and the search, inside the entry that is open. */
function passes(file: EntryFile, filters: Filters): boolean {
  const query = filters.query.trim().toLowerCase();
  const tagged =
    filters.fileTags.length === 0 ||
    (filters.tagMatch === "any"
      ? filters.fileTags.some((tag) => hasTag(file.tags, tag))
      : filters.fileTags.every((tag) => hasTag(file.tags, tag)));
  return tagged && (!query || fileName(file).toLowerCase().includes(query));
}

/** The summary inside an entry that was read, which a list shows. */
function summaryOf(entry: Entry): EntrySummary {
  const summary: EntrySummary & Partial<Pick<Entry, "folder" | "files">> = {
    ...entry,
  };
  delete summary.folder;
  delete summary.files;
  return summary;
}

/** The whole app: filters, the entries or files that pass them, and details. */
export function Browser({ local }: { local: boolean }) {
  const settings = useSettings();
  const places = usePlaces(settings.place);
  const opened = places.place;
  const [filters, setFilters] = useState<Filters>(NO_FILTERS);
  const [revision, setRevision] = useState(0);
  const counts = useCounts(filters.store, revision);
  const open = useEntry(opened, revision);
  const [selection, setSelection] = useState<Selection | null>(null);
  const picked = useEntry(
    selection && !sameEntry(selection.entry, opened) ? selection.entry : null,
    revision,
  );
  const [menuOn, setMenuOn] = useState<MenuOn>(null);
  // The entry that was open stays picked once the list shows again, so it is easy to find among the others.
  const [placeShown, setPlaceShown] = useState(opened);
  if (JSON.stringify(placeShown) !== JSON.stringify(opened)) {
    setPlaceShown(opened);
    setSelection(
      placeShown && opened === null
        ? { entry: placeShown, summary: null, file: null, shown: null }
        : null,
    );
  }
  const [viewer, setViewer] = useState<{
    files: Shown[];
    index: number;
  } | null>(null);
  const [dialog, setDialog] = useState<DialogState | null>(null);
  const [said, setSaid] = useState<Said | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [openGroups, setOpenGroups] = useState<string[]>([]);
  const [dragging, setDragging] = useState(false);
  const search = useRef<HTMLInputElement>(null);
  const filtersPanel = usePanelRef();
  const detailsPanel = usePanelRef();
  // The sizes the panes start at. A panel registers again whenever its `defaultSize` changes, which ends a drag, so
  // the sizes saved while one is dragged can't be passed on every render.
  const [startingSizes] = useState(() => ({
    filters: settings.filtersPane.open ? settings.filtersPane.size : 0,
    details: settings.detailsPane.open ? settings.detailsPane.size : 0,
  }));

  // Read a moment after typing stops, rather than once for every key.
  const query = useSettled(filters.query.trim(), SEARCH_AFTER_MS);
  const base = libraryFilters(filters);
  const view = settings.view;
  const entriesAs = settings.entries;
  const filesAs = settings.files;
  const inEntryAs = settings.inEntry;

  const groups = groupSpecs(
    entriesAs.group,
    filters,
    counts.stores,
    counts.tags,
    counts.sites,
  );
  const readEntries =
    (extra: EntryFilters) =>
    async (
      after: string | null,
      limit: number,
    ): Promise<Page<EntrySummary>> => {
      const asked = { ...base, ...extra };
      const page = query
        ? await searchEntries(query, asked, limit, after)
        : await listEntries(
            asked,
            entriesAs.sort,
            entriesAs.descending,
            limit,
            after,
          );
      return { items: page.entries, total: page.total, after: page.after };
    };
  const entryLists = usePaged<EntrySummary>(
    JSON.stringify({
      base,
      query,
      sort: entriesAs.sort,
      descending: entriesAs.descending,
      group: entriesAs.group,
    }),
    Object.fromEntries(
      (groups ?? [{ key: "all", filters: {} }]).map((spec) => [
        spec.key,
        readEntries(spec.filters),
      ]),
    ),
  );

  const pattern = query ? `**/*${escapeGlob(query)}*` : "**";
  const readFiles = async (
    after: string | null,
    limit: number,
  ): Promise<Page<Shown>> => {
    const page = await globFiles(
      pattern,
      base,
      filesAs.sort,
      filesAs.descending,
      limit,
      after,
    );
    const images = page.files.filter(isImage);
    const sizes = images.length
      ? await imageSizes(
          images.map(({ store, entry, path }) => ({ store, entry, path })),
        )
      : [];
    const found = new Map(images.map((file, index) => [file, sizes[index]]));
    return {
      items: page.files.map((file) => ({
        file,
        dimensions: found.get(file) ?? null,
      })),
      total: page.total,
      after: page.after,
    };
  };
  const fileLists = usePaged<Shown>(
    JSON.stringify({
      base,
      pattern,
      sort: filesAs.sort,
      descending: filesAs.descending,
    }),
    { all: readFiles },
  );
  const acrossFiles = opened === null && view === "files";
  useEffect(() => {
    if (acrossFiles) {
      fileLists.open("all");
    }
  });

  const refresh = () => {
    setRevision((was) => was + 1);
    entryLists.refresh();
    fileLists.refresh();
  };
  useRefreshOnFocus(refresh);

  const say = (text: string, done = true) => setSaid({ text, done });
  const failed = (cause: unknown) => say(describe(cause), false);
  const storeNamed = (name: string) =>
    counts.stores.find((store) => store.name === name) ?? null;
  const lockedBecause = (name: string) => lockedOf(storeNamed(name));

  const openEntry: Read | null = open.read;
  const selectedEntryRead: Read | null =
    selection && sameEntry(selection.entry, opened) ? openEntry : picked.read;
  const detailsEntry: EntrySummary | null =
    selectedEntryRead?.entry ??
    selection?.summary ??
    (selection ? null : (openEntry?.entry ?? null));
  const detailsFull: Entry | null = selection
    ? (selectedEntryRead?.entry ?? null)
    : (openEntry?.entry ?? null);
  const detailsFile: EntryFile | null = selection?.file
    ? (detailsFull?.files.find((file) => file.path === selection.file) ??
      selection.shown?.file ??
      null)
    : null;
  const detailsSize: [number, number] | null = selection?.file
    ? (selectedEntryRead?.sizes[selection.file] ??
        selection.shown?.dimensions) ||
      null
    : null;

  /** Puts a changed entry in place wherever it shows, without reading the lists again. */
  const changed = (entry: Entry, was: EntryRef = entry) => {
    const summary = summaryOf(entry);
    entryLists.patch((item) => (sameEntry(item, was) ? summary : item));
    if (sameEntry(was, opened)) {
      open.set({ entry, sizes: openEntry?.sizes ?? {} });
    } else if (picked.read && sameEntry(was, picked.read.entry)) {
      picked.set({ entry, sizes: picked.read.sizes });
    }
    setSelection((now) =>
      now && sameEntry(now.entry, was)
        ? { ...now, entry: { store: entry.store, name: entry.name }, summary }
        : now,
    );
  };
  /** Counts again what a change may have changed, such as how many have a tag. */
  const recount = () => setRevision((was) => was + 1);

  const goTo = (entry: EntryRef | null) => {
    places.go(entry && { store: entry.store, name: entry.name });
    setSelection(null);
    // What was searched for found the entry, and inside it the search is of its files' names.
    if (entry !== null && opened === null && filters.query) {
      setFilters({ ...filters, query: "" });
    }
  };
  const back = () => {
    if (places.canGoBack) {
      places.back();
    } else if (opened !== null) {
      goTo(null);
    }
  };
  const showFile = (
    entry: EntryRef,
    file: EntryFile,
    among: Shown[] | null,
  ) => {
    const isIt = (each: Shown) =>
      each.file.path === file.path &&
      sameEntry({ store: each.file.store, name: each.file.entry }, entry);
    const list = among?.some(isIt) ? among : null;
    const files =
      list ??
      (openEntry && sameEntry(entry, opened)
        ? openEntry.entry.files.map((each) =>
            asShown(openEntry.entry, each, openEntry),
          )
        : [
            {
              file: { ...file, store: entry.store, entry: entry.name },
              dimensions: null,
            },
          ]);
    const index = Math.max(0, files.findIndex(isIt));
    setViewer({ files, index });
  };

  const saveEntry = (entry: EntryRef, change: EntryChange) =>
    updateEntry(entry.name, entry.store, change).then((now) => {
      changed(now);
      if (change.add_tags || change.remove_tags) {
        recount();
      }
    }, failed);
  const saveFile = (entry: EntryRef, path: string, change: FileChange) =>
    updateFile(entry.name, entry.store, path, change).then((now) => {
      changed(now);
      if (change.add_tags || change.remove_tags) {
        recount();
      }
    }, failed);

  /** Sends files, telling the status bar how it goes, and returns their sources. */
  const send = async (
    outgoing: Outgoing[],
    onProgress?: (sent: number, total: number) => void,
  ) => {
    try {
      return await sendFiles(outgoing, (sent, total) => {
        setBusy(
          TEXT.busy.sending(Math.round((100 * sent) / Math.max(1, total))),
        );
        onProgress?.(sent, total);
      });
    } finally {
      setBusy(null);
    }
  };

  const doing: Doing = {
    say,
    local,
    lockedBecause,
    openLink: (url) => void app.openLink({ url }),
    reveal: (store, entry, path) => {
      showInFileManager(store, entry, path).catch(failed);
    },
    open: (entry) => goTo(entry),
    rename: (entry) => setDialog({ kind: "rename", entry }),
    move: (entry) => setDialog({ kind: "move", entry }),
    remove: (entry) => setDialog({ kind: "delete", entry, title: entry.name }),
    addFiles: (entry) => {
      void chooseFiles().then((outgoing) => {
        if (outgoing.length > 0) {
          setDialog({ kind: "add-files", entry, outgoing });
        }
      });
    },
    choosePreview: (entry) => {
      void chooseFiles("image/*").then(async (outgoing) => {
        if (outgoing.length === 0) {
          return;
        }
        try {
          const [source] = await send(outgoing.slice(0, 1));
          await saveEntry(entry, { preview: { source } });
          say(TEXT.said.previewSet(entry.name));
        } catch (cause) {
          failed(cause);
        }
      });
    },
    clearPreview: (entry) => void saveEntry(entry, { preview: null }),
    usePreview: (entry, file) =>
      void saveEntry(entry, { preview: { file: file.path } }).then(() =>
        say(TEXT.said.previewUsed(fileName(file), entry.name)),
      ),
    viewFile: (entry, file) => showFile(entry, file, null),
    renameFile: (entry, file) =>
      setDialog({ kind: "rename-file", entry, file }),
    moveFile: (entry, file) => setDialog({ kind: "move-file", entry, file }),
    removeFile: (entry, file) =>
      setDialog({ kind: "delete-file", entry, file }),
    makeDefault: (store) =>
      void setDefaultStore(store.name).then(() => {
        say(TEXT.said.madeDefault(store.name));
        recount();
      }, failed),
    sync: (store) => {
      setBusy(TEXT.busy.syncing(store.name));
      syncStore(store.name)
        .then(([result]) => {
          if (result?.error) {
            say(TEXT.said.syncFailed(store.name, result.error), false);
          } else {
            say(
              TEXT.said.synced(
                store.name,
                result?.pulled ?? 0,
                result?.pushed ?? 0,
              ),
            );
          }
          refresh();
        }, failed)
        .finally(() => setBusy(null));
    },
    removeStore: (store) => setDialog({ kind: "remove-store", store }),
    arrangeStores: () => setDialog({ kind: "stores" }),
  };

  const add = async (
    { name, url, title, description, tags, store, files }: Adding,
    onProgress: (sent: number, total: number) => void,
  ) => {
    const sources = files.length > 0 ? await send(files, onProgress) : [];
    const entry = await addEntry({
      name,
      url: url || undefined,
      title: title || undefined,
      description: description || undefined,
      tags: tags.length > 0 ? tags : undefined,
      files:
        sources.length > 0
          ? sources.map((source): NewFile => ({ source, move: true }))
          : undefined,
      store,
    });
    say(TEXT.said.added(shownName(entry), entry.store));
    refresh();
    setSelection({
      entry: { store: entry.store, name: entry.name },
      summary: summaryOf(entry),
      file: null,
      shown: null,
    });
  };
  const addInto = async (
    entry: EntryRef,
    outgoing: Outgoing[],
    goingIn: GoingIn[],
    onProgress?: (sent: number, total: number) => void,
  ) => {
    const sources = await send(outgoing, onProgress);
    const about = new Map(goingIn.map((each) => [each.top, each]));
    const files = sources.map((source): NewFile => {
      const top = source.split(/[\\/]/).at(-1) ?? "";
      const said = about.get(top);
      return {
        source,
        move: true,
        description: said?.description || undefined,
        tags: said && said.tags.length > 0 ? said.tags : undefined,
      };
    });
    const now = await addFiles(entry.name, entry.store, files);
    changed(now);
    recount();
    say(TEXT.said.addedFiles(outgoing.length, entry.name));
  };

  // The view of the entry that is open: its files that pass the file tags and the search, in their groups.
  const inEntryFiles = openEntry
    ? openEntry.entry.files.filter((file) => passes(file, filters))
    : [];
  const inEntryGroups = openEntry ? groupInEntry(inEntryFiles, inEntryAs) : [];
  const inEntrySections: FileSection[] = openEntry
    ? inEntryGroups.map((group) => ({
        key: group.key,
        // An entry whose files are all at its top has one folder, which needs no line saying so.
        title:
          inEntryAs.group === "none" ||
          (inEntryAs.group === "folder" && inEntryGroups.length < 2)
            ? null
            : group.title,
        items: group.items.map((file) =>
          asShown(openEntry.entry, file, openEntry),
        ),
      }))
    : [];
  const acrossList = fileLists.list("all");
  const acrossSections: FileSection[] = (() => {
    const loader =
      acrossList.after !== null ||
      acrossList.loading ||
      acrossList.error !== null ||
      acrossList.total === null
        ? loaderRow(
            "files",
            acrossList.loading || acrossList.total === null,
            acrossList.error,
            () => fileLists.more("all"),
            fileLists.refresh,
          )
        : undefined;
    if (filesAs.sort !== "path") {
      return [{ key: "all", title: null, items: acrossList.items, loader }];
    }
    // In the order of their paths, the files come entry by entry, so each entry's run has its name over it.
    const runs: FileSection[] = [];
    for (const shown of acrossList.items) {
      const key = `${shown.file.store}/${shown.file.entry}`;
      const last = runs.at(-1);
      if (last && last.key === key) {
        last.items.push(shown);
      } else {
        const ref = { store: shown.file.store, name: shown.file.entry };
        runs.push({
          key,
          title: shown.file.entry,
          items: [shown],
          aside: (
            <Button
              size="sm"
              onClick={() => goTo(ref)}
              className="text-ink-muted"
            >
              {TEXT.common.open}
            </Button>
          ),
        });
      }
    }
    for (const run of runs) {
      run.count = formatCount(run.items.length);
    }
    if (runs.length === 0) {
      return [{ key: "all", title: null, items: [], loader }];
    }
    runs[runs.length - 1].loader = loader;
    return runs;
  })();
  const showing: Shown[] = openEntry
    ? inEntrySections.flatMap((section) => section.items)
    : acrossFiles
      ? acrossList.items
      : [];

  const isSelectedFile = (shown: Shown) =>
    selection !== null &&
    selection.file === shown.file.path &&
    sameEntry(selection.entry, {
      store: shown.file.store,
      name: shown.file.entry,
    });
  const pickFile = (shown: Shown) =>
    setSelection({
      entry: { store: shown.file.store, name: shown.file.entry },
      summary:
        openEntry &&
        sameEntry(openEntry.entry, {
          store: shown.file.store,
          name: shown.file.entry,
        })
          ? openEntry.entry
          : null,
      file: shown.file.path,
      shown,
    });
  const fileMenu = (shown: Shown) => {
    pickFile(shown);
    setMenuOn({
      kind: "file",
      entry: { store: shown.file.store, name: shown.file.entry },
      file: shown.file,
    });
  };

  const togglePane = (pane: Pane) => {
    const panel = (pane === "filters" ? filtersPanel : detailsPanel).current;
    if (panel?.isCollapsed()) {
      panel.expand();
    } else {
      panel?.collapse();
    }
  };
  const toggleBeside = () => {
    const panel = detailsPanel.current;
    if (
      !settings.beside &&
      panel &&
      panel.getSize().inPixels < DETAILS.beside
    ) {
      panel.resize(DETAILS.beside);
    }
    changeSettings({ beside: !settings.beside });
  };
  const setWidth = (list: string, column: string, width: number | null) =>
    changeSettings((now) => {
      const key = `${list}:${column}`;
      const rest = Object.fromEntries(
        Object.entries(now.widths).filter(([each]) => each !== key),
      );
      return { widths: width === null ? rest : { ...rest, [key]: width } };
    });
  const widthsOf = (list: string) =>
    Object.fromEntries(
      Object.entries(settings.widths)
        .filter(([key]) => key.startsWith(`${list}:`))
        .map(([key, width]) => [key.slice(list.length + 1), width]),
    );

  useEffect(() => {
    if (said === null) {
      return;
    }
    const timer = setTimeout(() => setSaid(null), SAID_FOR);
    return () => clearTimeout(timer);
  }, [said]);

  const blocked = viewer !== null || dialog !== null;
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (
        blocked ||
        typing(event.target) ||
        event.ctrlKey ||
        event.metaKey ||
        event.altKey
      ) {
        return;
      }
      if (event.key === "/") {
        event.preventDefault();
        search.current?.focus();
      } else if (event.key === "n") {
        event.preventDefault();
        setDialog({ kind: "add", link: "" });
      } else if (event.key === "[") {
        togglePane("filters");
      } else if (event.key === "]") {
        togglePane("details");
      } else if (event.key === "Escape") {
        if (selection !== null) {
          setSelection(null);
        } else if (opened !== null) {
          back();
        }
      }
    };
    const onPaste = (event: ClipboardEvent) => {
      const text = event.clipboardData?.getData("text").trim() ?? "";
      if (!blocked && !typing(event.target) && isLink(text)) {
        setDialog({ kind: "add", link: text });
      }
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("paste", onPaste);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("paste", onPaste);
    };
  });

  const showStore =
    filters.store === null &&
    entriesAs.group !== "store" &&
    counts.stores.length > 1;
  const entriesTotal = groups === null ? entryLists.list("all").total : null;
  const filesTotal = acrossList.total;
  const listedCount = acrossFiles
    ? filesTotal === null
      ? ""
      : TEXT.count.files(filesTotal)
    : entriesTotal === null
      ? groups !== null && counts.totals[filters.store ?? ""] !== undefined
        ? TEXT.count.entries(counts.totals[filters.store ?? ""])
        : ""
      : TEXT.count.entriesOf(entriesTotal, counts.totals[""] ?? entriesTotal);
  const nothing =
    (acrossFiles ? filesTotal === 0 : entriesTotal === 0) && groups === null;
  const searching = query !== "";
  const openLocked = opened ? lockedBecause(opened.store) : null;

  const onDrop = (event: DragEvent) => {
    event.preventDefault();
    setDragging(false);
    if (!opened || openLocked) {
      if (openLocked) {
        say(openLocked, false);
      }
      return;
    }
    const target = opened;
    void dropped(event.dataTransfer).then((outgoing) => {
      if (outgoing.length > 0) {
        setDialog({ kind: "add-files", entry: target, outgoing });
      }
    });
  };

  const listHeader = (
    <>
      <h2 className="shrink-0 text-label">{TEXT.list.title}</h2>
      <span className="min-w-0 flex-1 truncate mono-annotation text-ink-muted">
        {listedCount}
      </span>
      <Segmented
        label={TEXT.list.show}
        value={view}
        onChange={(next) => {
          changeSettings({ view: next });
          setSelection(null);
        }}
        options={[
          { value: "entries", label: TEXT.list.entries },
          { value: "files", label: TEXT.list.files },
        ]}
      />
    </>
  );
  const fixed = searching
    ? acrossFiles
      ? undefined
      : TEXT.sort.whileSearching
    : undefined;
  const arrangeControls: ReactNode = opened ? (
    openEntry &&
    openEntry.entry.files.length > 0 && (
      <>
        <Segmented
          label={TEXT.list.layout}
          value={inEntryAs.layout}
          onChange={(layout) =>
            changeSettings({ inEntry: { ...inEntryAs, layout } })
          }
          options={LAYOUTS}
        />
        <SortMenu
          sort={inEntryAs.sort}
          descending={inEntryAs.descending}
          group={inEntryAs.group}
          sorts={IN_ENTRY_SORTS}
          groups={IN_ENTRY_GROUPS}
          onSort={(sort) =>
            changeSettings({
              inEntry: {
                ...inEntryAs,
                sort,
                descending: startsDescending(sort),
              },
            })
          }
          onDescending={(descending) =>
            changeSettings({ inEntry: { ...inEntryAs, descending } })
          }
          onGroup={(group) =>
            changeSettings({ inEntry: { ...inEntryAs, group } })
          }
        />
      </>
    )
  ) : view === "files" ? (
    <>
      <Segmented
        label={TEXT.list.layout}
        value={filesAs.layout}
        onChange={(layout) => changeSettings({ files: { ...filesAs, layout } })}
        options={LAYOUTS}
      />
      <SortMenu
        sort={filesAs.sort}
        descending={filesAs.descending}
        sorts={FILE_SORTS}
        onSort={(sort) =>
          changeSettings({
            files: { ...filesAs, sort, descending: startsDescending(sort) },
          })
        }
        onDescending={(descending) =>
          changeSettings({ files: { ...filesAs, descending } })
        }
      />
    </>
  ) : (
    <>
      <Segmented
        label={TEXT.list.layout}
        value={entriesAs.layout}
        onChange={(layout) =>
          changeSettings({ entries: { ...entriesAs, layout } })
        }
        options={LAYOUTS}
      />
      <SortMenu
        sort={searching ? "name" : entriesAs.sort}
        descending={searching ? false : entriesAs.descending}
        group={entriesAs.group}
        sorts={ENTRY_SORTS}
        groups={ENTRY_GROUPS}
        fixed={fixed}
        onSort={(sort) =>
          changeSettings({
            entries: { ...entriesAs, sort, descending: startsDescending(sort) },
          })
        }
        onDescending={(descending) =>
          changeSettings({ entries: { ...entriesAs, descending } })
        }
        onGroup={(group) => {
          changeSettings({ entries: { ...entriesAs, group } });
          setOpenGroups([]);
        }}
      />
    </>
  );

  const emptyList = (
    <div className="grid h-full place-items-center bg-canvas p-3">
      {isFiltered(filters) ? (
        <EmptyState
          tile={<Icon name="search" size={24} />}
          tileClassName="bg-pastel-butter"
          title={TEXT.list.tryFewerFilters}
          action={
            <Button
              variant="secondary"
              size="lg"
              onClick={() => setFilters(NO_FILTERS)}
              className="mt-2"
            >
              {TEXT.list.clearFilters}
            </Button>
          }
          className="w-full max-w-sm"
        />
      ) : (
        <EmptyState
          tile={<Icon name="folder" size={24} />}
          tileClassName="bg-pastel-butter"
          title={
            counts.stores.length === 0
              ? TEXT.list.noStores
              : TEXT.list.nothingYet
          }
          action={
            counts.stores.length === 0 ? (
              local && (
                <Button
                  variant="secondary"
                  size="lg"
                  onClick={() => setDialog({ kind: "add-store" })}
                  className="mt-2"
                >
                  {TEXT.common.addStore}
                </Button>
              )
            ) : (
              <Button
                variant="secondary"
                size="lg"
                onClick={() => setDialog({ kind: "add", link: "" })}
                className="mt-2"
              >
                {TEXT.common.addReference}
              </Button>
            )
          }
          className="w-full max-w-sm"
        />
      )}
    </div>
  );
  // A list sits on the panel, as rows do everywhere else. Pictures sit on the canvas.
  const ground = (layout: Layout) =>
    layout === "details" ? "bg-panel" : "bg-canvas";
  const menuEntrySummary = menuOn?.kind === "entry" ? menuOn.entry : null;

  return (
    <div className="flex h-screen flex-col bg-canvas text-ink">
      <TopBar
        query={filters.query}
        onQuery={(next) => setFilters({ ...filters, query: next })}
        placeholder={
          opened || acrossFiles
            ? TEXT.topBar.searchFiles
            : TEXT.topBar.searchEntries
        }
        search={search}
        panes={{
          filters: settings.filtersPane.open,
          details: settings.detailsPane.open,
        }}
        onTogglePane={togglePane}
        onAdd={() => setDialog({ kind: "add", link: "" })}
        onRefresh={() => {
          refresh();
          say(TEXT.said.refreshed);
        }}
      />
      {counts.error && (
        <Notice className="m-2 mb-0" onDismiss={refresh}>
          {counts.error}
        </Notice>
      )}
      <PanelGroup orientation="horizontal" className="min-h-0 flex-1">
        <Panel
          id="filters"
          panelRef={filtersPanel}
          collapsible
          collapsedSize={0}
          minSize={FILTERS.min}
          defaultSize={startingSizes.filters}
          groupResizeBehavior="preserve-pixel-size"
          onResize={(size) =>
            changeSettings((now) => ({
              filtersPane: {
                open: size.inPixels > 0,
                size:
                  size.inPixels > 0
                    ? Math.round(size.inPixels)
                    : now.filtersPane.size,
              },
            }))
          }
          className="h-full"
        >
          <FiltersPane
            stores={counts.stores}
            totals={counts.totals}
            sites={counts.sites}
            tags={counts.tags}
            filters={filters}
            onFilters={(next) => {
              setFilters(next);
              if (
                opened &&
                (next.store !== filters.store ||
                  next.tags !== filters.tags ||
                  next.sites !== filters.sites)
              ) {
                goTo(null);
              }
            }}
            sections={settings.sections}
            onSections={(sections) => changeSettings({ sections })}
            onManageStores={() => setDialog({ kind: "stores" })}
            storeMenu={(store) => <StoreActions store={store} doing={doing} />}
          />
        </Panel>
        <ResizeHandle label={TEXT.panes.resizeFilters} />
        <Panel id="middle" minSize={MIDDLE_MIN} className="h-full">
          <section className="flex h-full min-w-0 flex-col">
            <header className="flex h-10 shrink-0 items-center gap-2 border-b border-line bg-panel pr-2 pl-3">
              {opened ? (
                <>
                  <Tooltip content={TEXT.common.back} keys="Esc">
                    <Button
                      size="sm"
                      icon
                      aria-label={TEXT.common.back}
                      onClick={back}
                      className="-ml-1"
                    >
                      <Icon name="chevron" className="rotate-90" />
                    </Button>
                  </Tooltip>
                  <button
                    type="button"
                    onClick={() => goTo(null)}
                    className="shrink-0 cursor-default rounded-sm text-label text-ink-muted outline-none hover:text-ink focus-visible:focus-ring"
                  >
                    {TEXT.list.title}
                  </button>
                  <span aria-hidden className="text-ink-faint">
                    /
                  </span>
                  <h2 className="min-w-0 truncate text-label">
                    {openEntry ? shownName(openEntry.entry) : opened.name}
                  </h2>
                  {openEntry && openEntry.entry.files.length > 0 && (
                    <span className="shrink-0 mono-annotation text-ink-muted">
                      {shownOf(
                        inEntryFiles.length,
                        openEntry.entry.files.length,
                      )}
                    </span>
                  )}
                  <span className="flex-1" />
                </>
              ) : (
                listHeader
              )}
              {arrangeControls}
            </header>
            <ContextMenu>
              <ContextMenuTrigger
                // On the way down, so what was right clicked says so after this clears what the last menu was for.
                onContextMenuCapture={() => setMenuOn(null)}
                className="relative min-h-0 flex-1"
              >
                {opened && (
                  <div
                    onDragOver={(event) => {
                      event.preventDefault();
                      setDragging(true);
                    }}
                    onDragLeave={() => setDragging(false)}
                    onDrop={onDrop}
                    className={cn(
                      "absolute inset-0 overflow-auto",
                      ground(
                        openEntry && openEntry.entry.files.length > 0
                          ? inEntryAs.layout
                          : "icons",
                      ),
                      dragging &&
                        "outline-2 -outline-offset-4 outline-accent-ink",
                    )}
                  >
                    {openEntry ? (
                      <EntryPage
                        entry={openEntry.entry}
                        shown={inEntryFiles.length}
                        fileTags={filters.fileTags}
                        onFileTags={(fileTags) =>
                          setFilters({ ...filters, fileTags })
                        }
                        onShowAll={() =>
                          setFilters({ ...filters, fileTags: [], query: "" })
                        }
                        onOpenLink={doing.openLink}
                      >
                        <FilesView
                          sections={inEntrySections}
                          layout={inEntryAs.layout}
                          inEntry
                          rowHeight={ENTRY_ROW}
                          sort={inEntryAs.sort}
                          descending={inEntryAs.descending}
                          onSort={(sort) => {
                            if (sort !== "path") {
                              changeSettings({
                                inEntry: resorted(
                                  inEntryAs,
                                  sort as InEntrySort,
                                ),
                              });
                            }
                          }}
                          widths={widthsOf("entry")}
                          onWidth={(column, width) =>
                            setWidth("entry", column, width)
                          }
                          isSelected={isSelectedFile}
                          onSelect={pickFile}
                          onOpen={(shown) =>
                            showFile(
                              {
                                store: shown.file.store,
                                name: shown.file.entry,
                              },
                              shown.file,
                              showing,
                            )
                          }
                          onMenu={fileMenu}
                        />
                      </EntryPage>
                    ) : open.error ? (
                      <div className="p-3">
                        <Notice title={TEXT.entry.couldNotOpen(opened.name)}>
                          {open.error}{" "}
                          <button
                            type="button"
                            onClick={() => goTo(null)}
                            className="text-accent-ink underline underline-offset-2"
                          >
                            {TEXT.entry.backToReferences}
                          </button>
                        </Notice>
                      </div>
                    ) : (
                      <div className="grid h-full place-items-center">
                        <LoadingMark size={24} />
                      </div>
                    )}
                  </div>
                )}
                {/* Kept while an entry is open, so going back finds it scrolled to where it was. */}
                <div
                  className={cn(
                    "absolute inset-0 overflow-auto",
                    ground(
                      view === "files" ? filesAs.layout : entriesAs.layout,
                    ),
                    opened && "invisible",
                  )}
                >
                  {nothing ? (
                    emptyList
                  ) : view === "entries" ? (
                    <EntriesView
                      lists={entryLists}
                      groups={groups}
                      opened={openGroups}
                      onToggleGroup={(key) =>
                        setOpenGroups((was) =>
                          was.includes(key)
                            ? was.filter((each) => each !== key)
                            : [...was, key],
                        )
                      }
                      arrangement={entriesAs}
                      sortable={!searching}
                      onSort={(sort) =>
                        !searching &&
                        changeSettings({ entries: resorted(entriesAs, sort) })
                      }
                      widths={widthsOf("entries")}
                      onWidth={(column, width) =>
                        setWidth("entries", column, width)
                      }
                      selected={
                        selection && selection.file === null
                          ? selection.entry
                          : null
                      }
                      showStore={showStore}
                      canChange={(entry) => lockedBecause(entry.store) === null}
                      onSelect={(entry) =>
                        setSelection({
                          entry: { store: entry.store, name: entry.name },
                          summary: entry,
                          file: null,
                          shown: null,
                        })
                      }
                      onOpen={(entry) => goTo(entry)}
                      onMenu={(entry) => {
                        setSelection({
                          entry: { store: entry.store, name: entry.name },
                          summary: entry,
                          file: null,
                          shown: null,
                        });
                        setMenuOn({ kind: "entry", entry });
                      }}
                      onRate={(entry, rating) =>
                        void saveEntry(entry, { rating })
                      }
                    />
                  ) : (
                    <FilesView
                      sections={acrossSections}
                      layout={filesAs.layout}
                      inEntry={false}
                      rowHeight={WALL_ROW}
                      sort={filesAs.sort}
                      descending={filesAs.descending}
                      onSort={(sort: FileColumnSort) => {
                        if (sort !== "tags") {
                          changeSettings({ files: resorted(filesAs, sort) });
                        }
                      }}
                      widths={widthsOf("files")}
                      onWidth={(column, width) =>
                        setWidth("files", column, width)
                      }
                      isSelected={isSelectedFile}
                      onSelect={pickFile}
                      onOpen={(shown) =>
                        showFile(
                          { store: shown.file.store, name: shown.file.entry },
                          shown.file,
                          showing,
                        )
                      }
                      onMenu={fileMenu}
                    />
                  )}
                </div>
              </ContextMenuTrigger>
              <ContextMenuContent>
                {menuOn?.kind === "file" ? (
                  <FileActions
                    entry={menuOn.entry}
                    file={menuOn.file}
                    showOpenEntry={!sameEntry(menuOn.entry, opened)}
                    doing={doing}
                  />
                ) : menuEntrySummary ? (
                  <EntryActions
                    entry={menuEntrySummary}
                    folder={null}
                    showOpen
                    doing={doing}
                  />
                ) : (
                  <>
                    <MenuItem
                      onClick={() => setDialog({ kind: "add", link: "" })}
                    >
                      <Icon name="add" />
                      {TEXT.common.addReference}
                    </MenuItem>
                    {openEntry && (
                      <EntryActions
                        entry={openEntry.entry}
                        folder={openEntry.entry.folder}
                        showOpen={false}
                        doing={doing}
                      />
                    )}
                  </>
                )}
              </ContextMenuContent>
            </ContextMenu>
          </section>
        </Panel>
        <ResizeHandle label={TEXT.panes.resizeDetails} />
        <Panel
          id="details"
          panelRef={detailsPanel}
          collapsible
          collapsedSize={0}
          minSize={DETAILS.min}
          defaultSize={startingSizes.details}
          groupResizeBehavior="preserve-pixel-size"
          onResize={(size) =>
            changeSettings((now) => ({
              detailsPane: {
                open: size.inPixels > 0,
                size:
                  size.inPixels > 0
                    ? Math.round(size.inPixels)
                    : now.detailsPane.size,
              },
            }))
          }
          className="h-full"
        >
          <DetailsPane
            entry={detailsEntry}
            full={detailsFull}
            file={detailsFile}
            size={detailsSize}
            open={detailsEntry !== null && sameEntry(detailsEntry, opened)}
            beside={settings.beside}
            onBeside={toggleBeside}
            tags={counts.tags
              .filter((each) => each.entries > 0)
              .map(({ tag, entries }) => ({ tag, count: entries }))}
            fileTags={
              openEntry
                ? fileTagsOf(openEntry.entry)
                : counts.tags
                    .filter((each) => each.files > 0)
                    .map(({ tag, files }) => ({ tag, count: files }))
            }
            activeTags={filters.tags}
            activeFileTags={filters.fileTags}
            onFilterTag={(tag, several) => {
              setFilters({
                ...filters,
                tags: pickTag(filters.tags, tag, several),
              });
              if (opened) {
                goTo(null);
              }
            }}
            onFilterFileTag={(tag, several) =>
              setFilters({
                ...filters,
                fileTags: pickTag(filters.fileTags, tag, several),
              })
            }
            onEntry={(change) =>
              detailsEntry && void saveEntry(detailsEntry, change)
            }
            onFile={(change) =>
              detailsEntry &&
              detailsFile &&
              void saveFile(detailsEntry, detailsFile.path, change)
            }
            onView={() =>
              detailsEntry &&
              detailsFile &&
              showFile(detailsEntry, detailsFile, showing)
            }
            doing={doing}
          />
        </Panel>
      </PanelGroup>
      <StatusBar
        stores={counts.stores}
        total={counts.totals[""] ?? null}
        entry={detailsEntry}
        file={detailsFile}
        size={detailsSize}
        busy={busy}
      />
      {viewer && (
        <Viewer
          files={viewer.files}
          index={viewer.index}
          onIndex={(index) => {
            setViewer({ ...viewer, index });
            const now = viewer.files[index];
            if (now) {
              pickFile(now);
            }
          }}
          onClose={() => setViewer(null)}
        />
      )}
      {dialog && renderDialog()}
      {said !== null && (
        <Notice
          tone="neutral"
          icon={said.done ? "check" : "warning"}
          onDismiss={() => setSaid(null)}
          className="fixed bottom-10 left-1/2 z-60 w-max max-w-[90vw] -translate-x-1/2 bg-raised shadow-popover"
        >
          {said.text}
        </Notice>
      )}
    </div>
  );

  function renderDialog(): ReactNode {
    const close = () => setDialog(null);
    const known = counts.tags
      .filter((each) => each.files > 0)
      .map(({ tag, files }) => ({ tag, count: files }));
    switch (dialog?.kind) {
      case "add":
        return (
          <AddDialog
            link={dialog.link}
            stores={counts.stores}
            known={counts.tags
              .filter((each) => each.entries > 0)
              .map(({ tag, entries }) => ({ tag, count: entries }))}
            onAdd={add}
            onClose={close}
          />
        );
      case "add-files": {
        const target = dialog.entry;
        return (
          <AddFilesDialog
            entry={target.name}
            outgoing={dialog.outgoing}
            known={known}
            onAdd={(goingIn, onProgress) =>
              addInto(target, dialog.outgoing, goingIn, onProgress)
            }
            onClose={close}
          />
        );
      }
      case "rename": {
        const target = dialog.entry;
        return (
          <TextDialog
            title={TEXT.dialogs.rename.title(target.name)}
            label={TEXT.fields.name.label}
            initial={target.name}
            hint={TEXT.fields.name.help}
            action={TEXT.common.rename}
            onSubmit={async (name) => {
              const now = await renameEntry(target.name, target.store, name);
              changed(now, target);
              if (sameEntry(target, opened)) {
                places.replace({ store: now.store, name: now.name });
              }
              say(TEXT.said.renamed(now.name));
            }}
            onClose={close}
          />
        );
      }
      case "move": {
        const target = dialog.entry;
        return (
          <MoveDialog
            name={target.name}
            from={target.store}
            stores={counts.stores}
            onSubmit={async (to) => {
              const now = await moveEntry(target.name, target.store, to);
              if (sameEntry(target, opened)) {
                places.replace({ store: now.store, name: now.name });
              }
              setSelection(null);
              refresh();
              say(TEXT.said.moved(now.name, now.store));
            }}
            onClose={close}
          />
        );
      }
      case "delete": {
        const target = dialog.entry;
        return (
          <ConfirmDialog
            title={TEXT.dialogs.delete.title(target.name)}
            action={TEXT.common.delete}
            onConfirm={async () => {
              await deleteEntry(target.name, target.store);
              entryLists.patch((item) =>
                sameEntry(item, target) ? null : item,
              );
              setSelection(null);
              if (sameEntry(target, opened)) {
                goTo(null);
              }
              recount();
              say(TEXT.said.deleted(target.name));
            }}
            onClose={close}
          >
            <p>{TEXT.dialogs.delete.entry(target.store)}</p>
          </ConfirmDialog>
        );
      }
      case "rename-file": {
        const { entry, file } = dialog;
        return (
          <TextDialog
            title={TEXT.dialogs.rename.title(fileName(file))}
            label={TEXT.dialogs.renameFile.label}
            initial={file.path}
            hint={TEXT.dialogs.renameFile.help}
            action={TEXT.common.rename}
            onSubmit={async (path) => {
              const now = await renameFile(
                entry.name,
                entry.store,
                file.path,
                path,
              );
              changed(now);
              setSelection((was) =>
                was && was.file === file.path
                  ? { ...was, file: path, shown: null }
                  : was,
              );
              refresh();
            }}
            onClose={close}
          />
        );
      }
      case "move-file": {
        const { entry, file } = dialog;
        return (
          <MoveFileDialog
            file={fileName(file)}
            store={entry.store}
            stores={counts.stores}
            onSubmit={async (to, store) => {
              await addFiles(to, store, [
                {
                  source: file.full_path,
                  path: file.path,
                  description: file.description || undefined,
                  notes: file.notes || undefined,
                  tags: file.tags.length > 0 ? file.tags : undefined,
                },
              ]);
              const now = await deleteFile(entry.name, entry.store, file.path);
              changed(now);
              setSelection(null);
              refresh();
              say(TEXT.said.moved(fileName(file), to));
            }}
            onClose={close}
          />
        );
      }
      case "delete-file": {
        const { entry, file } = dialog;
        return (
          <ConfirmDialog
            title={TEXT.dialogs.delete.title(fileName(file))}
            action={TEXT.common.delete}
            onConfirm={async () => {
              const now = await deleteFile(entry.name, entry.store, file.path);
              changed(now);
              setSelection(null);
              fileLists.refresh();
              recount();
              say(TEXT.said.deleted(fileName(file)));
            }}
            onClose={close}
          >
            <p>{TEXT.dialogs.delete.file(file.path, entry.name)}</p>
          </ConfirmDialog>
        );
      }
      case "remove-store": {
        const store = dialog.store;
        return (
          <ConfirmDialog
            title={TEXT.dialogs.removeStore.title(store.name)}
            action={TEXT.common.remove}
            onConfirm={async () => {
              await removeStore(store.name);
              if (filters.store === store.name) {
                setFilters({ ...filters, store: null });
              }
              refresh();
              say(TEXT.said.removedStore(store.name));
            }}
            onClose={close}
          >
            <p>
              {store.kind === "github"
                ? TEXT.dialogs.removeStore.github
                : TEXT.dialogs.removeStore.folder(store.path)}
            </p>
          </ConfirmDialog>
        );
      }
      case "stores":
        return (
          <StoreOrderDialog
            stores={counts.stores}
            onMove={async (store, place) => {
              await setStorePriority(store, place);
              recount();
            }}
            onAdd={local ? () => setDialog({ kind: "add-store" }) : undefined}
            onClose={close}
          />
        );
      case "add-store":
        return (
          <AddStoreDialog
            onSubmit={async (name, location, push) => {
              setBusy(TEXT.busy.adding(name));
              try {
                await addStore(name, location, false, push);
              } finally {
                setBusy(null);
              }
              refresh();
              say(TEXT.said.addedStore(name));
            }}
            onClose={close}
          />
        );
      default:
        return null;
    }
  }
}
