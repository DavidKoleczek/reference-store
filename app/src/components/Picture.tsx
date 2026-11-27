import type { ReactNode } from "react";

import { usePicture, type PictureKind } from "@/lib/pictures";
import { cn } from "@/lib/utils";

/**
 * An image read through the server: empty while it comes, and `fallback` when there is none or it can't be read, such
 * as a file that only has an image's name.
 */
export function Picture({
  uri,
  version,
  kind = "small",
  alt = "",
  fallback,
  className,
}: {
  uri: string | null;
  /** What changes when the image does, so a changed one is read again. */
  version: string;
  kind?: PictureKind;
  alt?: string;
  fallback?: ReactNode;
  className?: string;
}) {
  const { url, failed } = usePicture(uri, kind, version);
  if (uri === null || failed) {
    return fallback ?? null;
  }
  if (url === null) {
    return null;
  }
  return (
    <img
      src={url}
      alt={alt}
      draggable={false}
      decoding="async"
      className={cn("select-none", className)}
    />
  );
}
