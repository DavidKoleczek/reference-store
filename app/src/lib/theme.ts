import { useSyncExternalStore } from "react";

export type Theme = "light" | "dark";

/** What the person picked: System follows the host's theme. */
export type ThemePreference = Theme | "system";

const darkScheme = window.matchMedia("(prefers-color-scheme: dark)");
const listeners = new Set<() => void>();
let hostTheme: Theme | null = null;
let preference: ThemePreference = "system";

/** The theme the view shows: the person's pick, or for System the host's, else the computer's. */
export function effectiveTheme(): Theme {
  if (preference !== "system") {
    return preference;
  }
  return hostTheme ?? (darkScheme.matches ? "dark" : "light");
}

function notify() {
  for (const listener of listeners) {
    listener();
  }
}

function apply() {
  const theme = effectiveTheme();
  const root = document.documentElement;
  if (root.dataset.theme !== theme) {
    root.dataset.theme = theme;
    root.style.colorScheme = theme;
    notify();
  }
}

/** Record the theme the host gives, which System follows. */
export function setHostTheme(theme: Theme) {
  hostTheme = theme;
  apply();
}

export function setThemePreference(next: ThemePreference) {
  if (preference !== next) {
    preference = next;
    apply();
    notify();
  }
}

darkScheme.addEventListener("change", apply);
apply();

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** The theme in effect, rerendering when it changes. */
export function useTheme(): Theme {
  return useSyncExternalStore(subscribe, effectiveTheme);
}

/** What the person picked, rerendering when it changes. */
export function useThemePreference(): ThemePreference {
  return useSyncExternalStore(subscribe, () => preference);
}
