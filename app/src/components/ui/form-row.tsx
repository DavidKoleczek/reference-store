import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/** A control of a form beside its label. `off` says why it does not apply now, and greys the label. */
export function FormRow({
  label,
  off,
  children,
}: {
  label: string;
  off?: string;
  children: ReactNode;
}) {
  return (
    <div title={off} className="flex min-h-7 items-center gap-2">
      <span
        className={cn(
          "w-21 shrink-0 text-label",
          off ? "text-ink-faint" : "text-ink-muted",
        )}
      >
        {label}
      </span>
      <div className="flex min-w-0 flex-1 gap-1.5">{children}</div>
    </div>
  );
}
