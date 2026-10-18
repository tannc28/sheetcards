/**
 * The contact page: the feedback form, its Google sign-in, and the post to the
 * owner's Apps Script web app (tools/feedback/Code.gs).
 *
 * The rules — what is open, what a token says, what a reply means — are in
 * feedback.js, where node can test them; this module draws them. Google's
 * sign-in script is loaded here and nowhere else on the site, and only once the
 * form is configured: a page with nothing to sign in to has no reason to call
 * Google.
 *
 * The ID token lives in this module's memory and nowhere else — not in
 * the browser's storage, not in the address — and goes out once, in the post. Reloading
 * the page means signing in again, which is a click.
 */

import { dark, onRepaint } from "./page.js";
import { lang, t } from "./i18n.js";
import { FEEDBACK } from "./feedback-config.js";
import {
  MAX_MESSAGE,
  NETWORK,
  cameFrom,
  expired,
  formState,
  imageProblem,
  payload,
  readReply,
  readToken,
} from "./feedback.js";
import { detectDevice } from "./devices.js";
import { inAppBrowser } from "./inapp.js";
import { CONTACT_STATE, readState, writeState } from "./urlstate.js";

const $ = (sel) => document.querySelector(sel);
const GSI = "https://accounts.google.com/gsi/client";

const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const state = {
  token: "",
  who: null,
  image: null, // {data, type, name, url}
  status: null, // {key, bad}
  signinError: "",
  sending: false,
};

const nav = globalThis.navigator;
const app = inAppBrowser({ userAgent: nav.userAgent || "", standalone: nav.standalone === true });
const page = cameFrom(location.search, document.referrer, location.origin);

// ?kind=bug|feature|other picks the kind of message, so a "Báo lỗi" link can
// open the form already on it; changing it is written back, so the address
// copied from the bar still says which.
{
  const asked = readState(location.search, CONTACT_STATE).kind;
  const radio = asked && document.querySelector(`#fb-form input[name="kind"][value="${asked}"]`);
  if (radio) radio.checked = true;
  $("#fb-form")?.addEventListener("change", (e) => {
    if (e.target.name !== "kind") return;
    const now = readState(location.search, CONTACT_STATE);
    const next = writeState(location.href, { ...now, kind: e.target.value }, CONTACT_STATE);
    if (next.href !== location.href) history.replaceState(history.state, "", next);
  });
}
const device =
  detectDevice({ userAgent: nav.userAgent || "", maxTouchPoints: nav.maxTouchPoints || 0 }) +
  (app ? ` · ${app}` : "") +
  ` · ${screen.width}×${screen.height}`;

// ---- sign-in -----------------------------------------------------------------

let gsiReady = false;

function loadGsi() {
  const script = document.createElement("script");
  script.src = GSI;
  script.async = true;
  script.onload = () => {
    const id = globalThis.google?.accounts?.id;
    if (!id) return failGsi();
    id.initialize({
      client_id: FEEDBACK.clientId.trim(),
      callback: signedIn,
      auto_select: false,
      cancel_on_tap_outside: true,
      context: "use",
      ux_mode: "popup",
    });
    gsiReady = true;
    drawButton();
  };
  script.onerror = failGsi;
  document.head.append(script);
}

function failGsi() {
  setSigninError("fbErrGsi");
}

/** Google's own button, in the page's theme and language; redrawn when they change. */
function drawButton() {
  const slot = $("#fb-signin");
  slot.hidden = !!state.token;
  if (!gsiReady || state.token) return;
  slot.innerHTML = "";
  globalThis.google.accounts.id.renderButton(slot, {
    type: "standard",
    theme: dark() ? "filled_black" : "outline",
    size: "large",
    text: "signin_with",
    shape: "pill",
    logo_alignment: "left",
    locale: lang(),
  });
}

function signedIn(response) {
  const who = readToken(response?.credential);
  if (!who) return setSigninError("fbErrAuth");
  state.token = response.credential;
  state.who = who;
  setSigninError("");
  drawWho();
}

function signOut() {
  state.token = "";
  state.who = null;
  globalThis.google?.accounts?.id?.disableAutoSelect?.();
  drawWho();
}

function drawWho() {
  const signed = !!state.token;
  $("#fb-signed").hidden = !signed;
  if (signed) {
    const { name, email } = state.who;
    $("#fb-signed-text").innerHTML = t("fbSignedIn", esc(name || email), esc(email));
  }
  drawButton();
}

function setSigninError(key) {
  state.signinError = key;
  const el = $("#fb-signin-error");
  el.hidden = !key;
  el.textContent = key ? t(key) : "";
}

// ---- the screenshot ------------------------------------------------------------

function takeImage(file) {
  const problem = imageProblem(file);
  showImageError(problem);
  if (problem) return;
  const reader = new FileReader();
  reader.onload = () => {
    const url = String(reader.result);
    state.image = { data: url.slice(url.indexOf(",") + 1), type: file.type, name: file.name || "screenshot", url };
    drawImage();
  };
  reader.onerror = () => showImageError("fbErrImageRead");
  reader.readAsDataURL(file);
}

function showImageError(key) {
  const el = $("#fb-image-error");
  el.dataset.key = key;
  el.hidden = !key;
  el.textContent = key ? t(key) : "";
}

function drawImage() {
  const has = !!state.image;
  $("#fb-preview").hidden = !has;
  $("#fb-preview-img").src = has ? state.image.url : "";
  $("#fb-preview-name").textContent = has ? state.image.name : "";
}

function dropImage() {
  state.image = null;
  $("#fb-file").value = "";
  showImageError("");
  drawImage();
}

// ---- what goes with it ---------------------------------------------------------

function extras() {
  return [
    ["fbExtraDevice", device],
    ["fbExtraPage", page || "—"],
    ["fbExtraLang", lang()],
    ["fbExtraAgent", nav.userAgent || ""],
  ];
}

function drawExtras() {
  $("#fb-extra").innerHTML = extras()
    .map(([key, value]) => `<div><dt>${t(key)}</dt><dd>${esc(value)}</dd></div>`)
    .join("");
}

function drawCount() {
  const n = $("#fb-message").value.length;
  const el = $("#fb-count");
  el.textContent = `${n} / ${MAX_MESSAGE}`;
  el.classList.toggle("full", n >= MAX_MESSAGE);
}

// ---- sending -------------------------------------------------------------------

function setStatus(key, bad = false) {
  state.status = key ? { key, bad } : null;
  drawStatus();
}

function drawStatus() {
  const el = $("#fb-status");
  el.textContent = state.status ? t(state.status.key) : "";
  el.className = "fb-status" + (state.status?.bad ? " bad" : "") + (state.sending ? " busy" : "");
}

function messageError(key) {
  const el = $("#fb-message-error");
  el.dataset.key = key;
  el.hidden = !key;
  el.textContent = key ? t(key) : "";
  $("#fb-message").setAttribute("aria-invalid", key ? "true" : "false");
}

async function send(e) {
  e.preventDefault();
  if (state.sending) return;
  setStatus("");
  const message = $("#fb-message").value;
  if (!message.trim()) {
    messageError("fbErrEmpty");
    $("#fb-message").focus();
    return;
  }
  messageError("");
  if (!state.token || expired(state.who)) {
    const key = state.token ? "fbErrAuth" : "fbErrSignIn";
    signOut();
    setSigninError(key);
    setStatus(key, true);
    $("#fb-who").scrollIntoView({ block: "center", behavior: "smooth" });
    return;
  }
  const body = payload({
    idToken: state.token,
    kind: new FormData($("#fb-form")).get("kind"),
    message,
    image: state.image,
    device,
    sheetUrl: $("#fb-sheet").value,
    page,
    userAgent: nav.userAgent || "",
    lang: lang(),
  });

  state.sending = true;
  $("#fb-send").disabled = true;
  setStatus("fbSending");
  let result;
  try {
    // text/plain keeps this a "simple" request: no CORS preflight, which an
    // Apps Script web app cannot answer. The body is JSON all the same.
    const res = await fetch(FEEDBACK.endpoint.trim(), {
      method: "POST",
      headers: { "Content-Type": "text/plain;charset=utf-8" },
      body: JSON.stringify(body),
      redirect: "follow",
      credentials: "omit",
    });
    let reply = null;
    try {
      reply = await res.json();
    } catch {
      // Not the web app's JSON: readReply calls it a server problem.
    }
    result = readReply(reply);
  } catch {
    result = NETWORK;
  }
  state.sending = false;
  $("#fb-send").disabled = false;

  if (result.ok) {
    setStatus("");
    done();
    return;
  }
  setStatus(result.key, true);
  if (result.signIn) {
    signOut();
    setSigninError("fbErrAuth");
  }
}

function done() {
  const email = state.who?.email || "";
  $("#fb-form").reset();
  dropImage();
  drawCount();
  $("#fb-form").hidden = true;
  $("#fb-done").hidden = false;
  drawDone(email);
  $("#fb-done").focus();
}

function drawDone(email = $("#fb-done").dataset.email || "") {
  $("#fb-done").dataset.email = email;
  $("#fb-done-text").innerHTML = t("fbDoneText", esc(email));
}

function again() {
  $("#fb-done").hidden = true;
  $("#fb-form").hidden = false;
  $("#fb-message").focus();
}

// ---- wiring --------------------------------------------------------------------

function repaint() {
  drawWho();
  drawExtras();
  drawStatus();
  if (state.signinError) setSigninError(state.signinError);
  for (const id of ["#fb-image-error", "#fb-message-error"]) {
    const el = $(id);
    if (el.dataset.key) el.textContent = t(el.dataset.key);
  }
  if (!$("#fb-done").hidden) drawDone();
}

if (formState(FEEDBACK) === "open") {
  $("#fb-closed").hidden = true;
  $("#fb-open").hidden = false;
  $("#fb-form").addEventListener("submit", send);
  $("#fb-message").addEventListener("input", () => {
    drawCount();
    if ($("#fb-message").value.trim()) messageError("");
  });
  $("#fb-file").addEventListener("change", (e) => {
    const file = e.target.files?.[0];
    if (file) takeImage(file);
  });
  $("#fb-image-remove").addEventListener("click", dropImage);
  $("#fb-switch").addEventListener("click", signOut);
  $("#fb-again").addEventListener("click", again);
  // A screenshot pasted anywhere on the page is the screenshot; text pasted
  // into a field is left to the field.
  document.addEventListener("paste", (e) => {
    const file = [...(e.clipboardData?.items || [])]
      .find((item) => item.kind === "file" && item.type.startsWith("image/"))
      ?.getAsFile();
    if (!file) return;
    e.preventDefault();
    takeImage(file);
  });
  onRepaint(repaint);
  drawCount();
  drawExtras();
  // Google refuses to sign anyone in from a chat app's own browser; saying so
  // first beats a popup that fails with a Google error page.
  if (app) setSigninError("fbErrInApp");
  loadGsi();
}
