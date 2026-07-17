import asyncio

import db
import talents
import focuses
from app import STAApp
from screens.sheet import CharacterSheetScreen
from textual.widgets import Select, Input


def run(scenario):
    asyncio.run(scenario())


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


async def _open_reference(pilot, app):
    await pilot.press("T")
    await pilot.pause()
    return app.screen


async def _open_sheet(pilot, app, entity_id):
    app.push_screen(CharacterSheetScreen(entity_id))
    for _ in range(8):
        await pilot.pause()
    return app.screen


# -- reference screen ---------------------------------------------------------

def test_reference_screen_opens_and_lists_are_empty(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(180, 50)) as pilot:
            await pilot.pause()
            screen = await _open_reference(pilot, app)
            from screens.reference import ReferenceScreen
            assert isinstance(screen, ReferenceScreen)
            assert screen.query_one("#ref-talent-list").__len__() == 0
            assert screen.query_one("#ref-focus-list").__len__() == 0

    run(scenario)


def test_reference_screen_saves_a_talent(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(180, 50)) as pilot:
            await pilot.pause()
            screen = await _open_reference(pilot, app)
            screen.query_one("#ref-talent-name", Input).value = "Bold: Command"
            screen.query_one("#ref-talent-desc", Input).value = "Re-roll bought dice."
            screen.query_one("#btn-ref-talent-save").press()
            await pilot.pause()
            assert screen.query_one("#ref-talent-list").__len__() == 1
            saved = talents.find("Bold: Command")
            assert saved is not None and saved["description"] == "Re-roll bought dice."

    run(scenario)


def test_reference_screen_adds_a_focus(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(180, 50)) as pilot:
            await pilot.pause()
            screen = await _open_reference(pilot, app)
            screen.query_one("#ref-focus-input", Input).value = "Astrophysics"
            screen.query_one("#btn-ref-focus-add").press()
            await pilot.pause()
            assert screen.query_one("#ref-focus-list").__len__() == 1
            assert focuses.all_focuses() == ["Astrophysics"]

    run(scenario)


# -- auto-remember + pick from the character sheet ----------------------------

def test_adding_a_focus_on_the_sheet_remembers_it_in_the_library(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = db.create_entity("adventurer", "Kai Vantar", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_sheet(pilot, app, eid)
            screen.query_one("#focus-input", Input).value = "Warp Field Dynamics"
            screen.query_one("#btn-add-focus").press()
            await pilot.pause()
            assert "Warp Field Dynamics" in screen.pending_focuses
            assert focuses.all_focuses() == ["Warp Field Dynamics"]
            # It now appears in the sheet's library picker.
            options = [str(v) for _, v in screen.query_one("#focus-library", Select)._options]
            assert "Warp Field Dynamics" in options

    run(scenario)


def test_picking_a_talent_from_the_library_adds_it(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    talents.save("Studious", "Extra time on Reason tasks.")
    eid = db.create_entity("adventurer", "Kai Vantar", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_sheet(pilot, app, eid)
            screen.query_one("#talent-library", Select).value = "Studious"
            screen.query_one("#btn-talent-from-library").press()
            await pilot.pause()
            assert "Studious" in screen.pending_talents

    run(scenario)
