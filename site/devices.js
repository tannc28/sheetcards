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
