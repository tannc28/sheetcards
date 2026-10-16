/**
 * Carries a file picked on the landing page over to Create deck.
 *
 * A link can travel in the address (?url=), a File cannot, and the landing page
 * must not load Pyodide just to read one. So the File is put in this browser's
 * IndexedDB, the page moves to create.html#file, and Create deck takes it out
 * again — once: it is deleted on the way out, so a reload or a shared address
 * never finds someone else's file. Nothing leaves the device.
 */

const DB = "sheetcards";
const STORE = "handoff";
const KEY = "file";

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

/** Keeps the file for the next page. Resolves once it is safely stored. */
export function stashFile(file) {
  return run("readwrite", (store) => store.put(file, KEY));
}

/** The file the landing page left, or null; either way the slot is emptied. */
export async function takeFile() {
  try {
    const file = await run("readonly", (store) => store.get(KEY));
    await run("readwrite", (store) => store.delete(KEY));
    return file instanceof Blob ? file : null;
  } catch {
    return null;
  }
}
