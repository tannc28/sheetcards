/**
 * Opened inside Zalo, Messenger, Facebook, Instagram, TikTok…: say so first.
 *
 * A link to this site is most often met inside a chat app, and a chat app opens
 * it in its own browser — a WebView that cannot save a file. The .apkg (and the
 * .csv) is the whole product on a phone, so a page that looks fine there and
 * then does nothing at Download is the worst failure it has. It is caught at
 * the door instead: a banner over everything, a button that copies the address,
 * and on Android a link that hands it to Chrome.
 *
 * The markers are the apps' own user-agent tokens. Facebook and Messenger write
 * `FBAN`/`FBAV` (iOS) or `FB_IAB`/`FBAV` (Android) and Messenger adds its name;
 * Instagram, Line (`Line/`), TikTok (`musical_ly`, `BytedanceWebview`, `trill`),
 * WeChat (`MicroMessenger`), Snapchat, LinkedIn (`LinkedInApp`) and Twitter
 * name themselves; Zalo writes `Zalo` (`ZaloTheme/`, `ZaloLanguage/` on Android).
 * An app that names nothing is still caught by the shape every WebView has: an
 * Android user agent carrying `; wv)`, or an iPhone one without `Safari/` —
 * except a page saved to the Home Screen, which is a real browser that drops
 * the token too.
 *
 * Detection has no DOM, so tests/test_site_inapp.py can run it in node.
 */

const APPS = [
  ["Zalo", /\bZalo/i],
  ["Messenger", /\bFB[\w_]+\/(Messenger|MESSENGER)|FB_IAB\/MESSENGER|MessengerForiOS|\bOrca-Android/i],
  ["Instagram", /\bInstagram/i],
  ["Facebook", /\bFBAN\/|\bFBAV\/|\bFB_IAB\/|\bFBIOS|\bFacebook/i],
  ["TikTok", /musical_ly|Bytedance|\btrill_|\bTikTok/i],
  ["Line", /\bLine\//],
  ["WeChat", /\bMicroMessenger\//i],
  ["Snapchat", /\bSnapchat/i],
  ["LinkedIn", /\bLinkedInApp/i],
  ["Twitter", /\bTwitter/i],
];

/**
 * The in-app browser this is, by name — `"WebView"` for an unnamed one — or ""
 * in a real browser.
 */
export function inAppBrowser({ userAgent = "", standalone = false } = {}) {
  for (const [name, marker] of APPS) if (marker.test(userAgent)) return name;
  if (/Android/i.test(userAgent) && /; wv\)/.test(userAgent)) return "WebView";
  if (/iPhone|iPad|iPod/.test(userAgent) && !/Safari\//.test(userAgent) && !standalone) {
    return "WebView";
  }
  return "";
}

/**
 * An address Chrome on Android opens instead of the app's WebView.
 *
 * The intent URI spends the address's own `#` on `#Intent;…`, so a fragment —
 * which is where a shared sheet lives — travels in `?sc_hash=` and is put back
 * by `restoreHash()` on arrival.
 */
export function chromeIntent(href) {
  const url = new URL(href);
  if (url.hash) {
    url.searchParams.set("sc_hash", url.hash.slice(1));
    url.hash = "";
  }
  const rest = url.href.replace(/^https?:\/\//, "");
  return (
    `intent://${rest}#Intent;scheme=${url.protocol.replace(":", "")};` +
    `package=com.android.chrome;S.browser_fallback_url=${encodeURIComponent(href)};end`
  );
}

/** Puts back a fragment that came through `chromeIntent`, before anything reads it. */
export function restoreHash(loc = globalThis.location, hist = globalThis.history) {
  if (!loc?.search || !/[?&]sc_hash=/.test(loc.search)) return;
  const params = new URLSearchParams(loc.search);
  const hash = params.get("sc_hash");
  params.delete("sc_hash");
  const query = params.toString();
  hist.replaceState(null, "", `${loc.pathname}${query ? `?${query}` : ""}#${hash}`);
}

/**
 * Draws the banner when this is an in-app browser, and returns the app's name.
 *
 * Its words are `data-i18n` placeholders, so the page's own language switch
 * repaints them with everything else; `t` fills them the first time.
 */
export function mountInAppBanner({ t, icon, nav = globalThis.navigator, doc = globalThis.document } = {}) {
  const standalone =
    nav.standalone === true || !!globalThis.matchMedia?.("(display-mode: standalone)").matches;
  const app = inAppBrowser({ userAgent: nav.userAgent || "", standalone });
  if (!app) return "";
  const android = /Android/i.test(nav.userAgent || "");
  // Taken now: a page may tidy its address once it has read it (Create sheet
  // drops a shared sheet's #s= after opening it), and the sheet is what has
  // to reach the other browser.
  const href = doc.location.href;
  const say = (key) => `<span data-i18n="${key}">${t(key)}</span>`;
  const bar = doc.createElement("div");
  bar.className = "inapp";
  bar.setAttribute("role", "alert");
  bar.innerHTML =
    `<p class="inapp-text">${icon("triangle-alert")}<span><strong>` +
    (app === "WebView" ? say("inappTitle") : `${say("inappTitleIn")} ${app}.`) +
    `</strong> ${say(android ? "inappAndroid" : "inappIos")}</span></p>` +
    '<p class="inapp-acts">' +
    (android
      ? `<a class="btn" href="${chromeIntent(href).replace(/"/g, "&quot;")}">` +
        `${icon("external-link")}${say("inappOpenChrome")}</a>`
      : "") +
    `<button type="button" class="${android ? "toolbtn" : "btn"} inapp-copy">${icon("copy")}${say("inappCopy")}</button></p>` +
    '<p class="inapp-url" hidden></p>';
  bar.querySelector(".inapp-copy").addEventListener("click", async () => {
    const label = bar.querySelector(".inapp-copy [data-i18n]");
    try {
      await nav.clipboard.writeText(href);
      label.dataset.i18n = "inappCopied";
      label.textContent = t("inappCopied");
    } catch {
      // No clipboard in this WebView: the address, to copy by hand.
      const line = bar.querySelector(".inapp-url");
      line.textContent = href;
      line.hidden = false;
    }
  });
  doc.body.prepend(bar);
  doc.documentElement.classList.add("in-app");
  return app;
}

restoreHash();
