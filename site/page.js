/**
 * The chrome shared by the pages that are read rather than worked in: the
 * landing page and the documentation. The masthead's theme and language
 * switches, the translated text, the icons, and the docs' table of contents.
 *
 * The preview and the editor wire the same two switches inside their own
 * modules, because a theme change there also has to redraw a card; this is the
 * same behaviour for pages with nothing else to redraw. Whatever a page does need
 * to redraw, it registers with `onRepaint`.
 */

import { LANGUAGES, lang, paintDocLinks, setLang, t } from "./i18n.js";
import { icon, paintIcons } from "./icons.js";

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
  paintDocLinks();
  for (const el of document.querySelectorAll("[data-i18n]")) {
    el.innerHTML = t(el.dataset.i18n);
  }
  for (const el of document.querySelectorAll("[data-i18n-attr]")) {
    for (const pair of el.dataset.i18nAttr.split(",")) {
      const [attr, key] = pair.split(":").map((s) => s.trim());
      el.setAttribute(attr, t(key));
    }
  }
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

paintIcons();
paint();
