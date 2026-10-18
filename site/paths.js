/**
 * Where the site's own pages are, from any page.
 *
 * Every module sits at the site's root, but the pages that load them do not:
 * Sheet to Anki is served at create/, Create sheet at sheet/, the docs two or
 * three folders down. A relative address in a script resolves against the page,
 * so `./create/` written in a module means one thing on the landing page and
 * another on Create sheet. Resolved against this module instead, it means the
 * same thing everywhere — which is also what keeps the site working under
 * /sheetcards/ on GitHub Pages and at / on a local server.
 */

export const ROOT = new URL("./", import.meta.url).href;

/** `path` (written as if from the site's root: "create/", "docs/en/") made absolute. */
export const site = (path = "") => new URL(path, ROOT).href;

/** The site's pages by what they are, each a folder. */
export const PAGE = {
  home: "",
  create: "create/",
  sheet: "sheet/",
  contact: "contact/",
  docs: "docs/",
};

/**
 * Links inside a translated string are written from the site's root
 * (`href="./#addon"`), because the same string is painted on pages at several
 * depths. This points each one at the page it means, wherever it was painted.
 */
export function rootLinks(el) {
  for (const a of el.querySelectorAll('a[href^="./"]')) {
    a.setAttribute("href", site(a.getAttribute("href")));
  }
}
