import { Separator } from "react-resizable-panels";

import { cn } from "@/lib/utils";

const LIT =
  "data-[separator=active]:bg-accent-ink data-[separator=active]:shadow-[0_0_0_1px_var(--accent-ink)] data-[separator=focus]:bg-accent-ink data-[separator=focus]:shadow-[0_0_0_1px_var(--accent-ink)] data-[separator=hover]:bg-accent-ink data-[separator=hover]:shadow-[0_0_0_1px_var(--accent-ink)]";
const GRIP =
  "absolute hidden size-1.75 border border-accent-ink bg-panel group-data-[separator=active]/handle:block group-data-[separator=focus]/handle:block group-data-[separator=hover]/handle:block";

/**
 * The handle between two panes: a hairline at rest, accent ink with a square grip while hovered, dragged, or focused.
 * Double-click puts the pane back to its default size; arrow keys resize it when focused. `stacked` is for panes one
 * above the other, where the handle lies flat.
 */
export function ResizeHandle({
  label,
  stacked = false,
}: {
  label: string;
  stacked?: boolean;
}) {
  return (
    <Separator
      aria-label={label}
      className={cn(
        "group/handle relative z-10 shrink-0 bg-line outline-none",
        stacked ? "h-px" : "w-px",
        LIT,
      )}
    >
      <span
        className={cn(
          GRIP,
          stacked
            ? "-top-0.75 left-1/2 -translate-x-1/2"
            : "top-1/2 -left-0.75 -translate-y-1/2",
        )}
      />
    </Separator>
  );
}
