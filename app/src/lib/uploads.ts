import { uploadPiece } from "@/lib/api";

// How much of a file goes up in one call, before base64 makes it a third longer, within what the server takes.
const PIECE_BYTES = 2 * 1024 * 1024;

/** A file to send, and where it goes under what was dropped: its name, or its path in a dropped folder. */
export type Outgoing = { file: File; path: string };

/** An id for the files sent together, which the server takes as 16 to 64 hex digits. */
export function newUploadId(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join(
    "",
  );
}

function base64(bytes: Uint8Array): string {
  let binary = "";
  // In runs, since a call takes only so many arguments.
  for (let at = 0; at < bytes.length; at += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(at, at + 0x8000));
  }
  return btoa(binary);
}

/**
 * Sends files in pieces under one upload, and returns the `source` of each thing at the top of what was sent: each
 * file, or each folder once for all the files in it. `onProgress` hears how many bytes went up of how many.
 */
export async function sendFiles(
  outgoing: Outgoing[],
  onProgress?: (sent: number, total: number) => void,
): Promise<string[]> {
  const upload = newUploadId();
  const total = outgoing.reduce((sum, each) => sum + each.file.size, 0);
  let sent = 0;
  const sources: string[] = [];
  for (const { file, path } of outgoing) {
    let source: string | null = null;
    const send = async (offset: number, piece: string) => {
      try {
        return await uploadPiece(upload, path, offset, piece);
      } catch {
        // A piece sent again lands where it did, so one lost on the way is sent once more.
        return await uploadPiece(upload, path, offset, piece);
      }
    };
    if (file.size === 0) {
      source = (await send(0, "")).source;
    }
    for (let offset = 0; offset < file.size; offset += PIECE_BYTES) {
      const bytes = new Uint8Array(
        await file.slice(offset, offset + PIECE_BYTES).arrayBuffer(),
      );
      source = (await send(offset, base64(bytes))).source;
      sent += bytes.length;
      onProgress?.(sent, total);
    }
    if (source !== null && !sources.includes(source)) {
      sources.push(source);
    }
  }
  return sources;
}

/** Reads what was dropped: files, and folders with everything in them, each with its path under what was dropped. */
export async function dropped(data: DataTransfer): Promise<Outgoing[]> {
  const entries = Array.from(data.items)
    .filter((item) => item.kind === "file")
    .map((item) => item.webkitGetAsEntry())
    .filter((entry): entry is FileSystemEntry => entry !== null);
  if (entries.length === 0) {
    return Array.from(data.files).map((file) => ({ file, path: file.name }));
  }
  const found: Outgoing[] = [];
  const walk = async (entry: FileSystemEntry, path: string): Promise<void> => {
    if (entry.isFile) {
      const file = await new Promise<File>((resolve, reject) =>
        (entry as FileSystemFileEntry).file(resolve, reject),
      );
      found.push({ file, path });
      return;
    }
    const reader = (entry as FileSystemDirectoryEntry).createReader();
    // A folder's reader hands its entries over in batches until one is empty.
    for (;;) {
      const batch = await new Promise<FileSystemEntry[]>((resolve, reject) =>
        reader.readEntries(resolve, reject),
      );
      if (batch.length === 0) {
        break;
      }
      for (const child of batch) {
        await walk(child, `${path}/${child.name}`);
      }
    }
  };
  for (const entry of entries) {
    await walk(entry, entry.name);
  }
  return found;
}

/** Lets the person pick files, from the computer or, on a phone, the camera. */
export function chooseFiles(accept?: string): Promise<Outgoing[]> {
  return new Promise((resolve) => {
    const input = document.createElement("input");
    input.type = "file";
    input.multiple = true;
    if (accept) {
      input.accept = accept;
    }
    input.addEventListener("change", () =>
      resolve(
        Array.from(input.files ?? []).map((file) => ({
          file,
          path: file.name,
        })),
      ),
    );
    input.addEventListener("cancel", () => resolve([]));
    input.click();
  });
}
