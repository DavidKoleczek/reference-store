import { useState } from "react";

import { TEXT } from "@/lib/text";
import { cn } from "@/lib/utils";

const STEPS = [1, 2, 3, 4, 5];

/** The square the pointer is on, and once it is clicked, the rating it had and the one asked for. */
type Pointer = {
  on: number;
  click?: { from: number | null; to: number | null };
};

/**
 * A rating of 1 to 5 as squares, filled up to it. Picking the one it has clears it. While the pointer is on a square,
 * the squares up to it show the rating a click gives, paler than the rating it has.
 */
export function Rating({
  value,
  onChange,
  className,
}: {
  value: number | null;
  /** Leave it out for a rating that only shows. */
  onChange?: (value: number | null) => void;
  className?: string;
}) {
  const [pointer, setPointer] = useState<Pointer | null>(null);
  if (!onChange) {
    return (
      <span
        role="img"
        aria-label={TEXT.rating.rated(value ?? 0)}
        className={cn("inline-flex gap-0.5", className)}
      >
        {STEPS.map((step) => (
          <span
            key={step}
            className={cn(
              "size-1.5",
              step <= (value ?? 0) ? "bg-accent-ink" : "bg-line",
            )}
          />
        ))}
      </span>
    );
  }
  const click = pointer?.click;
  // A click shows what it asked for at once, rather than the rating before until it is saved.
  const shown =
    pointer === null
      ? value
      : click === undefined
        ? pointer.on
        : value === click.from
          ? click.to
          : value;
  const previewing =
    pointer !== null && click === undefined && pointer.on !== value;
  return (
    <span
      onPointerLeave={() => setPointer(null)}
      className={cn("inline-flex", className)}
    >
      {STEPS.map((step) => (
        <button
          key={step}
          type="button"
          aria-label={TEXT.rating.rate(step)}
          aria-pressed={value === step}
          onPointerEnter={() => setPointer({ on: step })}
          onClick={() => {
            const to = value === step ? null : step;
            setPointer(
              (now) => now && { on: now.on, click: { from: value, to } },
            );
            onChange(to);
          }}
          className="grid size-5 cursor-default place-items-center rounded-sm outline-none focus-visible:focus-ring"
        >
          <span
            className={cn(
              "size-3 border transition-colors",
              step > (shown ?? 0)
                ? "border-line-control bg-field"
                : previewing
                  ? "border-accent-ink bg-accent/70"
                  : "border-accent-ink bg-accent",
            )}
          />
        </button>
      ))}
    </span>
  );
}
