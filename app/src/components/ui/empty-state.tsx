import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

const CORNERS = [
  "top-0 left-0 border-t border-l",
  "top-0 right-0 border-t border-r",
  "bottom-0 left-0 border-b border-l",
  "right-0 bottom-0 border-r border-b",
];

/** Crop marks in the corners of the nearest positioned ancestor, framing where something will go. */
export function CropMarks() {
  return CORNERS.map((corner) => (
    <span
      key={corner}
      aria-hidden
      className={cn(
        "pointer-events-none absolute size-4 border-line-control",
        corner,
      )}
    />
  ));
}

/**
 * An invitation for a place with nothing in it yet, on the canvas with crop marks and one pastel tile. Never for an
 * error; those are notices.
 */
export function EmptyState({
  tile,
  tileClassName,
  title,
  action,
  className,
}: {
  tile: ReactNode;
  tileClassName: string;
  title: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "relative flex flex-col items-center justify-center gap-2 bg-canvas px-6 py-8 text-center",
        className,
      )}
    >
      <CropMarks />
      <div
        className={cn(
          "my-2 grid size-16 place-items-center rounded-xl text-on-pastel",
          tileClassName,
        )}
      >
        {tile}
      </div>
      <p className="text-title">{title}</p>
      {action}
    </div>
  );
}
