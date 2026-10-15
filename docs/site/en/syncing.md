# Syncing

Every time you choose **Update Decks from Sheets…** (`Ctrl+Shift+S`), the add-on
downloads each sheet you ticked and makes Anki match it. Nothing is ever written
back to the sheet.

## Notes are matched by `ID`

Each row's `ID` is stored in the note's first field, also called `ID`. On every
sync the add-on reads that field to pair rows with notes. So:

- **Never change an ID.** A changed ID looks like one row deleted and a new one
  added: the old note is removed and a new one is created, without its review
  history.
- **Never reuse an ID.** Two rows with the same ID become one note. The sync
  lists duplicates as an error: *"Duplicate IDs in the spreadsheet"*.
- **A row with an empty `ID` is never synced.**
- **Keep the notes in their deck.** A note moved out of its `sc_…` deck in Anki
  is no longer found, and the next sync creates it again.

## What each change does

| You do this in the sheet | The sync does this |
| :--- | :--- |
| Add a row | Creates a note |
| Edit a cell | Updates that field; the note keeps its review history |
| Change a `SUBDECK` cell | Moves the note's cards to the new subdeck and updates its tags |
| Set `SYNC` to anything but yes | **Leaves the note as it is** and stops updating it. It is not deleted |
| Set `SYNC` back to yes | Updates that note again |
| Delete a row | **Deletes the note** |
| Add a column | Adds a field of that name and puts it on the back of the card |
| Remove a column | **Keeps the field and its content in Anki** and stops showing it |
| Rename a column | Counts as removing one column and adding another: a new empty field appears, and the old one keeps its content |
| Edit the [settings row](settings-row.md) | Rebuilds the card design. Notes and review history are untouched |

## Safety rules

- **No valid rows, no deletions.** If a download comes back with no row that has
  an `ID` (an empty sheet, the wrong tab, a broken export), every note would look
  deleted. The add-on deletes nothing and says so: *"Sync safety: the spreadsheet
  returned no valid rows…"*.
- **Changing a note's type never loses it.** When a sheet becomes a cloze sheet,
  or stops being one, each note has to be recreated as the other type. The new
  note is created before the old one is removed. Its review history starts again;
  Anki cannot change a note's type in place.
- **Removing a column never deletes what you collected** in it.

## Names come from the sheet

A deck is named after the spreadsheet file and the sheet: `sc_<file>::<sheet>`,
and its note types `SheetCards - <deck> - Basic` and `- Cloze`. When you rename
the spreadsheet file, the next sync renames the deck and note types to match.

**Renaming a SheetCards deck or note type inside Anki does not last**: the next
sync renames it back. Rename the spreadsheet instead.

Editing a SheetCards note type's front or back template in Anki does not last
either: it is rebuilt from the sheet on every sync. The Styling section can carry
your own CSS; see [the settings row](settings-row.md#styling-one-column-with-css).

## When a sync finishes

- Subdecks left with no cards are removed.
- All connected decks study under one Anki preset, **SheetCards - Default
  Options**, created if missing. A new preset starts at 20 new and 200 review
  cards a day. Change it in Anki's own deck options; the add-on never overwrites
  a preset that already exists.
- A clean sync ends with a short message. If something needs your attention, a
  summary window opens with three views (*Summary*, *Full details*, *Errors
  only*) and the row counts: rows in the sheet, rows with an ID, rows skipped for
  a missing ID, empty rows ignored, rows ticked and not ticked in `SYNC`, and
  notes created, updated, deleted and unchanged.
- If **Upload to AnkiWeb** is on in Settings, Anki's own sync runs next, so the
  new cards reach your phone.

A deck that fails does not stop the others; its error appears in the summary.
Syncing runs in the background, and **Cancel** stops after the current deck.

## Where settings are kept

| What | Where | Travels to your other devices? |
| :--- | :--- | :--- |
| The card design read from the settings row | Anki's collection | **Yes**, with AnkiWeb |
| Note types, notes and cards | Anki's collection | **Yes** |
| Which sheets are connected, the AnkiWeb and debug settings | `meta.json` in the add-on's folder | No, this computer only |

The settings row is copied into the collection so a second computer shows the
same cards before it has downloaded the sheet itself. The sheet is still the
source: the next sync overwrites that copy.
