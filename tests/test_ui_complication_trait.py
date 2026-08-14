"""A rolled Complication becomes a scene Trait (Phase 29).

`roll_task` has always counted Complications and the UI has always reported the
number, and that was the end of it. At the table a Complication *is* something,
and `scene.py` already tracks that as scene Traits -- these check the join, at
both roll sites.
"""
import asyncio

import db
import scene
import sta_sheet as sta
from app import STAApp
from screens.common import ComplicationPrompt


def run(scenario):
    asyncio.run(scenario())


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    monkeypatch.setenv("STA_SETTINGS_PATH", str(tmp_path / "settings.json"))
    db.init_db()


def _an_adventurer(name="T'Pol"):
    sheet = sta.normalize_sheet({})
    sheet["attributes"]["reason"] = 12
    sheet["departments"]["science"] = 5
    return db.create_entity("adventurer", name, {"sheet": sheet}, "")


class FixedRng:
    def __init__(self, faces):
        self.faces = list(faces)

    def randint(self, low, high):
        return self.faces.pop(0) if len(self.faces) > 1 else self.faces[0]


async def _roll_in_quick_task(pilot, app, entity_id, faces, monkeypatch):
    await pilot.press("ctrl+r")
    await pilot.pause()
    modal = app.screen
    modal.query_one("#qt-entity").value = str(entity_id)
    await pilot.pause()
    monkeypatch.setattr("task.random", FixedRng(faces))
    modal.roll()
    await pilot.pause()
    return modal


def test_a_clean_roll_offers_nothing(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    entity_id = _an_adventurer()

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            modal = await _roll_in_quick_task(pilot, app, entity_id, [5, 6], monkeypatch)

            prompt = modal.query_one(ComplicationPrompt)
            assert prompt.pending == 0
            assert not prompt.has_class("-active")

    run(scenario)


def test_a_complication_reveals_the_prompt(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    entity_id = _an_adventurer()

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            modal = await _roll_in_quick_task(pilot, app, entity_id, [20, 20], monkeypatch)

            prompt = modal.query_one(ComplicationPrompt)
            assert prompt.pending == 2
            assert prompt.has_class("-active")

    run(scenario)


def test_naming_the_complication_adds_a_scene_trait(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    entity_id = _an_adventurer()

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            modal = await _roll_in_quick_task(pilot, app, entity_id, [20, 20], monkeypatch)
            modal.query_one("#qt-complication-name").value = "Sparking Console"
            modal.query_one("#qt-complication-add").press()
            await pilot.pause()

            assert "Sparking Console" in scene.traits()
            prompt = modal.query_one(ComplicationPrompt)
            assert not prompt.has_class("-active")  # dealt with, so it goes away

    run(scenario)


def test_an_unnamed_complication_is_not_added(monkeypatch, tmp_path):
    """Opening the field and thinking better of it is a normal thing to do, and
    an empty scene Trait would be worse than none."""
    _setup(monkeypatch, tmp_path)
    entity_id = _an_adventurer()

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            modal = await _roll_in_quick_task(pilot, app, entity_id, [20, 20], monkeypatch)
            modal.query_one("#qt-complication-name").value = "   "
            modal.query_one("#qt-complication-add").press()
            await pilot.pause()

            assert scene.traits() == []

    run(scenario)


def test_the_combat_tracker_offers_the_same_prompt(monkeypatch, tmp_path):
    """A Complication means the same thing in a conflict as out of one."""
    _setup(monkeypatch, tmp_path)
    entity_id = _an_adventurer()
    encounter_id = db.create_entity("encounter", "Boarding Action", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            from screens.combat import CombatTrackerScreen

            app.push_screen(CombatTrackerScreen(encounter_id))
            await pilot.pause()
            screen = app.screen
            screen.combat = screen.combat  # settled
            screen.query_one("#sel-add-combatant").value = str(entity_id)
            screen._add_combatant()
            await pilot.pause()
            screen.query_one("#sel-attack-attacker").value = str(entity_id)
            await pilot.pause()

            monkeypatch.setattr("task.random", FixedRng([20, 20]))
            screen._roll_task()
            await pilot.pause()

            prompt = screen.query_one(ComplicationPrompt)
            assert prompt.pending == 2

            screen.query_one("#combat-complication-name").value = "Hull Breach"
            screen.query_one("#combat-complication-add").press()
            await pilot.pause()

            assert "Hull Breach" in scene.traits()

    run(scenario)
