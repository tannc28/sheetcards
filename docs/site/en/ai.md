# Make a word set with AI

ChatGPT, Gemini and Claude can write a whole word set for you. Pick one of two
kinds of answer: the same set, the same settings (see
[Write a whole set as text](import.md#write-a-whole-set-as-text)):

- **Text**: one block, line 1 `#config name=…`, line 2 the column names with
  their settings in square brackets, then one word per line. Paste it straight
  into [Make flashcards](../../create/), and keep it in a note to add words later.
- **Table**: row 1 the column names, row 2 the `#config` settings row, then one
  word per row. The AI sends a `.csv` file (if it can attach files) to open with
  **Open file**, or a table to paste into **Paste text**. Good when you want the
  set in Google Sheets or Excel.

For a simple set the prompt says the whole format itself. For fancier cards
(writing practice, furigana, cloze, pictures) give the AI the full guide, in
English, which every AI follows best:

```text
%%SITE%%ai.md
```

## Steps

1. **Copy a prompt** below and change the topic, count and set name.
2. **Paste it into ChatGPT, Gemini or Claude** and send it.
3. **Text**: copy the block it answers with, go to
   [Make flashcards](../../create/), press **Paste text** and paste it. **Table**:
   open the `.csv` with **Open .xlsx/.csv file**, or copy the table and paste it
   into **Paste text**.
4. **Check each card**, then press **Download `.apkg`** and open that file in
   AnkiDroid, AnkiMobile or Anki.

Do not import the `.csv` into Anki or AnkiDroid directly: they would turn the
settings row into a junk card. The `.csv` always goes through SheetCards first.

## Prompts to copy

English vocabulary, as **Text**:

```text
Make 30 English words about travel, level B1, meanings in Vietnamese. Answer in one code block. Line 1 exactly: #config name=Travel B1. Line 2: Word [tts=en_US; bold] | IPA [color=muted] | Meaning | Example [italic]. Then one word per line, columns separated by |.
```

The same set, as a **Table**:

```text
Make 30 English words about travel, level B1, meanings in Vietnamese, as a table (or a CSV file if you can attach files). Row 1: Word | IPA | Meaning | Example. Row 2 is the settings row: first cell exactly #config name=Travel B1; tts=en_US; bold, then color=muted, an empty cell, italic. Then one word per row.
```

Chinese, writing practice:

```text
Read the guide at %%SITE%%ai.md, then make me 20 HSK 1 characters as writing-practice cards (draw), with pinyin and meanings in English, and a short example sentence each. Set name: HSK 1 writing.
```

Japanese with furigana:

```text
Read the guide at %%SITE%%ai.md, then make me 25 JLPT N5 words about school, with furigana on the kanji, meanings in English and an example sentence. Set name: JLPT N5 school.
```

Korean basics, as a table:

```text
Read the guide at %%SITE%%ai.md, then make me a CSV file: 20 beginner Korean words about family, with romanization, meanings in English and an example sentence, the word read aloud in ko_KR. Set name: Korean family.
```

IELTS cloze:

```text
Read the guide at %%SITE%%ai.md, then make me a cloze set: 20 IELTS Writing band 6.5 sentences, each with one academic collocation blanked out, plus what the whole sentence means. Set name: IELTS collocations.
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

**Text**: write the new words under the block in your note yourself, or paste
the block to the AI and say *"Add 20 words, keep the old lines, the #config line
and the column names."* **Table**: attach last time's `.csv` and send:

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
  sometimes off. Check each card in the Make flashcards page before Download `.apkg`, and
  fix it in [Create sheet](../../sheet/) if needed.
- **Your words go to the company behind that AI** (OpenAI, Google or
  Anthropic). SheetCards receives nothing: the file is read in your own browser.
- The AI must not invent picture or audio links. If you want pictures, give it
  the links yourself.
- A warning in the Make flashcards page means the AI wrote the settings row wrong. Send the
  warning back to the AI and ask it to fix the file.
