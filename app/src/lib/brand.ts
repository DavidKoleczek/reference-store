/** The app's name, as its windows, titles, and wordmark show it. */
export const APP_NAME = "Reference Store";

/** What the server filled into the view's meta tag `name`; nothing when it was served without one. */
function served(name: string): string | null {
  const content = document
    .querySelector<HTMLMetaElement>(`meta[name="${name}"]`)
    ?.content.trim();
  return content && !content.startsWith("{{") ? content : null;
}

/** The tool's version. */
export const VERSION = served("reference-store-version");

/** The tool's repository, where its docs are. */
export const DOCUMENTATION = served("reference-store-repository");
