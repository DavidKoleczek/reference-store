import type { FileOf } from "@/lib/api";

/** How tall a group's header is in a windowed list, with the space above it. */
export const GROUP_HEADER_HEIGHT = 36;

// Each card's caption, below its picture: a line for its name, one for its facts, and the space around them.
const CAPTION_HEIGHT = 56;
const CARD = { min: 176, gap: 12 };

/** How the cards fit across `width`: how many in a row, and how tall each row is with the gap under it. */
export function cardLayout(width: number) {
  const columns = Math.max(
    1,
    Math.floor((width + CARD.gap) / (CARD.min + CARD.gap)),
  );
  const cardWidth = (width - CARD.gap * (columns - 1)) / columns;
  const imageHeight = Math.round((cardWidth * 3) / 4);
  // The card's border, and the line under its picture.
  return {
    columns,
    imageHeight,
    rowHeight: imageHeight + CAPTION_HEIGHT + 3 + CARD.gap,
  };
}

/** A file shown in a wall or a list: which it is, its facts, and its size in pixels when it is an image. */
export type Shown = {
  file: FileOf & {
    full_path: string;
    size: number;
    modified: string;
    description: string;
    notes: string;
    tags: string[];
  };
  dimensions: [number, number] | null;
};

export function shownKey({ file }: Shown): string {
  return `${file.store}/${file.entry}/${file.path}`;
}

// A tile is never narrower or wider than these times its height, so a very tall or very wide image still fits a row.
const RATIOS = { min: 0.56, max: 2.4 };
const DOCUMENT_RATIO = 0.8;
// How far past its height a row stretches to fill its width, before it is left short instead.
const STRETCH = 1.4;
const WALL = { gapX: 8, gapY: 12, label: 20 };

export type WallRowLayout = {
  tiles: { shown: Shown; width: number }[];
  imageHeight: number;
  height: number;
};

function ratioOf({ dimensions }: Shown): number {
  return dimensions
    ? Math.min(RATIOS.max, Math.max(RATIOS.min, dimensions[0] / dimensions[1]))
    : DOCUMENT_RATIO;
}

/** Files in rows that fill `width`, each image at its own shape and every tile in a row the same height. */
export function wallLayout(
  files: Shown[],
  width: number,
  target: number,
): WallRowLayout[] {
  const rows: WallRowLayout[] = [];
  let current: { shown: Shown; ratio: number }[] = [];
  let sum = 0;
  const finish = (last: boolean) => {
    if (current.length === 0) {
      return;
    }
    const room = width - WALL.gapX * (current.length - 1);
    const fill = room / sum;
    // The last row keeps the height of the rows above, unless it is too wide for the room.
    const scale = Math.min(fill, last ? 1 : STRETCH);
    const imageHeight = Math.max(24, Math.floor(target * scale));
    rows.push({
      tiles: current.map(({ shown, ratio }) => ({
        shown,
        width: Math.floor(ratio * imageHeight),
      })),
      imageHeight,
      height: imageHeight + WALL.label + WALL.gapY,
    });
    current = [];
    sum = 0;
  };
  for (const shown of files) {
    const ratio = ratioOf(shown);
    const basis = ratio * target;
    if (
      current.length > 0 &&
      sum + basis + WALL.gapX * current.length > width
    ) {
      finish(false);
    }
    current.push({ shown, ratio });
    sum += basis;
  }
  finish(true);
  return rows;
}
