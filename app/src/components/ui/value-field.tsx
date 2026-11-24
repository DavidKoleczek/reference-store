import { useRef, useState, type KeyboardEvent, type PointerEvent } from "react";

import { cn } from "@/lib/utils";

// How far the pointer moves before a press is a drag rather than a click to type.
const DRAG_START = 3;
const FINE = 0.1;
const COARSE = 10;

/** Units that sit against the number, such as 80% or 2x; any other follows a space, such as 12 px. */
const TIGHT_UNIT = /^[%x]/;

/**
 * A number in a field: drag it sideways to change it, click to type it, or step it with the arrow keys. Shift drags
 * finely and steps by ten. The fill shows where the value sits between `min` and `max`.
 */
export function ValueField({
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
  unit,
  bar = true,
  disabled = false,
  className,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step?: number;
  unit?: string;
  /** Off for a value whose range says nothing, such as a size in pixels. */
  bar?: boolean;
  disabled?: boolean;
  className?: string;
}) {
  const [typed, setTyped] = useState<string | null>(null);
  const press = useRef<{ x: number; value: number; dragged: boolean } | null>(
    null,
  );
  const field = useRef<HTMLDivElement>(null);

  const snapped = (next: number) => {
    const stepped = min + Math.round((next - min) / step) * step;
    // Rounded to the step's own precision, so 0.1 steps never show 0.30000000000000004.
    const places = (String(step).split(".")[1] ?? "").length;
    return Number(Math.min(max, Math.max(min, stepped)).toFixed(places));
  };

  const commit = () => {
    const parsed = Number(typed);
    if (typed !== null && typed.trim() !== "" && Number.isFinite(parsed)) {
      onChange(snapped(parsed));
    }
    setTyped(null);
  };

  const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (disabled || typed !== null || event.button !== 0) {
      return;
    }
    event.currentTarget.setPointerCapture(event.pointerId);
    press.current = { x: event.clientX, value, dragged: false };
  };

  const onPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    const from = press.current;
    if (!from) {
      return;
    }
    const moved = event.clientX - from.x;
    if (!from.dragged && Math.abs(moved) < DRAG_START) {
      return;
    }
    from.dragged = true;
    const range =
      (moved / event.currentTarget.offsetWidth) *
      (max - min) *
      (event.shiftKey ? FINE : 1);
    onChange(snapped(from.value + range));
  };

  const onPointerUp = () => {
    const from = press.current;
    press.current = null;
    if (from && !from.dragged) {
      setTyped(String(value));
    }
  };

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (disabled || typed !== null) {
      return;
    }
    const way =
      event.key === "ArrowRight" || event.key === "ArrowUp"
        ? 1
        : event.key === "ArrowLeft" || event.key === "ArrowDown"
          ? -1
          : 0;
    if (way !== 0) {
      event.preventDefault();
      onChange(snapped(value + way * step * (event.shiftKey ? COARSE : 1)));
    } else if (event.key === "Enter") {
      event.preventDefault();
      setTyped(String(value));
    }
  };

  const fill = max > min ? ((value - min) / (max - min)) * 100 : 0;
  return (
    <div
      ref={field}
      role="slider"
      tabIndex={disabled ? -1 : 0}
      aria-label={label}
      aria-valuenow={value}
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuetext={unit ? `${value} ${unit}` : undefined}
      aria-disabled={disabled || undefined}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={() => (press.current = null)}
      onKeyDown={onKeyDown}
      className={cn(
        "relative flex h-7 min-w-0 touch-none items-center gap-2 overflow-hidden rounded-sm border px-2 select-none focus-visible:focus-ring focus-visible:outline-none",
        disabled
          ? "border-line bg-field"
          : typed !== null
            ? "cursor-text border-ink bg-panel"
            : "cursor-ew-resize border-line-control bg-field hover:border-ink-muted",
        className,
      )}
    >
      {bar && typed === null && (
        <span
          aria-hidden
          className={cn(
            "pointer-events-none absolute inset-y-0 left-0",
            disabled ? "bg-hover" : "bg-accent-soft",
          )}
          style={{ width: `${fill}%` }}
        />
      )}
      <span
        className={cn(
          "relative min-w-0 flex-1 truncate text-label",
          disabled ? "text-ink-faint" : "text-ink-muted",
        )}
      >
        {label}
      </span>
      {typed === null ? (
        <span
          className={cn(
            "relative mono-value",
            disabled ? "text-ink-faint" : "text-ink",
          )}
        >
          {value}
          {unit && (TIGHT_UNIT.test(unit) ? unit : ` ${unit}`)}
        </span>
      ) : (
        <input
          autoFocus
          aria-label={label}
          inputMode="decimal"
          value={typed}
          onChange={(event) => setTyped(event.target.value)}
          onFocus={(event) => event.target.select()}
          onBlur={commit}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              commit();
              field.current?.focus();
            } else if (event.key === "Escape") {
              event.stopPropagation();
              setTyped(null);
              field.current?.focus();
            }
          }}
          className="relative h-full w-1/2 min-w-0 bg-transparent text-right mono-value text-ink outline-none"
        />
      )}
    </div>
  );
}
