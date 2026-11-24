import type { ReactNode } from "react";

import { Icon } from "@/components/ui/icon";
import { cn } from "@/lib/utils";

/** A part of a pane that opens and closes under its title, with whatever sits at the right of its header. */
export function Section({
  title,
  open,
  onOpenChange,
  aside,
  className,
  children,
}: {
  title: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  aside?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className={cn("border-b border-line", className)}>
      <header className="flex h-8 items-center gap-2 pr-2 pl-3">
        <button
          type="button"
          aria-expanded={open}
          onClick={() => onOpenChange(!open)}
          className="-ml-1 flex h-full min-w-0 flex-1 cursor-default items-center gap-1 rounded-sm px-1 text-left text-label text-ink focus-visible:focus-ring focus-visible:outline-none"
        >
          <Icon
            name="chevron"
            className={cn(
              "text-ink-muted transition-transform",
              !open && "-rotate-90",
            )}
          />
          <span className="truncate">{title}</span>
        </button>
        {aside}
      </header>
      {open && <div className="px-3 pb-3">{children}</div>}
    </section>
  );
}
