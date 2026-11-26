import { useEffect, useState } from "react";

import { Markdown } from "@/components/ui/markdown";
import { Notice } from "@/components/ui/notice";
import { readText, type FileOf } from "@/lib/api";
import { describe } from "@/lib/errors";
import { TEXT } from "@/lib/text";

type Read = { key: string; text: string | null; error: string | null };

/** A text file read and shown: Markdown rendered, anything else as it is. */
export function Document({ file }: { file: FileOf }) {
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
  }, [store, entry, path, key]);
  if (read?.key !== key) {
    return null;
  }
  if (read.error !== null) {
    return <Notice title={TEXT.viewer.couldNotRead}>{read.error}</Notice>;
  }
  return path.toLowerCase().endsWith(".md") ? (
    <Markdown>{read.text ?? ""}</Markdown>
  ) : (
    <pre className="mono-value whitespace-pre-wrap">{read.text}</pre>
  );
}
