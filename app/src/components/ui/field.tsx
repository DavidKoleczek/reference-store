import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

const FIELD =
  "w-full min-w-0 rounded-sm border border-line-control bg-field px-2 text-body text-ink transition-[background-color,border-color] outline-none placeholder:text-ink-muted focus-visible:border-ink focus-visible:bg-panel focus-visible:focus-ring disabled:text-ink-faint aria-invalid:border-danger";

export function Input({ className, ...props }: ComponentProps<"input">) {
  return <input className={cn(FIELD, "h-7", className)} {...props} />;
}

export function Textarea({ className, ...props }: ComponentProps<"textarea">) {
  return (
    <textarea className={cn(FIELD, "min-h-16 py-1.5", className)} {...props} />
  );
}

export function Label({ className, ...props }: ComponentProps<"label">) {
  return (
    <label
      className={cn("mb-1.5 block text-label text-ink", className)}
      {...props}
    />
  );
}
