import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icon";
import { TEXT } from "@/lib/text";
import { copyText } from "@/lib/utils";

/** Puts a path on the clipboard, to hand to an agent or paste into another tool. */
export function CopyPath({
  path,
  label = TEXT.menu.copyPath,
  variant = "secondary",
  size = "md",
}: {
  path: string;
  label?: string;
  variant?: "secondary" | "ghost";
  size?: "sm" | "md";
}) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      variant={variant}
      size={size}
      onClick={async () => {
        if (await copyText(path)) {
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        }
      }}
    >
      <Icon name={copied ? "check" : "copy"} />
      {copied ? TEXT.common.copied : label}
    </Button>
  );
}

/** A path in mono, cut at its start so the end, which tells it apart, always shows. */
export function PathLine({ path }: { path: string }) {
  return (
    <p
      title={path}
      dir="rtl"
      className="truncate rounded-sm border border-line bg-field px-2 py-1 text-left mono-value text-ink-muted"
    >
      {/* The mark keeps a path's punctuation in place while the line reads right to left. */}
      <bdi>{path}</bdi>
    </p>
  );
}
