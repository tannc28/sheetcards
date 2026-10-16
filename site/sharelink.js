/**
 * A whole sheet carried in a link, the way Excalidraw and the TypeScript
 * playground carry a drawing or a program: nothing is uploaded anywhere, the
 * link *is* the sheet.
 *
 *   #s=1.<base64url of deflate-raw(UTF-8 of "name\nTSV")>
 *
 * In the fragment rather than the query, because a browser never sends the
 * fragment to a server — not to GitHub Pages, not to anyone — so a shared sheet
 * stays between the two people sharing it. `1.` is the format's version: a later
 * format gets a new number, and a link written today keeps opening. The dot
 * cannot occur in base64url, so the version ends where it says it does.
 *
 * The sheet travels as TSV because that is what both pages already speak: Create
 * sheet writes it, and Sheet to Anki reads it with the add-on's own parser — which
 * runs csv.reader with a tab, so a cell holding a tab, a newline or a quote is
 * quoted the way csv.writer would quote it.
 */

export const SHARE_VERSION = "1";
const PREFIX = `#s=${SHARE_VERSION}.`;

// Past this, some chat apps and mail clients cut a link short, and a cut link is
// a sheet that will not open. The page says so and offers the file instead.
export const LONG_LINK = 8 * 1024;

// ---------------------------------------------------------------------------
// TSV
// ---------------------------------------------------------------------------

/** One cell, quoted when csv.writer would quote it. */
function quote(cell) {
  const text = String(cell ?? "");
  return /[\t\n\r"]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

/** Rows of cells as TSV, read back by csv.reader exactly as they were. */
export function toTsv(rows) {
  return rows.map((row) => row.map(quote).join("\t")).join("\n");
}

/**
 * Rows of cells as the project's .csv: RFC 4180, CRLF, and a byte order mark —
 * the only way to tell Excel the file is UTF-8. One writer for every .csv the
 * site hands out, so a template's sample and an edited sheet are the same file.
 */
export function asCsv(rows) {
  const cell = (value) => {
    const text = String(value ?? "");
    return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  };
  return `\ufeff${rows.map((row) => row.map(cell).join(",")).join("\r\n")}\r\n`;
}

/**
 * TSV — or a block copied out of Sheets or Excel, which is TSV — as rows.
 *
 * Walked a character at a time rather than split on tabs: a cell holding a line
 * break arrives quoted, and split naively it would become two rows.
 */
export function parseTsv(text) {
  const rows = [[""]];
  let quoted = false;
  const push = (ch) => {
    const row = rows[rows.length - 1];
    row[row.length - 1] += ch;
  };
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch !== '"') push(ch);
      else if (text[i + 1] === '"') (push('"'), i++);
      else quoted = false;
      continue;
    }
    const row = rows[rows.length - 1];
    if (ch === '"' && row[row.length - 1] === "") quoted = true;
    else if (ch === "\t") row.push("");
    else if (ch === "\n") rows.push([""]);
    else if (ch !== "\r") push(ch);
  }
  // A selection dragged to the end of a sheet ends in a newline.
  const last = rows[rows.length - 1];
  if (rows.length > 1 && last.length === 1 && last[0] === "") rows.pop();
  return rows;
}

// ---------------------------------------------------------------------------
// The link
// ---------------------------------------------------------------------------

async function squeeze(bytes, Stream) {
  const stream = new Blob([bytes]).stream().pipeThrough(new Stream("deflate-raw"));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

function toBase64Url(bytes) {
  let binary = "";
  for (let i = 0; i < bytes.length; i += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  }
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function fromBase64Url(text) {
  const plain = text.replace(/-/g, "+").replace(/_/g, "/");
  const binary = atob(plain + "=".repeat((4 - (plain.length % 4)) % 4));
  return Uint8Array.from(binary, (ch) => ch.charCodeAt(0));
}

/** The fragment for a sheet: `#s=1.…`. The name is the sheet's title. */
export async function encodeShare(name, tsv) {
  const title = String(name ?? "").replace(/[\r\n]+/g, " ").trim();
  const bytes = new TextEncoder().encode(`${title}\n${tsv}`);
  return PREFIX + toBase64Url(await squeeze(bytes, CompressionStream));
}

/** True when an address's fragment carries a shared sheet, of any version. */
export function isShare(hash) {
  return /^#s=/.test(hash || "");
}

/**
 * `{name, tsv}` out of a fragment made by `encodeShare`.
 *
 * Throws an Error whose `code` says what went wrong: `version` for a format this
 * page is too old to read, `broken` for a link that was cut short or mangled —
 * which is what a long link pasted through a chat app usually turns into.
 */
export async function decodeShare(hash) {
  const body = String(hash || "").replace(/^#?s=/, "");
  const dot = body.indexOf(".");
  const fail = (code) => Object.assign(new Error(`share link: ${code}`), { code });
  if (dot < 0 || !/^\d+$/.test(body.slice(0, dot))) throw fail("broken");
  if (body.slice(0, dot) !== SHARE_VERSION) throw fail("version");
  let text;
  try {
    const bytes = await squeeze(fromBase64Url(body.slice(dot + 1)), DecompressionStream);
    text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch {
    throw fail("broken");
  }
  const cut = text.indexOf("\n");
  if (cut < 0) throw fail("broken");
  return { name: text.slice(0, cut), tsv: text.slice(cut + 1) };
}
