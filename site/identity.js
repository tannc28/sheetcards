/**
 * Which deck a sheet is, as both pages need to know it.
 *
 * A sheet names its own deck in the settings row — `#config name=Từ vựng` —
 * and that name is also its identity: the .apkg's note guids and note type id
 * derive from it (src/apkg.py, resolve_identity), so the same sheet updates the
 * same notes whichever file, copy or link it arrives as. A sheet that names no
 * deck falls back on its Google Sheets id, or on its file name with what a
 * phone adds to a second download taken off.
 *
 * No DOM in here, so tests/test_site_identity.py can import it in node.
 */

const MARKER = /^\s*#config/i;

/**
 * A file's name as the deck it was made for: no extension, and none of the
 * suffixes a browser adds to a second download of the same name — `Từ vựng (1)`
 * on Android and Windows, `Từ vựng-2` on iOS. A bare trailing number (`HSK 2`)
 * is left alone: it is far more often part of the name than a copy count, and
 * two different decks merging is worse than one deck doubling.
 */
export function fileStem(name) {
  let stem = String(name ?? "").replace(/\.(csv|tsv|txt|xlsx|xlsm)$/i, "").trim();
  stem = stem.replace(/\s*\(\d{1,3}\)$/, "").replace(/-\d{1,3}$/, "").trim();
  return stem || "Deck";
}

/**
 * What a file is keyed by when the sheet inside it names no deck. `.tsv` for
 * every kind, because the Create sheet hand-off has always been a .tsv and that
 * is the identity the decks already imported carry.
 */
export function fileIdentity(name, tab = "") {
  return `file:${fileStem(name)}.tsv#${tab}`;
}

/** A deck name as an identity — the same rule as apkg.deck_identity. */
export function deckKey(name) {
  return String(name ?? "").normalize("NFC").split(/\s+/).filter(Boolean).join(" ").toLowerCase();
}

/** The `key=value` pairs written after `#config` in a marker cell. */
export function markerPairs(marker) {
  return String(marker ?? "")
    .replace(MARKER, "")
    .split(";")
    .map((part) => part.trim())
    .filter(Boolean);
}

/** One deck-wide key's value in a marker cell, or null when it is not there. */
export function markerGet(marker, key) {
  for (const part of markerPairs(marker)) {
    const at = part.indexOf("=");
    const name = (at < 0 ? part : part.slice(0, at)).trim().toLowerCase();
    if (name === key) return at < 0 ? "" : part.slice(at + 1).trim();
  }
  return null;
}

/**
 * The marker cell with `key` set to `value` (null or "" removes it). An existing
 * pair is replaced where it stands; a new one goes at the end, so whatever the
 * sheet said first still reads first. `;` cannot be written into a value.
 */
export function markerSet(marker, key, value) {
  const clean = value === null || value === undefined ? "" : String(value).replace(/;/g, ",").trim();
  const pairs = markerPairs(marker);
  const at = pairs.findIndex((part) => part.split("=")[0].trim().toLowerCase() === key);
  if (!clean) {
    if (at >= 0) pairs.splice(at, 1);
  } else if (at >= 0) pairs[at] = `${key}=${clean}`;
  else pairs.push(`${key}=${clean}`);
  return "#config" + (pairs.length ? " " + pairs.join("; ") : "");
}

// ---------------------------------------------------------------------------
// The deck names this browser has made sheets for
// ---------------------------------------------------------------------------

export const NAMES = "sc-deck-names";

function store(given) {
  if (given) return given;
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}

/** Every deck name used here, as written; unreadable storage reads as none. */
export function usedNames(given) {
  try {
    const list = JSON.parse(store(given)?.getItem(NAMES) || "[]");
    return Array.isArray(list) ? list.filter((n) => typeof n === "string") : [];
  } catch {
    return [];
  }
}

/** True when `name` is, as an identity, one already used here. */
export function nameUsed(name, given) {
  const key = deckKey(name);
  return Boolean(key) && usedNames(given).some((n) => deckKey(n) === key);
}

/** Remembers a deck name. Returns false when the browser would not keep it. */
export function rememberName(name, given) {
  const key = deckKey(name);
  if (!key) return false;
  const list = usedNames(given).filter((n) => deckKey(n) !== key);
  try {
    store(given)?.setItem(NAMES, JSON.stringify([String(name).trim(), ...list].slice(0, 200)));
    return true;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// The note type each deck's last .apkg carried
// ---------------------------------------------------------------------------

export const SHAPES = "sc-deck-shapes";

/** The shape of the last package built for `identity`, or null. */
export function lastShape(identity, given) {
  try {
    const all = JSON.parse(store(given)?.getItem(SHAPES) || "{}");
    const one = all?.[identity];
    return one && Array.isArray(one.fields) ? one : null;
  } catch {
    return null;
  }
}

export function keepShape(identity, shape, given) {
  try {
    const s = store(given);
    if (!s) return false;
    const all = JSON.parse(s.getItem(SHAPES) || "{}") || {};
    all[identity] = { ...shape, at: Date.now() };
    s.setItem(SHAPES, JSON.stringify(all));
    return true;
  } catch {
    return false;
  }
}

/**
 * What changed between the last package and this one, in Anki's eyes:
 * "cloze" (Basic ↔ Cloze — Anki cannot merge those), "schema" (fields or card
 * templates, which need Merge note types once), or null.
 */
export function shapeChange(before, now) {
  if (!before || !now) return null;
  if (before.kind !== now.kind) return "cloze";
  const same = (a, b) => JSON.stringify(a ?? []) === JSON.stringify(b ?? []);
  return same(before.fields, now.fields) && same(before.templates, now.templates) ? null : "schema";
}

/**
 * The card templates this package newly keeps as stubs (apkg.kept_templates) —
 * `reverse` taken out of the settings row. The note type stays the same to
 * Anki, but the cards the template already made stay too, until Tools → Empty
 * Cards removes them; the page says so, once.
 */
export function droppedTemplates(before, now) {
  if (!before || !now || before.kind !== now.kind) return [];
  const had = new Set(before.stubs || []);
  return (now.stubs || []).filter((name) => !had.has(name));
}
