/**
 * The landing page: the demo in the hero, and the sections rising into view.
 *
 * The demo is the page's one claim — this row becomes this card, on a phone, in
 * a file Anki opens — so it is made of the real thing. `home-cards.js` is written
 * by scripts/build_site.py, which runs the add-on's own card_layout.py over four
 * rows of the example workbook; here those templates are filled by the same
 * `renderCard` and framed by the same `cardDoc` Sheet to Anki uses. No Pyodide: the
 * Python already ran at build time.
 *
 * It tells Sheet to Anki's three steps in order — the link goes in, the card is
 * checked front then back, the .apkg lands in Anki — and then does it again with
 * the next example, each in a different theme. Each step ends in a tap on the
 * button that leads to the next (Tạo flashcard, Show Answer, Download .apkg), a
 * fingertip pressing it, so the story reads as what a learner would do rather
 * than as cuts. A writing card is written: the question's square fills in stroke
 * by stroke, as a hand would, and the answer's loops the order the way the card
 * itself does. It plays by itself, which an
 * animation that changes on its own must let you stop (WCAG 2.2.2): the button
 * beside the examples pauses it, and anything you do to the demo — a step, an
 * example, Show Answer — stops it too, since by then you are the one driving.
 * With reduced motion asked for it never starts, and the card turns without the
 * flip.
 */

import { renderCard, escapeHtml } from "./anki.js";
import { cardDoc } from "./cardframe.js";
import { t } from "./i18n.js";
import { icon } from "./icons.js";
import { dark, onRepaint } from "./page.js";
import { CARDS, HANZI_WRITER, THEME_SWATCHES } from "./home-cards.js";
import { stashFile } from "./handoff.js";
import { site } from "./paths.js";

const $ = (sel) => document.querySelector(sel);

const still = matchMedia("(prefers-reduced-motion: reduce)");

// The story, one phase at a time, and how long each stays up (ms).
const PHASES = ["link", "front", "back", "apkg"];
const HOLD = { link: 2400, front: 2600, back: 3400, apkg: 2800 };
// A character takes longer to write than a word takes to read.
const DRAW_HOLD = { front: 7200, back: 5600 };
// The phases that end in a tap, and the button tapped; the tap takes this long,
// out of the end of the phase's hold.
const TAPS = { link: ".scr-go", front: "#show-answer", back: ".scr-bar" };
const TAP_MS = 760;
// Which of Sheet to Anki's three steps each phase is.
const STEP = { link: "link", front: "front", back: "front", apkg: "apkg" };

const state = {
  at: 0,
  phase: "front",
  playing: !still.matches,
  visible: true,
  timer: 0,
  taps: [],
};

// The rendered faces of every example, built once: switching examples then
// shows a frame that is already drawn, instead of reloading one in view.
const rendered = CARDS.map((card) =>
  renderCard(card.template, card.values, { ordinal: 1 }),
);
const draws = rendered.map((r) => r.front.html.includes('class="sc-draw"'));

/**
 * What a writing box does on the demo, in place of the card's own script.
 *
 * The card's script quizzes on the question — an empty square waiting for a
 * finger — which on a phone nobody is holding is just an empty square. Here the
 * question's character is written out once, without its outline, as a hand
 * would write it; the answer loops the stroke order over the outline, as the
 * card does. Each starts when the page says that face is showing (a message,
 * since the frame shares no origin with the page), and the frame says when it is
 * ready, in case the word came before the library did. With less motion asked
 * for, both show the finished character. The square is sized to the room the
 * rest of the card leaves, since the sheet's 260px is a desktop's, and an answer
 * still too tall for the phone is drawn smaller rather than cut off.
 */
function drawScript(tab) {
  return (
    "<script>(function () {\n" +
    `var face = ${JSON.stringify(tab)};\n` +
    'var still = matchMedia("(prefers-reduced-motion: reduce)").matches;\n' +
    "var writers = [], ready = false, wanted = false;\n" +
    "function play() {\n" +
    "  wanted = true; if (!ready) return;\n" +
    "  writers.forEach(function (w) {\n" +
    "    if (still) { w.showCharacter(); return; }\n" +
    '    if (face === "front") { w.hideCharacter(); w.animateCharacter(); }\n' +
    "    else { w.loopCharacterAnimation(); }\n" +
    "  });\n" +
    "}\n" +
    "function build() {\n" +
    '  document.querySelectorAll(".sc-draw").forEach(function (box) {\n' +
    '    box.style.minWidth = "0"; box.style.height = "0";\n' +
    "    var rest = document.body.getBoundingClientRect().bottom;\n" +
    "    var size = Math.max(96, Math.min(parseInt(box.dataset.scSize, 10) || 200,\n" +
    "      innerWidth - 48, innerHeight - rest - 12));\n" +
    '    box.style.minWidth = box.style.height = size + "px";\n' +
    "    var style = getComputedStyle(box);\n" +
    '    var faint = style.getPropertyValue("--sc-muted").trim() || "#888";\n' +
    '    Array.from((box.dataset.scChar || "").trim()).forEach(function (ch) {\n' +
    "      if (!ch.trim()) return;\n" +
    '      var cell = document.createElement("div");\n' +
    "      box.appendChild(cell);\n" +
    "      writers.push(HanziWriter.create(cell, ch, {\n" +
    "        width: size, height: size, padding: 6,\n" +
    '        showCharacter: still || face !== "front",\n' +
    '        showOutline: face !== "front",\n' +
    "        strokeColor: style.color, outlineColor: faint,\n" +
    "        strokeAnimationSpeed: 1.1, delayBetweenStrokes: 220,\n" +
    "        onLoadCharDataError: function () { cell.textContent = ch; }\n" +
    "      }));\n" +
    "    });\n" +
    "  });\n" +
    "  var bottom = document.body.getBoundingClientRect().bottom;\n" +
    '  if (bottom > innerHeight) document.body.style.zoom = String(innerHeight / bottom);\n' +
    "  ready = true;\n" +
    "  if (wanted) play();\n" +
    '  parent.postMessage({ sc: "draw-ready" }, "*");\n' +
    "}\n" +
    'addEventListener("message", function (e) {\n' +
    '  if (e.data && e.data.sc === "draw-play") play();\n' +
    "});\n" +
    'var tag = document.createElement("script");\n' +
    `tag.src = ${JSON.stringify(HANZI_WRITER)};\n` +
    'tag.addEventListener("load", build);\n' +
    "document.head.appendChild(tag);\n" +
    "})();<\/script>"
  );
}

/**
 * The card's own document, as Sheet to Anki builds it, adjusted for a card that
 * is looked at rather than studied: no scrollbars (the frame is sized to fit),
 * no "TTS voices" list (it lists the voices of the device reviewing the card,
 * and this page is not one), and no scripts — the ones a card carries are for
 * speaking, typing and that list, and a frame nobody can click has no use for
 * them. Taken out rather than blocked, so the console is not a wall of refusals.
 */
function faceDoc(index, tab) {
  const { front, back } = rendered[index];
  const doc = cardDoc({ front, back, tab, dark: dark() })
    .replace(/<script\b[\s\S]*?<\/script>/gi, "")
    .replace(
      '<meta charset="utf-8">',
      '<meta charset="utf-8"><style>html, body { overflow: hidden; } ' +
        "body { padding: 14px; font-size: 16px; } .sc-tts-debug { display: none; }</style>",
    );
  return draws[index] ? doc.replace(/<\/body>|$/, (end) => drawScript(tab) + end) : doc;
}

/** Tells the showing face of a writing card to start writing. */
function playDrawing() {
  if (!draws[state.at] || (state.phase !== "front" && state.phase !== "back")) return;
  const face = state.phase === "front" ? "front" : "both";
  const el = document.querySelector(`.flip[data-card="${state.at}"] .face.${face}`);
  el?.contentWindow?.postMessage({ sc: "draw-play" }, "*");
}

// A frame whose library arrived after the word to start did: say it again.
addEventListener("message", (e) => {
  if (e.data?.sc !== "draw-ready") return;
  const face = state.phase === "front" ? "front" : "both";
  const el = document.querySelector(`.flip[data-card="${state.at}"] .face.${face}`);
  if (el && e.source === el.contentWindow) playDrawing();
});

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
        i === state.at && state.phase === "back" ? " turned" : ""
      }" data-card="${i}" ${i === state.at ? "" : "inert"}>` +
      // "both" on the back, as Anki and Sheet to Anki show an answered card.
      frame(i, "front") +
      frame(i, "both") +
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
  // While the link goes in the whole row is the selection; after that, the
  // columns on the side of the card that is showing.
  const lit = state.phase === "back" ? "back" : "front";
  const litIdx = cols
    .map((c, i) => (state.phase === "link" || state.phase === "apkg" || c.side === lit ? i : -1))
    .filter((i) => i >= 0);
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

/** Shows example `index` at `phase`. */
function show(index, phase) {
  state.at = index;
  state.phase = phase;
  const demo = $("#demo");
  demo.dataset.phase = phase;
  for (const flip of document.querySelectorAll(".flip")) {
    const here = Number(flip.dataset.card) === index;
    flip.classList.toggle("active", here);
    flip.classList.toggle("turned", here && phase === "back");
    flip.toggleAttribute("inert", !here);
  }
  for (const b of document.querySelectorAll("[data-pick]")) {
    b.setAttribute("aria-pressed", String(Number(b.dataset.pick) === index));
  }
  for (const b of document.querySelectorAll("[data-phase-to]")) {
    b.setAttribute("aria-pressed", String(b.dataset.phaseTo === STEP[phase]));
  }
  $("#show-answer").textContent = t(phase === "back" ? "flipBack" : "showAnswer");
  paintSheet();
  playDrawing();
}

// --- the clock -------------------------------------------------------------

function schedule() {
  clearTimeout(state.timer);
  untap();
  if (!state.playing || !state.visible || document.hidden) return;
  const hold = (draws[state.at] && DRAW_HOLD[state.phase]) || HOLD[state.phase];
  const target = TAPS[state.phase];
  state.timer = setTimeout(
    () => {
      if (!target) return advance();
      tap(target);
      state.timer = setTimeout(advance, TAP_MS);
    },
    hold - (target ? TAP_MS : 0),
  );
}

function advance() {
  const next = PHASES.indexOf(state.phase) + 1;
  if (next < PHASES.length) show(state.at, PHASES[next]);
  else show((state.at + 1) % CARDS.length, PHASES[0]);
  schedule();
}

/**
 * A fingertip on `sel`: it lands, the button goes down under it with a ripple,
 * and comes back up just before the screen changes. A fresh dot each time,
 * since Show Answer rewrites its own text and would take a child with it.
 */
function tap(sel) {
  const button = document.querySelector(`#demo ${sel}`);
  if (!button) return;
  const dot = document.createElement("span");
  dot.className = "tapdot";
  dot.setAttribute("aria-hidden", "true");
  button.closest(".phone-screen").append(dot);
  // Placed in the screen's own pixels, which stay true under the demo's zoom.
  let x = button.offsetWidth / 2;
  let y = button.offsetHeight / 2;
  for (let el = button; el && el !== dot.offsetParent; el = el.offsetParent) {
    x += el.offsetLeft;
    y += el.offsetTop;
  }
  dot.style.left = `${x}px`;
  dot.style.top = `${y}px`;
  state.taps.push(
    setTimeout(() => button.classList.add("pressed"), 300),
    setTimeout(() => button.classList.remove("pressed"), 560),
  );
}

function untap() {
  for (const id of state.taps) clearTimeout(id);
  state.taps = [];
  for (const el of document.querySelectorAll("#demo .tapdot")) el.remove();
  for (const el of document.querySelectorAll("#demo .pressed")) el.classList.remove("pressed");
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
    show(state.at, state.phase === "back" ? "front" : "back");
    return;
  }
  const step = e.target.closest("[data-phase-to]");
  if (step) {
    setPlaying(false);
    show(state.at, step.dataset.phaseTo);
    return;
  }
  const pick = e.target.closest("[data-pick]");
  if (pick) {
    setPlaying(false);
    show(Number(pick.dataset.pick), "front");
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
  if (what !== "theme") buildTabs();
  buildCards();
  show(state.at, state.phase);
});

// --- the themes, as swatches ------------------------------------------------
//
// Each listed theme's own ground, ink and accent, taken from the palettes a card
// is painted with (home-cards.js), in the page's light or dark.

function paintSwatches() {
  const mode = dark() ? "night" : "light";
  $("#swatches").innerHTML = THEME_SWATCHES.map(({ name, ...modes }) => {
    const { bg, fg, accent } = modes[mode];
    return (
      `<li class="hchip sw"><span class="sw-dot" style="--sw-bg:${bg};--sw-fg:${fg};--sw-ac:${accent}">` +
      `<span></span></span>${escapeHtml(name)}</li>`
    );
  }).join("");
}
paintSwatches();
onRepaint((what) => what === "theme" && paintSwatches());

// --- step 1, on the landing page ---------------------------------------------
//
// The same first step Sheet to Anki asks for, so a learner who arrives with a
// sheet in hand starts from here. Nothing is read on this page: a link goes over
// in ?url=, a file through IndexedDB (handoff.js) to create/#file.

const FILE_TYPES = /\.(xlsx|xlsm|csv|tsv|txt)$/i;

function quickError(key) {
  const box = $("#q-err");
  box.hidden = !key;
  box.textContent = key ? t(key) : "";
  $("#q-url").toggleAttribute("aria-invalid", Boolean(key));
  if (key) $("#q-url").focus();
}

async function sendFile(file) {
  if (!file) return;
  if (!FILE_TYPES.test(file.name)) return quickError("homeBadFile");
  try {
    await stashFile(file);
  } catch {
    return quickError("homeStashFailed");
  }
  location.href = site("create/#file");
}

$("#quick").addEventListener("submit", (e) => {
  e.preventDefault();
  let link = $("#q-url").value.trim();
  if (!link) return quickError("homeNoLink");
  // Typed or copied without its https:// — "docs.google.com/spreadsheets/…" is
  // a link to anybody reading it, so it is one here too.
  if (/^[\w-]+(\.[\w-]+)+\/\S*$/.test(link)) link = "https://" + link;
  if (!/^https?:\/\/\S+$/i.test(link)) return quickError("homeNotLink");
  location.href = site("create/?url=" + encodeURIComponent(link));
});
$("#q-url").addEventListener("input", () => quickError(""));
$("#q-pick").addEventListener("click", () => $("#q-file").click());
$("#q-file").addEventListener("change", (e) => sendFile(e.target.files[0]));

// A file dragged anywhere over the page: the whole window becomes the target,
// so a drop never lands inside a card frame or opens the file in the browser.
let dragDepth = 0;
const carriesFile = (e) => [...(e.dataTransfer?.types || [])].includes("Files");
addEventListener("dragenter", (e) => {
  if (!carriesFile(e)) return;
  dragDepth += 1;
  $("#q-drop").hidden = false;
});
addEventListener("dragleave", () => {
  dragDepth = Math.max(0, dragDepth - 1);
  if (!dragDepth) $("#q-drop").hidden = true;
});
addEventListener("dragover", (e) => {
  if (carriesFile(e)) e.preventDefault();
});
addEventListener("drop", (e) => {
  if (!carriesFile(e)) return;
  e.preventDefault();
  dragDepth = 0;
  $("#q-drop").hidden = true;
  sendFile(e.dataTransfer.files[0]);
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

$("#demo-file").textContent = "sheetcards-examples.apkg";
buildCards();
buildTabs();
// Still, the demo opens on the card — the step that needs no motion to read.
show(0, still.matches ? "front" : "link");
schedule();
