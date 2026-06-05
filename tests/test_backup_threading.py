"""Regression tests: backup/restore must run on the main (caller) thread.

Anki's collection (``mw.col``) is not thread-safe, so
``BackupDialog._run_with_progress`` must execute its operation synchronously on the
calling thread. It previously spawned a daemon thread, which risked DB corruption
during backup/restore. Anki/Qt are mocked by ``conftest.py``.
"""

import threading

import pytest


@pytest.mark.unit
def test_run_with_progress_executes_synchronously_on_caller_thread():
    from src.ui.backup_dialog import BackupDialog

    dialog = BackupDialog()
    caller_thread = threading.current_thread()
    captured = {}

    def operation():
        captured["thread"] = threading.current_thread()
        return "RESULT"

    result, timed_out, error = dialog._run_with_progress(operation, "Title", "Message")

    assert result == "RESULT"
    assert error is None
    assert timed_out is False
    # The operation must run on THIS thread, not a spawned worker (the old bug).
    assert captured["thread"] is caller_thread


@pytest.mark.unit
def test_run_with_progress_reports_errors_without_raising():
    from src.ui.backup_dialog import BackupDialog

    dialog = BackupDialog()

    def boom():
        raise RuntimeError("kaboom")

    result, timed_out, error = dialog._run_with_progress(boom, "Title", "Message")

    assert result is False
    assert timed_out is False
    assert "kaboom" in error
