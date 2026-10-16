/**
 * The contact form's logic, with no page in it: whether the form is open, who
 * the sign-in says you are, which page you came from, whether a screenshot is
 * one the web app will take, what is posted, and what each answer means.
 *
 * Kept apart from contact.js (which draws the page) so
 * tests/test_site_contact.py can run all of it in node. The rules mirror
 * tools/feedback/Code.gs, which checks them again: what is refused here is only
 * refused sooner, with a clearer message.
 */

export const KINDS = ["bug", "feature", "other"];
export const MAX_MESSAGE = 5000;
export const MAX_IMAGE_BYTES = 4 * 1024 * 1024;
export const IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp", "image/gif"];

const CLIENT_ID = /^[\w-]+\.apps\.googleusercontent\.com$/;
const ENDPOINT = /^https:\/\/script\.google\.com\/macros\/s\/[\w-]+\/exec$/;

/**
 * "open" when both values are set and look like what they should be, else
 * "closed" — a half-filled or mistyped config shows the notice rather than a
 * form that cannot work.
 */
export function formState(config) {
  const id = String(config?.clientId || "").trim();
  const url = String(config?.endpoint || "").trim();
  return CLIENT_ID.test(id) && ENDPOINT.test(url) ? "open" : "closed";
}

/**
 * The ID token's payload, read for display only.
 *
 * Not verified — the browser has no business verifying it, and does not need
 * to: the web app asks Google about the token before it writes anything. A
 * token that does not decode is no sign-in at all.
 */
export function readToken(token) {
  try {
    const part = String(token).split(".")[1];
    const b64 = part.replace(/-/g, "+").replace(/_/g, "/");
    const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
    const bytes = Uint8Array.from(atob(padded), (c) => c.charCodeAt(0));
    const claims = JSON.parse(new TextDecoder().decode(bytes));
    if (!claims || typeof claims !== "object" || !claims.email) return null;
    return {
      email: String(claims.email),
      name: String(claims.name || ""),
      exp: Number(claims.exp) || 0,
    };
  } catch {
    return null;
  }
}

/** Whether a sign-in has run out (Google's ID tokens last an hour). */
export function expired(who, now = Date.now()) {
  return !who || who.exp * 1000 <= now + 30_000;
}

/**
 * The page the reader came from: `?from=` when a link of ours says so, else the
 * path of a referrer on this site, else "". Only a path, never a query: the
 * query of Sheet to Anki can carry somebody's sheet link.
 */
export function cameFrom(search, referrer, origin) {
  const from = new URLSearchParams(search || "").get("from");
  if (from) return from.replace(/[^\w./-]/g, "").slice(0, 200);
  try {
    const ref = new URL(referrer);
    if (ref.origin === origin) return ref.pathname.slice(0, 200);
  } catch {
    // No referrer, or not a URL: nothing to say.
  }
  return "";
}

/** "" for a screenshot the web app will store, else the i18n key saying why not. */
export function imageProblem(file) {
  if (!file) return "";
  if (!IMAGE_TYPES.includes(file.type)) return "fbErrImageType";
  if (file.size > MAX_IMAGE_BYTES) return "fbErrImageSize";
  return "";
}

/** The JSON the web app's doPost reads. */
export function payload({ idToken, kind, message, image, device, sheetUrl, page, userAgent, lang }) {
  const body = {
    idToken,
    kind: KINDS.includes(kind) ? kind : "other",
    message: String(message || "").slice(0, MAX_MESSAGE),
    device: device || "",
    sheetUrl: String(sheetUrl || "").trim(),
    page: page || "",
    userAgent: userAgent || "",
    lang: lang || "",
  };
  if (image) body.image = { data: image.data, type: image.type, name: image.name || "screenshot" };
  return body;
}

// Every answer the web app gives, and the two the network can, as an i18n key.
const ERRORS = {
  auth: "fbErrAuth",
  rate: "fbErrRate",
  empty: "fbErrEmpty",
  image: "fbErrImage",
  server: "fbErrServer",
  network: "fbErrNetwork",
};

/**
 * What a reply means: `{ok: true}`, or `{ok: false, key, signIn}` with the
 * message to show and whether the sign-in has to be done again. Anything that is
 * not the web app's JSON — an HTML error page, a Google login wall — is a
 * server problem, not a success.
 */
export function readReply(reply) {
  if (reply && reply.ok === true) return { ok: true };
  const code = reply && typeof reply.error === "string" ? reply.error : "server";
  return { ok: false, key: ERRORS[code] || ERRORS.server, signIn: code === "auth" };
}

/** The error for a request that never got an answer. */
export const NETWORK = readReply({ ok: false, error: "network" });
