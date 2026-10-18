/**
 * The site's icons, as inline SVG — one set, one style, one place.
 *
 * Every path below but the brand marks (GitHub, Facebook, Google Sheets, Quizlet, Anki) is copied by hand from Lucide (https://lucide.dev), ISC
 * licence, Copyright (c) Lucide Contributors 2022; portions derived from Feather,
 * MIT licence, Copyright (c) 2013-2022 Cole Bemis. Copied rather than loaded, so
 * nothing on the page depends on a CDN being up. All share Lucide's 24×24 box and
 * 2px round stroke, and draw in `currentColor`, so an icon is the colour of the
 * words beside it in either theme.
 *
 * An icon is here only when it helps somebody find or recognise an action
 * faster. Placed next to a label it is `aria-hidden` and says nothing to a
 * screen reader; an icon-only button carries its own `aria-label` instead.
 *
 * No emoji and no text glyphs (☾ ☀ ↻): those belong to the font, render as
 * colour pictures on some systems and as tofu on others, and are never the
 * colour of the text next to them.
 */

const PATHS = {
  // Fetch the sheet again.
  "rotate-cw":
    '<path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/>',
  upload:
    '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>' +
    '<polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/>',
  // Leave an app's own browser for a real one.
  "external-link":
    '<path d="M15 3h6v6"/><path d="M10 14 21 3"/>' +
    '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
  copy:
    '<rect width="14" height="14" x="8" y="8" rx="2" ry="2"/>' +
    '<path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
  // Create sheet: the words, the file, the link, and taking a step back.
  "file-plus":
    '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>' +
    '<path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M9 15h6"/><path d="M12 18v-6"/>',
  // Keep the sheet's columns and settings row as a template of one's own.
  "bookmark-plus":
    '<path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/>' +
    '<line x1="12" x2="12" y1="7" y2="13"/><line x1="15" x2="9" y1="10" y2="10"/>',
  "file-spreadsheet":
    '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>' +
    '<path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M8 13h2"/><path d="M14 13h2"/>' +
    '<path d="M8 17h2"/><path d="M14 17h2"/>',
  "file-text":
    '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>' +
    '<path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
  "folder-open":
    '<path d="m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2"/>',
  "share-2":
    '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>' +
    '<line x1="8.59" x2="15.42" y1="13.51" y2="17.49"/><line x1="15.41" x2="8.59" y1="6.51" y2="10.49"/>',
  "trash-2":
    '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/>' +
    '<path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>' +
    '<line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/>',
  "undo-2":
    '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5a5.5 5.5 0 0 1-5.5 5.5H11"/>',
  "redo-2":
    '<path d="m15 14 5-5-5-5"/><path d="M20 9H9.5A5.5 5.5 0 0 0 4 14.5A5.5 5.5 0 0 0 9.5 20H13"/>',
  "arrow-up": '<path d="m5 12 7-7 7 7"/><path d="M12 19V5"/>',
  "arrow-down": '<path d="M12 5v14"/><path d="m19 12-7 7-7-7"/>',
  plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
  x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  sun:
    '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/>' +
    '<path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/>' +
    '<path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/>' +
    '<path d="m19.07 4.93-1.41 1.41"/>',
  moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
  languages:
    '<path d="m5 8 6 6"/><path d="m4 14 6-6 2-3"/><path d="M2 5h12"/><path d="M7 2h1"/>' +
    '<path d="m22 22-5-10-5 10"/><path d="M14 18h6"/>',
  "triangle-alert":
    '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/>' +
    '<path d="M12 9v4"/><path d="M12 17h.01"/>',
  "circle-alert":
    '<circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/>' +
    '<line x1="12" x2="12.01" y1="16" y2="16"/>',
  "arrow-left": '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
  "arrow-right": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
  // The landing page's features: one icon each, for the thing a learner does.
  "sliders-horizontal":
    '<line x1="21" x2="14" y1="4" y2="4"/><line x1="10" x2="3" y1="4" y2="4"/>' +
    '<line x1="21" x2="12" y1="12" y2="12"/><line x1="8" x2="3" y1="12" y2="12"/>' +
    '<line x1="21" x2="16" y1="20" y2="20"/><line x1="12" x2="3" y1="20" y2="20"/>' +
    '<line x1="14" x2="14" y1="2" y2="6"/><line x1="8" x2="8" y1="10" y2="14"/>' +
    '<line x1="16" x2="16" y1="18" y2="22"/>',
  "volume-2":
    '<path d="M11 4.702a.705.705 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.705.705 0 0 0 11 19.298z"/>' +
    '<path d="M16 9a5 5 0 0 1 0 6"/><path d="M19.364 18.364a9 9 0 0 0 0-12.728"/>',
  // Create sheet: the "make your own" template tile.
  "pencil-ruler":
    '<path d="M13 7 8.7 2.7a2.41 2.41 0 0 0-3.4 0L2.7 5.3a2.41 2.41 0 0 0 0 3.4L7 13"/>' +
    '<path d="m8 6 2-2"/>' +
    '<path d="m18 16 2-2"/>' +
    '<path d="m17 11 4.3 4.3c.94.94.94 2.46 0 3.4l-2.6 2.6c-.94.94-2.46.94-3.4 0L11 17"/>' +
    '<path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/>' +
    '<path d="m15 5 4 4"/>',
  "pen-line":
    '<path d="M13 21h8"/>' +
    '<path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/>',
  // Sheet to Anki: the link field, its paste button, the example, the privacy line.
  link:
    '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>' +
    '<path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
  clipboard:
    '<rect width="8" height="4" x="8" y="2" rx="1" ry="1"/>' +
    '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>',
  sparkles:
    '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/>' +
    '<path d="M20 3v4"/><path d="M22 5h-4"/><path d="M4 17v2"/><path d="M5 18H3"/>',
  lock:
    '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
  // A spreadsheet: the source bar, the Sheet view, the landing page.
  sheet:
    '<rect width="18" height="18" x="3" y="3" rx="2" ry="2"/>' +
    '<line x1="3" x2="21" y1="9" y2="9"/><line x1="3" x2="21" y1="15" y2="15"/>' +
    '<line x1="9" x2="9" y1="9" y2="21"/><line x1="15" x2="15" y1="9" y2="21"/>',
  layers:
    '<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/>' +
    '<path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/>' +
    '<path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>',
  // The devices the .apkg is opened on.
  smartphone: '<rect width="14" height="20" x="5" y="2" rx="2" ry="2"/><path d="M12 18h.01"/>',
  monitor:
    '<rect width="20" height="14" x="2" y="3" rx="2"/>' +
    '<line x1="8" x2="16" y1="21" y2="21"/><line x1="12" x2="12" y1="17" y2="21"/>',
  download:
    '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>' +
    '<polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
  // Re-importing keeps the review history.
  history:
    '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>' +
    '<path d="M12 7v5l4 2"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  "chevron-down": '<path d="m6 9 6 6 6-6"/>',
  "chevron-right": '<path d="m9 18 6-6-6-6"/>',
  "chevron-left": '<path d="m15 18-6-6 6-6"/>',
  // A menu of the actions there is no room to spell out.
  ellipsis: '<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>',
  // The demo's own pause, which an animation that changes by itself has to offer.
  pause:
    '<rect x="14" y="4" width="4" height="16" rx="1"/><rect x="6" y="4" width="4" height="16" rx="1"/>',
  play: '<polygon points="6 3 20 12 6 21 6 3"/>',
  // The contact page: the link to it on every page, the screenshot, sending.
  "message-square": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  image:
    '<rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/>' +
    '<path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>',
  send:
    '<path d="M14.536 21.686a.5.5 0 0 0 .937-.024l6.5-19a.496.496 0 0 0-.635-.635l-19 6.5a.5.5 0 0 0-.024.937l7.93 3.18a2 2 0 0 1 1.112 1.11z"/>' +
    '<path d="m21.854 2.147-10.94 10.939"/>',
  // Notes, among the sources a set can come from.
  "notebook-pen":
    '<path d="M13.4 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7.4"/>' +
    '<path d="M2 6h4"/><path d="M2 10h4"/><path d="M2 14h4"/><path d="M2 18h4"/>' +
    '<path d="M21.378 5.626a1 1 0 1 0-3.004-3.004l-5.01 5.012a2 2 0 0 0-.506.854l-.837 2.87a.5.5 0 0 0 .62.62l2.87-.837a2 2 0 0 0 .854-.506z"/>',
  // The sources a set can come from that have a mark of their own: from Simple
  // Icons (https://simpleicons.org, v13.21.0), CC0 1.0, filled like GitHub's.
  // One colour, the text's, never the brand's. Excel has none there (Microsoft
  // asked for its marks to be removed), so a file is Lucide's file-spreadsheet.
  googlesheets:
    '<path fill="currentColor" stroke="none" d="M11.318 12.545H7.91v-1.909h3.41v1.91zM14.728 0v6h6l-6-6zm1.363 10.636h-3.41v1.91h3.41v-1.91zm0 3.273h-3.41v1.91h3.41v-1.91zM20.727 6.5v15.864c0 .904-.732 1.636-1.636 1.636H4.909a1.636 1.636 0 0 1-1.636-1.636V1.636C3.273.732 4.005 0 4.909 0h9.318v6.5h6.5zm-3.273 2.773H6.545v7.909h10.91v-7.91zm-6.136 4.636H7.91v1.91h3.41v-1.91z"/>',
  quizlet:
    '<path fill="currentColor" stroke="none" d="M12.779.025a11.789 11.789 0 0 0-5.338.896A11.829 11.829 0 0 0 3.058 4.11 11.928 11.928 0 0 0 .427 14.363a11.92 11.92 0 0 0 2.3 4.921 11.842 11.842 0 0 0 4.24 3.378 11.783 11.783 0 0 0 10.533-.226.327.327 0 0 1 .331.018 9.136 9.136 0 0 0 5.197 1.545.332.332 0 0 0 .332-.332v-4.038a.334.334 0 0 0-.276-.331 4.732 4.732 0 0 1-1.106-.319.329.329 0 0 1-.191-.352.33.33 0 0 1 .05-.133 11.943 11.943 0 0 0 .772-11.871 11.87 11.87 0 0 0-4.042-4.628A11.793 11.793 0 0 0 12.765.018l.013.007h.001ZM4.843 11.898a7.24 7.24 0 0 1 1.205-4.005 7.18 7.18 0 0 1 3.215-2.657 7.133 7.133 0 0 1 7.815 1.558 7.239 7.239 0 0 1 1.555 7.854 7.202 7.202 0 0 1-2.643 3.234 7.147 7.147 0 0 1-9.049-.896 7.228 7.228 0 0 1-2.103-5.089l.005.001Z"/>',
  anki:
    '<path fill="currentColor" stroke="none" d="m15.845 22.627-.169.131-.182.091c-.109.042-.23.069-.362.079-.27.021-.611-.036-.989-.16-.686-.223-1.537-.67-2.256-.973-.343-.145-.633-.281-.829-.254-.197.027-.44.236-.73.467-.611.486-1.311 1.145-1.91 1.546-.331.22-.644.368-.91.42-.13.026-.255.032-.37.021l-.201-.038-.196-.082-.177-.119-.143-.145a1.3 1.3 0 0 1-.187-.32c-.104-.25-.154-.593-.154-.99.001-.721.164-1.669.23-2.447.031-.37.07-.687-.016-.866-.087-.178-.359-.345-.67-.55-.65-.431-1.494-.893-2.06-1.34-.312-.246-.548-.498-.681-.735a1.3 1.3 0 0 1-.134-.345l-.025-.202.016-.213.059-.205.094-.18c.064-.097.145-.191.246-.277.207-.175.517-.33.895-.452.685-.222 1.637-.361 2.397-.539.362-.084.676-.145.819-.281.144-.138.217-.45.316-.808.209-.752.387-1.696.638-2.373.138-.373.305-.676.489-.874.091-.098.187-.176.286-.235l.185-.086.207-.051.214-.006.2.033c.113.03.226.079.339.148.231.143.473.389.706.711.424.584.85 1.446 1.253 2.114.192.318.347.598.522.692.174.094.494.068.865.052.78-.034 1.734-.157 2.455-.128.397.017.736.081.983.195.12.055.223.123.31.201l.14.148.112.181.072.201.03.202c.007.115-.005.238-.036.368-.063.263-.223.57-.457.891-.425.583-1.113 1.254-1.623 1.845-.244.281-.463.514-.498.71-.035.194.089.49.219.838.273.731.684 1.601.879 2.295.108.382.151.725.119.995-.015.131-.049.252-.095.358l-.098.179zm-1.54-18.929c-.018-.057-.07-.226-.122-.346-.17-.387-.418-.846-.544-1.216-.166-.483-.099-.88.102-1.096.201-.214.592-.308 1.086-.177.377.1.851.316 1.249.458.125.044.297.084.354.096.047-.032.193-.134.291-.221.316-.282.675-.659.988-.894.408-.305.807-.366 1.074-.241.266.124.476.468.504.977.021.391-.037.909-.049 1.331-.004.132.011.309.017.366.046.035.187.142.301.209.365.213.835.438 1.155.662.417.294.597.655.56.947-.035.293-.296.599-.773.782-.365.141-.875.246-1.28.364-.126.037-.29.106-.343.129-.019.056-.077.223-.105.351-.091.413-.159.93-.274 1.304-.151.487-.438.77-.727.826s-.661-.098-.983-.494c-.246-.303-.504-.756-.742-1.105-.074-.11-.19-.243-.229-.287-.058-.001-.235-.004-.366.009-.421.042-.933.135-1.324.141-.51.008-.867-.177-1.011-.435-.142-.257-.11-.659.167-1.088.212-.328.563-.713.822-1.047.08-.104.171-.256.202-.305"/>',
  // Facebook's mark, for the contact page only: from Simple Icons
  // (https://simpleicons.org), CC0 1.0, filled like the GitHub one below.
  facebook:
    '<path fill="currentColor" stroke="none" d="M9.101 23.691v-7.98H6.627v-3.667h2.474v-1.58c0-4.085 1.848-5.978 5.858-5.978.401 0 .955.042 1.468.103a8.68 8.68 0 0 1 1.141.195v3.325a8.623 8.623 0 0 0-.653-.036 26.805 26.805 0 0 0-.733-.009c-.707 0-1.259.096-1.675.309a1.686 1.686 0 0 0-.679.622c-.258.42-.374.995-.374 1.752v1.297h3.919l-.386 2.103-.287 1.564h-3.246v8.245C19.396 23.238 24 18.179 24 12.044c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.628 3.874 10.35 9.101 11.647Z"/>',
  // GitHub's mark, in the masthead beside the switches. Lucide ships no
  // brand marks, so this path is GitHub's from Simple Icons
  // (https://simpleicons.org), CC0 1.0. A solid shape, not a stroke: the path
  // fills itself in currentColor and turns the inherited stroke off.
  github:
    '<path fill="currentColor" stroke="none" d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/>',
};

/** One icon as markup, sized to the text around it (1em) unless CSS says more. */
export function icon(name, cls = "") {
  const body = PATHS[name];
  if (!body) return "";
  return (
    `<svg class="icon${cls ? ` ${cls}` : ""}" viewBox="0 0 24 24" width="1em" height="1em" ` +
    'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
    `stroke-linejoin="round" aria-hidden="true" focusable="false">${body}</svg>`
  );
}

/** Fills every `data-icon` placeholder in the static markup. */
export function paintIcons(root = document) {
  for (const el of root.querySelectorAll("[data-icon]")) {
    el.innerHTML = icon(el.dataset.icon);
  }
}

export const ICON_NAMES = Object.keys(PATHS);
