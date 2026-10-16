/**
 * Carries a file picked on the landing page over to Sheet to Anki.
 *
 * A link can travel in the address (?url=), a File cannot, and the landing page
 * must not load Pyodide just to read one. So the File is put in this browser's
 * IndexedDB, the page moves to create.html#file, and Sheet to Anki takes it out
 * again — once: it is deleted on the way out, so a reload or a shared address
 * never finds someone else's file. Nothing leaves the device.
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

/** `{file, from}` as the last page left them, or a null file; the slot is emptied. */
export async function takeHandoff() {
  try {
    const file = await run("readonly", (store) => store.get(KEY));
    const from = await run("readonly", (store) => store.get(FROM));
    await run("readwrite", (store) => {
      store.delete(FROM);
      return store.delete(KEY);
    });
    return { file: file instanceof Blob ? file : null, from: from || "" };
  } catch {
    return { file: null, from: "" };
  }
}
