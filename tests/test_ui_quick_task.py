"""The `ctrl+r` quick Task roll (Phase 28).

The point is reach: a Task roll used to require the combat tracker or the ship
screen, and most STA play is neither. So these check that it opens from an
ordinary screen and that a roll made here has the same consequences as one made
in a conflict -- pools moved, Determination spent, sheet written back.
"""
import asyncio

import db
import sta_sheet as sta
from app import STAApp
from screens.quick_task import QuickTaskModal


def run(scenario):
    asyncio.run(scenario())


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    monkeypatch.setenv("STA_SETTINGS_PATH", str(tmp_path / "settings.json"))
    db.init_db()


def _an_adventurer(name="T'Pol", determination=1):
    sheet = sta.normalize_sheet({})
    sheet["attributes"]["reason"] = 12
    sheet["departments"]["science"] = 5
    sheet["determination"] = determination
    return db.create_entity("adventurer", name, {"sheet": sheet}, "")


class FixedRng:
    def __init__(self, faces):
        self.faces = list(faces)

    def randint(self, low, high):
        return self.faces.pop(0) if len(self.faces) > 1 else self.faces[0]


def test_ctrl_r_opens_the_roller_from_the_dashboard(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _an_adventurer()

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()

            assert isinstance(app.screen, QuickTaskModal)

    run(scenario)


def test_ctrl_r_reaches_the_roller_from_a_list_screen_too(monkeypatch, tmp_path):
    """The whole point: rolling without first finding a combat to be in."""
    _setup(monkeypatch, tmp_path)
    _an_adventurer()

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            await pilot.press("a")           # the adventurer list
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()

            assert isinstance(app.screen, QuickTaskModal)

    run(scenario)


def test_pressing_ctrl_r_again_closes_rather_than_stacking(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _an_adventurer()

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            depth = len(app.screen_stack)
            await pilot.press("ctrl+r")
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()

            assert not isinstance(app.screen, QuickTaskModal)
            assert len(app.screen_stack) == depth

    run(scenario)


def test_only_sheet_bearing_entities_are_offered(monkeypatch, tmp_path):
    """You cannot roll a Task as a starbase."""
    _setup(monkeypatch, tmp_path)
    _an_adventurer("T'Pol")
    db.create_entity("location", "Starbase 47", {}, "")
    db.create_entity("enemy", "Romulan Centurion", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()

            from screens.quick_task import sheet_bearing_entities
            names = {name for name, _ in sheet_bearing_entities()}
            assert names == {"T'Pol", "Romulan Centurion"}

    run(scenario)


def test_a_roll_moves_the_shared_pools(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    entity_id = _an_adventurer()
    db.set_pools(0, 0)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()
            modal = app.screen
            modal.query_one("#qt-entity").value = str(entity_id)
            modal.query_one("#qt-attr").value = "reason"
            modal.query_one("#qt-dept").value = "science"
            modal.query_one("#qt-difficulty").value = "0"
            await pilot.pause()

            # Two natural 20s: no successes, two Complications, two Threat.
            monkeypatch.setattr("task.random", FixedRng([20, 20]))
            modal.roll()
            await pilot.pause()

            assert db.get_pools()["threat"] == 2

    run(scenario)


def test_invoking_a_value_writes_the_determination_back_to_the_sheet(monkeypatch, tmp_path):
    """A quick roll is still a real roll -- spending Determination has to cost
    the character, not just the dice."""
    _setup(monkeypatch, tmp_path)
    entity_id = _an_adventurer(determination=2)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()
            modal = app.screen
            modal.query_one("#qt-entity").value = str(entity_id)
            modal.query_one("#qt-invoke").value = True
            await pilot.pause()

            monkeypatch.setattr("task.random", FixedRng([5, 6]))
            modal.roll()
            await pilot.pause()

            saved = db.get_entity(entity_id)["fields"]["sheet"]
            assert saved["determination"] == 1
            assert modal.query_one("#qt-invoke").value is False

    run(scenario)


def test_rolling_without_a_character_says_so_instead_of_raising(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _an_adventurer()

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+r")
            await pilot.pause()
            modal = app.screen

            modal.roll()
            await pilot.pause()

            assert "Pick a character" in str(modal.query_one("#qt-result").content)

    run(scenario)


def test_escape_closes_the_roller(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _an_adventurer()

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            underneath = app.screen
            await pilot.press("ctrl+r")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()

            assert app.screen is underneath

    run(scenario)
