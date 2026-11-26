import type { EntryFile, EntrySummary, Store } from "@/lib/api";
import { dimensions, formatSize, shownName } from "@/lib/format";
import { TEXT } from "@/lib/text";

/** The line along the bottom: what is picked, or how much the stores hold, then where it is. */
export function StatusBar({
  stores,
  total,
  entry,
  file,
  size,
  busy,
}: {
  stores: Store[];
  /** How many entries there are in every store. */
  total: number | null;
  /** The entry picked or open. */
  entry: EntrySummary | null;
  file: EntryFile | null;
  size: [number, number] | null;
  /** What the app is doing that takes a moment, such as sending files. */
  busy: string | null;
}) {
  const store = entry && stores.find((each) => each.name === entry.store);
  return (
    <footer className="flex h-7 shrink-0 items-center gap-4 overflow-hidden border-t border-line bg-panel px-3 mono-annotation whitespace-nowrap text-ink-muted">
      {entry ? (
        <>
          <span className="truncate text-ink">{shownName(entry)}</span>
          {file ? (
            <>
              <span className="truncate">{file.path}</span>
              {size && <span>{dimensions(size)}</span>}
              <span>{formatSize(file.size)}</span>
            </>
          ) : (
            entry.file_count > 0 && (
              <span>{TEXT.count.files(entry.file_count)}</span>
            )
          )}
        </>
      ) : (
        total !== null && (
          <span className="text-ink">{TEXT.count.entries(total)}</span>
        )
      )}
      <span className="flex-1" />
      {busy && <span className="text-ink">{busy}</span>}
      <span title={store?.path} className="truncate">
        {store ? store.path : TEXT.count.stores(stores.length)}
      </span>
    </footer>
  );
}
