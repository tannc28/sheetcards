/**
 * The landing page's "Nhờ AI tạo bộ từ": a prompt a reader copies into an AI
 * assistant, naming the guide the assistant should read.
 *
 * The guide's address is worked out from the site's own root (site/paths.js),
 * never written down, so the prompt names whatever domain the site is served
 * from. DOM-free, so tests/test_site_aiprompt.py runs it in node.
 */

/** The guide an assistant reads, under the site's root. */
export const guideUrl = (root) => new URL("ai.md", root).href;

const escape = (s) =>
  String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

const unescape = (s) =>
  s.replace(/&(amp|lt|gt|quot);/g, (_, e) => ({ amp: "&", lt: "<", gt: ">", quot: '"' })[e]);

/**
 * The prompt as markup (its [slots] in `.ai-slot` spans) and as the plain text
 * that is copied. `say` is the translated string: a function of the address.
 */
export function promptFor(say, root) {
  const html = say(escape(guideUrl(root)));
  return { html, text: unescape(html.replace(/<[^>]*>/g, "")) };
}

/**
 * Where each assistant opens. ChatGPT and Claude take the prompt in `?q=`;
 * Gemini has no such parameter, so it opens empty and the prompt is pasted.
 * Every button also copies first, so a parameter that stops working still
 * leaves the prompt on the clipboard.
 */
export function chatLinks(text) {
  const q = encodeURIComponent(text);
  return {
    chatgpt: `https://chatgpt.com/?q=${q}`,
    claude: `https://claude.ai/new?q=${q}`,
    gemini: "https://gemini.google.com/app",
  };
}
