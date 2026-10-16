# Dành cho developer

SheetCards là một add-on cho Anki, không có server. Thư mục gốc của repository
chính là thư mục add-on: Anki nạp `__init__.py`, file này dựng menu, còn mọi thứ
khác nằm trong `src/`. Add-on không có dependency bên thứ ba nào lúc chạy. Mã
nguồn ở [github.com/tannc28/sheetcards](https://github.com/tannc28/sheetcards),
theo giấy phép MIT.

[`CLAUDE.md`](https://github.com/tannc28/sheetcards/blob/main/CLAUDE.md) là tài
liệu tham khảo về kiến trúc, còn
[`CONTRIBUTING.md`](https://github.com/tannc28/sheetcards/blob/main/CONTRIBUTING.md)
nói về quy trình làm việc.

## Cài đặt môi trường

Công cụ được quản lý bằng [uv](https://docs.astral.sh/uv/), Python 3.13:

```bash
uv sync --extra dev          # or: pip install -e ".[dev]"
```

## Test

Anki được mock trong `tests/conftest.py`, nên bộ test không cần cài Anki. Hãy
dùng runner, nó truyền các flag mà pytest cần (`--rootdir=tests
--import-mode=importlib`):

```bash
python tests/run_tests.py                  # everything
python tests/run_tests.py --fast           # skip slow tests
python tests/run_tests.py --file core_logic
python tests/run_tests.py --coverage       # report in htmlcov/
```

Lint và format:

```bash
ruff check src/ tests/
black src/ tests/
mypy src/
```

## Website

Trang web này là trang tĩnh, nằm trong `site/`, còn docs là Markdown trong
`docs/site/` (tiếng Việt, ở `/docs/`) và `docs/site/en/` (tiếng Anh, ở `/docs/en/`). `scripts/build_site.py` gom tất cả vào `build/site/`: nó copy
`site/`, copy các module Python thuần của add-on (những module không import Anki)
để Sheet to Anki chạy qua Pyodide, dùng chính các module đó để render các card demo của
trang chủ, và chuyển Markdown thành các trang này.

```bash
python scripts/build_site.py            # build into build/site
python scripts/build_site.py --serve    # build, then serve on :8000
```

Một lần push lên `main` có đụng tới site, `src/` hay docs sẽ deploy lại lên GitHub
Pages.

## Build và release

```bash
python scripts/build_packages.py           # build .ankiaddon packages
python scripts/validate_packages.py build/sheetcards.ankiaddon
```

Version nằm ở cả `manifest.json` lẫn `pyproject.toml` và hai chỗ phải khớp nhau.
Merge vào `main` khi cả hai đã được tăng version, kèm một mục tương ứng trong
`docs/CHANGELOG.md`, thì workflow release sẽ tag, build và publish các file
`.ankiaddon`. Link tải trên trang này luôn trỏ tới bản release mới nhất.

Khi `IS_DEVELOPMENT_MODE` là `True` trong `src/templates_and_definitions.py`, menu
có thêm mục **Import Test Deck** (`Ctrl+Shift+T`) để kết nối
[example workbook](examples.md). Các script build sẽ tắt nó trong add-on được
đóng gói.
