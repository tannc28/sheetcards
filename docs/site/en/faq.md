# FAQ and troubleshooting

## Common messages

**"This sheet isn't shared."**
The sheet is private. In Google Sheets: **Share → General access → Anyone with
the link → Viewer**.

**"This file isn't public."**
The `.xlsx` link needs signing in. Make sure anyone with the link can open it.

**"There's no sheet at this address."**
The link is mistyped, or the file was deleted.

**"Can't reach Google."**
No internet connection, or Google could not be reached. Try again.

**"URL must be a Google Sheets edit URL…"**
Paste the link from your browser's address bar, the one that looks like
`https://docs.google.com/spreadsheets/d/…/edit…`.

**"Refusing to download over 'http'…" / "…inside a private network"**
The address must be public and start with `https`. See
[Sheets, files and .apkg](sources.md#an-xlsx-file-instead-of-a-google-sheet).

**"Mandatory header missing: 'ID'"**
Row 1 has no `ID` column. Only row 1 is read as the column names, so a title row
above it breaks this.

**"The sheet has no content columns"**
The sheet only has `ID`, `SYNC`, `TAGS` or `SUBDECK` columns. Add at least one
column of your own.

**"Duplicate IDs in the spreadsheet"**
Two or more rows share an `ID`, and only one of them reaches Anki. Give every row
its own.

**"Sync safety: the spreadsheet returned no valid rows…"**
Nothing was deleted, on purpose. Check that row 1 holds the column names and the
`ID` column is filled, then sync again.

**"AnkiWeb not configured - access Tools > Sync in Anki"**
Sign in to AnkiWeb once through Anki's own **Tools → Sync**; the add-on uses
that session.

## Cards and settings

**I changed the settings row and nothing happened.**
The settings row is read during a sync, so press `Ctrl+Shift+S` first. Then open
**Card Layout…** (`Ctrl+Shift+C`) and look at **Warnings**: a misspelled key
(`siz=48`) or a value out of range is reported there instead of being applied.

**A row full of `key=value` text became a card, or my first card is missing.**
The settings row is recognised only when its `ID` cell starts with `#config`.
Write `#config` alone, or `#config` followed by a space and the sheet-wide
settings. Equally, a row whose `ID` happens to start with `#config` is treated as
settings and never becomes a card.

**Text to speech is silent.**
Check, in this order: the code is complete (`zh_CN`, not `zh`); the device has a
voice for that language installed (open the **TTS voices** section on the back of
the card to see what it has); the cell is not empty. See
[Text to speech](tts.md).

**The wrong language is read for part of a card.**
Anki reads a whole field with one voice. Put each language in its own column with
its own `tts=`.

**`furigana` prints nothing above the text.**
The cell has to be written `推迟[tuī chí]`: text, then the reading in square
brackets.

**`reverse` does nothing on some sheets.**
Cloze sheets cannot have reverse cards.

**A cloze card's question is blank, with `{{c1::…}}` printed on the back.**
The sheet does not say which column holds the deletions. Add `cloze` to that
column in the settings row. See [Card types](card-types.md#cloze).

**Pictures do not appear.**
A picture pasted into a cell is not a link Anki can reach. Upload it somewhere
with a link, put the link in the cell and mark the column `image`. The card then
needs the internet to show it. See [Media](media.md).

**A video shows an error.**
The link names a channel, playlist or folder rather than one video, or the video
does not allow embedding. The warnings in Sheet to Anki say which.

## Decks

**Anki renamed my deck back after I renamed it.**
That is expected: names come from the sheet. Rename the spreadsheet file instead.
See [Syncing](syncing.md#names-come-from-the-sheet).

**I renamed a sheet tab and its deck stopped updating.**
A deck remembers its sheet by name. Connect the file again to pick up the new
name.

**I deleted a row but the card is still in Anki.**
If you imported an `.apkg` from Sheet to Anki, that is how imports work: they
update and add but never delete. Syncing with the add-on does delete.

**I set `SYNC` to no, but the card was not deleted.**
That is on purpose: an unticked row is left as it is and stops being updated.
Delete the row to delete the card.

## On a phone

**Download gives no file, or the page says "Open this page in Chrome/Safari".**
You are in an app's built-in browser (Zalo, Messenger, Facebook, Instagram,
TikTok, Line…), which cannot save files. Press **Copy link** on the banner and
paste it into Chrome or Safari; on Android press **Open in Chrome**. Or open the
app's menu (the three dots) and choose to open in a browser.

**Chrome on Android saves the file as `….apkg.zip` and AnkiDroid won't open it.**
The file is fine; it only gained a `.zip`. Open the **Files** app, long-press the
file → **Rename**, delete the `.zip` so the name ends in `.apkg`, then tap it and
pick AnkiDroid. Or, in AnkiDroid: menu → **Import** → choose the file.

**On an iPhone, AnkiMobile is not in the Share sheet.**
Open AnkiMobile once first (it has to be installed and opened at least once). In
the **Files** app, tap the `.apkg` → **Share**, scroll the row of apps to
**More** and turn AnkiMobile on. AnkiMobile is Anki's paid app; if you have not
bought it, it is not on the phone.

**My cards doubled after importing again.**
Anki updates the old notes only when the new file is recognised as the same deck.
A deck is recognised by the **flashcard set's name** (`name=` in the settings
row's `#config` cell); a sheet without one goes by its Google Sheets link, then
by its file name. Renaming the set, or an old unnamed sheet whose file was
renamed, makes a new deck. To fix it, delete the extra deck in Anki (keep the one
with your review history), and keep the set's name the same from then on. Create
sheet always asks for the name, and offers to write it into an old sheet that has
none. See [Sheets, files and .apkg](sources.md#download-an-apkg).

**The import changed nothing.**
You added or renamed a column or turned on `reverse`, so the note type changed,
and with the default options Anki skips every note. Import the same file again
with **Merge note types** on and **Update notes** set to **Always**. Sheet to
Anki says so just before the download too.

**Words I deleted from the sheet are still in Anki.**
Importing an `.apkg` adds and updates; it never deletes. Delete them in Anki:
**Browse**, find the word, **Delete**. The add-on on a computer syncs deletions.

**I saved a `.csv` on Android, tapped it, and AnkiDroid imported strange notes.**
AnkiDroid accepts CSV files too and turns every row into a note, the settings
row included. Delete those notes in AnkiDroid, and next time open the `.csv` with
**Open a file to add words** in Create sheet. On a phone, **Save sheet link** is
easier than a file.

**My draft in Create sheet disappeared.**
The draft lives only in the browser, and Safari on an iPhone deletes a site's
data after 7 days without a visit. Save the sheet with **Save sheet link** (on a
phone) or **Save .csv** (on a computer); adding the page to the Home Screen
(**Share → Add to Home Screen**) makes it one tap away.

## Anything else

Turn on **Write a debug log** in **Settings…** (`Ctrl+Shift+O`), do whatever went
wrong again, and look at `debug_sheetcards.log` (the **Open folder** button takes
you there). Please report problems at
[github.com/tannc28/sheetcards/issues](https://github.com/tannc28/sheetcards/issues),
and read the log before attaching it: it contains your sheet's content.
