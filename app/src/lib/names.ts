// What a name can't have, as the library's rules say: Windows refuses these in a folder's name.
const FORBIDDEN = /[\\/:*?"<>|]+/g;
const NAME_LIMIT = 64;
// Parts of a link that say nothing about what it is.
const EMPTY_PARTS = new Set([
  "",
  "index.html",
  "index.htm",
  "index",
  "watch",
  "status",
  "p",
  "post",
  "posts",
  "comments",
]);

/** A name made to keep to the library's rules: what Windows refuses gone, no dot to start it, and not too long. */
export function cleanName(text: string): string {
  return Array.from(text, (character) =>
    character.charCodeAt(0) < 32 ? " " : character,
  )
    .join("")
    .replace(FORBIDDEN, "-")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^[.\s-]+/, "")
    .slice(0, NAME_LIMIT)
    .replace(/[.\s-]+$/, "");
}

/** Whether text is a link the app can add. */
export function isLink(text: string): boolean {
  return /^https?:\/\/\S+$/i.test(text.trim());
}

/**
 * A name for an entry suggested from its link, which the person can change: the last part of the path that says
 * something, such as the repository on GitHub, else the site.
 */
export function suggestName(link: string): string {
  let url: URL;
  try {
    url = new URL(link.trim());
  } catch {
    return cleanName(link);
  }
  const site = url.hostname.replace(/^www\./, "");
  const video = url.searchParams.get("v");
  if (video) {
    return cleanName(`${site.split(".")[0]}-${video}`);
  }
  const parts = url.pathname
    .split("/")
    .map((part) => decodeURIComponent(part).replace(/\.[a-z0-9]{1,5}$/i, ""))
    .filter((part) => !EMPTY_PARTS.has(part.toLowerCase()));
  const last = parts.at(-1);
  if (!last) {
    return cleanName(site);
  }
  // A number alone, such as a post's id, says more with what comes before it.
  const named =
    /^\d+$/.test(last) && parts.length > 1 ? `${parts.at(-2)}-${last}` : last;
  return cleanName(named.replace(/[_+]+/g, "-"));
}
