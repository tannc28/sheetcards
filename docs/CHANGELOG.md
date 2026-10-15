# Changelog

SheetCards stays on `0.x.y` until it is declared official, which will be `1.0.0`.
Until then a minor bump (`0.2.0`) may change how a sheet is read; a patch bump
(`0.1.1`) only fixes things.

---

## **v0.1.0** - October 2026

The first release under the new numbering. Earlier releases (up to v7.0.0) were
withdrawn; their history is in git.

- Keep flashcards in a Google Sheet (or an `.xlsx` on GitHub) and sync them into
  Anki: one row is one note, the sheet decides the fields, the deck path and the
  tags, and an optional settings row on row 2 decides how the card looks.
- Syncing runs in the background, so Anki no longer freezes while a sheet
  downloads; Cancel stops after the current deck. A clean sync ends in a short
  tooltip instead of a window.
- Errors say what to do: a sheet that isn't shared, a link with no sheet behind
  it and a missing connection each get their own sentence.
- The menu reads in plain words (*Connect a Google Sheet…*, *Update Decks from
  Sheets…*), and Add-ons → Config opens the add-on's own Settings.
- Shortcuts no longer collide with Anki's: Connect and Disconnect have none
  (`Ctrl+Shift+A` is Anki's Add-ons, `Ctrl+Shift+D` its Set Due Date).
- Disconnecting keeps the cards unless you tick the box, and Enter on the
  confirmation cancels rather than deletes.
- Cards are readable on a phone: the front scales down on narrow screens, and a
  spoken column tells the phone its language so CJK text uses the right glyphs.
- `theme=sakura` paints the card in cherry-blossom pink with blossoms behind the
  text; `theme=ptrang` is the VIP edition.
