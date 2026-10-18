# Text to speech

`tts=` on a column makes Anki read it aloud with the voices on your device:

```text
ID       Word                 Meaning
#config  tts=en_US            size=20
1        library              thư viện
```

The word is spoken when the side it is on appears, and there is a button to hear
it again.

## The language code must be complete

Write the full code: **`en_US`, `zh_CN`, `ja_JP`, `ko_KR`, `de_DE`, `pt_BR`**.
`zh-CN` is accepted too. A short code like `zh` is **refused with a warning**:
Anki matches the code against your installed voices exactly, so `zh` would match
nothing and play silence. Guessing is not safe either: `zh_CN` would be wrong for
someone learning Traditional Chinese (`zh_TW`).

## Choosing a voice and speed

- **`voices=`** names the voices you would like, separated by commas:
  `tts=zh_CN; voices=Huihui,Yaoyao`. It is a preference: if none of them exist on
  a device, Anki uses any voice for that language. So the same sheet works on your
  computer and your phone.
- **`speed=`** sets the column's speaking rate, from 0.5 to 2.0. Write it in each
  spoken column's own cell; in the `#config` cell it no longer does anything and
  gives a warning.
- A column with Chinese, Japanese or Korean `tts` gets that language's
  [font](text.md#fonts-for-chinese-japanese-and-korean) by itself, unless you
  write a different `font=`.

## Finding the voices a device has

Which voices exist depends on the device doing the reviewing, and your phone
usually has different ones from your computer. So **every card with a spoken
column carries a small collapsed "TTS voices" section on its answer side**. Open
it on the device you study on to see:

- the voices that device has for your language, the natural-sounding
  *Premium* and *Enhanced* ones first;
- each one written the way to put it in your sheet (`voices=…`), ready to copy;
- if nothing matches, the language codes the device does have, so you can see
  whether your `tts=` code is the problem.

On a phone each voice has a play button so you can hear it first. Joke voices
(Zarvox, Bells, Bubbles and the like) are left out, and character voices shared
by every language (Eddy, Flo, Grandma…) are folded behind a button.

## Installing voices

A language with no voice installed is **silent, with no error**: the sheet is
fine, the device is missing the voice.

- **Windows:** Settings → Time & Language → Speech.
- **macOS:** System Settings → Accessibility → Spoken Content.
- **iPhone and iPad:** Settings → Accessibility → Spoken Content → Voices.
- **Android:** the text-to-speech settings of your phone, under Accessibility or
  Languages.

### Voices an iPhone already has

Apple publishes no list of the voices it ships. On a real iPhone (iOS 26,
AnkiMobile) these were there without downloading anything:

| Language | Write in the sheet |
| :--- | :--- |
| English (US) | `tts=en_US; voices=Apple_Samantha` |
| English (UK) | `tts=en_GB; voices=Apple_Daniel` |
| English (Australia) | `tts=en_AU; voices=Apple_Karen` |
| Chinese | `tts=zh_CN; voices=Apple_Tingting` |
| German | `tts=de_DE; voices=Apple_Anna` |
| Vietnamese | `tts=vi_VN; voices=Apple_Linh` |

That iPhone had **no Japanese or Korean voice at all**: for `ja_JP` and `ko_KR`
a voice usually has to be downloaded in Settings → Accessibility → Spoken
Content → Voices. Since `voices=` is only a preference, naming an iPhone voice
does no harm on Android or a computer: Anki uses another voice of the language
there.

## Things to know

- **One cell, one language.** Anki reads the whole field with one voice, so a
  cell holding a Chinese sentence and its English translation is read entirely in
  Chinese. Give each language its own column, each with its own `tts=`.
- **An empty cell is not spoken.**
- **`hint` hides text, not sound.** A column with both `hint` and `tts` is still
  read when its side appears.
- **`furigana` and `tts` together read the reading.** On a furigana column the
  voice is given the reading in brackets, so `日本語[にほんご]` is spoken once,
  correctly.
- **Heard but not shown:** `side=hide; tts=…` reads a column without printing it;
  see [the settings row](settings-row.md#heard-but-not-shown-sidehide-with-tts).
