# Make a word set with AI

ChatGPT, Gemini and Claude can write a whole word set for you. Give the AI the
link to SheetCards' guide and say what you want to learn; it sends back a `.csv`
file that opens straight in SheetCards, with a settings row already in it, so
the cards look right.

The guide for the AI lives here, in English, which every AI follows best:

```text
%%SITE%%ai.md
```

## Steps

1. **Copy a prompt** below and change the parts you want.
2. **Paste it into ChatGPT, Gemini or Claude** and send it.
3. **Get the `.csv` file.** If the AI only prints a block of text, reply:
   *"Send it as a .csv file I can download."*
4. **Open the file in SheetCards**: go to [Sheet to Anki](../../create/), press
   **Open .xlsx/.csv file** and pick the file. To fix a few words first, open it
   in [Create sheet](../../sheet/) with the same **Open .xlsx/.csv file** button.
5. **Check each card**, then press **Download `.apkg`** and open that file in
   AnkiDroid, AnkiMobile or Anki.

Do not import the `.csv` into Anki or AnkiDroid directly: they would turn the
settings row into a junk card. The `.csv` always goes through SheetCards first.

## Prompts to copy

English vocabulary:

```text
Read the guide at %%SITE%%ai.md, then make me a CSV file: 30 English travel words, level B1, Vocabulary cards, meanings in Vietnamese, with an example sentence. Set name: Travel B1.
```

Chinese, writing practice:

```text
Read the guide at %%SITE%%ai.md, then make me a CSV file: 20 HSK 1 characters as writing-practice cards (draw), with pinyin and meanings in English, and a short example sentence each. Set name: HSK 1 writing.
```

Japanese with furigana:

```text
Read the guide at %%SITE%%ai.md, then make me a CSV file: 25 JLPT N5 words about school, with furigana on the kanji, meanings in English and an example sentence. Set name: JLPT N5 school.
```

Korean basics:

```text
Read the guide at %%SITE%%ai.md, then make me a CSV file: 20 beginner Korean words about family, with romanization, meanings in English and an example sentence, the word read aloud in ko_KR. Set name: Korean family.
```

IELTS cloze:

```text
Read the guide at %%SITE%%ai.md, then make me a cloze CSV file: 20 IELTS Writing band 6.5 sentences, each with one academic collocation blanked out, plus what the whole sentence means. Set name: IELTS collocations.
```

Say anything else you want: how many words, the topic, the level, typed answers
(*"Typed answer cards"*), both directions (*"reverse cards"*) or a theme
(*"theme sakura"*). If the language or the topic is missing, the AI asks at most
two short questions.

## If the AI cannot open the link

Some free plans cannot read web pages, and the AI either says so or guesses.
Then:

1. [Download `ai.md`](../../ai.md).
2. Attach it in the chat (the paperclip or + button) and send the prompt, with
   *"Read the guide at …"* replaced by *"Read the attached guide"*.

If you cannot attach files, open it, copy everything and paste it before the
prompt.

## Adding words later

Attach last time's `.csv` and send:

```text
Read the guide at %%SITE%%ai.md. Here is my file. Add 20 words, keep the old rows and the set name.
```

With the same set name (`name=`) and the old rows unchanged, the new `.apkg`
updates the same deck and keeps your review progress; a new set name makes a
new deck.

## With an ID column or without

A set made as Vocabulary cards has **no `ID` column**: the first column (the
word) is each card's key. That is enough for a simple set, but correcting a
word's spelling later makes a new card (its review progress starts over).

If you expect to fix words later, add *"with an ID column"*: the AI adds an `ID`
column with `w01`, `w02`… When adding words it carries the numbering on and
never reuses an ID. See [A sheet with no ID column](columns.md#a-sheet-with-no-id-column).

## Notes

- **The AI can be wrong**: IPA, pinyin, meanings or example sentences are
  sometimes off. Check each card in Sheet to Anki before Download `.apkg`, and
  fix it in [Create sheet](../../sheet/) if needed.
- **Your words go to the company behind that AI** (OpenAI, Google or
  Anthropic). SheetCards receives nothing: the file is read in your own browser.
- The AI must not invent picture or audio links. If you want pictures, give it
  the links yourself.
- A warning in Sheet to Anki means the AI wrote the settings row wrong. Send the
  warning back to the AI and ask it to fix the file.
