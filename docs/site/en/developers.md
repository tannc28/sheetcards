# For developers

SheetCards is an Anki add-on with no server. The repository root is the add-on
folder: Anki loads `__init__.py`, which builds the menu, and everything else is in
`src/`. The add-on has no third-party runtime dependencies. The source is at
[github.com/tannc28/sheetcards](https://github.com/tannc28/sheetcards), under the
MIT licence.

[`CLAUDE.md`](https://github.com/tannc28/sheetcards/blob/main/CLAUDE.md) is the
architecture reference, and
[`CONTRIBUTING.md`](https://github.com/tannc28/sheetcards/blob/main/CONTRIBUTING.md)
covers the workflow.

## Set up

Tooling is managed with [uv](https://docs.astral.sh/uv/), Python 3.13:

```bash
uv sync --extra dev          # or: pip install -e ".[dev]"
```

## Test

Anki is mocked by `tests/conftest.py`, so the suite needs no Anki install. Use
the runner, which passes the flags pytest needs (`--rootdir=tests
--import-mode=importlib`):

```bash
python tests/run_tests.py                  # everything
python tests/run_tests.py --fast           # skip slow tests
python tests/run_tests.py --file core_logic
python tests/run_tests.py --coverage       # report in htmlcov/
```

Lint and format:

```bash
ruff check src/ tests/
black src/ tests/
mypy src/
```

## The website

This site is static and lives in `site/`: the landing page (`index.html`),
Sheet to Anki (`create.html`), Create sheet (`sheet.html`) and Contact &
feedback (`contact.html`), with the documentation as Markdown in
`docs/site/` (Vietnamese, served at `/docs/`) and `docs/site/en/` (English, at
`/docs/en/`). `scripts/build_site.py` assembles it into `build/site/`: it copies
`site/`, copies the add-on's pure Python modules (the ones with no Anki import)
for Sheet to Anki to run through Pyodide, renders the landing page's demo cards with
those same modules, and converts the Markdown into these pages.

```bash
python scripts/build_site.py            # build into build/site
python scripts/build_site.py --serve    # build, then serve on :8000
```

A push to `main` that touches the site, `src/`, the docs or the example workbook
redeploys it to GitHub Pages.

## Build and release

```bash
python scripts/build_packages.py           # interactive menu: AnkiWeb, standalone or both
python scripts/validate_packages.py build/sheetcards.ankiaddon
```

The version lives in both `manifest.json` and `pyproject.toml` and the two must
agree. Merging to `main` with both bumped, and a matching section in
`docs/CHANGELOG.md`, makes the release workflow tag, build and publish the
`.ankiaddon` files. The download link on this site always points at the newest
release.

While `IS_DEVELOPMENT_MODE` is `True` in `src/templates_and_definitions.py`, the
menu has an extra **Import Test Deck** item (`Ctrl+Shift+T`) that connects the
[example workbook](examples.md). The build scripts switch it off in the packaged
add-on.
