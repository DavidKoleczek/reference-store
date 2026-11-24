import { APP_NAME } from "@/lib/brand";
import { cn } from "@/lib/utils";

/** The app's name in the brand's type, with the accent square where a period would be. */
export function Wordmark({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-baseline text-[14px]/4 font-semibold tracking-[-0.015em] whitespace-nowrap text-ink",
        className,
      )}
    >
      {APP_NAME}
      <span
        aria-hidden
        className="ml-[0.12em] inline-block size-[0.3em] shrink-0 bg-accent"
      />
    </span>
  );
}

/**
 * The compact mark, for where the wordmark has no room: three crop corners around a bookmark on an ink tile, with the
 * square standing in for the fourth corner. `public/favicon.svg` is the same drawing.
 */
export function AppMark({
  size = 20,
  className,
}: {
  size?: number;
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      role="img"
      aria-label={APP_NAME}
      className={cn("block shrink-0", className)}
    >
      <rect width="64" height="64" rx="14" fill="#12161c" />
      <g
        transform="translate(9 9) scale(1.5)"
        fill="none"
        stroke="#eef2f6"
        strokeWidth="2.2"
        strokeLinejoin="miter"
        strokeLinecap="square"
      >
        <path d="M2.5 8.5V3h5.5M16 3h5.5v5.5M2.5 15.5V21H8" />
        <path d="M8 6.5h8v11.75l-4-3.25-4 3.25z" fill="#eef2f6" stroke="none" />
      </g>
      <rect x="44" y="44" width="11" height="11" fill="#f4c542" />
    </svg>
  );
}
