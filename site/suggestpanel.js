/**
 * Create sheet's "Gợi ý": what Wiktionary, Tatoeba and Commons have for a word,
 * offered field by field, written into the sheet only when the learner says so.
 *
 * Nothing is picked for them: a sense, an example and a picture are choices; a
 * choice becomes a suggestion beside the cell's current value, marked until it
 * is used, edited or skipped; and a cell the learner typed is replaced only by
 * an explicit "Thay". The sources each accepted value came from are written
 * into the sheet as a credit (Note or Source column, else a hidden Nguồn one).
 *
 * The data is site/suggest.js's; the page hands this an `editor` (mountSuggest).
 */

import { escapeHtml } from "./anki.js";
import { t } from "./i18n.js";
import { icon } from "./icons.js";
import { columnRoles, guessMapping, listLanguage, loadReader, roleOf } from "./wordlist.js";
import { coverage, creditLine, filePath, lookup, mergeCredit } from "./suggest.js";

const CONSENT = "sc-suggest-consent";
const AHEAD = 5;

let editor = null;
let box = null;
const looked = new Map();
const credits = new Map();
const ours = new Map();
const view = { queue: [], at: 0, accent: "us", choice: {}, fields: {} };

const $in = (sel) => box.querySelector(sel);

function consented() {
  try {
    return localStorage.getItem(CONSENT) === "1";
  } catch {
    return false;
  }
}
function consent() {
  try {
    localStorage.setItem(CONSENT, "1");
  } catch {
    /* asked again next visit, which is no harm */
  }
}

// ---------------------------------------------------------------------------
// The sheet, as this panel sees it
// ---------------------------------------------------------------------------

function columns() {
  return editor.sheet().columns;
}
function wordAt() {
  const roles = columnRoles(columns());
  return roles.word ?? guessMapping(columns(), 1)[0];
}
const rowIndex = (id) => editor.sheet().rows.findIndex((r) => r.id === id);
const rowOf = (id) => editor.sheet().rows[rowIndex(id)];
const wordOf = (id) => String(rowOf(id)?.values[wordAt()] ?? "").trim();
const languageOf = (id) => listLanguage(columns(), [wordOf(id)], wordAt());

/** The columns each kind of suggestion goes to by default. */
function targets(language) {
  const roles = columnRoles(columns());
  const cjk = ["zh", "ja", "ko"].includes(language);
  return {
    meaning: roles.meaning,
    reading: cjk ? (roles.reading ?? roles.ipa) : (roles.ipa ?? roles.reading),
    example: roles.example,
    exampleMeaning: roles.exampleMeaning,
    audio: roles.audio,
    image: roles.image,
  };
}

/** Whether the sheet has anywhere a suggestion could go. */
export function canSuggest() {
  const roles = columnRoles(columns());
  return ["meaning", "reading", "ipa", "example", "audio", "image"].some((r) => roles[r] !== undefined);
}

// ---------------------------------------------------------------------------
// Looking words up
// ---------------------------------------------------------------------------

function fetchFor(id) {
  const word = wordOf(id);
  const language = languageOf(id);
  const key = keyOf(id);
  if (!word) return Promise.resolve(null);
  if (!looked.has(key)) {
    const tg = targets(language);
    const job = (async () => {
      const found = await lookup(word, language, { want: { examples: tg.example !== undefined, images: tg.image !== undefined } });
      if (["zh", "ko"].includes(language) && tg.reading !== undefined) {
        try {
          const read = await loadReader(language);
          found.reading = read ? read(word) : "";
        } catch {
          found.reading = "";
        }
      }
      return found;
    })().catch(() => ({ senses: [], ipa: { us: "", uk: "" }, audio: [], examples: [], images: [], errors: [{ source: "all", offline: !navigator.onLine }] }));
    looked.set(key, job);
    job.then(() => {
      settled.add(key);
      paintProgress();
    });
  }
  return looked.get(key);
}

function prefetch() {
  for (const id of view.queue.slice(view.at, view.at + AHEAD + 1)) fetchFor(id);
}

const settled = new Set();
const keyOf = (id) => `${languageOf(id)}:${wordOf(id)}`;
const doneCount = () => view.queue.filter((id) => settled.has(keyOf(id))).length;

function paintProgress() {
  if (!box?.open || view.queue.length < 2) return;
  $in("#sg-progress").textContent = t("sgProgress", doneCount(), view.queue.length);
}

// ---------------------------------------------------------------------------
// Drawing
// ---------------------------------------------------------------------------

function build() {
  box = document.createElement("dialog");
  box.id = "suggestbox";
  box.className = "donebox pickbox wtbox sgbox";
  box.setAttribute("aria-labelledby", "sg-title");
  box.innerHTML = `
    <div class="done-head">
      <strong id="sg-title"></strong>
      <span class="small muted" id="sg-progress"></span>
      <button class="iconbtn" data-close type="button" title="${escapeHtml(t("close"))}" aria-label="${escapeHtml(t("close"))}">${icon("x")}</button>
    </div>
    <div class="wt-body" id="sg-body"></div>
    <div class="wt-foot" id="sg-foot"></div>`;
  document.body.append(box);
  box.querySelector("[data-close]").addEventListener("click", () => box.close());
  box.addEventListener("close", () => editor.closed?.());
  box.addEventListener("click", onClick);
  box.addEventListener("input", (e) => {
    const kind = e.target.closest?.(".sg-field")?.dataset.kind;
    if (!kind || !e.target.matches(".sg-input")) return;
    const f = view.fields[kind];
    if (!f) return;
    f.value = e.target.value;
    // Written over by hand, it is the learner's own text now.
    f.edited = true;
    e.target.classList.remove("sgval");
  });
  box.addEventListener("change", (e) => {
    const field = e.target.closest?.(".sg-field");
    if (field && e.target.matches(".sg-target select")) {
      view.fields[field.dataset.kind].target = Number(e.target.value);
      paint();
      return;
    }
    const pick = e.target.dataset?.pick;
    if (pick) {
      view.choice[pick] = Number(e.target.value);
      propose();
      paint();
    }
  });
}

const current = () => view.queue[view.at];

function onClick(e) {
  if (e.target === box) return box.close();
  const btn = e.target.closest("button");
  if (!btn) return;
  const act = btn.dataset.act;
  if (act === "consent") {
    consent();
    prefetch();
    return paint();
  }
  if (act === "decline") return box.close();
  if (act === "prev" || act === "next") return go(view.at + (act === "prev" ? -1 : 1));
  if (act === "done") return box.close();
  if (act === "retry") {
    const id = current();
    looked.delete(keyOf(id));
    settled.delete(keyOf(id));
    fetchFor(id);
    return paint();
  }
  if (act === "accent") {
    view.accent = btn.dataset.accent;
    propose();
    return paint();
  }
  if (act === "image") {
    view.choice.image = Number(btn.dataset.i);
    propose();
    return paint();
  }
  const kind = btn.closest(".sg-field")?.dataset.kind;
  if (act === "use" && kind) {
    use(kind);
    return paint();
  }
  if (act === "skip" && kind) {
    view.fields[kind].done = "skipped";
    return paint();
  }
  if (act === "useall") {
    for (const [k, f] of Object.entries(view.fields)) if (f.value && !f.done && !typed(f)) use(k);
    paint();
    if (view.at < view.queue.length - 1) go(view.at + 1);
  }
}

function go(at) {
  view.at = Math.max(0, Math.min(view.queue.length - 1, at));
  view.choice = {};
  view.fields = {};
  editor.showRow?.(rowIndex(current()));
  prefetch();
  paint();
}

/** The value now in a field's target cell. */
function cellNow(f) {
  const row = rowOf(current());
  return f.target >= 0 ? String(row?.values[f.target] ?? "") : "";
}
/** Whether the target cell holds something the learner wrote (not a value from here). */
function typed(f) {
  const now = cellNow(f).trim();
  return Boolean(now) && ours.get(`${current()}:${f.target}`) !== now;
}

/** The suggestion each field carries, from the choices made and the accent. */
let result = null;
function propose() {
  if (!result) return;
  const lang = languageOf(current());
  const tg = targets(lang);
  const set = (kind, value, source) => {
    if (tg[kind] === undefined && !view.fields[kind]) return;
    const f = (view.fields[kind] ??= { target: tg[kind] ?? -1, value: "", edited: false, done: "" });
    if (f.edited || f.done) return;
    f.value = value;
    f.source = source;
  };
  const sense = result.senses[view.choice.sense];
  // The Vietnamese when there is some (three words at most), else the English
  // gloss without its leading labels: "(countable)" is for the chooser, not the card.
  const meaning = sense && (sense.vi ? sense.vi.split(/,\s*/).slice(0, 3).join(", ") : sense.en.replace(/^(\([^)]*\)\s*)+/, ""));
  if (sense) set("meaning", meaning, { wiktionary: true });
  else set("meaning", "", null);
  if (result.reading) set("reading", result.reading, null);
  else if (result.ipa?.us || result.ipa?.uk) set("reading", result.ipa[view.accent] || result.ipa.us || result.ipa.uk, { wiktionary: true });
  const ex = result.examples[view.choice.example];
  set("example", ex ? ex.text : "", ex ? { tatoeba: [ex] } : null);
  set("exampleMeaning", ex ? ex.vi : "", ex ? { tatoeba: [ex] } : null);
  const audio = result.audio[view.choice.audio] ?? (view.choice.audio === undefined ? preferredAudio() : null);
  set("audio", audio ? filePath(audio.file) : "", audio ? { audio: audio.file } : null);
  const image = result.images[view.choice.image];
  set("image", image ? image.url : "", image ? { image } : null);
}

function preferredAudio() {
  return result.audio.find((a) => a.accent === view.accent) || null;
}

function use(kind) {
  const f = view.fields[kind];
  if (!f || f.target < 0 || !f.value) return;
  const id = current();
  editor.setCell(rowIndex(id), f.target, f.value);
  ours.set(`${id}:${f.target}`, f.value);
  f.done = "used";
  if (f.source && !f.edited) credit(id, f.source);
}

/** Records where an accepted value came from, in the sheet beside the word. */
function credit(id, source) {
  const used = credits.get(id) || { wiktionary: false, tatoeba: [], audio: "", image: null };
  if (source.wiktionary) used.wiktionary = true;
  for (const s of source.tatoeba || []) if (!used.tatoeba.some((x) => x.id === s.id)) used.tatoeba.push(s);
  if (source.audio) used.audio = source.audio;
  if (source.image) used.image = source.image;
  credits.set(id, used);
  const line = creditLine(used);
  if (!line) return;
  const roles = columnRoles(columns());
  const row = rowOf(id);
  let at = roles.source;
  if (at === undefined && roles.note !== undefined) {
    const note = String(row.values[roles.note] ?? "").trim();
    if (!note || ours.get(`${id}:${roles.note}`) === note) at = roles.note;
  }
  if (at === undefined) {
    at = columns().findIndex((c) => roleOf(c) === "source");
    if (at < 0) at = editor.addColumn(t("sgSourceColumn"), "side=hide");
  }
  const before = String(rowOf(id).values[at] ?? "");
  const value = ours.get(`${id}:${at}`) === before.trim() || !before.trim() ? line : mergeCredit(before, line);
  editor.setCell(rowIndex(id), at, value);
  ours.set(`${id}:${at}`, value);
}

function columnSelect(f) {
  const opts = columns()
    .map((c, i) => `<option value="${i}"${i === f.target ? " selected" : ""}>${escapeHtml(c.name || String(i + 1))}</option>`)
    .join("");
  return `<label class="sg-target"><span>${escapeHtml(t("sgInto"))}</span><select>${f.target < 0 ? '<option value="-1" selected>—</option>' : ""}${opts}</select></label>`;
}

function fieldLine(kind, hint = "") {
  const f = view.fields[kind];
  if (!f) return "";
  if (f.done === "used") return `<div class="sg-field sg-done" data-kind="${kind}">${icon("check")}<span>${escapeHtml(t("sgUsedIn", columns()[f.target]?.name || ""))}</span></div>`;
  if (f.done === "skipped") return `<div class="sg-field sg-done" data-kind="${kind}"><span class="muted">${escapeHtml(t("sgSkipped"))}</span></div>`;
  const now = cellNow(f);
  const isTyped = typed(f);
  const value = f.value;
  if (value && value.trim() === now.trim()) {
    return `<div class="sg-field sg-done" data-kind="${kind}">${icon("check")}<span>${escapeHtml(t("sgSame", columns()[f.target]?.name || ""))}</span></div>`;
  }
  return `<div class="sg-field" data-kind="${kind}">
    <div class="sg-fieldtop">${columnSelect(f)}<span class="sg-now"><span class="muted">${escapeHtml(t("sgNow"))}</span> ${
      now.trim() ? `<b>${escapeHtml(now)}</b>` : `<i class="muted">${escapeHtml(t("shEmptyWord"))}</i>`
    }</span></div>
    ${
      value
        ? `<div class="sg-fieldrow"><input class="sg-input${f.edited ? "" : " sgval"}" value="${escapeHtml(value)}" aria-label="${escapeHtml(t("sgSuggestion"))}" spellcheck="false">
      <button class="btn sg-use" type="button" data-act="use"${f.target < 0 ? " disabled" : ""}>${escapeHtml(t(isTyped ? "sgReplace" : "sgUse"))}</button>
      <button class="toolbtn sg-skip" type="button" data-act="skip">${escapeHtml(t("sgSkip"))}</button></div>`
        : `<p class="small muted sg-pickhint">${escapeHtml(hint)}</p>`
    }
  </div>`;
}

function errorsHtml(errors) {
  if (!errors?.length) return "";
  const offline = errors.some((e) => e.offline) || !navigator.onLine;
  const names = [...new Set(errors.map((e) => e.source))].map((s) => ({ wiktionary: "Wiktionary", tatoeba: "Tatoeba", commons: "Wikimedia Commons" })[s] || s);
  return `<p class="note sg-error">${escapeHtml(offline ? t("sgOffline") : t("sgFailed", names.join(", ")))}
    <button class="toolbtn" type="button" data-act="retry">${icon("rotate-cw")}<span>${escapeHtml(t("sgRetry"))}</span></button></p>`;
}

async function paint() {
  const id = current();
  const word = wordOf(id);
  const lang = languageOf(id);
  const cover = coverage(lang);
  $in("#sg-title").textContent = word ? t("sgTitleWord", word) : t("sgTitle");
  $in("#sg-progress").textContent = view.queue.length > 1 ? t("sgProgress", doneCount(), view.queue.length) : "";
  const body = $in("#sg-body");
  const foot = $in("#sg-foot");

  if (!consented()) {
    body.innerHTML = `<p class="sg-privacy">${icon("lock")}<span>${t("sgConsent")}</span></p>`;
    foot.innerHTML = `<button class="toolbtn" type="button" data-act="decline">${escapeHtml(t("sgDecline"))}</button>
      <button class="btn" type="button" data-act="consent">${escapeHtml(t("sgAgree"))}</button>`;
    return;
  }
  const nav = `${view.queue.length > 1 ? `<button class="navbtn" type="button" data-act="prev" title="${escapeHtml(t("shPrevWord"))}" aria-label="${escapeHtml(t("shPrevWord"))}"${view.at === 0 ? " disabled" : ""}>${icon("arrow-up")}</button>` : ""}
      <button class="toolbtn" type="button" data-act="useall">${icon("check")}<span>${escapeHtml(t("sgUseAll"))}</span></button>
      ${
        view.at < view.queue.length - 1
          ? `<button class="btn" type="button" data-act="next"><span>${escapeHtml(t("sgNext"))}</span>${icon("arrow-right")}</button>`
          : `<button class="btn" type="button" data-act="done">${escapeHtml(t("shDone"))}</button>`
      }`;
  foot.innerHTML = nav;
  if (!word) {
    body.innerHTML = `<p class="muted">${escapeHtml(t("sgNoWord"))}</p>`;
    return;
  }
  if (!cover) {
    body.innerHTML = `<p class="muted">${escapeHtml(t("sgNoLanguage"))}</p>`;
    return;
  }
  const job = fetchFor(id);
  let ready = null;
  job.then((r) => (ready = r));
  await Promise.resolve();
  if (!ready) {
    body.innerHTML = `<p class="sg-loading"><span class="spinner" aria-hidden="true"></span>${escapeHtml(t("sgLooking", word))}</p>`;
    ready = await job;
    if (current() !== id || !box.open) return;
  }
  result = ready;
  propose();
  const tg = targets(lang);
  const parts = [];
  if (!cover.vi) parts.push(`<p class="note small">${escapeHtml(t("sgCjkNote"))}</p>`);
  parts.push(errorsHtml(result.errors));

  if (tg.meaning !== undefined || view.fields.meaning) {
    const list = result.senses
      .map(
        (s, i) => `<label class="sg-choice"><input type="radio" name="sg-sense" data-pick="sense" value="${i}"${view.choice.sense === i ? " checked" : ""}>
        <span><span class="sg-pos">${escapeHtml(s.pos)}</span>${s.vi ? `<b class="sg-vi">${escapeHtml(s.vi)}</b>` : ""}${s.en ? `<span class="sg-en">${escapeHtml(s.en)}</span>` : ""}
        <span class="sg-src">${s.source === "vi" ? "vi.wiktionary" : "en.wiktionary"}</span></span></label>`,
      )
      .join("");
    parts.push(`<section class="sg-sec"><h3>${escapeHtml(t("sgMeaning"))}</h3>
      ${list ? `<div class="sg-choices" role="radiogroup">${list}</div>` : `<p class="small muted">${escapeHtml(t("sgNoSenses"))}</p>`}
      ${fieldLine("meaning", t("sgPickSense"))}</section>`);
  }
  if ((tg.reading !== undefined || view.fields.reading) && (result.reading || result.ipa?.us || result.ipa?.uk)) {
    const accents = result.reading
      ? ""
      : `<div class="seg sg-accent" role="group">${["us", "uk"]
          .map((a) => `<button type="button" data-act="accent" data-accent="${a}" aria-pressed="${view.accent === a}"${result.ipa[a] ? "" : " disabled"}>${a.toUpperCase()} <span class="mono">${escapeHtml(result.ipa[a] || "—")}</span></button>`)
          .join("")}</div>`;
    parts.push(`<section class="sg-sec"><h3>${escapeHtml(result.reading ? t(lang === "zh" ? "sgPinyin" : "sgRoman") : "IPA")}</h3>${accents}${fieldLine("reading")}</section>`);
  }
  if (tg.example !== undefined && cover.examples) {
    const list = result.examples
      .map(
        (s, i) => `<label class="sg-choice"><input type="radio" name="sg-ex" data-pick="example" value="${i}"${view.choice.example === i ? " checked" : ""}>
        <span><span class="sg-ex">${escapeHtml(s.text)}</span><span class="sg-vi2">${escapeHtml(s.vi)}</span><span class="sg-src">Tatoeba #${s.id}</span></span></label>`,
      )
      .join("");
    parts.push(`<section class="sg-sec"><h3>${escapeHtml(t("sgExample"))}</h3>
      ${list ? `<div class="sg-choices" role="radiogroup">${list}</div><p class="small muted">${escapeHtml(t("sgCheckExample"))}</p>` : `<p class="small muted">${escapeHtml(t("sgNoExamples"))}</p>`}
      ${fieldLine("example", t("sgPickExample"))}${fieldLine("exampleMeaning", t("sgPickExample"))}</section>`);
  }
  if (tg.audio !== undefined && cover.audio && result.audio.length) {
    const chosen = view.choice.audio ?? result.audio.indexOf(preferredAudio());
    const list = result.audio
      .slice(0, 4)
      .map(
        (a, i) => `<label class="sg-choice sg-audio"><input type="radio" name="sg-au" data-pick="audio" value="${i}"${chosen === i ? " checked" : ""}>
        <span><span class="sg-pos">${escapeHtml(a.accent ? a.accent.toUpperCase() : "—")}</span><span class="sg-en">${escapeHtml(a.file)}</span>
        <audio controls preload="none" src="${escapeHtml(filePath(a.file))}"></audio></span></label>`,
      )
      .join("");
    parts.push(`<section class="sg-sec"><h3>${escapeHtml(t("sgAudio"))}</h3><div class="sg-choices">${list}</div>${fieldLine("audio")}</section>`);
  }
  if (tg.image !== undefined && cover.images) {
    const grid = result.images
      .map(
        (im, i) => `<button type="button" class="sg-thumb" data-act="image" data-i="${i}" aria-pressed="${view.choice.image === i}" title="${escapeHtml([im.file, im.author, im.licence].filter(Boolean).join(" — "))}">
        <img src="${escapeHtml(im.thumb)}" alt="${escapeHtml(im.file)}" loading="lazy" referrerpolicy="no-referrer"></button>`,
      )
      .join("");
    parts.push(`<section class="sg-sec"><h3>${escapeHtml(t("sgImage"))}</h3>
      ${grid ? `<div class="sg-thumbs">${grid}</div>` : `<p class="small muted">${escapeHtml(t("sgNoImages"))}</p>`}
      ${fieldLine("image", t("sgPickImage"))}</section>`);
  }
  parts.push(`<p class="small muted sg-credit">${escapeHtml(t("sgCreditNote"))}</p>`);
  const scroll = body.scrollTop;
  body.innerHTML = parts.join("");
  body.scrollTop = scroll;
}

// ---------------------------------------------------------------------------

/**
 * Wires the panel to the page. `editor` is the page's side of it:
 *   sheet()                the sheet being edited
 *   setCell(k, c, value)   writes one cell (one undo step), repaints, saves
 *   addColumn(name, cell)  adds a column at the end; returns its index
 *   showRow(k)             brings word k into view
 *   closed()               called when the panel closes
 */
export function mountSuggest(page) {
  editor = page;
  return { open, canSuggest };
}

/** Opens suggestions for the words at these row indices, the first one first. */
export function open(rows) {
  if (!box) build();
  const sheet = editor.sheet();
  view.queue = rows.map((k) => sheet.rows[k]?.id).filter((id) => id && String(sheet.rows[rowIndex(id)].values[wordAt()] ?? "").trim());
  if (!view.queue.length) {
    editor.toast(t("sgNoWord"), "bad");
    return;
  }
  view.at = 0;
  view.choice = {};
  view.fields = {};
  if (!box.open) box.showModal();
  if (consented()) prefetch();
  paint();
}
