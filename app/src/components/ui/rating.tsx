import { TEXT } from "@/lib/text";
import { cn } from "@/lib/utils";

const STEPS = [1, 2, 3, 4, 5];

/** A rating of 1 to 5 as squares, filled up to it. Picking the one it has clears it. */
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
  return (
    <span className={cn("group/rating inline-flex", className)}>
      {STEPS.map((step) => (
        <button
          key={step}
          type="button"
          aria-label={TEXT.rating.rate(step)}
          aria-pressed={value === step}
          onClick={() => onChange(value === step ? null : step)}
          className="group/step grid size-5 cursor-default place-items-center rounded-sm outline-none focus-visible:focus-ring"
        >
          <span
            className={cn(
              "size-3 border transition-colors",
              step <= (value ?? 0)
                ? "border-accent-ink bg-accent"
                : "border-line-control bg-field group-hover/step:bg-accent-soft",
            )}
          />
        </button>
      ))}
    </span>
  );
}
