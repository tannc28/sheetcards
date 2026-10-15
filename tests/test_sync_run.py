"""How a sync run moves from deck to deck, and what it leaves behind.

The download runs in a ``QueryOp`` on a background thread and the write in its
success callback on the main thread. Here ``QueryOp`` is replaced by one that
calls straight through, so the run's own decisions can be checked without Qt:
Cancel stops between decks, a clean run ends in a tooltip and the AnkiWeb
hand-off, and only a run with something to read opens the summary.
"""

import ast
import inspect
import re

import pytest

from src import sync
from src.errors import RemoteDeckError

EMOJI = re.compile("[\U0001f000-\U0001ffff☀-➿⬀-⯿✅✔]")


class FakeProgress:
    def __init__(self):
        self.on_cancel = None
        self.titles = []
        self.closed = False
        self.cancel_enabled = True

    def setTitle(self, text):
        self.titles.append(text)

    def setCancelEnabled(self, enabled):
        self.cancel_enabled = enabled

    def setValue(self, value):
        pass

    def maximum(self):
        return 9

    def setLabelText(self, text):
        self.text = text

    def appendMessage(self, text):
        pass

    def close_when_done(self):
        self.closed = True


class SyncQueryOp:
    """QueryOp, minus the thread."""

    after_fetch = None

    def __init__(self, *, parent, op, success):
        self.op, self.success, self.fail = op, success, None

    def failure(self, fail):
        self.fail = fail
        return self

    def without_collection(self):
        return self

    def run_in_background(self):
        try:
            result = self.op(None)
        except Exception as e:
            self.fail(e)
            return
        if SyncQueryOp.after_fetch:
            SyncQueryOp.after_fetch()
        self.success(result)


@pytest.fixture
def run_env(monkeypatch):
    calls = {"fetched": [], "written": [], "tooltip": [], "summary": [], "ankiweb": 0}

    def fetch(url):
        calls["fetched"].append(url)
        if "broken" in url:
            raise RemoteDeckError("There's no sheet at this address.")
        return object()

    def write(remote_decks, key, progress, msgs, step, debug_messages=None, **kw):
        calls["written"].append(key)
        stats = sync.SyncStats(created=2, updated=1)
        if key == "warns":
            stats.warnings.append("Settings row — size=900 is out of range")
        return step, 1, stats

    def ankiweb(*_):
        calls["ankiweb"] += 1

    def summary(*args, on_close_callback=None, **kwargs):
        calls["summary"].append(args)
        if on_close_callback:
            on_close_callback()

    monkeypatch.setattr(sync, "QueryOp", SyncQueryOp)
    monkeypatch.setattr(sync, "_fetch_deck", fetch)
    monkeypatch.setattr(sync, "_sync_single_deck", write)
    monkeypatch.setattr(sync, "_finalize_sync_cleanup", lambda progress: 0)
    monkeypatch.setattr(sync, "tooltip", lambda msg, **k: calls["tooltip"].append(msg))
    monkeypatch.setattr(sync, "_show_sync_summary_new", summary)
    monkeypatch.setattr(sync, "_hand_off_to_ankiweb", ankiweb)
    monkeypatch.setattr(
        sync, "_resolve_deck_name_for_error", lambda key, decks: f"deck {key}"
    )
    import src.config_manager as config_manager

    monkeypatch.setattr(
        config_manager, "update_deck_sync_status", lambda url, success: False
    )
    SyncQueryOp.after_fetch = None
    yield calls
    SyncQueryOp.after_fetch = None
    sync._ACTIVE_RUN = None


def make_run(keys):
    decks = {
        k: {"remote_deck_url": f"https://x/{k}", "local_deck_name": k} for k in keys
    }
    progress = FakeProgress()
    run = sync._SyncRun(
        deck_keys=keys,
        remote_decks=decks,
        progress=progress,
        status_msgs=[],
        sync_errors=[],
    )
    sync._ACTIVE_RUN = run
    return run, progress


@pytest.mark.unit
class TestTheRun:
    def test_a_clean_run_ends_in_a_tooltip_then_ankiweb(self, run_env):
        run, progress = make_run(["a", "b"])
        run.start()
        assert run_env["written"] == ["a", "b"]
        assert run_env["summary"] == []
        assert run_env["tooltip"] == ["2 decks synced · 4 new · 2 changed"]
        assert run_env["ankiweb"] == 1
        assert progress.closed
        assert sync._ACTIVE_RUN is None

    def test_a_failure_opens_the_summary_and_ankiweb_follows_it(self, run_env):
        run, _ = make_run(["a", "broken"])
        run.start()
        assert run_env["tooltip"] == []
        assert len(run_env["summary"]) == 1
        sync_errors, total_stats = run_env["summary"][0][:2]
        assert total_stats.error_details == [
            "deck broken: There's no sheet at this address."
        ]
        assert total_stats.errors == 1 and sync_errors == []
        assert run_env["ankiweb"] == 1

    def test_a_warning_alone_is_worth_the_summary(self, run_env):
        run, _ = make_run(["warns"])
        run.start()
        assert len(run_env["summary"]) == 1
        assert run_env["tooltip"] == []

    def test_cancel_stops_between_decks(self, run_env):
        run, progress = make_run(["a", "b", "c"])
        SyncQueryOp.after_fetch = lambda: progress.on_cancel()
        run.start()
        # The deck already downloaded is still written; nothing after it starts.
        assert run_env["fetched"] == ["https://x/a"]
        assert run_env["written"] == ["a"]
        assert run_env["tooltip"] == [
            "Sync stopped · 1 of 3 decks synced · 2 new · 1 changed"
        ]
        assert run_env["ankiweb"] == 0
        assert progress.closed

    def test_cancel_after_the_end_is_harmless(self, run_env):
        run, progress = make_run(["a"])
        run.start()
        progress.on_cancel()
        assert not run.cancelled


@pytest.mark.unit
class TestCleanRunMessage:
    def test_no_changes(self):
        assert (
            sync.clean_run_message(1, 1, sync.SyncStats())
            == "1 deck synced · no changes"
        )

    def test_zeros_are_left_out(self):
        stats = sync.SyncStats(created=0, updated=3, deleted=1)
        assert (
            sync.clean_run_message(2, 2, stats)
            == "2 decks synced · 3 changed · 1 removed"
        )


@pytest.mark.unit
class TestOffTheMainThread:
    def test_the_background_step_never_touches_the_collection(self):
        func = ast.parse(inspect.getsource(sync._fetch_deck)).body[0]
        func.body = func.body[1:]  # the docstring
        names = {
            getattr(n, "id", None) or getattr(n, "attr", None) for n in ast.walk(func)
        }
        assert not names & {"mw", "col"}

    def test_the_write_step_does_not_download(self):
        source = inspect.getsource(sync._sync_single_deck)
        assert "validate_url" not in source
        assert "getRemoteDeck(" not in source


@pytest.mark.unit
def test_every_colour_the_summary_asks_for_exists():
    """The summary's stylesheet indexes ``get_colors()`` directly, so a name the
    palette adapter does not have is a KeyError the moment the window opens —
    which is how it shipped, asking for ``accent_error`` and ``header_bg``."""
    from src import theme

    used = set(re.findall(r"colors\[['\"](\w+)['\"]\]", inspect.getsource(sync)))
    assert used - set(theme._TOKENS) == set()


def _user_visible_strings(module):
    """Every string literal not handed to the debug log."""
    tree = ast.parse(inspect.getsource(module))
    logged = set()
    for node in ast.walk(tree):
        # A docstring is read by whoever edits the file, not by the user.
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            logged.add(id(node.value))
        if isinstance(node, ast.Call):
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name in ("add_debug_message", "add_debug_msg", "debug"):
                for sub in ast.walk(node):
                    logged.add(id(sub))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in logged
        ):
            yield node.lineno, node.value


@pytest.mark.unit
@pytest.mark.parametrize("module_name", ["sync", "sync_report", "ui.add_deck_dialog"])
def test_no_emoji_reaches_the_reader(module_name):
    import importlib

    module = importlib.import_module(f"src.{module_name}")
    found = [
        (line, text)
        for line, text in _user_visible_strings(module)
        if EMOJI.search(text)
    ]
    assert not found, f"emoji in user-visible strings of {module_name}: {found}"
