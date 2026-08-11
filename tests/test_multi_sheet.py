"""One Google Sheets file, one deck per sheet.

A file holds several sheets — the tabs along the bottom — and people keep a deck
per sheet. Until this existed a file could only ever be one deck, because a deck
is identified by its URL and every sheet of a file shares one URL.

What is worth testing here is not that a second deck appears. It is the two ways
this can go quietly wrong on a collection that already exists:

* two decks of one file sharing a configuration entry or a settings-row cache,
  so each sync overwrites what the other just wrote;
* a deck connected before any of this stops being found, so the add-on decides
  it is not connected and builds a duplicate beside it.
"""

import pytest

from src.config_manager import get_deck_id
from src.utils import convert_edit_url_to_tsv
from src.utils import convert_edit_url_to_xlsx
from src.utils import sheet_name_from_url
from src.utils import url_for_sheet

FILE_ID = "1503Ytkf0FFqllo-tjwdIxt9tgjb2aNxt"
EDIT = f"https://docs.google.com/spreadsheets/d/{FILE_ID}/edit"
# What the browser actually gives you, tab number and all.
FROM_BROWSER = f"{EDIT}?gid=27341628#gid=27341628"


@pytest.mark.unit
class TestWhichSheetAUrlNames:
    def test_a_plain_link_names_no_sheet(self):
        assert sheet_name_from_url(EDIT) is None

    def test_a_gid_is_not_a_sheet_name(self):
        """The export carries no gid, so a number copied from the browser cannot
        be resolved to a sheet and must not be mistaken for one."""
        assert sheet_name_from_url(FROM_BROWSER) is None

    def test_the_sheet_survives_the_round_trip(self):
        assert sheet_name_from_url(url_for_sheet(EDIT, "vocab")) == "vocab"

    def test_a_name_with_spaces_and_accents_survives(self):
        for name in ["Ngữ pháp", "unit 1 & 2", "50% done", "a#b", "a/b"]:
            assert sheet_name_from_url(url_for_sheet(EDIT, name)) == name

    def test_pointing_at_a_sheet_replaces_the_gid(self):
        """Two answers to 'which sheet' is one too many."""
        pointed = url_for_sheet(FROM_BROWSER, "grammar")
        assert "gid=27341628#" not in pointed
        assert pointed.endswith("#sheet=grammar")

    def test_repointing_does_not_stack_fragments(self):
        once = url_for_sheet(EDIT, "vocab")
        twice = url_for_sheet(once, "grammar")
        assert twice.count("#") == 1
        assert sheet_name_from_url(twice) == "grammar"

    def test_the_download_url_still_points_at_the_file(self):
        pointed = url_for_sheet(FROM_BROWSER, "grammar")
        assert convert_edit_url_to_xlsx(pointed) == (
            f"https://docs.google.com/spreadsheets/d/{FILE_ID}/export?format=xlsx"
        )
        assert convert_edit_url_to_tsv(pointed) == (
            f"https://docs.google.com/spreadsheets/d/{FILE_ID}/export?format=tsv"
        )


@pytest.mark.unit
class TestDeckIdentity:
    def test_two_sheets_of_one_file_are_two_decks(self):
        """The whole point. Sharing a key means sharing a settings-row cache, and
        then each sync rebuilds the other deck's cards from the wrong config."""
        vocab = get_deck_id(url_for_sheet(EDIT, "vocab"))
        grammar = get_deck_id(url_for_sheet(EDIT, "grammar"))
        assert vocab != grammar
        assert vocab.startswith(FILE_ID) and grammar.startswith(FILE_ID)

    def test_the_same_sheet_is_always_the_same_deck(self):
        assert get_deck_id(url_for_sheet(EDIT, "vocab")) == get_deck_id(
            url_for_sheet(FROM_BROWSER, "vocab")
        )

    def test_a_deck_from_before_keeps_the_key_it_has_always_had(self):
        """If this changes, every already-connected deck looks unconnected and the
        next sync builds a duplicate beside it."""
        assert get_deck_id(EDIT) == FILE_ID
        assert get_deck_id(FROM_BROWSER) == FILE_ID

    def test_the_sheet_name_cannot_be_confused_with_another_file(self):
        other = "https://docs.google.com/spreadsheets/d/OTHERFILEID/edit"
        assert get_deck_id(url_for_sheet(EDIT, "vocab")) != get_deck_id(
            url_for_sheet(other, "vocab")
        )


@pytest.fixture
def stored(monkeypatch):
    """A stand-in for meta.json's deck table, so nothing touches a real one.

    `get_remote_decks` hands back a copy, the way the real one does — it reads
    meta.json afresh every call. Handing back the table itself would let a caller
    mutate storage without saving, which is exactly what a test must not permit.
    """
    from src import config_manager

    table = {}

    def replace(decks):
        table.clear()
        table.update(decks)

    monkeypatch.setattr(config_manager, "get_remote_decks", lambda: dict(table))
    monkeypatch.setattr(config_manager, "save_remote_decks", replace)
    monkeypatch.setattr(
        config_manager, "forget_sheet_settings", lambda key: True, raising=False
    )
    return table


def _legacy_entry(url=EDIT):
    """What a deck connected before any of this looks like on disk."""
    return {
        "remote_deck_url": url,
        "local_deck_id": 1234,
        "local_deck_name": "Sheets2Anki::My words",
        "remote_deck_name": "My words",
        "note_types": {"55": "Sheets2Anki - My words - Basic"},
        "sync_count": 9,
    }


@pytest.mark.unit
class TestAdoptingAnOlderDeck:
    """Upgrading a deck that was connected before a file could hold several.

    This runs against someone's real collection, on a deck that already has notes
    and review history in it, so the failure that matters is not an exception — it
    is the deck quietly ending up pointed at rows that were never its own.
    """

    def test_the_old_deck_is_moved_rather_than_copied(self, stored):
        from src.config_manager import adopt_sheet_into_legacy_deck

        stored[FILE_ID] = _legacy_entry()
        assert adopt_sheet_into_legacy_deck(EDIT, "vocab") is True

        assert (
            FILE_ID not in stored
        ), "the old key still resolves — two decks, one sheet"
        assert list(stored) == [f"{FILE_ID}#vocab"]

    def test_it_keeps_the_deck_it_was_attached_to(self, stored):
        """Anything lost here is a user's notes and review history."""
        from src.config_manager import adopt_sheet_into_legacy_deck

        stored[FILE_ID] = _legacy_entry()
        adopt_sheet_into_legacy_deck(EDIT, "vocab")

        moved = stored[f"{FILE_ID}#vocab"]
        assert moved["local_deck_id"] == 1234
        assert moved["local_deck_name"] == "Sheets2Anki::My words"
        assert moved["note_types"] == {"55": "Sheets2Anki - My words - Basic"}
        assert moved["sync_count"] == 9

    def test_the_stored_url_now_names_the_sheet(self, stored):
        """Otherwise the next sync recomputes the old key and loses the deck."""
        from src.config_manager import adopt_sheet_into_legacy_deck

        stored[FILE_ID] = _legacy_entry()
        adopt_sheet_into_legacy_deck(EDIT, "vocab")

        moved = stored[f"{FILE_ID}#vocab"]
        assert sheet_name_from_url(moved["remote_deck_url"]) == "vocab"
        assert get_deck_id(moved["remote_deck_url"]) == f"{FILE_ID}#vocab"

    def test_a_deck_that_already_names_its_sheet_is_left_alone(self, stored):
        from src.config_manager import adopt_sheet_into_legacy_deck

        key = f"{FILE_ID}#vocab"
        stored[key] = _legacy_entry(url_for_sheet(EDIT, "vocab"))
        assert adopt_sheet_into_legacy_deck(EDIT, "vocab") is False
        assert list(stored) == [key]

    def test_a_file_that_was_never_connected_is_not_invented(self, stored):
        from src.config_manager import adopt_sheet_into_legacy_deck

        assert adopt_sheet_into_legacy_deck(EDIT, "vocab") is False
        assert stored == {}

    def test_it_refuses_without_a_sheet_to_adopt(self, stored):
        from src.config_manager import adopt_sheet_into_legacy_deck

        stored[FILE_ID] = _legacy_entry()
        assert adopt_sheet_into_legacy_deck(EDIT, "") is False
        assert list(stored) == [FILE_ID]

    def test_another_file_is_not_disturbed(self, stored):
        from src.config_manager import adopt_sheet_into_legacy_deck

        stored[FILE_ID] = _legacy_entry()
        stored["OTHERFILEID"] = _legacy_entry(
            "https://docs.google.com/spreadsheets/d/OTHERFILEID/edit"
        )
        adopt_sheet_into_legacy_deck(EDIT, "vocab")

        assert "OTHERFILEID" in stored
        assert sorted(stored) == sorted(["OTHERFILEID", f"{FILE_ID}#vocab"])


@pytest.mark.unit
class TestSelectingWhichDecksSync:
    """Turning the URLs a dialog hands back into the keys decks are stored under.

    This shipped broken once in development: the lookup used the bare spreadsheet
    id, so a per-sheet deck resolved to a key that is not in the table and the
    sync quietly did nothing — no error, no notes, just a run that reported
    success over an empty list.
    """

    def _keys(self, table, urls):
        from src.sync import _get_deck_keys_to_sync

        return _get_deck_keys_to_sync(table, None, urls)

    def test_a_sheet_url_finds_its_own_deck(self):
        table = {f"{FILE_ID}#vocab": {}, f"{FILE_ID}#grammar": {}}
        assert self._keys(table, [url_for_sheet(EDIT, "grammar")]) == [
            f"{FILE_ID}#grammar"
        ]

    def test_each_sheet_of_one_file_resolves_separately(self):
        table = {f"{FILE_ID}#vocab": {}, f"{FILE_ID}#grammar": {}}
        urls = [url_for_sheet(EDIT, "vocab"), url_for_sheet(EDIT, "grammar")]
        assert sorted(self._keys(table, urls)) == sorted(table)

    def test_a_deck_from_before_still_resolves(self):
        table = {FILE_ID: {}}
        assert self._keys(table, [EDIT]) == [FILE_ID]

    def test_a_sheet_that_is_not_connected_selects_nothing(self):
        table = {f"{FILE_ID}#vocab": {}}
        assert self._keys(table, [url_for_sheet(EDIT, "grammar")]) == []


@pytest.mark.unit
class TestDeckNaming:
    """What a deck ends up called, which the automatic name sync recomputes.

    It recomputes it on *every* run, so a name that leaves the sheet out does not
    just look wrong once — it renames every deck of a file onto the same name and
    then shoves them apart with "#conflict1", every sync, for ever.
    """

    def test_a_deck_is_named_after_its_file_and_its_sheet(self):
        from src.deck_manager import DeckNameManager

        assert (
            DeckNameManager._with_sheet(url_for_sheet(EDIT, "vocab"), "English")
            == "English::vocab"
        )

    def test_two_sheets_do_not_land_on_the_same_name(self):
        from src.deck_manager import DeckNameManager

        vocab = DeckNameManager._with_sheet(url_for_sheet(EDIT, "vocab"), "English")
        grammar = DeckNameManager._with_sheet(url_for_sheet(EDIT, "grammar"), "English")
        assert vocab != grammar

    def test_a_deck_with_no_sheet_keeps_the_plain_file_name(self):
        from src.deck_manager import DeckNameManager

        assert DeckNameManager._with_sheet(EDIT, "English") == "English"

    def test_an_uploaded_file_does_not_bring_its_extension_into_anki(self):
        """A Google Sheets document has no extension; one is left over from the
        file it was uploaded from, and reads as a mistake in the deck list."""
        from src.deck_manager import _without_file_extension

        assert _without_file_extension("my-vocab-sheet.xlsx") == "my-vocab-sheet"
        assert _without_file_extension("notes.csv") == "notes"
        assert _without_file_extension("HSK 4") == "HSK 4"
        assert _without_file_extension("v1.2 words") == "v1.2 words"


@pytest.mark.unit
class TestClozeNoteTypeProvisioning:
    """A Cloze note type is only made when a column asks for one.

    Anki refuses a cloze note type whose template holds no `{{cloze:…}}` — and a
    sheet that never mentions cloze produces exactly that, so provisioning one
    unconditionally failed the entire sync of a sheet with nothing to do with
    cloze. Verified against a real collection: "Expected to find '{{cloze:Text}}'
    or similar on the front and back of the card template."
    """

    def _config(self, tsv):
        from src.tsv_model import build_remote_deck_from_tsv
        from src.tsv_model import parse_tsv_data

        return build_remote_deck_from_tsv(parse_tsv_data(tsv), "u").sheet_config

    def test_a_sheet_with_no_cloze_column_declares_none(self):
        config = self._config("ID\tWord\tMeaning\n1\tx\ty\n")
        assert config.cloze_field is None

    def test_a_sheet_that_declares_cloze_names_the_column(self):
        config = self._config(
            "ID\tWord\tSentence\n#config\t\tcloze\n1\tx\ta {{c1::b}} c\n"
        )
        assert config.cloze_field == "Sentence"

    def test_cloze_markup_alone_does_not_declare_a_column(self):
        """Markup in a cell is a warning, not a declaration — wrapping a column
        that holds no deletion would blank it."""
        config = self._config("ID\tWord\tSentence\n1\tx\ta {{c1::b}} c\n")
        assert config.cloze_field is None

    def test_the_template_has_no_cloze_filter_to_offer(
        self,
    ):
        """Why the note type cannot be made: there is nothing to put in it."""
        from src.card_layout import build_templates
        from src.column_model import plan_columns
        from src.sheet_config import SheetConfig

        plan = plan_columns(["ID", "Word", "Meaning"])
        templates = build_templates(plan, SheetConfig(), is_cloze=True)
        assert "cloze:" not in templates[0]["qfmt"]

    def test_no_cloze_note_type_is_built_for_a_sheet_that_never_asked(
        self, monkeypatch
    ):
        """The other half of it: Anki refuses such a model, so we must not offer one.

        Checked at the point of creation rather than through the return value,
        because the failure being prevented is the *call* — col.models.add() is
        what raises, and by then the sync is already over.
        """
        from src import templates_and_definitions as td
        from src.column_model import plan_columns
        from src.sheet_config import SheetConfig

        made = []
        monkeypatch.setattr(
            td,
            "create_model",
            lambda col, name, fields, templates, is_cloze=False, **kw: made.append(
                (name, is_cloze)
            ),
        )
        monkeypatch.setattr(td, "get_deck_note_type_ids", lambda url: {}, raising=False)

        import src.config_manager as config_manager
        import src.utils as utils

        monkeypatch.setattr(config_manager, "get_deck_note_type_ids", lambda url: {})
        monkeypatch.setattr(config_manager, "get_deck_remote_name", lambda url: "Deck")
        monkeypatch.setattr(
            utils, "register_note_type_for_deck", lambda *a, **k: None, raising=False
        )

        class _Models:
            def by_name(self, name):
                return None

        class _Col:
            models = _Models()

        plan = plan_columns(["ID", "Word", "Meaning"])
        td.ensure_custom_models(_Col(), "https://x/d/ABC/edit", plan, SheetConfig())

        assert made, "the Basic note type should still be built"
        assert not [
            name for name, is_cloze in made if is_cloze
        ], f"built a Cloze note type Anki will refuse: {made}"

    def test_a_sheet_that_declares_cloze_still_gets_its_note_type(self, monkeypatch):
        """Otherwise the guard above would pass by never building one at all."""
        from src import templates_and_definitions as td
        from src.column_model import plan_columns
        from src.sheet_config import parse_config_row

        made = []
        monkeypatch.setattr(
            td,
            "create_model",
            lambda col, name, fields, templates, is_cloze=False, **kw: made.append(
                (name, is_cloze)
            ),
        )
        import src.config_manager as config_manager
        import src.utils as utils

        monkeypatch.setattr(config_manager, "get_deck_note_type_ids", lambda url: {})
        monkeypatch.setattr(config_manager, "get_deck_remote_name", lambda url: "Deck")
        monkeypatch.setattr(
            utils, "register_note_type_for_deck", lambda *a, **k: None, raising=False
        )

        class _Models:
            def by_name(self, name):
                return None

        class _Col:
            models = _Models()

        plan = plan_columns(["ID", "Word", "Sentence"])
        config = parse_config_row({"ID": "#config", "Sentence": "cloze"}, plan)
        td.ensure_custom_models(_Col(), "https://x/d/ABC/edit", plan, config)

        assert [name for name, is_cloze in made if is_cloze], made
