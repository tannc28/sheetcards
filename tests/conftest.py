#!/usr/bin/env python3
"""
Shared pytest configuration and fixtures for Sheets2Anki.

Unlike the previous version, these fixtures use the CURRENT (English) spreadsheet
schema and the tests that consume them import and exercise the REAL ``src`` modules.

Anki (``aqt`` / ``anki``) is not installed in CI, so we install a lightweight import
hook that fabricates mock modules on demand. The mocks are *subclassable* — Anki code
does ``class SomeDialog(QDialog): ...`` at import time, which a plain ``MagicMock``
cannot support — so the addon package imports cleanly without a real Anki.
"""

import importlib
import importlib.abc
import importlib.machinery
import os
import sys
import types
from unittest.mock import MagicMock

import pytest

# =============================================================================
# ANKI / QT IMPORT MOCKING (installed at collection time, before any src import)
# =============================================================================

_MOCK_ROOTS = ("aqt", "anki")


class _MockMeta(type):
    """Metaclass so attribute access on a mock *class* (e.g. QDialog.DialogCode)
    yields a mock instead of AttributeError."""

    def __getattr__(cls, name):
        return MagicMock()


class _MockBase(metaclass=_MockMeta):
    """Base for fabricated Anki/Qt classes: instantiable, subclassable, and tolerant
    of arbitrary attribute access on both the class and its instances."""

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        return MagicMock()


class _MockModule(types.ModuleType):
    """A module whose every attribute is a fresh subclassable mock class (cached)."""

    def __getattr__(self, name):
        obj = type(name, (_MockBase,), {})
        setattr(self, name, obj)
        return obj


class _MockFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in _MOCK_ROOTS:
            return importlib.machinery.ModuleSpec(fullname, self)
        return None

    def create_module(self, spec):
        return _MockModule(spec.name)

    def exec_module(self, module):  # nothing to execute for a mock
        pass


if not any(isinstance(f, _MockFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _MockFinder())

# Expose the addon's ``src`` directory as an importable package WITHOUT running its
# heavy __init__.py (which would import every dialog + the sync engine). We register a
# bare package object whose __path__ points at src/, so ``from src.data_processor import x``
# pulls in just that module and its lightweight deps. We deliberately do NOT put the repo
# root on sys.path — the root __init__.py is the Anki entry point (``from .src...``) and
# must never be imported as a top-level module during tests.
_SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if "src" not in sys.modules:
    _src_pkg = types.ModuleType("src")
    _src_pkg.__path__ = [_SRC_DIR]
    _src_pkg.__package__ = "src"
    sys.modules["src"] = _src_pkg

# Also expose submodules under their bare names so legacy ``from data_processor import x``
# imports resolve too.
for _modname in (
    "templates_and_definitions",
    "utils",
    "data_processor",
    "config_manager",
    "student_manager",
):
    try:
        sys.modules.setdefault(_modname, importlib.import_module(f"src.{_modname}"))
    except Exception as _e:  # pragma: no cover - surfaced as a clear skip in tests
        print(f"[conftest] could not import src.{_modname}: {_e}")


# =============================================================================
# TEST DATA FIXTURES (current English schema)
# =============================================================================


@pytest.fixture
def sample_tsv_content():
    """A small, valid TSV document using the live English column names."""
    return (
        "ID\tQUESTION\tANSWER\tSYNC\tSTUDENTS\tTOPIC\tSUBTOPIC\tCONCEPT\tIMPORTANCE\n"
        "Q001\tCapital of France?\tParis\ttrue\tJohn, Mary\tGeography\tEurope\tCapitals\tHigh\n"
        "Q002\tThe capital of {{c1::Brazil}} is {{c2::Brasília}}\tCloze\ttrue\tMary\tGeography\tCloze\tCards\tMedium\n"
    )


@pytest.fixture
def sample_students():
    return ["John", "Mary", "Peter", "Ann", "Charles"]


@pytest.fixture
def sample_tsv_data():
    """Row dicts in the current English schema (legacy fixture, kept for older tests)."""
    return [
        {
            "ID": "Q001",
            "QUESTION": "Capital of France?",
            "ANSWER": "Paris",
            "SYNC": "true",
            "STUDENTS": "John, Mary",
            "TOPIC": "Geography",
        },
        {
            "ID": "Q002",
            "QUESTION": "The {{c1::sun}} is a star",
            "ANSWER": "Cloze",
            "SYNC": "true",
            "STUDENTS": "Mary",
            "TOPIC": "Science",
        },
    ]


@pytest.fixture
def temp_config_file(tmp_path):
    import json

    cfg = tmp_path / "test_config.json"
    cfg.write_text(json.dumps({"config": {}, "students": {}, "decks": {}}, indent=2))
    return str(cfg)


@pytest.fixture
def sample_edit_url():
    return "https://docs.google.com/spreadsheets/d/1N-Va4ZzLUJBsD6wBaOkoeFTE6EnbZdaPBB88FYl2hrs/edit?usp=sharing"


# =============================================================================
# ANKI MOCK FIXTURES (for the few tests that need a fake collection)
# =============================================================================


@pytest.fixture
def mock_mw():
    mw = MagicMock()
    mw.col = MagicMock()
    return mw


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: marks a test as a unit test")
    config.addinivalue_line("markers", "integration: marks a test as an integration test")
    config.addinivalue_line("markers", "slow: marks a test as slow (skipped in quick mode)")
    config.addinivalue_line("markers", "requires_anki: marks a test that requires a real Anki")
