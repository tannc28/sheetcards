/**
 * Which Anki the downloaded file is about to be opened in, and how.
 *
 * The .apkg is the whole product on a phone, and the step after the download is
 * the one people get stuck on: an Android phone asks which app should open the
 * file, an iPhone files it away in Files and says nothing. So the page guesses
 * the device and opens on its instructions, with the other two a tap away —
 * a guess, because the file is often downloaded on one machine and opened on
 * another.
 *
 * No DOM in here, so tests/test_site_devices.py can import it in node.
 */

export const DEVICES = ["android", "ios", "desktop"];

/** The i18n keys for each device's tab: its app, and the hardware it runs on. */
export const DEVICE_LABELS = {
  android: ["devAndroid", "devAndroidSub"],
  ios: ["devIos", "devIosSub"],
  desktop: ["devDesktop", "devDesktopSub"],
};

/** The i18n keys of each device's steps, in order. Each takes the file name. */
export const DEVICE_STEPS = {
  android: ["instAndroid1", "instAndroid2", "instAndroid3"],
  ios: ["instIos1", "instIos2", "instIos3"],
  desktop: ["instDesktop1", "instDesktop2"],
};

/**
 * The device a browser is running on, as one of `DEVICES`.
 *
 * iPadOS 13 and later sends a desktop Safari user agent ("Macintosh"), so the
 * only thing telling an iPad from a Mac is a touchscreen — no Mac has one.
 */
export function detectDevice({ userAgent = "", maxTouchPoints = 0 } = {}) {
  if (/android/i.test(userAgent)) return "android";
  if (/iPhone|iPad|iPod/i.test(userAgent)) return "ios";
  if (/Macintosh/i.test(userAgent) && maxTouchPoints > 1) return "ios";
  return "desktop";
}

/**
 * Where each Anki comes from, and what it costs. Studying happens in one of
 * these, never on this site, and on an iPhone the only one is paid — said in
 * so many words, since "free" on this site means SheetCards and only that.
 * AnkiMobile's price was read off the App Store in October 2026 (799.000đ in
 * Vietnam, US$24.99 in the US); the strings say it varies by country.
 */
export const ANKI_APPS = {
  android: {
    url: "https://play.google.com/store/apps/details?id=com.ichi2.anki",
    store: "Google Play",
    price: "ankiFree",
  },
  ios: {
    url: "https://apps.apple.com/app/ankimobile-flashcards/id373493387",
    store: "App Store",
    price: "ankiPaidIos",
  },
  desktop: { url: "https://apps.ankiweb.net/", store: "apps.ankiweb.net", price: "ankiFree" },
};

/**
 * The three apps as list items, the reader's own device first and marked.
 * `t` is the page's translator, so this module stays free of the DOM.
 */
export function ankiAppsHtml(t, mine = "", { only = false } = {}) {
  const order = only ? [mine] : mine ? [mine, ...DEVICES.filter((d) => d !== mine)] : DEVICES;
  return order
    .map((d) => {
      const app = ANKI_APPS[d];
      const [name, sub] = DEVICE_LABELS[d];
      return (
        `<li${d === mine ? ' class="mine"' : ""}><a class="ankiapp" href="${app.url}" rel="noopener" target="_blank">` +
        '<img src="./anki.png" alt="" width="32" height="32">' +
        `<span class="ankiapp-text"><strong>${t(name)}</strong><span>${t(sub)}</span>` +
        `<span class="ankiapp-price ${app.price === "ankiFree" ? "free" : "paid"}">${t(app.price)}</span></span>` +
        `<span class="ankiapp-store">${d === mine && !only ? `<em>${t("ankiYours")}</em>` : ""}${t("ankiGetAt", app.store)}</span></a></li>`
      );
    })
    .join("");
}
