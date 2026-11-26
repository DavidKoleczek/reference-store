import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";

/** The nearest element around `element` that scrolls, or the page. */
function scrollerOf(element: HTMLElement): HTMLElement {
  for (let at = element.parentElement; at; at = at.parentElement) {
    const { overflowY } = getComputedStyle(at);
    if (overflowY === "auto" || overflowY === "scroll") {
      return at;
    }
  }
  return document.documentElement;
}

/** A row of a windowed list: how tall it is, and what draws it, which only runs while it is near the screen. */
export type WindowRow = {
  key: string;
  height: number;
  render: () => ReactNode;
  /** Called while it is near the screen, such as to read the next page when the end of a list comes into view. */
  onNear?: () => void;
};

// How far past the screen rows are kept drawn, above and below, so a fast scroll rarely shows an empty space.
const OVERSCAN = 900;
// How far the list scrolls before which rows are drawn is worked out again, kept under the overscan.
const STEP = 300;

type Viewport = { top: number; height: number; width: number };

/** Where the list is in what scrolls it, in steps of `STEP`, and how wide it is. */
function useViewport(list: RefObject<HTMLElement | null>): Viewport {
  const [viewport, setViewport] = useState<Viewport>({
    top: 0,
    height: 0,
    width: 0,
  });
  useLayoutEffect(() => {
    const own = list.current;
    if (!own) {
      return;
    }
    const outer = scrollerOf(own);
    let frame = 0;
    const measure = () => {
      frame = 0;
      const exact =
        outer.getBoundingClientRect().top - own.getBoundingClientRect().top;
      const next = {
        top: Math.floor(exact / STEP) * STEP,
        height: outer.clientHeight,
        width: own.clientWidth,
      };
      setViewport((was) =>
        was.top === next.top &&
        was.height === next.height &&
        was.width === next.width
          ? was
          : next,
      );
    };
    const schedule = () => {
      if (frame === 0) {
        frame = requestAnimationFrame(measure);
      }
    };
    measure();
    outer.addEventListener("scroll", schedule, { passive: true });
    const observer = new ResizeObserver(schedule);
    observer.observe(outer);
    observer.observe(own);
    return () => {
      outer.removeEventListener("scroll", schedule);
      observer.disconnect();
      cancelAnimationFrame(frame);
    };
  }, [list]);
  return viewport;
}

/**
 * A list where only the rows near the screen are in the page, so ten thousand rows cost what fifty do. Its rows are
 * made from its width, which `rows` is given once it is known.
 */
export function Windowed({
  rows,
  className,
}: {
  rows: (width: number) => WindowRow[];
  className?: string;
}) {
  const list = useRef<HTMLDivElement>(null);
  const viewport = useViewport(list);
  const made = viewport.width > 0 ? rows(viewport.width) : [];
  const offsets: number[] = [];
  let total = 0;
  for (const row of made) {
    offsets.push(total);
    total += row.height;
  }
  const from = viewport.top - OVERSCAN;
  const to = viewport.top + viewport.height + OVERSCAN;
  let start = 0;
  let low = 0;
  let high = made.length - 1;
  while (low <= high) {
    const middle = (low + high) >> 1;
    if (offsets[middle] + made[middle].height < from) {
      start = middle + 1;
      low = middle + 1;
    } else {
      high = middle - 1;
    }
  }
  let end = start;
  while (end < made.length && offsets[end] < to) {
    end += 1;
  }
  const shown = made.slice(start, end);
  const near = shown.filter((row) => row.onNear).map((row) => row.onNear!);

  useEffect(() => {
    for (const onNear of near) {
      onNear();
    }
  });

  return (
    <div
      ref={list}
      style={{ height: total, position: "relative" }}
      className={className}
    >
      {shown.map((row, index) => (
        <div
          key={row.key}
          style={{
            position: "absolute",
            top: offsets[start + index],
            left: 0,
            right: 0,
            height: row.height,
          }}
        >
          {row.render()}
        </div>
      ))}
    </div>
  );
}
