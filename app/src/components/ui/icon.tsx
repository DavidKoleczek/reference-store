import { cn } from "@/lib/utils";

// Line icons on a 24 grid, stroked at 1.5 with square caps and miter joins. A leading "f:" fills the path instead.
const PATHS = {
  add: ["M12 4v16M4 12h16"],
  area: ["M4 4h16v16H4z", "M4 12l8-8M4 20L20 4M12 20l8-8"],
  arrow: ["M5 19L19 5", "M10 5h9v9"],
  "arrow-down": ["M12 4v15.5", "M5.5 13L12 19.5l6.5-6.5"],
  attach: [
    "M16.5 7v9a4.5 4.5 0 0 1-9 0V6.5a3 3 0 0 1 6 0V16a1.5 1.5 0 0 1-3 0V8",
  ],
  box: ["M4 5.5h16v13H4z"],
  check: ["M4 12.5l5 5L20 6.5"],
  chevron: ["M6 9l6 6 6-6"],
  circle: ["M20 12a8 8 0 1 1-16 0 8 8 0 0 1 16 0z"],
  clock: ["M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z", "M12 7v5.5l3.5 2"],
  close: ["M5 5l14 14M19 5L5 19"],
  compare: ["M3 5h18v14H3z", "M12 2v20"],
  copy: ["M8 8h12v12H8z", "M16 8V4H4v12h4"],
  cut: [
    "M8.5 6.5a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0z",
    "M8.5 17.5a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0z",
    "M8 8l12.5 10M8 16L20.5 6",
  ],
  delete: [
    "M3.5 6.5h17",
    "M9 6.5v-3h6v3",
    "M5.5 6.5l1 14h11l1-14",
    "M10 10.5v6M14 10.5v6",
  ],
  draw: ["M3 17c2-7 5-9 7-4s4 3 6-2 3-5 5-3"],
  eraser: ["M3.5 15L13 5.5l7.5 7.5-6 6H7.5z", "M9 9.5l7.5 7.5"],
  expand: ["M14 3h7v7", "M21 3l-7.5 7.5", "M10 21H3v-7", "M3 21l7.5-7.5"],
  export: ["M12 15V3M8 7l4-4 4 4", "M9 11H5v10h14V11h-4"],
  eye: [
    "M2 12c3-5.5 6.5-7 10-7s7 1.5 10 7c-3 5.5-6.5 7-10 7s-7-1.5-10-7z",
    "M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0z",
  ],
  file: ["M6 3h8l4 4v14H6z", "M14 3v4h4"],
  "file-edit": [
    "M11 21.5H5v-19h9.5L19 7v3.5",
    "M14 2.5V7.5h5",
    "M13.5 21.5V19l6-6 2.5 2.5-6 6z",
  ],
  fit: ["M3 8V3h5M16 3h5v5M21 16v5h-5M8 21H3v-5", "M8.5 8.5h7v7h-7z"],
  folder: ["M2.5 4.5h7l2 2.5h10v12.5h-19z", "M2.5 10h19"],
  "folder-add": ["M2.5 4.5h7l2 2.5h10v12.5h-19z", "M12 10v6M9 13h6"],
  grid: ["M3 3h18v18H3z", "M9 3v18M15 3v18M3 9h18M3 15h18"],
  grip: [
    "f:M8 5h2.5v2.5H8zM13.5 5H16v2.5h-2.5zM8 10.75h2.5v2.5H8zM13.5 10.75H16v2.5h-2.5zM8 16.5h2.5V19H8zM13.5 16.5H16V19h-2.5z",
  ],
  image: [
    "M3 4.5h18v15H3z",
    "M3 16l5-5 4.5 4.5 3-3L21 18",
    "f:M14.5 7.5H17V10h-2.5z",
  ],
  import: ["M12 3v12.5M8 11.5l4 4 4-4", "M8 8H5v13h14V8h-3"],
  "link-out": ["M14 3.5h6.5V10", "M20.5 3.5l-9 9", "M18 14v6.5H3.5V6H10"],
  list: ["M4 6h16M4 12h16M4 18h16"],
  loop: ["M4 11V8h14", "M15 5l3 3-3 3", "M20 13v3H6", "M9 13l-3 3 3 3"],
  mark: ["M3 8V3h5M13 3h5v5M3 13v5h5", "f:M11.5 11.5l9 3.5-3.75 1.75L15 20.5z"],
  minus: ["M4 12h16"],
  monitor: ["M3 4.5h18v12H3z", "M8 20.5h8M12 16.5v4"],
  moon: ["M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z"],
  more: ["f:M4 11h2.5v2.5H4zM10.75 11h2.5v2.5h-2.5zM17.5 11H20v2.5h-2.5z"],
  move: [
    "M12 3v18M3 12h18",
    "M9 6l3-3 3 3M9 18l3 3 3-3M6 9l-3 3 3 3M18 9l3 3-3 3",
  ],
  paste: ["M8.5 5H5v16h14V5h-3.5", "M8.5 3.5h7v4h-7z"],
  pause: ["f:M6.5 5h4v14h-4zM13.5 5h4v14h-4z"],
  pin: ["M8.5 3.5h7", "M10 3.5V9l-3 4.5h10L14 9V3.5", "M12 13.5V21"],
  pinned: [
    "M8.5 3.5h7",
    "f:M10 3.5h4V9l3 4.5H7L10 9z",
    "M10 3.5V9l-3 4.5h10L14 9V3.5",
    "M12 13.5V21",
  ],
  play: ["f:M7.5 4.5v15l12-7.5z"],
  rename: ["M4 20v-4.5L15.5 4 20 8.5 8.5 20z", "M12.5 7l4.5 4.5"],
  search: [
    "M17 10.5a6.5 6.5 0 1 1-13 0 6.5 6.5 0 0 1 13 0z",
    "M15.5 15.5L21 21",
  ],
  select: ["M6 3v16l4.5-4.5 3 6.5 2.5-1-3-6.5H19z"],
  send: ["M12 20V4.5", "M5.5 11L12 4.5l6.5 6.5"],
  "sidebar-left": ["M3 4.5h18v15H3z", "M9 4.5v15"],
  "sidebar-right": ["M3 4.5h18v15H3z", "M15 4.5v15"],
  sliders: ["M3 7h4M11 7h10M3 17h10M17 17h4", "M7 5h4v4H7zM13 15h4v4h-4z"],
  "step-back": ["f:M18 5.5v13L9.5 12z", "M6.5 5.5v13"],
  "step-forward": ["f:M6 5.5v13l8.5-6.5z", "M17.5 5.5v13"],
  stop: ["M6 6h12v12H6z"],
  sun: [
    "M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0z",
    "M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8",
  ],
  terminal: ["M3 4.5h18v15H3z", "M7 9.5l3 2.5-3 2.5", "M12.5 15H17"],
  thought: [
    "M12 3a6 6 0 0 0-3.5 10.9V16.5h7v-2.6A6 6 0 0 0 12 3z",
    "M9.5 19.5h5M10.5 22h3",
  ],
  undo: ["M9 5L4 10l5 5", "M4 10h10.5a5.5 5.5 0 0 1 0 11H11"],
  warning: ["M12 3l10 18H2z", "M12 10v5", "f:M11 17h2v2h-2z"],
} satisfies Record<string, string[]>;

export type IconName = keyof typeof PATHS;

/**
 * One of the app's icons in the current text color: 16 in dense rows, 20 in toolbars and buttons. An icon that
 * stands alone, with no text beside it to name it, takes a `label`.
 */
export function Icon({
  name,
  size = 16,
  label,
  className,
}: {
  name: IconName;
  size?: 16 | 20 | 24;
  label?: string;
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="square"
      strokeLinejoin="miter"
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      className={cn("block shrink-0", className)}
    >
      {PATHS[name].map((path) =>
        path.startsWith("f:") ? (
          <path
            key={path}
            d={path.slice(2)}
            fill="currentColor"
            stroke="none"
          />
        ) : (
          <path key={path} d={path} />
        ),
      )}
    </svg>
  );
}
