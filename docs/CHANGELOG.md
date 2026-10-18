# Changelog

SheetCards stays on `0.x.y` until it is declared official, which will be `1.0.0`.
Until then a minor bump (`0.2.0`) may change how a sheet is read; a patch bump
(`0.1.1`) only fixes things.

---

## Unreleased (next minor — changes how a sheet is read)

- **The settings row is smaller.** `rtl` and `sort` are done without asking and
  still accepted silently: every field reads its own direction (`dir="auto"`),
  and Anki lists notes by the first content column that is not a deck level.
  `vertical` and a deck-wide `align`/`speed` in the `#config` cell are gone and
  warn with what to write instead (per-column `align`/`speed` stay).
- **The browser's sort column** only changes for note types Anki does not have
  yet. On an existing note type the add-on leaves it alone (a changed sort field
  is a schema change in Anki and would force a full sync), and Sheet to Anki
  keeps the one the last package used (a changed one makes the next default
  import skip every note).
- **`SUBDECK n` headers are being retired.** They still file notes, with a
  warning; write a column with a real name (`Bài học`) and `subdeck=1` in the
  settings row instead. Renaming the column adds it to the note type's fields,
  so Sheet to Anki asks for *Merge note types* once; the example workbook's
  sheets were converted this way. A shared Anki deck read back into a sheet gets
  `Deck 1`, `Deck 2`… columns marked `subdeck=n`.
- A bare `label` captions the field with the column's name; a spoken column
  takes its language's font (`zh_CN` → `sc`, `ja_JP` → `jp`…) unless it names
  one; columns that look like picture links or `漢字[かな]` say so.
- Line breaks inside a cell show on the card (not in code, formula, media or
  deck-level columns).
- A typed answer that differs only by capitals is no longer marked wrong.
- Create sheet: the full editor shows the Basic keys and folds the rest under
  *Nâng cao*; a new sheet on a phone opens on its word list, with *Thêm từ* and
  *Dán danh sách từ* side by side.

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
