# Pictures, sound and video

A cell can hold a link to a picture, a sound or a video. Mark the column `image`,
`audio` or `video` in the [settings row](settings-row.md), and the card shows the
thing the link points to instead of the address.

| Its cell in the settings row | What the card shows |
| :--- | :--- |
| `image; size=320` | The picture, at most 320 px wide |
| `audio` | A sound player you can replay |
| `video; size=480` | The site's own video player, at most 480 px wide |

The cells in your data rows hold **only the link**, nothing else. A column holds
one kind of media; `image; video` keeps `image` and warns.

## Video: paste the link from the address bar

Write `video` and paste whatever your browser shows. When the card is made (as the
add-on syncs, or in Sheet to Anki), it is turned into the address of that site's
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

- **Links need the internet.** The picture or video is fetched each time the
  card is shown, so it is blank offline, and phone apps are stricter than the
  desktop about loading remote content. For a deck that must work offline, put
  the files in Anki's own media folder and use them the ordinary Anki way.
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
