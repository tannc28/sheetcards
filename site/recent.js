/**
 * The sets this browser downloaded, newest first — the way back next week.
 *
 * Each is kept with the address that opens it again (a `#s=` link for words
 * written out, `?url=` for a Google Sheet) and the words on its cards' fronts,
 * so pasting under the same name can say how many words are new. A file opened
 * from the device has no address, so it is not kept. Storage is this browser's
 * own; a private window simply has no recent sets.
 */

import { deckKey } from "./identity.js";

export const RECENT = "sc-recent-sets";
const MAX = 5;
const MAX_KEYS = 3000;

function store(given) {
  try {
    return given ?? globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}

/** Every recent set, newest first: {name, href, at, count, keys}. */
export function recentSets(given) {
  try {
    const list = JSON.parse(store(given)?.getItem(RECENT) || "[]");
    return Array.isArray(list) ? list.filter((r) => r && typeof r.name === "string" && typeof r.href === "string") : [];
  } catch {
    return [];
  }
}

/** The recent set with this name, as an identity (case and spacing ignored), or null. */
export function recentFor(name, given) {
  const key = deckKey(name);
  return (key && recentSets(given).find((r) => deckKey(r.name) === key)) || null;
}

/** Remembers a download; the same set (by name) moves to the top. */
export function keepRecent({ name, href, count = 0, keys = [] }, given) {
  const key = deckKey(name);
  if (!key || !href) return false;
  const list = recentSets(given).filter((r) => deckKey(r.name) !== key && r.href !== href);
  const entry = { name: String(name).trim(), href, count, at: Date.now(), keys: keys.slice(0, MAX_KEYS) };
  try {
    store(given)?.setItem(RECENT, JSON.stringify([entry, ...list].slice(0, MAX)));
    return true;
  } catch {
    return false;
  }
}
