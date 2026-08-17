/**
 * A stand-in for Anki's template renderer.
 *
 * This is the one part of the preview with no source of truth in the add-on:
 * `{{Field}}`, `{{#Field}}`, `{{cloze:}}`, `{{furigana:}}` and `{{tts}}` are
 * interpreted by Anki itself (Rust, in rslib/src/template.rs and
 * template_filters.rs), not by any file in this repository. Everything else the
 * site shows comes from running the add-on's own Python; this file is an
 * approximation, and the page says so where it matters.
 *
 * It covers the constructs the add-on actually emits, plus the handful a user
 * might type into a field. Anything unrecognised is left visible rather than
 * dropped, so an unsupported tag looks like an unsupported tag instead of
 * looking like an empty field.
 */

/** Fields hold HTML in Anki, so only the *text* helpers escape anything. */
export function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function stripHtml(value) {
  return String(value ?? "").replace(/<[^>]+>/g, "");
}

// Anki: `kanji[reading]` becomes ruby text. Its own pattern is roughly
// /(?:^| )([^ >]+?)\[(.+?)\]/ — the space before the base is consumed so
// "推迟 [tuī chí]" and "推迟[tuī chí]" both work.
const FURIGANA_RE = /(^|[\s>])([^\s>]+?)\[(.+?)\]/g;

function furigana(value) {
  return String(value ?? "").replace(
    FURIGANA_RE,
    (_m, lead, base, reading) =>
      `${lead}<ruby><rb>${base}</rb><rt>${reading}</rt></ruby>`,
  );
}

// {{c1::answer}} or {{c1::answer::hint}}
const CLOZE_RE = /\{\{c(\d+)::(.*?)(?:::(.*?))?\}\}/g;

/** Every cloze number present in the row — one card each, as Anki generates. */
export function clozeOrdinals(text) {
  const found = new Set();
  for (const m of String(text ?? "").matchAll(CLOZE_RE)) found.add(Number(m[1]));
  return [...found].sort((a, b) => a - b);
}

function cloze(value, ordinal, isBack) {
  // Anki renders a clozed field that carries no deletion as nothing at all —
  // verified against a real collection, where a filled field came back as an
  // empty div. Reproducing that is the point: it is how a misplaced deletion
  // shows up as a blank prompt instead of looking fine here and failing in Anki.
  if (!CLOZE_RE.test(String(value ?? ""))) return "";
  CLOZE_RE.lastIndex = 0; // the regex is global, so .test() left an offset behind

  return String(value ?? "").replace(CLOZE_RE, (_m, n, answer, hint) => {
    if (Number(n) !== ordinal) return answer; // other deletions read normally
    if (isBack) return `<span class="cloze">${answer}</span>`;
    return `<span class="cloze">[${hint || "..."}]</span>`;
  });
}

let hintSeq = 0;

/**
 * Anki's {{hint:}} is a link that reveals the field's text in place. Reproduced
 * with the same shape (a link plus a hidden div) so the preview behaves like the
 * card rather than merely looking like it.
 */
function hint(value, fieldName) {
  if (!String(value ?? "").trim()) return "";
  const id = `hint-${++hintSeq}`;
  return (
    `<a class="hint" href="#" onclick="this.style.display='none';` +
    `document.getElementById('${id}').style.display='block';return false;">` +
    `${escapeHtml(fieldName)}</a>` +
    `<div id="${id}" class="hint" style="display:none">${value}</div>`
  );
}

/**
 * Anki turns a TTS tag into a play button backed by the OS voices. The browser's
 * speechSynthesis draws on the *same* system voices, so this button is a real
 * test of whether a language code will make a sound on this machine — which is
 * the thing a `tts=` directive most often gets wrong.
 */
function ttsButton(spec, value) {
  const text = stripHtml(value).trim();
  if (!text) return "";

  const [, lang = ""] = spec.match(/^tts\s+(\S+)/) || [];
  const voices = (spec.match(/voices=([^\s]+)/) || [])[1] || "";
  const speed = (spec.match(/speed=([\d.]+)/) || [])[1] || "1";

  const payload = escapeHtml(
    JSON.stringify({ lang, voices: voices ? voices.split(",") : [], speed, text }),
  );
  return (
    `<button type="button" class="tts" data-tts="${payload}" ` +
    `title="${escapeHtml(lang)} — speaks through this computer's voices">` +
    `▶ ${escapeHtml(lang)}</button>`
  );
}

/** What `{{type:cloze:F}}` asks you to type: the deletions of this card's c-number. */
function clozeForTyping(value, ordinal) {
  const answers = [];
  for (const m of String(value ?? "").matchAll(CLOZE_RE)) {
    if (Number(m[1]) === ordinal) answers.push(m[2]);
  }
  return answers.join(", ");
}

/**
 * Anki's typed-answer box.
 *
 * `{{type:F}}` is not a filter and never was: Anki's renderer leaves the tag
 * alone and the reviewer swaps it for an input on the question and for a
 * character-by-character comparison on the answer. Treating it as an unknown
 * filter — which is what this page did until the box existed — fell back to
 * printing the field, so a typed-answer card previewed with its answer already
 * on the question.
 *
 * The comparison is drawn inside the card document, by site/typeans.js, because
 * it depends on something no template knows: what the learner typed.
 */
function typeBox(field, raw, mods, ctx) {
  const expected = mods.includes("cloze")
    ? clozeForTyping(raw, ctx.ordinal)
    : stripHtml(raw).trim();
  // Anki removes the tag outright when the field is empty rather than drawing a
  // box with nothing to check against.
  if (!expected) return "";

  const spec = escapeHtml(
    JSON.stringify({ expect: expected, nc: mods.includes("nc") }),
  );
  return (
    `<div class="s2a-type" data-typeans="${spec}">` +
    `<center><input type="text" id="typeans" autocomplete="off" ` +
    `autocapitalize="off" autocorrect="off" spellcheck="false" ` +
    `aria-label="${escapeHtml(field)}"></center>` +
    `<div class="s2a-typeans" hidden></div></div>`
  );
}

function applyFilter(name, value, fieldName, ctx) {
  if (name.startsWith("tts ") || name === "tts") return ttsButton(name, value);
  switch (name) {
    case "text":
      return stripHtml(value);
    case "furigana":
      return furigana(value);
    case "kanji":
      return String(value ?? "").replace(FURIGANA_RE, (_m, lead, base) => lead + base);
    case "kana":
      return String(value ?? "").replace(
        FURIGANA_RE,
        (_m, lead, _base, reading) => lead + reading,
      );
    case "hint":
      return hint(value, fieldName);
    case "cloze":
      return cloze(value, ctx.ordinal, ctx.isBack);
    default:
      // Unknown filters render as Anki does when a filter is missing: the field
      // value, unchanged. Recording it lets the page say which one it ignored.
      ctx.unknownFilters.add(name);
      return value;
  }
}

/** Splits `{{a:b:Field}}` into its filters (outermost first) and field name. */
function parseReplacement(inner) {
  const parts = [];
  let buffer = "";
  for (const ch of inner) {
    if (ch === ":") {
      parts.push(buffer);
      buffer = "";
    } else buffer += ch;
  }
  parts.push(buffer);
  return { filters: parts.slice(0, -1), field: parts[parts.length - 1].trim() };
}

const TOKEN_RE = /\{\{([^{}]*)\}\}/g;

function isFilled(value) {
  return String(value ?? "").trim() !== "";
}

/**
 * Resolves `{{#Field}}…{{/Field}}` and `{{^Field}}…{{/Field}}`.
 *
 * Anki matches these by name, and an unclosed section is a template error rather
 * than something to guess at — so an unmatched open tag is left in place, where
 * it is visible.
 */
function resolveSections(template, values) {
  const openRe = /\{\{([#^])([^{}]+)\}\}/;
  let out = template;
  let guard = 0;

  while (guard++ < 200) {
    const open = out.match(openRe);
    if (!open) break;

    const [openTag, kind, rawName] = open;
    const name = rawName.trim();
    const closeTag = `{{/${name}}}`;
    const start = open.index;
    const bodyStart = start + openTag.length;
    const closeAt = out.indexOf(closeTag, bodyStart);
    if (closeAt === -1) break; // malformed: leave it showing

    const body = out.slice(bodyStart, closeAt);
    const filled = isFilled(values[name]);
    const keep = kind === "#" ? filled : !filled;
    out = out.slice(0, start) + (keep ? body : "") + out.slice(closeAt + closeTag.length);
  }
  return out;
}

/**
 * Renders one side of a card.
 *
 * @param {string} template  qfmt or afmt, exactly as the add-on generated it
 * @param {object} values    field name → cell value
 * @param {object} [opts]    {ordinal, isBack, frontSide}
 * @returns {{html: string, unknownFilters: string[], missingFields: string[]}}
 */
export function renderSide(template, values, opts = {}) {
  const ctx = {
    ordinal: opts.ordinal ?? 1,
    isBack: Boolean(opts.isBack),
    unknownFilters: new Set(),
    missingFields: new Set(),
  };

  let out = resolveSections(template, values);

  out = out.replace(TOKEN_RE, (whole, inner) => {
    const trimmed = inner.trim();
    if (trimmed === "FrontSide") return opts.frontSide ?? "";
    if (trimmed.startsWith("/")) return ""; // stray close tag

    const { filters, field } = parseReplacement(inner);
    if (!(field in values)) {
      ctx.missingFields.add(field);
      return whole; // Anki shows the unknown field name too
    }

    // Filters apply innermost-first: {{text:furigana:F}} reads furigana, then text.
    let value = values[field] ?? "";
    for (const name of [...filters].reverse()) {
      value = applyFilter(name.trim(), value, field, ctx);
    }
    return value;
  });

  return {
    html: out,
    unknownFilters: [...ctx.unknownFilters],
    missingFields: [...ctx.missingFields],
  };
}

/** Renders a whole card, wiring `{{FrontSide}}` on the answer to the question. */
export function renderCard(template, values, opts = {}) {
  const front = renderSide(template.qfmt, values, opts);
  const back = renderSide(template.afmt, values, {
    ...opts,
    isBack: true,
    frontSide: front.html,
  });
  return { front, back };
}
