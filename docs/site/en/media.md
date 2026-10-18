# Pictures, sound and video

A cell can hold a link to a picture, a sound or a video. Mark the column `image`,
`audio` or `video` in the [settings row](settings-row.md), and the card shows the
thing the link points to instead of the address.

| Its cell in the settings row | What the card shows |
| :--- | :--- |
| `image; size=320` | The picture, at most 320 px wide |
| `audio` | Anki's play button: plays when the card shows, replay with R |
| `video; size=480` | The site's own video player, at most 480 px wide |

The cells in your data rows hold **only the link**, nothing else. A column holds
one kind of media; `image; video` keeps `image` and warns.

## Reviewing offline

Pictures and sounds are **downloaded and put inside the deck**, so a card still
shows its picture and plays its sound without a connection. This happens when you
press Download .apkg in the Make flashcards page (the .apkg carries the media files), and
when the add-on syncs (the files go into Anki's media folder). The sheet keeps its
links; only the notes in Anki point at the files.

- **Wikimedia Commons** (`commons.wikimedia.org/wiki/File:…`,
  `…/Special:FilePath/…`, `upload.wikimedia.org/…`) always works. Pictures come
  500 px wide (about 40 KB each); `.ogg`, `.wav`, `.flac` and `.opus` recordings
  come as Commons' own MP3 (about 20 KB a word), because AnkiMobile on an iPhone
  cannot play Ogg.
- **Other sites** work when they let a browser download the file (CORS). When one
  does not, the cell stays a link: the card still shows it online, and Sheet to
  Anki says how many after the download. The add-on downloads exactly what a
  browser could, so the notes from an .apkg and the notes from a sync are always
  the same.
- **Limits:** 20 MB a file and 100 MB a deck; anything past that stays a link.
- **Video is not downloaded.** A `video` column is that site's own player, so it
  still needs the internet.
- Downloading the .apkg again does not fetch the media again: the browser
  remembers what it fetched, and Anki does not duplicate files when you import
  over a deck.

## Video: paste the link from the address bar

Write `video` and paste whatever your browser shows. When the card is made (as the
add-on syncs, or in the Make flashcards page), it is turned into the address of that site's
player:

| You paste | It becomes |
| :--- | :--- |
| `youtube.com/watch?v=ID`, `youtu.be/ID`, `youtube.com/shorts/ID`, `youtube.com/live/ID` | `youtube.com/embed/ID` |
| `youtu.be/ID?t=1m30s` | `youtube.com/embed/ID?start=90` (the start time is kept) |
| `drive.google.com/file/d/ID/view?usp=sharing`, `drive.google.com/open?id=ID` | `drive.google.com/file/d/ID/preview` |
| `vimeo.com/123456789` | `player.vimeo.com/video/123456789` |
| `example.com/lesson.mp4` | unchanged; a direct file plays too |

A link that names no single video (a channel, a playlist, a Drive folder) is left
alone and reported as a warning, because it would show an error where the video
should be.

On AnkiDroid and AnkiMobile, YouTube refuses to play inside a card loaded from
the phone itself. So a video card goes through a small player page on this site,
which plays it inline on a phone, and also shows a plain link under the frame in
case that page is ever unreachable. The link's text is the column's `label` if it
has one.

## Things to know

- **The links that are left need the internet.** Video, and any picture or sound
  that could not be downloaded (see above), is fetched each time the card is
  shown, so it is blank offline.
- **A picture pasted into a cell is not a link.** Google Sheets stores it as a
  drawing, which Anki cannot reach. Upload the picture somewhere with a link
  (Google Drive, Wikimedia Commons, a GitHub repository) and put that link in the
  cell.
- **Text settings do not apply to media.** `color`, `bold`, `italic` and the
  column's own `align` are ignored on a media column, with a warning. `size` sets
  the width (1–2000), and a video keeps a 16 : 9 shape. `size` on `audio` is
  refused.
- **`tts` and `furigana` are refused** on a media column, because they would act
  on the address: the card would read the link aloud.
- **`hint`** puts the picture or player behind a click.
- **Forgot `image`?** A column whose cells mostly look like picture links gives
  the warning *looks like picture links — add `image`*, because without it the
  card prints the link itself.
