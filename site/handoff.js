/**
 * Carries a file picked on the landing page over to Sheet to Anki.
 *
 * A link can travel in the address (?url=), a File cannot, and the landing page
 * must not load Pyodide just to read one. So the File is put in this browser's
 * IndexedDB, the page moves to create/#file, and Sheet to Anki takes it out
 * again. It stays there while create/#file is what is open, so a reload
 * opens the same deck; the next sheet or link opened there drops it
 * (dropHandoff). IndexedDB is this browser's own, so a shared #file address
 * finds nothing on anyone else's device. Nothing leaves the device.
 */

const DB = "sheetcards";
const STORE = "handoff";
const KEY = "file";
const FROM = "from";

function open() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function run(mode, work) {
  return open().then(
    (db) =>
      new Promise((resolve, reject) => {
        const tx = db.transaction(STORE, mode);
        const result = work(tx.objectStore(STORE));
        tx.oncomplete = () => {
          db.close();
          resolve(result.result);
        };
        tx.onerror = tx.onabort = () => {
          db.close();
          reject(tx.error);
        };
      }),
  );
}

/**
 * Keeps the file for the next page. Resolves once it is safely stored.
 *
 * `from` names the page that left it ("sheet" for Create sheet), so Sheet to Anki
 * can offer the way back to where the sheet is being written.
 */
export function stashFile(file, from = "") {
  return run("readwrite", (store) => {
    store.put(from, FROM);
    return store.put(file, KEY);
  });
}

/** `{file, from}` as the last page left them, or a null file. Kept for a reload. */
export async function takeHandoff() {
  try {
    const file = await run("readonly", (store) => store.get(KEY));
    const from = await run("readonly", (store) => store.get(FROM));
    return { file: file instanceof Blob ? file : null, from: from || "" };
  } catch {
    return { file: null, from: "" };
  }
}

/** Empties the slot, once something else has been opened in its place. */
export async function dropHandoff() {
  try {
    await run("readwrite", (store) => {
      store.delete(FROM);
      return store.delete(KEY);
    });
  } catch {
    // Nothing kept, or storage refused: either way nothing is left to open.
  }
}

// ---- pasted text ---------------------------------------------------------
//
// The landing page's field takes a word list as well as a link. A list goes
// over to create/#paste through this tab's sessionStorage — it is text, it is
// small, and it should not outlive the tab — and opens there in Dán văn bản,
// filled in. Taken once: a reload of create/ is the empty form again.

const TEXT_KEY = "sc-paste-text";

/** Keeps `text` for the next page in this tab. False if storage refused it. */
export function stashText(text) {
  try {
    sessionStorage.setItem(TEXT_KEY, text);
    return true;
  } catch {
    return false;
  }
}

/** The text the last page left, removed as it is read; "" when there is none. */
export function takeText() {
  try {
    const text = sessionStorage.getItem(TEXT_KEY) || "";
    sessionStorage.removeItem(TEXT_KEY);
    return text;
  } catch {
    return "";
  }
}

/**
 * Whether what was pasted or typed into the one field is a link (to a sheet or
 * a file) rather than words: one line, no spaces, `https://…` or a bare
 * `host.tld/path`. Anything else — a list, one "apple - quả táo" line — is
 * text, and goes to Dán văn bản.
 */
export function isLink(value) {
  const v = String(value || "").trim();
  if (!v || /\s/.test(v)) return false;
  return /^https?:\/\/\S+$/i.test(v) || /^[\w-]+(\.[\w-]+)+\/\S*$/.test(v);
}
