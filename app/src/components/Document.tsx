import { useEffect, useState } from "react";

import { Markdown } from "@/components/ui/markdown";
import { Notice } from "@/components/ui/notice";
import { readText, type FileOf } from "@/lib/api";
import { describe } from "@/lib/errors";
import { fileName } from "@/lib/format";
import { TEXT } from "@/lib/text";

type Read = { key: string; text: string | null; error: string | null };

// A link followed in a page's frame would show the page the policy blocks in its place. Aimed at a new window, which
// the sandbox doesn't open, a click on one does nothing instead. It goes last, so a page's own base comes first.
const LINKS_STAY = '<base target="_blank">';

/**
 * A text file as read, again whenever `version` changes, which keeps showing what it was until then. Null while the
 * file is first read.
 */
function useText(file: FileOf, version: string): Read | null {
  const { store, entry, path } = file;
  const key = `${store}/${entry}/${path}`;
  const [read, setRead] = useState<Read | null>(null);
  useEffect(() => {
    let current = true;
    readText({ store, entry, path }).then(
      (text) => current && setRead({ key, text, error: null }),
      (cause: unknown) =>
        current && setRead({ key, text: null, error: describe(cause) }),
    );
    return () => {
      current = false;
    };
  }, [store, entry, path, key, version]);
  return read?.key === key ? read : null;
}

/** A text file read and shown: Markdown rendered, anything else as it is. */
export function Document({
  file,
  version,
}: {
  file: FileOf;
  /** What changes when the file does, so a changed one is read again. */
  version: string;
}) {
  const read = useText(file, version);
  if (read === null) {
    return null;
  }
  if (read.error !== null) {
    return <Notice title={TEXT.viewer.couldNotRead}>{read.error}</Notice>;
  }
  return file.path.toLowerCase().endsWith(".md") ? (
    <Markdown>{read.text ?? ""}</Markdown>
  ) : (
    <pre className="mono-value whitespace-pre-wrap">{read.text}</pre>
  );
}

/**
 * An HTML file drawn as a page over the whole of its box. Its frame runs none of its scripts, and keeps the view's
 * content security policy, so it loads nothing from elsewhere: only what the file holds itself shows.
 */
export function HtmlPage({ file, version }: { file: FileOf; version: string }) {
  const read = useText(file, version);
  if (read === null) {
    return null;
  }
  if (read.error !== null) {
    return (
      <div className="absolute inset-0 px-4 py-3">
        <Notice title={TEXT.viewer.couldNotRead}>{read.error}</Notice>
      </div>
    );
  }
  return (
    <iframe
      title={fileName(file)}
      sandbox=""
      srcDoc={`${read.text ?? ""}${LINKS_STAY}`}
      // A page draws on white unless it says otherwise, whatever the app's theme.
      className="absolute inset-0 size-full bg-[white]"
    />
  );
}
