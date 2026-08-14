"""The `?` keyboard-help overlay.

The point of the overlay is the keys the footer does not show: the dashboard
carries nine `show=False` bindings, one per entity type, and until now nothing
in the app said so. So the tests below check the hidden ones specifically, and
check that the list is built from the *live* bindings rather than a copy that
would drift.
"""
import asyncio

import db
from app import STAApp
from screens.help import HelpScreen, binding_rows, group_rows


def run(scenario):
    asyncio.run(scenario())


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    monkeypatch.setenv("STA_SETTINGS_PATH", str(tmp_path / "settings.json"))
    db.init_db()


def _rows_on_screen(app):
    return app.screen.rows


def test_question_mark_opens_the_overlay_from_the_dashboard(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            await pilot.press("question_mark")
            await pilot.pause()

            assert isinstance(app.screen, HelpScreen)

    run(scenario)


def test_the_overlay_lists_the_bindings_the_footer_hides(monkeypatch, tmp_path):
    """The nine `show=False` dashboard keys are the whole reason for this
    feature: fast once you know them, invisible until someone says so."""
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            await pilot.press("question_mark")
            await pilot.pause()

            described = {desc: key for key, desc, _ in _rows_on_screen(app)}
            for key, description in [
                ("n", "NPCs"), ("a", "Adventurers"), ("x", "Enemies"),
                ("l", "Locations"), ("q", "Quests"), ("f", "Factions"),
                ("i", "Items"), ("s", "Sessions"), ("c", "Encounters"),
            ]:
                assert described.get(description) == key, f"{description} missing from help"

    run(scenario)


def test_the_overlay_includes_app_wide_keys_as_well_as_the_screen_s(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            await pilot.press("question_mark")
            await pilot.pause()

            rows = _rows_on_screen(app)
            descriptions = {desc for _, desc, _ in rows}
            assert "Quick Capture" in descriptions   # from STAApp
            assert "Search All" in descriptions      # from Dashboard

            groups = dict(group_rows(rows, "Dashboard"))
            assert ("/", "Search All") in groups["This screen"]
            assert any(desc == "Quick Capture" for _, desc in groups["Everywhere"])

    run(scenario)


def test_escape_closes_the_overlay_and_returns_to_the_screen_beneath(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            underneath = app.screen
            await pilot.press("question_mark")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()

            assert app.screen is underneath

    run(scenario)


def test_pressing_question_mark_again_closes_rather_than_stacking(monkeypatch, tmp_path):
    """Otherwise the second `?` opens a help screen describing the help screen,
    and escape has to be pressed as many times as `?` was."""
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            depth = len(app.screen_stack)
            await pilot.press("question_mark")
            await pilot.pause()
            await pilot.press("question_mark")
            await pilot.pause()

            assert not isinstance(app.screen, HelpScreen)
            assert len(app.screen_stack) == depth

    run(scenario)


def test_the_overlay_describes_whichever_screen_is_active(monkeypatch, tmp_path):
    """Not a fixed list: open a different screen and the keys change with it."""
    _setup(monkeypatch, tmp_path)
    db.create_entity("npc", "Sarek", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            await pilot.press("n")            # entity list for NPCs
            await pilot.pause()
            list_screen_name = type(app.screen).__name__

            await pilot.press("f1")
            await pilot.pause()

            assert app.screen.screen_name == list_screen_name
            descriptions = {desc for _, desc, _ in _rows_on_screen(app)}
            assert "NPCs" not in descriptions  # a dashboard-only binding

    run(scenario)


def test_f1_reaches_help_from_a_screen_whose_search_box_has_focus(monkeypatch, tmp_path):
    """This is F1's whole reason for existing.

    The entity lists focus their search Input on mount, so `?` is typed into it
    rather than dispatched as a binding -- correct behaviour for a text field,
    and it would leave the help overlay unreachable from the screens people
    spend the most time on. F1 is not a printable character, so it still fires.
    """
    _setup(monkeypatch, tmp_path)
    db.create_entity("npc", "Sarek", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            await pilot.press("n")
            await pilot.pause()
            entity_list = app.screen

            await pilot.press("question_mark")
            await pilot.pause()
            assert app.screen is entity_list, "a bare ? should type into the search box"
            assert "?" in entity_list.query_one("#search").value

            await pilot.press("f1")
            await pilot.pause()
            assert isinstance(app.screen, HelpScreen)

    run(scenario)


def test_the_overlay_titles_itself_from_the_screen_s_own_docstring(monkeypatch, tmp_path):
    """Screens carry docstrings far more reliably than titles, and the first
    line is already written for a reader."""
    _setup(monkeypatch, tmp_path)
    entity_id = db.create_entity("adventurer", "T'Pol", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            from screens.sheet import CharacterSheetScreen
            app.push_screen(CharacterSheetScreen(entity_id))
            await pilot.pause()

            app.action_help()
            await pilot.pause()

            assert app.screen.help_title == "Star Trek Adventures 2e character sheet editor"

    run(scenario)


# ── The row builder, without an app ────────────────────────────────────────────

class _FakeNode:
    pass


class _Dashboard(_FakeNode):
    pass


def _active(key, description, node, action="noop", key_display=None):
    from textual.binding import ActiveBinding, Binding

    return ActiveBinding(
        node=node,
        binding=Binding(key, action, description, key_display=key_display),
        enabled=True,
    )


def test_binding_rows_skips_undescribed_and_framework_bindings():
    """An unlabelled binding has nothing to tell a reader, and Textual's own
    bindings are the framework's, not this app's."""
    bindings = {
        "a": _active("a", "Adventurers", _Dashboard()),
        "b": _active("b", "", _Dashboard()),
        "ctrl+c": _active("ctrl+c", "Copy selected text", _Dashboard(), action="screen.copy_text"),
        "tab": _active("tab", "Focus Next", _Dashboard(), action="app.focus_next"),
        "ctrl+p": _active("ctrl+p", "palette", _Dashboard(), action="command_palette"),
        "enter": _active("enter", "Press button", _Dashboard(), action="press"),
    }

    rows = binding_rows(bindings)

    assert rows == [("a", "Adventurers", "_Dashboard")]


def test_binding_rows_merges_two_keys_for_the_same_action():
    """`?` and F1 are one thing you can do, not two."""
    bindings = {
        "question_mark": _active("question_mark", "Help", _Dashboard()),
        "f1": _active("f1", "Help", _Dashboard()),
    }

    rows = binding_rows(bindings, key_display=lambda b: {"question_mark": "?", "f1": "F1"}[b.key])

    assert rows == [("? / F1", "Help", "_Dashboard")]


def test_binding_rows_renders_keys_the_way_the_app_displays_them():
    """Textual normalises `/` to `slash` and `?` to `question_mark`, and
    `binding.key` holds the normalised form -- so an overlay that printed the
    raw key would tell the reader to press a word."""
    bindings = {
        "slash": _active("slash", "Search All", _Dashboard()),
        "question_mark": _active("question_mark", "Help", _Dashboard()),
    }

    shown = dict((desc, key) for key, desc, _ in binding_rows(
        bindings, key_display=lambda b: {"slash": "/", "question_mark": "?"}[b.key]))

    assert shown == {"Search All": "/", "Help": "?"}


def test_binding_rows_falls_back_to_the_raw_key_without_a_display_helper():
    bindings = {"a": _active("a", "Adventurers", _Dashboard())}

    assert binding_rows(bindings)[0][0] == "a"


def test_group_rows_splits_this_screen_from_everywhere():
    rows = [
        ("/", "Search All", "_Dashboard"),
        ("ctrl+n", "Quick Capture", "STAApp"),
        ("e", "Export MD", "_Dashboard"),
    ]

    groups = dict(group_rows(rows, "_Dashboard"))

    assert groups["This screen"] == [("e", "Export MD"), ("/", "Search All")]
    assert groups["Everywhere"] == [("ctrl+n", "Quick Capture")]


def test_group_rows_omits_an_empty_group():
    rows = [("ctrl+n", "Quick Capture", "STAApp")]

    groups = dict(group_rows(rows, "_Dashboard"))

    assert "This screen" not in groups
    assert groups["Everywhere"] == [("ctrl+n", "Quick Capture")]


def test_the_overlay_scopes_itself_to_the_screen_and_the_app(monkeypatch, tmp_path):
    """A focused text field contributes its own editing keys to
    `active_bindings` -- thirty rows of "Delete character left" and "Move cursor
    right a word and select" on any screen with a search box. Listing them
    buries the handful of keys the screen actually offers.
    """
    _setup(monkeypatch, tmp_path)
    db.create_entity("npc", "Sarek", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            await pilot.press("n")
            await pilot.pause()
            await pilot.press("f1")
            await pilot.pause()

            descriptions = {desc for _, desc, _ in _rows_on_screen(app)}
            assert "Search" in descriptions          # the screen's own
            assert "Quick Capture" in descriptions   # the app's
            for editing_key in ("Delete character left", "Move cursor left",
                                "Paste text from the clipboard", "Select all"):
                assert editing_key not in descriptions

    run(scenario)


def test_a_screen_without_a_docstring_still_gets_a_readable_title(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    db.create_entity("npc", "Sarek", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            await pilot.press("n")
            await pilot.pause()
            await pilot.press("f1")
            await pilot.pause()

            assert app.screen.help_title == "Entity List"

    run(scenario)
