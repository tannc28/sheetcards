# Contributing to Sheets2Anki

Thanks for your interest in improving Sheets2Anki. This guide covers the development
setup and where to find deeper documentation.

## Project layout

This repository *is* the Anki add-on directory — Anki loads `__init__.py` from the
root. There is no server and no `main()`; all code runs inside Anki's Python/Qt6 process.

- `__init__.py` — Anki integration entry point (menu, shortcuts, hooks).
- `src/` — all add-on logic (sync, data processing, dialogs, config, AI, …).
- `libs/` — **vendored** third-party dependencies. Never edit or lint these.
- `tests/` — the pytest suite (Anki is mocked, so no Anki install is needed).
- `scripts/` — build/packaging tooling for `.ankiaddon` files.
- `docs/` — changelog and the long-form developer guide.

## Documentation map

| Document | Audience |
| :--- | :--- |
| [`README.md`](README.md) | End users — install and usage. |
| [`CLAUDE.md`](CLAUDE.md) | Architecture & conventions reference (concise; also used by AI tooling). |
| [`docs/README.md`](docs/README.md) | Long-form developer guide. |
| [`docs/CHANGELOG.md`](docs/CHANGELOG.md) | Release history. |
| [`scripts/README.md`](scripts/README.md) | Build & packaging. |

## Development setup

Tooling is managed with [uv](https://docs.astral.sh/uv/) (Python 3.13 is pinned in
`.python-version`):

```bash
uv sync --extra dev          # or: pip install -e ".[dev]"
```

## Running the tests

Anki is auto-mocked by `tests/conftest.py`, so the suite runs without an Anki install.
Use the canonical runner — it sets the flags pytest needs:

```bash
python tests/run_tests.py                 # all tests
python tests/run_tests.py --unit          # only @pytest.mark.unit
python tests/run_tests.py --coverage      # coverage report → htmlcov/
```

> Tests **must** run with `--rootdir=tests --import-mode=importlib` (the runner adds
> these automatically). Otherwise pytest treats the repo-root `__init__.py` as a package
> and fails to import it.

## Linting, formatting & types

```bash
ruff check src/ tests/
black src/ tests/            # line length 88
mypy src/
```

Optionally enable the git hooks:

```bash
pip install pre-commit
pre-commit install
```

> CI enforces `ruff` and `black` as **blocking** gates (`mypy` runs as advisory). Run
> them before pushing, or install the pre-commit hooks above. The ruff config ignores a
> few intentional conventions (camelCase Anki-API names, the dual-import pattern) and
> defers some stylistic rules — see `[tool.ruff.lint]` in `pyproject.toml`.

## Building distributable packages

```bash
python scripts/build_packages.py   # interactive: AnkiWeb and/or standalone .ankiaddon
```

See [`scripts/README.md`](scripts/README.md) for details. `IS_DEVELOPMENT_MODE` is left
`True` in the repo; the build scripts flip it to `False` in the packaged copy.

## Pull requests

- Keep changes focused; describe the user-facing impact.
- Run the test suite before opening a PR.
- For card-template (JS/CSS) changes, verify the rendered template strings — see the
  card-JS note in [`CLAUDE.md`](CLAUDE.md).
