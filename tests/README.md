# Sheets2Anki — Test Suite

The pytest suite for the add-on. **Anki is auto-mocked**, so the tests run without an
Anki install: `tests/conftest.py` installs an import hook that fabricates subclassable
`aqt`/`anki` modules and registers `src` as a package, so the real `src` modules import
and run unchanged.

## Running the tests

Use the canonical runner — it sets the two flags pytest needs (see the note below):

```bash
python tests/run_tests.py                  # all tests
python tests/run_tests.py --unit           # only @pytest.mark.unit
python tests/run_tests.py --fast           # skip @pytest.mark.slow
python tests/run_tests.py --coverage       # coverage report → htmlcov/
python tests/run_tests.py --info           # list available tests
python tests/run_tests.py --file core_logic
python tests/run_tests.py --file core_logic --function test_duplicate_ids_detected
```

Supported runner flags: `--unit`, `--integration`, `--fast`, `--coverage`, `--verbose`,
`--file <name>`, `--function <name>`. (`--info`, which just lists the available tests,
must be passed on its own — it is not combinable with the other flags.)

### Running pytest directly

If you invoke pytest yourself, **both** of these flags are required:

```bash
python -m pytest --rootdir=tests --import-mode=importlib tests/
python -m pytest --rootdir=tests --import-mode=importlib tests/test_core_logic.py::TestUrls
```

> **Why:** pytest configuration lives only in `pyproject.toml`
> `[tool.pytest.ini_options]` (there is no `pytest.ini`). Without `--rootdir=tests`,
> pytest builds a `Package` node for the repo-root `__init__.py` — the Anki entry point,
> which does `from .src…` — and fails to import it. `tests/run_tests.py` passes both
> flags automatically.

Coverage is **opt-in** via `--coverage` (it is not always-on).

## Test modules

| File | Covers |
| :--- | :--- |
| `test_core_logic.py` | URL conversion, note keying, duplicate-ID detection, core helpers |
| `test_data_processor.py` | TSV parsing, validation, Cloze detection, `RemoteDeck` |
| `test_config_manager.py` | Settings CRUD and persistence |
| `test_student_manager.py` | Multi-student filtering and subdecks |
| `test_utils.py` | URL / hash / validation utilities |
| `test_url_simplification.py` | Edit-URL → TSV export-URL conversion |
| `test_deck_configurations.py` | Deck-option handling |
| `test_search_fix.py` | Note-search edge cases |
| `test_sanity_check_isolation.py` | Assertions on evaluated templates / imported prompt dicts |
| `conftest.py` | Anki mock-finder, `src` package registration, shared fixtures |
| `run_tests.py` | The test runner (adds the required flags) |

### Markers

`@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`,
`@pytest.mark.requires_anki` (declared in `pyproject.toml`; `--strict-markers` is on, so
unknown markers fail).

## Fixtures (`conftest.py`)

| Fixture | Provides |
| :--- | :--- |
| `sample_tsv_content` | A TSV string with the English headers (`ID`, `QUESTION`, `ANSWER`, …) |
| `sample_tsv_data` | The same data parsed into a list of row dicts |
| `sample_students` | A list of student names for multi-student tests |
| `sample_edit_url` | An example Google Sheets **edit** URL |
| `temp_config_file` | A temporary config path under pytest's `tmp_path` |
| `mock_mw` | A mock of Anki's main window (`mw`) |

> The schema is **English** (`ID`, `QUESTION`, `ANSWER`, `STUDENTS`, `SYNC`, …) — the old
> Portuguese headers (`PERGUNTA`, `ALUNOS`) are no longer used.

## Writing tests

Import from `src` (registered as a package by `conftest.py`) and follow
Arrange-Act-Assert:

```python
import pytest

from src.utils import convert_edit_url_to_tsv


@pytest.mark.unit
class TestUrlConversion:
    def test_edit_url_becomes_tsv_export(self, sample_edit_url):
        result = convert_edit_url_to_tsv(sample_edit_url)
        assert "export?format=tsv" in result
```

Guidelines: test behavior rather than implementation, cover edge cases (empty / `None` /
malformed input), keep fixtures for shared data, and don't test the vendored `libs/`.

## Coverage

```bash
python tests/run_tests.py --coverage
open htmlcov/index.html          # or: xdg-open / start
```

Coverage is configured in `pyproject.toml` (`[tool.coverage.*]`): source is `src`,
`libs/` and `tests/` are omitted, branch coverage is on.

## Debugging tests

```bash
python -m pytest --rootdir=tests --import-mode=importlib tests/ -x      # stop on first failure
python -m pytest --rootdir=tests --import-mode=importlib tests/ -l      # show locals on failure
python -m pytest --rootdir=tests --import-mode=importlib tests/ -s      # don't capture stdout
python -m pytest --rootdir=tests --import-mode=importlib tests/ --pdb   # drop into the debugger
```

If imports fail with a collection error on the repo-root `__init__.py`, you almost
certainly dropped the `--rootdir=tests` flag — use `python tests/run_tests.py` instead.

## CI

The suite runs in GitHub Actions on every push to `main` and on pull requests
(`.github/workflows/ci.yml`), via `python tests/run_tests.py`. `ruff` and `black` run as
**blocking** lint gates in the same workflow; `mypy` is advisory.
