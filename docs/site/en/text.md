# Themes and text

How a card looks: its colour scheme, and the colour, typeface and direction of
the words on it, plus the two kinds of cell that are not ordinary text. All of
these are keys in the [settings row](settings-row.md).

## Themes

Without a theme a card has Anki's own colours. A theme colours the whole card.
Name it in the settings row's marker cell:

```text
#config theme=paper
```

In [Create sheet](../../sheet.html) the theme is chosen in the template step, in
the **Theme** row under the card preview: press **Default** (Anki's colours) or a
theme, the card changes at once, and Create sheet writes `theme=` into the
`#config` cell for you. A theme is not a template: any template takes any theme.

| Theme | What it looks like |
| :--- | :--- |
| `paper` | Warm paper and ink; the calmest for long sessions. |
| `contrast` | Black and white with a blue accent (yellow at night), for weak eyes or a phone in sunlight. |
| `matcha` | Soft green tea. |
| `momiji` | Autumn: warm tones with maple leaves drawn behind the text. |
| `yuki` | Winter: cool blue with snowflakes. |
| `sakura` | Spring: cherry-blossom pink with blossoms drawn behind the text. |

- Every theme has a light and a dark version, and follows Anki's night mode.
- A theme sets what `color=muted` and `color=accent` mean, so columns using
  them match the theme.
- The leaves, snowflakes and blossoms are drawn by the card itself; they need no
  internet.
- A theme colours the card, not Anki around it: on a computer the top bar and
  the answer buttons keep Anki's colours. On a phone the card fills the screen.
- An unknown name is refused with a warning, and the card keeps Anki's colours.

## Colour

`color=` takes one of:

- **`muted`** or **`accent`**: a quiet grey and a highlight colour that follow
  Anki's light and dark mode. Prefer these.
- **A CSS colour name** such as `crimson` or `teal`.
- **A `#hex` value** such as `#c2410c`.

A fixed colour stays the same in night mode, so `color=black` disappears on a
dark card. `muted` and `accent` do not have that problem.

## Fonts for Chinese, Japanese and Korean

Many Chinese, Japanese and Korean characters share one code but are drawn
differently in each language: `直` and `骨` look different in a Chinese and a
Japanese font. A device with only a Japanese font draws a Chinese deck in
Japanese shapes. `font=` tells the card which one you mean:

| Value | Font |
| :--- | :--- |
| `sc` | Noto Sans SC, Simplified Chinese |
| `tc` | Noto Sans TC, Traditional Chinese |
| `jp` | Noto Sans JP, Japanese |
| `kr` | Noto Sans KR, Korean |
| `serif`, `sans`, `mono` | The device's own serif, sans-serif or monospace font |
| any other name | That font, if the device has it |

The four Noto fonts are loaded from Google Fonts, so they need a connection the
first time.

## Writing direction

- **`rtl`** writes right to left, for Arabic, Hebrew and Persian. The text is
  right-aligned unless `align` says otherwise.
- **`vertical`** writes top to bottom, columns right to left, the way Japanese is
  set in a book. Latin letters stay upright.

A column takes one direction; if both are written, `rtl` wins.

## Formulas and code

**`math`** says the cell is a formula written in LaTeX. Anki draws it with the
MathJax it already ships, so nothing extra is needed. `math` keeps it in the
line; `math=block` centres it on its own.

```text
ID       Formula               Meaning
#config  math=block
1        E = mc^2              mass-energy equivalence
```

**`code`** says the cell is source code. It is kept exactly as typed, left
aligned, and coloured by language: `code=python`, `code=bash`, `code=html`,
`code=javascript` and so on. The colouring is done by highlight.js, loaded over
the internet; without a connection the code is shown uncoloured.

## Sort order in Anki's browser

`sort` on a column makes Anki's browser list and sort the notes by that column.
Without it they are listed by `ID`, which reads `w01, w02, w03`.
