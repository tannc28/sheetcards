/**
 * The landing page: the demo in the hero, and the sections rising into view.
 *
 * The demo is the page's one claim — this row becomes this card — so it is made
 * of the real thing. `home-cards.js` is written by scripts/build_site.py, which
 * runs the add-on's own card_layout.py over three rows of the example workbook;
 * here those templates are filled by the same `renderCard` and framed by the same
 * `cardDoc` the preview uses. No Pyodide: the Python already ran at build time.
 *
 * It plays by itself, which an animation that changes on its own must let you
 * stop (WCAG 2.2.2): the button beside the examples pauses it, and anything you
 * do to the demo — turning the card, picking an example — stops it too, since by
 * then you are the one driving. With reduced motion asked for it never starts,
 * and the card turns without the flip.
 */

import { renderCard, escapeHtml } from "./anki.js";
import { cardDoc } from "./cardframe.js";
import { t } from "./i18n.js";
import { icon } from "./icons.js";
import { dark, onRepaint } from "./page.js";
import { CARDS } from "./home-cards.js";

const $ = (sel) => document.querySelector(sel);

const still = matchMedia("(prefers-reduced-motion: reduce)");
const FRONT_FOR = 2800; // ms the question stays up before the card turns
const BACK_FOR = 3600; // ms the answer stays up before the next example

const state = {
  at: 0,
  turned: false,
  playing: !still.matches,
  visible: true,
  timer: 0,
};

// The rendered faces of every example, built once: switching examples then
// shows a frame that is already drawn, instead of reloading one in view.
const rendered = CARDS.map((card) =>
  renderCard(card.template, card.values, { ordinal: 1 }),
);

/**
 * The card's own document, as the preview builds it, adjusted for a card that
 * is looked at rather than studied: no scrollbars (the frame is sized to fit),
 * no "TTS voices" list (it lists the voices of the device reviewing the card,
 * and this page is not one), and no scripts — the ones a card carries are for
 * speaking, typing and that list, and a frame nobody can click has no use for
 * them. Taken out rather than blocked, so the console is not a wall of refusals.
 */
function faceDoc(index, tab) {
  const { front, back } = rendered[index];
  return cardDoc({ front, back, tab, dark: dark() })
    .replace(/<script\b[\s\S]*?<\/script>/gi, "")
    .replace(
      '<meta charset="utf-8">',
      '<meta charset="utf-8"><style>html, body { overflow: hidden; } ' +
        ".sc-tts-debug { display: none; }</style>",
    );
}

function frame(index, tab) {
  // Scripts allowed only so a card's inline handlers (a hint's onclick) do not
  // fill the console with refusals; without allow-same-origin the frame still
  // cannot reach this page, and nothing can be clicked in it anyway.
  return (
    `<iframe class="face ${tab}" sandbox="allow-scripts" tabindex="-1" ` +
    `title="${escapeHtml(t(tab === "front" ? "demoFront" : "demoBack"))}" ` +
    `srcdoc="${escapeHtml(faceDoc(index, tab))}"></iframe>`
  );
}

function buildCards() {
  $("#demo-card").innerHTML = CARDS.map(
    (_, i) =>
      `<div class="flip${i === state.at ? " active" : ""}${
        i === state.at && state.turned ? " turned" : ""
      }" data-card="${i}" ${i === state.at ? "" : "inert"}>` +
      frame(i, "front") +
      frame(i, "back") +
      "</div>",
  ).join("");
}

function buildTabs() {
  $("#demo-tabs").innerHTML = CARDS.map(
    (card, i) =>
      `<button type="button" data-pick="${i}" aria-pressed="${i === state.at}">` +
      `${escapeHtml(t(card.label))}</button>`,
  ).join("");
  const play = $("#demo-play");
  const playing = state.playing;
  play.innerHTML = icon(playing ? "pause" : "play");
  play.title = play.ariaLabel = t(playing ? "demoPause" : "demoPlay");
  play.hidden = still.matches;
}

/** The row as a spreadsheet draws it: letters, row numbers, the three rows. */
function paintSheet() {
  const card = CARDS[state.at];
  const cols = card.columns;
  const lit = state.turned ? "back" : "front";
  const litIdx = cols.map((c, i) => (c.side === lit ? i : -1)).filter((i) => i >= 0);
  const first = litIdx[0];
  const last = litIdx[litIdx.length - 1];

  const cell = (text, cls = "") =>
    `<span class="dcell ${cls}" title="${escapeHtml(text)}"><span>${escapeHtml(text)}</span></span>`;

  let out = `<span class="dcell corner"></span>`;
  out += cols.map((c) => cell(c.letter, "letter")).join("");
  out += `<span class="dcell rownum">1</span>` + cols.map((c) => cell(c.name, "head")).join("");
  out += `<span class="dcell rownum">2</span>` + cols.map((c) => cell(c.config, "conf")).join("");
  out +=
    `<span class="dcell rownum here">${card.line}</span>` +
    cols
      .map((c, i) => {
        const on = litIdx.includes(i);
        const cls = [
          "data",
          on ? "pick" : "",
          on && i === first ? "pick-l" : "",
          on && i === last ? "pick-r" : "",
        ].join(" ");
        return cell(c.value, cls);
      })
      .join("");

  const sheet = $("#demo-cells");
  sheet.style.setProperty("--cols", cols.length);
  sheet.innerHTML = out;

  const at = cols[first] ?? cols[1];
  $("#fx-ref").textContent = `${at.letter}${card.line}`;
  $("#fx-val").textContent = at.value;
  $("#demo-tab").textContent = card.sheet;
}

function paintBar() {
  $("#show-answer").hidden = state.turned;
  $("#ease").hidden = !state.turned;
}

/** Shows example `index`, question side up. */
function show(index, { turned = false } = {}) {
  state.at = index;
  state.turned = turned;
  for (const flip of document.querySelectorAll(".flip")) {
    const here = Number(flip.dataset.card) === index;
    flip.classList.toggle("active", here);
    flip.classList.toggle("turned", here && turned);
    flip.toggleAttribute("inert", !here);
  }
  for (const b of document.querySelectorAll("[data-pick]")) {
    b.setAttribute("aria-pressed", String(Number(b.dataset.pick) === index));
  }
  paintSheet();
  paintBar();
  pulse();
}

function turn() {
  state.turned = true;
  document.querySelector(".flip.active")?.classList.add("turned");
  paintSheet();
  paintBar();
  pulse();
}

/** The arrow between the row and the card runs once per change. */
function pulse() {
  const flow = $("#demo-flow");
  flow.classList.remove("run");
  void flow.getBoundingClientRect();
  flow.classList.add("run");
}

// --- the clock -------------------------------------------------------------

function schedule() {
  clearTimeout(state.timer);
  if (!state.playing || !state.visible || document.hidden) return;
  state.timer = setTimeout(
    () => {
      if (!state.turned) turn();
      else show((state.at + 1) % CARDS.length);
      schedule();
    },
    state.turned ? BACK_FOR : FRONT_FOR,
  );
}

function setPlaying(on) {
  state.playing = on;
  buildTabs();
  schedule();
}

// --- events ----------------------------------------------------------------

document.addEventListener("click", (e) => {
  if (e.target.closest("#show-answer")) {
    setPlaying(false);
    turn();
    // The button pressed has just been hidden; from the keyboard, focus goes to
    // what replaced it rather than back to the top of the page.
    if (e.detail === 0) $("#ease button")?.focus();
    return;
  }
  if (e.target.closest("[data-ease]")) {
    setPlaying(false);
    show((state.at + 1) % CARDS.length);
    if (e.detail === 0) $("#show-answer").focus();
    return;
  }
  const pick = e.target.closest("[data-pick]");
  if (pick) {
    setPlaying(false);
    show(Number(pick.dataset.pick));
    return;
  }
  if (e.target.closest("#demo-play")) setPlaying(!state.playing);
});

// Off screen or in a background tab, nothing is watching: hold the clock, so the
// demo is where it was when the reader comes back rather than three cards on.
new IntersectionObserver(([entry]) => {
  state.visible = entry.isIntersecting;
  schedule();
}).observe($("#demo"));
document.addEventListener("visibilitychange", schedule);

still.addEventListener("change", () => {
  if (still.matches) setPlaying(false);
  else buildTabs();
});

onRepaint((what) => {
  // The card is a separate document that was handed the old palette.
  if (what === "theme") buildCards();
  else {
    buildTabs();
    buildCards();
  }
});

// --- sections rising into view ----------------------------------------------

const reveal = new IntersectionObserver(
  (entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      entry.target.classList.add("in");
      reveal.unobserve(entry.target);
    }
  },
  { rootMargin: "0px 0px -8% 0px" },
);
for (const el of document.querySelectorAll(".reveal")) reveal.observe(el);
window.scHomeReady = true;

buildCards();
buildTabs();
show(0);
schedule();
