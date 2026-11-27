import { useEffect, useState } from "react";

import { readResource } from "@/lib/api";

/** Which copy of an image: a small or a large thumbnail, or the file itself, which only the large viewer reads. */
export type PictureKind = "small" | "large" | "file";

type Slot = {
  /** What changes when the image does, which the copy kept is of. */
  version: string;
  /** The data URL once read, or `FAILED`. */
  url: string | null;
  /** The copy read before the image changed, shown until this one is read. */
  stale: string | null;
  listeners: Set<(url: string) => void>;
  /** Takes it out of the queue while it waits there. */
  dequeue: (() => void) | null;
};

const FAILED = "";
// Small thumbnails are tens of kilobytes, so a few screens of them stay. The rest are large, so only the last few do.
const KEPT: Record<PictureKind, number> = { small: 600, large: 12, file: 4 };
// So the images on screen are read ahead of those that scrolled past, and the preview pane never waits behind them.
const SMALL_AT_ONCE = 6;

const slots: Record<PictureKind, Map<string, Slot>> = {
  small: new Map(),
  large: new Map(),
  file: new Map(),
};
let reading = 0;
const queue: (() => void)[] = [];

function next() {
  while (reading < SMALL_AT_ONCE && queue.length > 0) {
    queue.shift()?.();
  }
}

function read(uri: string, kind: PictureKind, slot: Slot) {
  const done = (url: string) => {
    slot.url = url;
    for (const listener of slot.listeners) {
      listener(url);
    }
    slot.listeners.clear();
  };
  const start = () => {
    slot.dequeue = null;
    if (kind === "small") {
      reading += 1;
    }
    readResource(uri)
      .then(
        ({ base64, mimeType }) => done(`data:${mimeType};base64,${base64}`),
        () => done(FAILED),
      )
      .finally(() => {
        if (kind === "small") {
          reading -= 1;
          next();
        }
      });
  };
  if (kind !== "small") {
    start();
    return;
  }
  queue.push(start);
  slot.dequeue = () => {
    const at = queue.indexOf(start);
    if (at >= 0) {
      queue.splice(at, 1);
    }
  };
  next();
}

/** Keeps a slot as the newest, letting the oldest go past what is kept. */
function keep(kind: PictureKind, uri: string, slot: Slot) {
  const kept = slots[kind];
  kept.delete(uri);
  kept.set(uri, slot);
  for (const [old, each] of kept) {
    if (kept.size <= KEPT[kind]) {
      break;
    }
    // One still being read for something on screen stays.
    if (each.url !== null || each.listeners.size === 0) {
      kept.delete(old);
    }
  }
}

/** The image if it was read, or the copy from before it changed, marking it the newest so it is the last to go. */
function peek(uri: string, kind: PictureKind): string | null {
  const kept = slots[kind];
  const slot = kept.get(uri);
  if (!slot) {
    return null;
  }
  kept.delete(uri);
  kept.set(uri, slot);
  return slot.url ?? slot.stale;
}

/**
 * Asks for an image as it is at `version`, which `listener` hears once it is read. The returned function says it is no
 * longer wanted, such as when its row scrolled away, which takes it out of the queue when it hasn't started.
 */
function want(
  uri: string,
  kind: PictureKind,
  version: string,
  listener: (url: string) => void,
): () => void {
  let slot = slots[kind].get(uri);
  if (!slot || slot.version !== version) {
    slot = {
      version,
      url: null,
      // A copy that failed has nothing to show in the meantime.
      stale: (slot?.url || slot?.stale) ?? null,
      listeners: new Set(),
      dequeue: null,
    };
    keep(kind, uri, slot);
    read(uri, kind, slot);
  }
  const held = slot;
  if (held.url !== null) {
    listener(held.url);
    return () => {};
  }
  held.listeners.add(listener);
  return () => {
    held.listeners.delete(listener);
    if (held.listeners.size === 0 && held.dequeue) {
      held.dequeue();
      // A newer version may have taken its place already.
      if (slots[kind].get(uri) === held) {
        slots[kind].delete(uri);
      }
    }
  };
}

/** Reads an image ahead of when it shows, such as the next one in the large viewer, or keeps it longer if it was read. */
export function readAhead(uri: string, kind: PictureKind, version: string) {
  peek(uri, kind);
  want(uri, kind, version, () => {});
}

/**
 * An image of the server's as a data URL, once it is read, or `failed` when it can't be. The view's content security
 * policy lets it load images from nowhere else.
 *
 * `version` is what changes when the image does, so a changed one is read again. The copy from before shows until it
 * is in.
 */
export function usePicture(
  uri: string | null,
  kind: PictureKind,
  version: string,
): { url: string | null; failed: boolean } {
  const [loaded, setLoaded] = useState<{ uri: string; url: string } | null>(
    null,
  );
  useEffect(() => {
    if (uri === null) {
      return;
    }
    return want(uri, kind, version, (url) => setLoaded({ uri, url }));
  }, [uri, kind, version]);
  if (uri === null) {
    return { url: null, failed: false };
  }
  const url = peek(uri, kind) ?? (loaded?.uri === uri ? loaded.url : null);
  return url === FAILED ? { url: null, failed: true } : { url, failed: false };
}
