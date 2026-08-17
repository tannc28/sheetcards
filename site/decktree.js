/**
 * The deck hierarchy, drawn the same way wherever it is drawn.
 *
 * Both pages show one: the preview builds it from every synced row of a sheet and
 * lets you filter the row list by clicking a level; the editor builds it from its
 * single row of data and has nothing to filter. That is the only difference, so it
 * is an argument (`pick`) rather than a second copy of the tree — a deck shown two
 * ways on two pages of the same site is two things to learn about one thing.
 */

import { escapeHtml } from "./anki.js";

/**
 * The hierarchy, with each level counting everything beneath it.
 *
 * Rows are `{deck, kind}` — the shape `analyze()` returns — and only the synced
 * ones are counted, because a row that will not be written to Anki has no deck.
 */
export function deckTree(rows) {
  const root = { name: null, path: "", count: 0, children: new Map() };
  for (const r of rows) {
    if (r.kind !== "synced") continue;
    root.count++;
    let node = root;
    const parts = [];
    for (const part of r.deck.split("::")) {
      parts.push(part);
      if (!node.children.has(part)) {
        node.children.set(part, {
          name: part,
          path: parts.join("::"),
          count: 0,
          children: new Map(),
        });
      }
      node = node.children.get(part);
      node.count++;
    }
  }
  return root;
}

/**
 * One tree as markup, sorted by name at every level.
 *
 * `pick` makes each level a button carrying `data-deck`, which is what the preview
 * page's filtering listens for; without it the levels are spans and the tree is
 * something to read. `selected` and `lit` are the two states the preview draws —
 * the level being filtered on, and the level the open column points at.
 */
export function treeHtml(node, opts = {}) {
  const { depth = 0, selected = null, lit = null, pop = "", pick = false } = opts;
  return [...node.children.values()]
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((child) => {
      const inner =
        `<span class="name">${escapeHtml(child.name)}</span>` +
        `<span class="count">${child.count}</span>`;
      const classes = pick
        ? `${selected === child.path ? "on" : ""}${lit === child.path ? " lit" + pop : ""}`
        : "";
      const row = pick
        ? `<button data-deck="${escapeHtml(child.path)}" style="--depth:${depth}"
             class="${classes}">${inner}</button>`
        : `<span class="node" style="--depth:${depth}">${inner}</span>`;
      const below = child.children.size
        ? `<ul class="tree">${treeHtml(child, { ...opts, depth: depth + 1 })}</ul>`
        : "";
      return `<li>${row}${below}</li>`;
    })
    .join("");
}
