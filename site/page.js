/**
 * The chrome shared by the pages that are read rather than worked in: the
 * landing page and the documentation. The masthead's theme and language
 * switches, the translated text, the icons, and the docs' table of contents.
 *
 * Sheet to Anki and Create sheet wire the same two switches inside their own
 * modules, because a theme change there also has to redraw a card; this is the
 * same behaviour for pages with nothing else to redraw. Whatever a page does need
 * to redraw, it registers with `onRepaint`.
 */

// First, so a fragment carried through Chrome's intent link is back before
// anything reads it.
import { mountInAppBanner } from "./inapp.js";
import { LANGUAGES, lang, paintStrings, setLang, t } from "./i18n.js";
import { icon, paintIcons } from "./icons.js";
import { ROOT } from "./paths.js";

const repaints = [];

// A docs page is written in one language, so its chrome speaks that language
// whatever was chosen before — without making it the choice. Picking the other
// language there means wanting the other page, so the switch goes to its twin.
const written = document.body.dataset.lang;
if (written) setLang(written, false);

/** Called after every theme or language change, with which one it was. */
export function onRepaint(fn) {
  repaints.push(fn);
}

export function dark() {
  return document.documentElement.dataset.theme === "dark";
}

function setTheme(on) {
  if (on) document.documentElement.dataset.theme = "dark";
  else delete document.documentElement.dataset.theme;
  try {
    localStorage.setItem("sc-theme", on ? "dark" : "light");
  } catch {
    // A browser refusing storage is not a reason to refuse the theme.
  }
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute("content", on ? "#18151f" : "#ffffff");
  paint();
  for (const fn of repaints) fn("theme");
}

/** Every translated string on the page, and the two switches. */
export function paint() {
  document.documentElement.lang = lang();
  paintStrings();
  const button = document.getElementById("theme");
  if (button) {
    button.innerHTML = icon(dark() ? "sun" : "moon");
    button.title = button.ariaLabel = t(dark() ? "toLight" : "toDark");
  }
  const langs = document.getElementById("langs");
  if (langs) {
    langs.innerHTML =
      `<span class="langs-icon">${icon("languages")}</span>` +
      LANGUAGES.map(
        (l) =>
          `<button data-lang="${l.code}" class="${lang() === l.code ? "on" : ""}"` +
          ` aria-pressed="${lang() === l.code}">${l.label}</button>`,
      ).join("");
  }
}

document.addEventListener("click", (e) => {
  if (e.target.closest("#theme")) return setTheme(!dark());
  const picker = e.target.closest("[data-lang]");
  if (!picker) return;
  setLang(picker.dataset.lang);
  const twin = document.querySelector('link[rel="alternate"][hreflang]');
  if (written && twin && picker.dataset.lang !== written) {
    location.href = twin.href;
    return;
  }
  paint();
  for (const fn of repaints) fn("lang");
});

// The docs' contents: always open beside the text on a wide screen, where the
// summary is hidden; a fold above the text on a phone, closed until asked for.
const contents = document.getElementById("docnav");
if (contents) {
  const wide = matchMedia("(min-width: 56rem)");
  const fit = () => {
    if (wide.matches) contents.open = true;
  };
  fit();
  wide.addEventListener("change", fit);
  // On a phone it is a menu, and a menu closes once something is picked from it.
  // Left open, it sits above the text, and the next scroll up lands in it again.
  contents.addEventListener("click", (e) => {
    if (!wide.matches && e.target.closest("a[href]")) contents.open = false;
  });
}

// The site's address, where a docs page names it (the build's %%SITE%% token):
// written by the build as the address it was built for, and repainted as the
// address this page was actually served from, so a prompt copied from the docs
// names the right domain wherever the site lives.
for (const el of document.querySelectorAll("[data-site-url]")) el.textContent = ROOT;

mountInAppBanner({ t, icon });
paintIcons();
paint();
