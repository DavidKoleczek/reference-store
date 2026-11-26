import { useEffect, useEffectEvent, useState } from "react";

import { changeSettings, type Place } from "@/lib/settings";

// The mouse's back and forward buttons, as `MouseEvent.button` numbers them.
const BACK_BUTTON = 3;
const FORWARD_BUTTON = 4;

type History = { place: Place; back: Place[]; forward: Place[] };

function same(a: Place, b: Place): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

/**
 * Where the app is, with Back and Forward, kept by the view itself: the browser's history doesn't step inside the
 * sandboxed frames the view runs in. The mouse's back and forward buttons and Alt+Left and Alt+Right step through it,
 * and the place is kept with what the app remembers, so a reload stays in the entry that was open.
 */
export function usePlaces(start: Place) {
  const [history, setHistory] = useState<History>({
    place: start,
    back: [],
    forward: [],
  });

  const go = (place: Place) =>
    setHistory((now) =>
      same(place, now.place)
        ? now
        : { place, back: [...now.back, now.place], forward: [] },
    );
  const back = () =>
    setHistory((now) => {
      const place = now.back.at(-1);
      return place === undefined
        ? now
        : {
            place,
            back: now.back.slice(0, -1),
            forward: [now.place, ...now.forward],
          };
    });
  const forward = () =>
    setHistory((now) => {
      const [place, ...rest] = now.forward;
      return place === undefined
        ? now
        : { place, back: [...now.back, now.place], forward: rest };
    });
  /** Changes where the app is without a step, such as when the open entry is renamed. */
  const replace = (place: Place) => setHistory((now) => ({ ...now, place }));

  useEffect(() => {
    changeSettings({ place: history.place });
  }, [history.place]);

  const step = useEffectEvent((forwards: boolean) =>
    forwards ? forward() : back(),
  );
  useEffect(() => {
    const isStep = (event: MouseEvent) =>
      event.button === BACK_BUTTON || event.button === FORWARD_BUTTON;
    // Held from the browser, which would otherwise leave the app's page.
    const hold = (event: MouseEvent) => {
      if (isStep(event)) {
        event.preventDefault();
      }
    };
    const onUp = (event: MouseEvent) => {
      if (isStep(event)) {
        event.preventDefault();
        step(event.button === FORWARD_BUTTON);
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (
        event.altKey &&
        (event.key === "ArrowLeft" || event.key === "ArrowRight")
      ) {
        event.preventDefault();
        step(event.key === "ArrowRight");
      }
    };
    window.addEventListener("mousedown", hold);
    window.addEventListener("auxclick", hold);
    window.addEventListener("mouseup", onUp);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", hold);
      window.removeEventListener("auxclick", hold);
      window.removeEventListener("mouseup", onUp);
      window.removeEventListener("keydown", onKey);
    };
  }, []);

  return {
    place: history.place,
    canGoBack: history.back.length > 0,
    go,
    back,
    forward,
    replace,
  };
}
