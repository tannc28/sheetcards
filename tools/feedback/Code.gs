/**
 * SheetCards feedback — the website's contact form posts here.
 *
 * Deployed by the site's owner as a Google Apps Script *web app* bound to a
 * Google Sheet. Nothing else stores feedback: there is no server of our own.
 *
 * Every post carries a Google ID token from "Sign in with Google" on the site.
 * The token is checked with Google before anything is written, so the email in
 * the sheet is one Google has verified — it cannot be typed in by hand. That is
 * the whole point of asking people to sign in.
 *
 * Setup: see tools/feedback/README.md. The only value to fill in is CLIENT_ID.
 */

// The OAuth client ID the website signs people in with (Google Cloud console →
// APIs & Services → Credentials). A token issued to any other client is refused.
const CLIENT_ID = "PASTE-YOUR-CLIENT-ID.apps.googleusercontent.com";

const SHEET_NAME = "Góp ý";
const HEADERS = [
  "Thời gian",
  "Email",
  "Tên",
  "Loại",
  "Nội dung",
  "Thiết bị",
  "Link sheet",
  "Ảnh",
  "Trang",
  "Trình duyệt",
  "Ngôn ngữ",
];
const KINDS = ["bug", "feature", "other"];
const KIND_LABEL = { bug: "Báo lỗi", feature: "Đề xuất tính năng", other: "Khác" };

const MAX_MESSAGE = 5000;
const MAX_FIELD = 500;
const MAX_IMAGE_BYTES = 4 * 1024 * 1024;
const IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp", "image/gif"];
// A person may send a few in a row (one bug, then another); more than this in
// ten minutes is a script, not a person.
const RATE_LIMIT = 5;
const RATE_WINDOW_SECONDS = 600;

/** A GET is a health check: the site can tell the endpoint is alive. */
function doGet() {
  return reply({ ok: true, service: "sheetcards-feedback" });
}

/**
 * The site sends the body as text/plain JSON — a "simple" request, so the
 * browser sends no CORS preflight, which Apps Script cannot answer.
 */
function doPost(e) {
  try {
    const body = JSON.parse((e && e.postData && e.postData.contents) || "{}");
    const who = verify(body.idToken);
    if (!who) return reply({ ok: false, error: "auth" });
    if (!allowed(who.email)) return reply({ ok: false, error: "rate" });

    const kind = KINDS.indexOf(body.kind) >= 0 ? body.kind : "other";
    const message = clip(body.message, MAX_MESSAGE);
    if (!message.trim()) return reply({ ok: false, error: "empty" });

    let imageLink = "";
    if (body.image && body.image.data) {
      imageLink = saveImage(body.image, who.email);
      if (imageLink === null) return reply({ ok: false, error: "image" });
    }

    const row = [
      new Date(),
      who.email,
      clip(who.name, MAX_FIELD),
      KIND_LABEL[kind],
      message,
      clip(body.device, MAX_FIELD),
      clip(body.sheetUrl, MAX_FIELD),
      imageLink,
      clip(body.page, MAX_FIELD),
      clip(body.userAgent, MAX_FIELD),
      clip(body.lang, 16),
    ];
    sheet().appendRow(row);
    notify(row);
    return reply({ ok: true });
  } catch (err) {
    console.error(err);
    return reply({ ok: false, error: "server" });
  }
}

/** The signed-in person, if Google confirms the token was issued to us. */
function verify(idToken) {
  if (!idToken || typeof idToken !== "string") return null;
  const res = UrlFetchApp.fetch(
    "https://oauth2.googleapis.com/tokeninfo?id_token=" + encodeURIComponent(idToken),
    { muteHttpExceptions: true },
  );
  if (res.getResponseCode() !== 200) return null;
  const info = JSON.parse(res.getContentText());
  const issuers = ["accounts.google.com", "https://accounts.google.com"];
  if (info.aud !== CLIENT_ID) return null;
  if (issuers.indexOf(info.iss) < 0) return null;
  if (String(info.email_verified) !== "true") return null;
  if (Number(info.exp) * 1000 < Date.now()) return null;
  return { email: String(info.email).toLowerCase(), name: info.name || "" };
}

function allowed(email) {
  const cache = CacheService.getScriptCache();
  const key = "rate:" + email;
  const count = Number(cache.get(key) || 0);
  if (count >= RATE_LIMIT) return false;
  cache.put(key, String(count + 1), RATE_WINDOW_SECONDS);
  return true;
}

/** Stores a screenshot in the owner's Drive; null when it is refused. */
function saveImage(image, email) {
  const type = String(image.type || "");
  if (IMAGE_TYPES.indexOf(type) < 0) return null;
  const bytes = Utilities.base64Decode(String(image.data));
  if (bytes.length > MAX_IMAGE_BYTES) return null;
  const name =
    Utilities.formatDate(new Date(), "Asia/Ho_Chi_Minh", "yyyy-MM-dd HH.mm.ss") +
    " " + email + " " + clip(image.name || "screenshot", 80);
  const file = folder().createFile(Utilities.newBlob(bytes, type, name));
  return file.getUrl();
}

function folder() {
  const props = PropertiesService.getScriptProperties();
  const id = props.getProperty("FOLDER_ID");
  if (id) {
    try {
      return DriveApp.getFolderById(id);
    } catch (err) {
      // Deleted by hand: make a new one below.
    }
  }
  const made = DriveApp.createFolder("SheetCards — ảnh góp ý");
  props.setProperty("FOLDER_ID", made.getId());
  return made;
}

function sheet() {
  const book = SpreadsheetApp.getActiveSpreadsheet();
  let tab = book.getSheetByName(SHEET_NAME);
  if (!tab) {
    tab = book.insertSheet(SHEET_NAME);
    tab.appendRow(HEADERS);
    tab.setFrozenRows(1);
    tab.getRange(1, 1, 1, HEADERS.length).setFontWeight("bold");
  }
  return tab;
}

/** One email to the owner per piece of feedback (Apps Script allows 100/day). */
function notify(row) {
  const owner = Session.getEffectiveUser().getEmail();
  if (!owner) return;
  const subject = "[SheetCards] " + row[3] + " — " + row[1];
  const lines = HEADERS.map(function (h, i) {
    return h + ": " + (row[i] instanceof Date ? row[i].toISOString() : row[i]);
  });
  MailApp.sendEmail({
    to: owner,
    replyTo: row[1],
    subject: subject,
    body: lines.join("\n") + "\n\n" + SpreadsheetApp.getActiveSpreadsheet().getUrl(),
  });
}

function clip(value, max) {
  return String(value == null ? "" : value).slice(0, max);
}

function reply(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(
    ContentService.MimeType.JSON,
  );
}

/** Run once by hand after pasting the code: creates the tab and asks for access. */
function setup() {
  sheet();
  folder();
  console.log("Ready. Sheet tab and Drive folder exist.");
}
