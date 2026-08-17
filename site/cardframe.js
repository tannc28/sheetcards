/**
 * The card, as a document of its own — the same document on both pages.
 *
 * A card is not part of this page: it is the thing Anki will draw, so it is drawn
 * inside a frame with its own stylesheet, its own body classes and its own script,
 * and nothing on the page around it can reach in and change how it looks. That is
 * the whole reason it is built as a string of HTML here rather than as elements.
 *
 * It used to be built twice — once on the preview page and once, hand-copied and
 * already slightly different, in the editor. The copy had lost the referrer meta
 * that keeps YouTube from refusing to be framed, which is exactly the kind of
 * thing a second copy loses.
 */

import { escapeHtml } from "./anki.js";
import { typeansRuntime } from "./typeans.js";

/**
 * The card's own document.
 *
 * `front` and `back` are what `renderCard` returned. `tab` is which of them to
 * show — "front", "back", or "both" with the answer under a rule, the way Anki
 * shows a card once it is answered. `ring` names a column to draw a ring around
 * (panel 1's open column on the preview page), and `flash` makes that ring arrive
 * with a hop.
 */
export function cardDoc({ front, back, tab, dark, ring = null, flash = false }) {
  return `<!doctype html><meta charset="utf-8">
    <!-- An embed loaded with no referrer at all is refused by YouTube with
         "Error 153", and a srcdoc document sends none unless it says so. -->
    <meta name="referrer" content="strict-origin-when-cross-origin">
    <style>
      html { color-scheme: light dark; }
      body { margin: 0; padding: 18px; font-family: arial, sans-serif; font-size: 20px;
             text-align: center; color: #111; background: #fff; }
      ${dark ? "body { color: #e6e9ee; background: #1b1f25; }" : ""}
      hr#answer { margin: 16px 0; border: 0; border-top: 1px solid currentColor; opacity: .25; }
      .cloze { color: #2f6fd0; font-weight: 700; }
      a.hint { color: #2f6fd0; font-size: 15px; }
      button.tts { font: inherit; font-size: 14px; padding: 2px 10px; cursor: pointer;
                   border: 1px solid currentColor; border-radius: 999px;
                   background: transparent; color: inherit; opacity: .8; }
      img, video, iframe { max-width: 100%; }
      /* The typed-answer box, in Anki's own colours — these three classes come
         from aqt's reviewer.css, not from a note type, so a card that renders
         right here would be uncoloured in Anki without them. */
      input#typeans { font: inherit; width: 100%; box-sizing: border-box;
                      line-height: 1.75; text-align: center; padding: 2px 6px;
                      border: 1px solid currentColor; border-radius: 4px;
                      background: transparent; color: inherit; }
      .s2a-type { margin: 10px auto; max-width: 22em; }
      code.typeans { white-space: pre-wrap; font-variant-ligatures: none;
                     font-family: inherit; line-height: 1.75; }
      .typeGood { background: #afa; color: #000; }
      .typeBad { background: #faa; color: #000; }
      .typeMissed { background: #ccc; color: #000; }
      ${
        ring
          ? `/* A column is open on the page outside; this is the block it made. The
                card is its own document, so the ring is written into the card's own
                stylesheet on the way in rather than reached for afterwards — there
                is no frame to wait for and nothing to clean up when the selection
                changes, because the frame is rebuilt either way. */
             [data-s2a-col="${ring.replace(/["\\]/g, "\\$&")}"] {
               outline: 2px solid #1a73e8; outline-offset: 6px; border-radius: 4px;
               ${flash ? "animation: s2a-pop .5s cubic-bezier(.2, .8, .2, 1);" : ""}
             }
             @keyframes s2a-pop {
               0%   { transform: translateY(0)    scale(1); }
               35%  { transform: translateY(-8px) scale(1.06); }
               70%  { transform: translateY(2px)  scale(.99); }
               100% { transform: translateY(0)    scale(1); }
             }
             @media (prefers-reduced-motion: reduce) {
               [data-s2a-col] { animation: none; }
             }`
          : ""
      }
    </style>
    <!-- The two classes Anki itself puts on a card's body: "card" is what a note
         type's CSS targets, and "night_mode" is how a card knows it is being drawn
         dark. A sheet's theme declares a colour pair for each, so without the second
         class the preview would show the light half of the theme on a dark page. -->
    <body class="card${dark ? " night_mode" : ""}"${tab === "front" ? "" : " data-answered"}>
      ${tab === "back" ? back.html : front.html}
      ${tab === "both" ? '<hr id="answer">' + backOnly(back.html, front.html) : ""}
      <script>
        // The tts button speaks, on both pages. Choosing a language and then
        // finding the button inert would teach that the directive does nothing —
        // and this is a real test of whether the machine has a voice for the code.
        document.addEventListener("click", (e) => {
          const b = e.target.closest("[data-tts]");
          if (!b) return;
          const t = JSON.parse(b.dataset.tts);
          const u = new SpeechSynthesisUtterance(t.text);
          u.lang = t.lang.replace("_", "-");
          u.rate = Number(t.speed) || 1;
          const want = new Set(t.voices);
          const v = speechSynthesis.getVoices();
          u.voice = v.find((x) => want.has(x.name))
                 || v.find((x) => x.lang.replace("-", "_") === t.lang) || null;
          speechSynthesis.cancel();
          speechSynthesis.speak(u);
        });
        const post = () => parent.postMessage(
          { h: document.documentElement.scrollHeight }, "*");
        addEventListener("load", post); new ResizeObserver(post).observe(document.body);
      <\/script>
      ${typeansRuntime()}`;
}

/**
 * The frame the document goes in.
 *
 * `allow-same-origin` is required, not incidental: a nested player inherits these
 * flags, and in an opaque origin YouTube and Drive render a dead black box. Cells
 * go in exactly as written, script and all, because Anki's webview runs them too
 * and a preview that quietly filtered them would be reporting on a card nobody is
 * going to see.
 */
export function cardFrame(doc) {
  return `<iframe id="card" title="Card preview"
    sandbox="allow-scripts allow-same-origin allow-popups allow-presentation"
    allow="fullscreen; encrypted-media; picture-in-picture; autoplay"
    srcdoc="${escapeHtml(doc)}"></iframe>`;
}

/** The answer side minus the repeated question, when the template used FrontSide. */
export function backOnly(backHtml, frontHtml) {
  return backHtml.startsWith(frontHtml) ? backHtml.slice(frontHtml.length) : backHtml;
}
