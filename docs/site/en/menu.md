# Menu and shortcuts

Everything is under **Tools → SheetCards** in Anki.

| Menu item | Shortcut | What it does |
| :--- | :--- | :--- |
| Connect a Google Sheet… | none | Adds decks from a sheet link |
| Update Decks from Sheets… | `Ctrl+Shift+S` | Syncs the decks you tick |
| Disconnect a Sheet… | none | Stops syncing a deck, and can delete it |
| Card Layout… | `Ctrl+Shift+C` | Shows what the sheet's settings row said |
| Settings… | `Ctrl+Shift+O` | AnkiWeb upload and the debug log |

On macOS, `Cmd` replaces `Ctrl`. Connect and Disconnect have no shortcut because
Anki already uses `Ctrl+Shift+A` (Add-ons) and `Ctrl+Shift+D` (Set Due Date).

## Connect a Google Sheet…

Paste the link to a Google Sheet, or to an `.xlsx` file. The window checks the
link a moment after you stop typing, downloads it, and tells you what it found:
the sheets, their rows, and the decks it will make. Each sheet with an `ID`
column becomes a deck (in a file where no sheet has one, every sheet does); see [Sheets, files and .apkg](sources.md).

- There is no name field: a deck takes the sheet's `name=` when it has one
  (exactly as typed), otherwise it is named after the file and the sheet.
- A sheet already connected cannot be added twice.
- The sheet must be shared as **Anyone with the link → Viewer**.

When nothing is connected yet, the other windows offer this one too.

## Update Decks from Sheets…

Lists every connected deck with a tick box and its card count. Your ticks are
remembered for next time. Press **Update** to sync; see [Syncing](syncing.md).

## Disconnect a Sheet…

Tick the decks to stop syncing. One box decides what happens to them in Anki:

- **Left unticked (the default):** the decks, cards and review history stay in
  Anki exactly as they are; only the link to the sheet is removed.
- **Ticked, "Also delete the local decks, cards and note types":** the decks and
  their subdecks, every card in them, and their SheetCards note types are deleted.

Pressing Enter on the confirmation cancels rather than deletes. If you delete by
mistake, Anki's **Edit → Undo** and its automatic backups (**Preferences →
Backups**) can bring the collection back, and the sheet is still there to sync
from. Review history of deleted cards cannot come back from the sheet.

## Card Layout…

A read-only window showing, for each deck, what the add-on understood from the
sheet's [settings row](settings-row.md):

- **What the add-on understood**: which columns go on the front, which on the
  back, which are hidden, and each column's settings as the add-on read them.
- **Warnings**: everything it could not understand, by column.
- **Preview**: the card design it built, with sample content.

It shows the result of the **last sync**, so after editing the sheet press
`Ctrl+Shift+S` first. It has no editing controls on purpose: a card's look is
changed in the sheet, so there is only one place it can be changed.

## Settings…

Also opened by the **Config** button for SheetCards in **Tools → Add-ons**.

- **Upload to AnkiWeb** (under *After a sync*). On by default. After a sync, Anki's own
  sync runs, so new cards reach your phone without a second click. You need to
  have signed in to AnkiWeb once through **Tools → Sync**.
- **Write a debug log.** Off by default. Records every step of a sync in
  `debug_sheetcards.log` in the add-on's folder; the window shows the path and
  opens the folder. A second box, **Keep the logs from earlier syncs** (on by
  default), keeps earlier syncs' logs; untick it and each sync starts a fresh
  log. Turn it on before reproducing a problem. The log contains
  your sheet's content, so read it before sharing it publicly.

Changes are saved when you press **Save**.
