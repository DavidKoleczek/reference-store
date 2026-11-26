import { useSyncExternalStore } from "react";

// A phone held upright, where the app is one column.
const NARROW = window.matchMedia("(max-width: 640px)");

function subscribe(listener: () => void): () => void {
  NARROW.addEventListener("change", listener);
  return () => NARROW.removeEventListener("change", listener);
}

/** Whether the screen is as narrow as a phone's, rerendering when that changes. */
export function useNarrow(): boolean {
  return useSyncExternalStore(subscribe, () => NARROW.matches);
}
