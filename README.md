# SheetCards

**Your spreadsheet is your deck.** SheetCards is an Anki add-on that turns a
Google Sheet into flashcards: one row is one card, and the columns you name become
the card's fields, in any language. An optional settings row says how the card
looks, what it reads aloud and which subdeck it goes in. Each sync brings your
changes into Anki: new rows become cards, edited rows update them (your review
history is kept), deleted rows are removed. Nothing is written back; the sheet is
the source and Anki holds the copy.

**Website and documentation: <https://tannc28.github.io/sheetcards/>**

## Install

Requires Anki 25.x or later on Windows, macOS or Linux.

1. Download
   [`sheetcards.ankiaddon`](https://github.com/tannc28/sheetcards/releases/latest/download/sheetcards.ankiaddon).
2. In Anki, open **Tools → Add-ons**, press **Install from file…** and pick the
   file.
3. Restart Anki. A **SheetCards** menu appears under **Tools**.

## Quick start

1. Make a Google Sheet whose row 1 holds `ID` and your own column names, for
   example `ID | Word | Meaning`. Each row below is a card.
2. Share it: **Share → Anyone with the link → Viewer**.
3. In Anki: **Tools → SheetCards → Connect a Google Sheet…**, paste the link.
4. **Update Decks from Sheets…** (`Ctrl+Shift+S`) syncs. Run it again whenever
   the sheet changes.

| Menu item | Shortcut |
| :--- | :--- |
| Connect a Google Sheet… | |
| Update Decks from Sheets… | `Ctrl+Shift+S` |
| Disconnect a Sheet… | |
| Card Layout… | `Ctrl+Shift+C` |
| Settings… | `Ctrl+Shift+O` |

## Learn more

- **Documentation:** <https://tannc28.github.io/sheetcards/docs/>: columns, the
  settings row, themes, pictures and video, text to speech, syncing, and
  troubleshooting.
- **Preview:** <https://tannc28.github.io/sheetcards/preview.html>: paste a sheet
  link and see the decks and cards it makes, in your browser, before you install
  anything. It can also build an `.apkg` for AnkiDroid or AnkiMobile.
- **Example workbook:** thirty-one small decks, each showing one feature. Paste
  this link into the preview or into *Connect a Google Sheet…*:

  ```text
  https://github.com/tannc28/sheetcards/blob/main/examples/sheetcards-examples.xlsx
  ```

- **Problems and ideas:** <https://github.com/tannc28/sheetcards/issues>.

## Developing

Tests, the build and the release process are described in
[For developers](https://tannc28.github.io/sheetcards/docs/developers.html),
[`CONTRIBUTING.md`](CONTRIBUTING.md) and [`CLAUDE.md`](CLAUDE.md).

## License

Released under the [MIT License](LICENSE). SheetCards is not made by or affiliated
with Anki or Ankitects.
