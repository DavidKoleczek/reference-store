import type { Store } from "@/lib/api";
import { formatAgo } from "@/lib/format";
import { TEXT } from "@/lib/text";

/** The store an entry is added to unless another is picked: the project's, else the default. */
export function startingStore(stores: Store[]): string | null {
  const usable = stores.filter((store) => store.available && !store.read_only);
  return (
    (
      usable.find((store) => store.priority_order === 0) ??
      usable.find((store) => store.default) ??
      usable[0]
    )?.name ?? null
  );
}

/** Why a store's entries can't be changed, or null when they can. */
export function lockedBecause(store: Store | null): string | null {
  if (!store) {
    return null;
  }
  if (!store.available) {
    return TEXT.stores.lockedUnreachable(store.name);
  }
  if (store.read_only) {
    return TEXT.stores.lockedReadOnly(store.name);
  }
  return null;
}

/** What a store says beside its name: why it can't be used or changed, or how it keeps in step with GitHub. */
export function storeState(store: Store): {
  note: string | null;
  title: string;
} {
  if (!store.available) {
    return {
      note: TEXT.stores.offline,
      title: TEXT.stores.offlineTitle(store.location),
    };
  }
  if (store.sync_error) {
    return {
      note: TEXT.stores.syncFailed,
      title: TEXT.stores.syncFailedTitle(store.sync_error),
    };
  }
  const synced = store.synced
    ? TEXT.stores.synced(formatAgo(store.synced))
    : "";
  if (store.read_only) {
    return {
      note: TEXT.stores.readOnly,
      title: `${TEXT.stores.readOnlyTitle(store.location)} ${synced}`.trim(),
    };
  }
  if (store.priority_order === 0) {
    return {
      note: TEXT.stores.project,
      title: TEXT.stores.projectTitle(store.path),
    };
  }
  return {
    note: store.default ? TEXT.stores.default : null,
    title: [store.path, synced].filter(Boolean).join("\n"),
  };
}
