/**
 * Suggestions for a word, from open sources: no DOM, so the parsers run in node.
 *
 *   Wiktionary (en, vi) — senses, IPA, pronunciation files; CC BY-SA 4.0
 *   Tatoeba             — example sentences with a Vietnamese translation; CC BY 2.0 FR
 *   Wikimedia Commons   — pictures; each file's own author and licence
 *
 * Every request is a plain GET with `origin=*` (or a server that answers `*`),
 * so nothing is sent but the word itself and the browser's usual headers. Only
 * en.wiktionary's `action=parse` is used: its REST definition endpoint is being
 * retired and dictionaryapi.dev 404s on common words.
 *
 * The parsers (parseSenses, parsePronunciation, parseTatoeba, parseCommons)
 * take a response body and return plain data; tests/test_site_suggest.py feeds
 * them responses saved in tests/fixtures/suggest/.
 */

// ---------------------------------------------------------------------------
// Languages
// ---------------------------------------------------------------------------

// The section a language has on en.wiktionary, and its Tatoeba code.
export const LANGS = {
  en: { name: "English", tatoeba: "eng" },
  fr: { name: "French", tatoeba: "fra" },
  de: { name: "German", tatoeba: "deu" },
  es: { name: "Spanish", tatoeba: "spa" },
  it: { name: "Italian", tatoeba: "ita" },
  pt: { name: "Portuguese", tatoeba: "por" },
  ru: { name: "Russian", tatoeba: "rus" },
  zh: { name: "Chinese", tatoeba: "cmn", cjk: true },
  ja: { name: "Japanese", tatoeba: "jpn", cjk: true },
  ko: { name: "Korean", tatoeba: "kor", cjk: true },
};

/**
 * What can be suggested in a language. For Chinese, Japanese and Korean only
 * the English glosses: there is no Vietnamese source good enough to offer
 * (Tatoeba's cmn→vie pairs mistranslate, vi.wiktionary has almost none).
 */
export function coverage(language) {
  const lang = LANGS[language];
  if (!lang) return null;
  if (lang.cjk) return { senses: true, vi: false, ipa: false, examples: false, audio: false, images: false };
  return { senses: true, vi: true, ipa: true, examples: true, audio: true, images: true };
}

// ---------------------------------------------------------------------------
// Wikitext
// ---------------------------------------------------------------------------

/** The arguments of a template call's body ("t|vi|táo|alt=x" → positional + named). */
function templateArgs(body) {
  const parts = [];
  let depth = 0;
  let cur = "";
  for (let i = 0; i < body.length; i++) {
    const two = body.slice(i, i + 2);
    if (two === "{{" || two === "[[") {
      depth++;
      cur += two;
      i++;
    } else if ((two === "}}" || two === "]]") && depth > 0) {
      depth--;
      cur += two;
      i++;
    } else if (body[i] === "|" && depth === 0) {
      parts.push(cur);
      cur = "";
    } else cur += body[i];
  }
  parts.push(cur);
  const name = parts.shift().trim();
  const pos = [];
  const named = {};
  for (const p of parts) {
    const m = p.match(/^\s*([\w-]+)\s*=([\s\S]*)$/);
    if (m) named[m[1]] = m[2].trim();
    else pos.push(p.trim());
  }
  return { name, pos, named };
}

/** Every top-level template in `text`, with where it sits. */
export function templates(text) {
  const out = [];
  let depth = 0;
  let start = -1;
  for (let i = 0; i < text.length - 1; i++) {
    const two = text.slice(i, i + 2);
    if (two === "{{") {
      if (depth === 0) start = i;
      depth++;
      i++;
    } else if (two === "}}" && depth > 0) {
      depth--;
      i++;
      if (depth === 0) out.push({ start, end: i + 1, ...templateArgs(text.slice(start + 2, i - 1)) });
    }
  }
  return out;
}

// Templates whose text is part of the gloss, and how to read it.
const LABEL_TEMPLATES = new Set(["lb", "lbl", "label", "q", "qual", "qualifier", "i", "gloss", "gl", "sense", "s"]);
const WORD_TEMPLATES = new Set(["l", "m", "l-self", "ll", "mention", "link", "cog", "noncog", "taxlink", "vern", "w", "wp", "taxfmt", "ja-r", "zh-l", "ko-l", "nowrap", "lang", "smallcaps", "1", "upright"]);

/** A line of wikitext as plain text: links, labels, templates and markup resolved. */
export function plainText(wikitext) {
  let text = String(wikitext ?? "");
  text = text.replace(/<ref[^>]*\/>/g, "").replace(/<ref[\s\S]*?<\/ref>/g, "").replace(/<!--[\s\S]*?-->/g, "");
  // Inner templates first, so an outer one sees its arguments as text.
  for (let guard = 0; guard < 6 && text.includes("{{"); guard++) {
    const found = templates(text);
    if (!found.length) break;
    let out = "";
    let at = 0;
    for (const tpl of found) {
      out += text.slice(at, tpl.start) + renderTemplate(tpl);
      at = tpl.end;
    }
    text = out + text.slice(at);
  }
  return text
    .replace(/\[\[(?:[^\]|]*\|)?([^\]]*)\]\]/g, "$1")
    .replace(/\[https?:\/\/\S+\s([^\]]*)\]/g, "$1")
    .replace(/'''?/g, "")
    .replace(/<[^>]+>/g, "")
    .replace(/&nbsp;/g, " ")
    .replace(/\(\s*\)/g, "")
    .replace(/\s+([,.;:)])/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
}

function renderTemplate({ name, pos, named }) {
  const key = name.toLowerCase();
  if (LABEL_TEMPLATES.has(key)) {
    // {{lb|en|informal|_|chiefly|UK}}: the first is a language code, "_" a join.
    const words = (["lb", "lbl", "label"].includes(key) ? pos.slice(1) : pos).filter((w) => w && w !== "_" && w !== "and" && w !== "or");
    return words.length ? `(${words.map(plainText).join(", ")})` : "";
  }
  if (WORD_TEMPLATES.has(key)) {
    // {{l|en|word|shown}} and its kin start with a language code; {{w|Page|shown}}
    // does not; {{taxfmt|Malus|genus}} shows its first argument only.
    if (["taxfmt", "taxlink", "vern", "nowrap", "smallcaps", "1", "upright"].includes(key)) return plainText(pos[0] || "");
    if (["w", "wp"].includes(key)) return plainText(pos[1] || pos[0] || "");
    return plainText(named.alt || pos[2] || pos[1] || "");
  }
  // {{plural of|en|apple}}, {{alternative form of|en|colour}}
  if (/ of$/.test(key) && pos[1]) return `${name} ${plainText(pos[1])}`;
  return "";
}

/** The section of a page in one language (`==English==` to the next `==…==`). */
export function languageSection(wikitext, name) {
  const text = String(wikitext ?? "");
  const head = new RegExp(`^==\\s*${name}\\s*==\\s*$`, "m");
  const m = text.match(head);
  if (!m) return "";
  const rest = text.slice(m.index + m[0].length);
  const next = rest.search(/^==[^=].*==\s*$/m);
  return next < 0 ? rest : rest.slice(0, next);
}

const POS = {
  noun: "noun", verb: "verb", adjective: "adjective", adverb: "adverb", pronoun: "pronoun",
  preposition: "preposition", conjunction: "conjunction", interjection: "interjection",
  "proper noun": "proper noun", numeral: "numeral", determiner: "determiner", particle: "particle",
  phrase: "phrase", "prepositional phrase": "phrase", idiom: "idiom", proverb: "proverb",
  classifier: "classifier", counter: "counter", "phrasal verb": "phrasal verb", article: "article",
};

/** `{{zh-see|銀行}}`, `{{ja-see-kango|林檎}}`: the page that holds the entry. */
export function seeAlso(section) {
  for (const tpl of templates(section)) {
    if (/^(zh|ja)-see(-kango)?$/.test(tpl.name) && tpl.pos[0]) return tpl.pos[0];
  }
  return null;
}

const STOP = new Set("the a an of to in on or and for by with as is be any that which from into its it this one some used who".split(" "));
const tokens = (text) => new Set(String(text).toLowerCase().match(/[a-z]{3,}/g)?.filter((w) => !STOP.has(w)) || []);

/**
 * The senses of a word on an en.wiktionary page: `[{pos, en, vi}]`, at most
 * `limit`, and at most three from one part of speech so a word that is a noun
 * and a verb shows both. `vi` comes from the page's translation tables
 * ({{t|vi|…}}), attached to the sense whose gloss its table's heading matches;
 * a table that matches no sense is left out rather than guessed at.
 */
export function parseSenses(wikitext, language = "en", { limit = 5 } = {}) {
  const section = languageSection(wikitext, LANGS[language]?.name || language);
  const all = [];
  const tables = [];
  let pos = "";
  let table = null;
  for (const line of section.split("\n")) {
    const header = line.match(/^(=+)\s*(.+?)\s*\1\s*$/);
    if (header) {
      const name = header[2].toLowerCase();
      if (POS[name]) pos = POS[name];
      else if (header[1].length <= 3 && /^etymology/.test(name)) pos = "";
      table = null;
      continue;
    }
    const sense = line.match(/^(#{1,2})(?![:*#])\s*(.*)$/);
    if (sense && pos) {
      const en = plainText(sense[2]);
      if (en && !/^\(.*\)$/.test(en) && !all.some((s) => s.pos === pos && s.en === shorten(en))) all.push({ pos, en: shorten(en), vi: [], depth: sense[1].length, words: tokens(en) });
      continue;
    }
    const top = line.match(/\{\{trans-top\|([^}]*)\}\}/);
    if (top && pos) {
      table = { pos, gloss: plainText(top[1].replace(/^id=[^|]*\|?/, "")), vi: [] };
      tables.push(table);
    }
    if (/\{\{trans-bottom\}\}/.test(line)) table = null;
    if (table && /^\*\s*Vietnamese\s*:/.test(line)) {
      for (const tpl of templates(line)) {
        if (/^t(t)?\+?(-check)?$/.test(tpl.name) && tpl.pos[0] === "vi" && tpl.pos[1]) {
          const word = plainText(tpl.named.alt || tpl.pos[1]);
          // Hán-Nôm spellings are listed beside the Quốc ngữ word; not a meaning.
          if (word && !/[㐀-鿿]/.test(word) && !table.vi.includes(word)) table.vi.push(word);
        }
      }
    }
  }
  for (const tbl of tables) {
    if (!tbl.vi.length) continue;
    const want = tokens(tbl.gloss);
    let best = null;
    let score = 0;
    for (const s of all) {
      if (s.pos !== tbl.pos) continue;
      let hit = 0;
      for (const w of want) if (s.words.has(w)) hit++;
      const value = hit / Math.max(1, want.size);
      if (value > score) [best, score] = [s, value];
    }
    if (best && score >= 0.5) for (const w of tbl.vi) if (!best.vi.includes(w)) best.vi.push(w);
  }
  // The sub-senses ## of a sense # are its specific meanings; a bare # whose
  // sub-senses carry the translations is the less useful of the two.
  const picked = [];
  const perPos = {};
  for (const s of all) {
    if (picked.length >= limit) break;
    if ((perPos[s.pos] || 0) >= 3) continue;
    perPos[s.pos] = (perPos[s.pos] || 0) + 1;
    picked.push(s);
  }
  for (const s of all) {
    if (picked.length >= limit) break;
    if (!picked.includes(s)) picked.push(s);
  }
  const order = new Map(all.map((s, i) => [s, i]));
  return picked
    .sort((a, b) => order.get(a) - order.get(b))
    .map(({ pos: p, en, vi }) => ({ pos: p, en, vi: vi.join(", ") }));
}

/** A gloss short enough to read in a list: its first clause, under ~110 characters. */
function shorten(text) {
  if (text.length <= 110) return text;
  const cut = text.slice(0, 110);
  const at = Math.max(cut.lastIndexOf("; "), cut.lastIndexOf(", "));
  return (at > 40 ? cut.slice(0, at) : cut.slice(0, cut.lastIndexOf(" "))) + "…";
}

// Accent labels as en.wiktionary writes them.
const US = /^(us|ga|genam|general american|american|ca|canada|north american)$/i;
const UK = /^(uk|rp|ssb|british|received pronunciation|southern england|england)$/i;

/**
 * IPA and pronunciation files for the US and UK: `{ipa: {us, uk}, audio: [{file,
 * accent}]}`. A transcription with no accent label stands for both.
 */
export function parsePronunciation(wikitext, language = "en") {
  const section = languageSection(wikitext, LANGS[language]?.name || language);
  const ipa = { us: "", uk: "" };
  const audio = [];
  const accents = (value) => String(value || "").split(/[,;]/).map((a) => a.split("!")[0].trim());
  for (const tpl of templates(section)) {
    if (tpl.name === "IPA" && tpl.pos[0] === language) {
      const first = tpl.pos.slice(1).find((p) => /^\/.*\/$/.test(p)) || tpl.pos.slice(1).find((p) => /^\[.*\]$/.test(p));
      if (!first) continue;
      const a = accents(tpl.named.a);
      const isUs = !tpl.named.a || a.some((x) => US.test(x));
      const isUk = !tpl.named.a || a.some((x) => UK.test(x));
      if (isUs && !ipa.us) ipa.us = first;
      if (isUk && !ipa.uk) ipa.uk = first;
    } else if (tpl.name === "audio" && tpl.pos[0] === language && tpl.pos[1]) {
      const file = tpl.pos[1].trim();
      const a = accents(tpl.named.a);
      let accent = "";
      if (a.some((x) => US.test(x)) || /^en-us-/i.test(file)) accent = "us";
      else if (a.some((x) => UK.test(x)) || /^en-(uk|gb)-/i.test(file)) accent = "uk";
      if (!audio.some((x) => x.file === file)) audio.push({ file, accent });
    }
  }
  return { ipa, audio };
}

/** vi.wiktionary's glosses for a word: `[{pos, vi}]` from its `{{-eng-}}` part. */
export function parseViSenses(wikitext, language = "en", { limit = 3 } = {}) {
  const code = { en: "eng", fr: "fra", de: "deu", es: "spa", it: "ita", pt: "por", ru: "rus" }[language];
  if (!code) return [];
  const text = String(wikitext ?? "");
  const start = text.indexOf(`{{-${code}-}}`);
  if (start < 0) return [];
  const rest = text.slice(start + code.length + 6);
  const end = rest.search(/^\{\{-[a-z]{3}-\}\}\s*$/m);
  const section = end < 0 ? rest : rest.slice(0, end);
  const VI_POS = { noun: "noun", verb: "verb", "intr-verb": "verb", "tr-verb": "verb", adj: "adjective", adv: "adverb", pron: "pronoun", prep: "preposition", conj: "conjunction", intj: "interjection", phrase: "phrase" };
  const out = [];
  let pos = "";
  for (const line of section.split("\n")) {
    const head = line.match(/^\{\{-([a-z-]+)-\}\}/);
    if (head) {
      pos = VI_POS[head[1]] || "";
      continue;
    }
    const sense = line.match(/^#(?![:*#])\s*(.*)$/);
    if (sense && pos && out.length < limit) {
      const vi = shorten(plainText(sense[1]).replace(/\.$/, ""));
      if (vi) out.push({ pos, vi });
    }
  }
  return out;
}

// ---------------------------------------------------------------------------
// Tatoeba and Commons
// ---------------------------------------------------------------------------

/**
 * Example sentences that carry a Vietnamese translation: `[{id, text, vi,
 * owner, viOwner}]`, in Tatoeba's order of relevance, unapproved ones left out, a direct
 * translation preferred over one reached through a third language.
 */
export function parseTatoeba(body, { limit = 3, maxLength = 90 } = {}) {
  const out = [];
  for (const s of body?.data || []) {
    if (s.is_unapproved || !s.text || s.text.length > maxLength) continue;
    const trans = (s.translations || []).flat().filter((x) => x && x.lang === "vie" && !x.is_unapproved && x.text);
    trans.sort((a, b) => Number(Boolean(b.is_direct)) - Number(Boolean(a.is_direct)));
    if (!trans.length) continue;
    out.push({ id: s.id, text: s.text, vi: trans[0].text, viId: trans[0].id, owner: s.owner || "", viOwner: trans[0].owner || "" });
  }
  return out.slice(0, limit);
}

const stripHtml = (html) => String(html ?? "").replace(/<[^>]+>/g, "").replace(/&amp;/g, "&").replace(/\s+/g, " ").trim();

/** The address a sheet stores for a Commons file — the same shape as the workbook's. */
export const filePath = (file, width = 0) =>
  `https://commons.wikimedia.org/wiki/Special:FilePath/${encodeURIComponent(file.replace(/^File:/, "").replace(/ /g, "_"))}${width ? `?width=${width}` : ""}`;

/** Pictures from a Commons search: `[{file, thumb, url, author, licence}]`. */
export function parseCommons(body, { limit = 8 } = {}) {
  const pages = body?.query?.pages;
  const list = Array.isArray(pages) ? pages : Object.values(pages || {});
  return list
    .sort((a, b) => (a.index ?? 0) - (b.index ?? 0))
    .map((p) => {
      const info = p.imageinfo?.[0];
      if (!info?.thumburl || !/\.(jpe?g|png|webp|gif|svg|tiff?)$/i.test(p.title || "")) return null;
      const meta = info.extmetadata || {};
      const file = p.title.replace(/^File:/, "");
      return {
        file,
        thumb: info.thumburl,
        url: filePath(file, 500),
        author: stripHtml(meta.Artist?.value) || "",
        licence: stripHtml(meta.LicenseShortName?.value) || "",
      };
    })
    .filter(Boolean)
    .slice(0, limit);
}

// ---------------------------------------------------------------------------
// Credits
// ---------------------------------------------------------------------------

/** One line naming every source a word's accepted values came from. */
export function creditLine(used) {
  const parts = [];
  if (used.wiktionary) parts.push("Wiktionary (CC BY-SA 4.0)");
  for (const s of used.tatoeba || []) parts.push(`Tatoeba #${s.id}${s.viId ? `/#${s.viId}` : ""} (CC BY 2.0 FR)`);
  if (used.audio) parts.push(`Wikimedia Commons: ${used.audio} (CC BY-SA)`);
  if (used.image) {
    const by = [used.image.author, used.image.licence].filter(Boolean).join(", ");
    parts.push(`Wikimedia Commons: ${used.image.file}${by ? ` — ${by}` : ""}`);
  }
  return parts.join("; ");
}

/** A credit line merged into what a source cell already says, without repeats. */
export function mergeCredit(existing, line) {
  const have = String(existing ?? "").split(/;\s*/).map((s) => s.trim()).filter(Boolean);
  for (const part of String(line).split(/;\s*/).map((s) => s.trim()).filter(Boolean)) {
    if (!have.includes(part)) have.push(part);
  }
  return have.join("; ");
}

// ---------------------------------------------------------------------------
// The network
// ---------------------------------------------------------------------------

const WIKT = (host, page) =>
  `https://${host}/w/api.php?action=parse&format=json&formatversion=2&redirects=1&prop=wikitext&origin=*&page=${encodeURIComponent(page)}`;
const TATOEBA = (lang, word) =>
  `https://api.tatoeba.org/unstable/sentences?lang=${lang}&q=${encodeURIComponent(word)}&trans:lang=vie&sort=relevance&limit=20`;
const COMMONS = (word) =>
  "https://commons.wikimedia.org/w/api.php?action=query&format=json&formatversion=2&origin=*" +
  `&generator=search&gsrnamespace=6&gsrlimit=12&gsrsearch=${encodeURIComponent(`${word} filetype:bitmap`)}` +
  "&prop=imageinfo&iiprop=url|extmetadata&iiurlwidth=240&iiextmetadatafilter=LicenseShortName|Artist";

/** At most `n` requests in flight; the rest wait their turn. */
export function limiter(n = 3) {
  let active = 0;
  const waiting = [];
  const next = () => {
    if (active >= n || !waiting.length) return;
    active++;
    const { job, resolve, reject } = waiting.shift();
    job().then(resolve, reject).finally(() => {
      active--;
      next();
    });
  };
  return (job) => new Promise((resolve, reject) => {
    waiting.push({ job, resolve, reject });
    next();
  });
}

const slot = limiter(3);

async function getJson(url, fetcher) {
  return slot(async () => {
    const response = await fetcher(url, { headers: { Accept: "application/json" } });
    if (response.status === 404) return null;
    if (!response.ok) throw Object.assign(new Error(`HTTP ${response.status}`), { status: response.status });
    return response.json();
  });
}

async function wikitext(host, page, fetcher) {
  const body = await getJson(WIKT(host, page), fetcher);
  // A missing page is an error body, not a 404.
  return body?.parse?.wikitext ?? "";
}

// ---- the cache: one entry per word, language and kind, in IndexedDB --------

const DB = "sc-suggest";
let dbOpen = null;
function db() {
  if (!globalThis.indexedDB) return Promise.resolve(null);
  dbOpen ??= new Promise((resolve) => {
    try {
      const req = indexedDB.open(DB, 1);
      req.onupgradeneeded = () => req.result.createObjectStore("words");
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
  return dbOpen;
}
async function cached(key, make) {
  const store = await db();
  if (store) {
    const hit = await new Promise((resolve) => {
      try {
        const req = store.transaction("words").objectStore("words").get(key);
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => resolve(undefined);
      } catch {
        resolve(undefined);
      }
    });
    // A week: Wiktionary changes, and a word looked up once is cheap to redo.
    if (hit && Date.now() - hit.at < 7 * 864e5) return hit.value;
  }
  const value = await make();
  if (store) {
    try {
      store.transaction("words", "readwrite").objectStore("words").put({ at: Date.now(), value }, key);
    } catch {
      /* a full or blocked store only costs a second lookup */
    }
  }
  return value;
}

/**
 * Everything there is to suggest for one word: `{senses, ipa, audio, examples,
 * images, errors}`. A source that fails leaves its part empty and its name in
 * `errors`, so one being down never hides the others.
 */
export async function lookup(word, language, { want = {}, fetcher = globalThis.fetch?.bind(globalThis) } = {}) {
  const cover = coverage(language);
  if (!cover || !word.trim()) return { senses: [], ipa: { us: "", uk: "" }, audio: [], examples: [], images: [], errors: [] };
  const term = word.trim();
  const key = (kind) => `${language}:${kind}:${term}`;
  const errors = [];
  const guard = (name, promise, empty) =>
    promise.catch((error) => {
      errors.push({ source: name, offline: error?.name === "TypeError", status: error?.status });
      return empty;
    });

  const wikt = guard(
    "wiktionary",
    cached(key("wikt"), async () => {
      let text = await wikitext("en.wiktionary.org", term, fetcher);
      let senses = parseSenses(text, language);
      // 银行 points at 銀行, りんご at 林檎: the entry is on the other page.
      const other = !senses.length && seeAlso(languageSection(text, LANGS[language].name));
      if (other) {
        text = await wikitext("en.wiktionary.org", other, fetcher);
        senses = parseSenses(text, language);
      }
      return { senses, ...(cover.ipa ? parsePronunciation(text, language) : { ipa: { us: "", uk: "" }, audio: [] }) };
    }),
    { senses: [], ipa: { us: "", uk: "" }, audio: [] },
  );
  const vi = cover.vi
    ? guard("wiktionary", cached(key("viwikt"), async () => parseViSenses(await wikitext("vi.wiktionary.org", term, fetcher), language)), [])
    : Promise.resolve([]);
  const examples =
    cover.examples && want.examples !== false
      ? guard("tatoeba", cached(key("tatoeba"), async () => parseTatoeba(await getJson(TATOEBA(LANGS[language].tatoeba, term), fetcher))), [])
      : Promise.resolve([]);
  const images =
    cover.images && want.images
      ? guard("commons", cached(key("commons"), async () => parseCommons(await getJson(COMMONS(term), fetcher))), [])
      : Promise.resolve([]);

  const [w, v, ex, im] = await Promise.all([wikt, vi, examples, images]);
  return { senses: mergeSenses(w.senses, v), ipa: w.ipa, audio: w.audio, examples: ex, images: im, errors };
}

/**
 * en.wiktionary's senses with vi.wiktionary's added: a Vietnamese gloss that
 * no English sense already carries becomes a choice of its own, so a word whose
 * translation tables say nothing still offers one. At most five in all.
 */
export function mergeSenses(en, vi, limit = 5) {
  const out = en.map((s) => ({ ...s, source: "en" }));
  const have = new Set(out.flatMap((s) => s.vi.split(/,\s*/)).map((w) => w.toLowerCase()).filter(Boolean));
  const extra = vi.filter((s) => !have.has(s.vi.toLowerCase())).map((s) => ({ pos: s.pos, en: "", vi: s.vi, source: "vi" }));
  // Keep room for two Vietnamese-only senses when the English ones carry none.
  const room = out.some((s) => s.vi) ? 1 : 2;
  const keep = Math.max(0, Math.min(out.length, limit - Math.min(room, extra.length)));
  return [...out.slice(0, keep), ...extra].slice(0, limit);
}
