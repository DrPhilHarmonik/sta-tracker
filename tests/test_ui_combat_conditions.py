"""UI tests for the STA conflict tracker's Trait picker and the Stress ->
Injury flow that replaces 5e HP/death saves."""
import asyncio

import db
import conditions as cnd
from app import STAApp
from textual.widgets import Select, Input, ListView


def run(scenario):
    asyncio.run(scenario())


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    pc_id = db.create_entity("adventurer", "Mira Vex", {}, "")
    db.update_entity(pc_id, "Mira Vex", {
        "sheet": {
            "attributes": {"control": 9, "daring": 10, "fitness": 10, "insight": 8, "presence": 9, "reason": 8},
            "departments": {"command": 2, "conn": 1, "engineering": 1, "security": 2, "medicine": 1, "science": 1},
            "stress_max": 12, "stress_current": 12,
        },
    }, "")
    db.create_entity("encounter", "Test Enc", {}, "")
    return pc_id


async def _open_combat(pilot, app):
    await pilot.press("c")
    await pilot.pause()
    app.screen.query_one("#entity-table").move_cursor(row=0)
    await pilot.pause()
    app.screen.action_open_selected()
    await pilot.pause()
    app.screen.action_open_combat()
    await pilot.pause()
    return app.screen


def test_trait_select_is_populated_from_library(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(140, 50)) as pilot:
            cs = await _open_combat(pilot, app)
            cs.query_one("#combat-tabs").active = "tab-conflict"
            await pilot.pause()
            sel = cs.query_one("#sel-condition-name", Select)
            option_values = [str(v) for _, v in sel._options]
            for name in cnd.CONDITION_NAMES:
                assert name in option_values, f"Missing trait: {name}"
            assert "__custom__" in option_values

    run(scenario)


def test_trait_description_appears_on_select(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(140, 50)) as pilot:
            cs = await _open_combat(pilot, app)
            cs.query_one("#combat-tabs").active = "tab-conflict"
            await pilot.pause()
            cs.query_one("#sel-condition-name", Select).value = "Injured"
            await pilot.pause()
            desc = str(cs.query_one("#condition-desc").content)
            assert "difficulty" in desc.lower() or "task" in desc.lower()

    run(scenario)


def test_applying_library_trait_adds_it_to_combatant(monkeypatch, tmp_path):
    pc_id = _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(140, 50)) as pilot:
            cs = await _open_combat(pilot, app)
            cs.query_one("#sel-add-combatant", Select).value = str(pc_id)
            cs.query_one("#btn-add-combatant").press()
            await pilot.pause()
            cs.query_one("#combat-tabs").active = "tab-conflict"
            await pilot.pause()
            cs.query_one("#sel-hp-target", Select).value = str(pc_id)
            cs.query_one("#sel-condition-name", Select).value = "Prone"
            cs.query_one("#btn-add-condition").press()
            await pilot.pause()
            combatant = next(c for c in cs.combat["combatants"] if c["entity_id"] == pc_id)
            assert any(c["name"] == "Prone" for c in combatant["conditions"])

    run(scenario)


def test_custom_trait_input_shows_when_custom_selected(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(140, 50)) as pilot:
            cs = await _open_combat(pilot, app)
            cs.query_one("#combat-tabs").active = "tab-conflict"
            await pilot.pause()
            custom_input = cs.query_one("#input-condition-custom", Input)
            assert not custom_input.display
            cs.query_one("#sel-condition-name", Select).value = "__custom__"
            await pilot.pause()
            assert custom_input.display

    run(scenario)


def test_apply_stress_reduces_sheet_stress(monkeypatch, tmp_path):
    pc_id = _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(140, 50)) as pilot:
            cs = await _open_combat(pilot, app)
            cs.query_one("#sel-add-combatant", Select).value = str(pc_id)
            cs.query_one("#btn-add-combatant").press()
            await pilot.pause()
            cs.query_one("#combat-tabs").active = "tab-conflict"
            await pilot.pause()
            cs.query_one("#sel-hp-target", Select).value = str(pc_id)
            cs.query_one("#input-hp-amount", Input).value = "5"
            cs.query_one("#btn-damage").press()
            await pilot.pause()
            assert db.get_entity(pc_id)["fields"]["sheet"]["stress_current"] == 7

    run(scenario)


def test_reaching_zero_stress_records_an_injury_and_injured_trait(monkeypatch, tmp_path):
    pc_id = _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(140, 50)) as pilot:
            cs = await _open_combat(pilot, app)
            cs.query_one("#sel-add-combatant", Select).value = str(pc_id)
            cs.query_one("#btn-add-combatant").press()
            await pilot.pause()
            cs.query_one("#combat-tabs").active = "tab-conflict"
            await pilot.pause()
            cs.query_one("#sel-hp-target", Select).value = str(pc_id)
            cs.query_one("#input-hp-amount", Input).value = "99"
            cs.query_one("#btn-damage").press()
            await pilot.pause()
            sheet = db.get_entity(pc_id)["fields"]["sheet"]
            assert sheet["stress_current"] == 0
            assert len(sheet["injuries"]) == 1
            combatant = next(c for c in cs.combat["combatants"] if c["entity_id"] == pc_id)
            assert any(c["name"] == "Injured" for c in combatant["conditions"])

    run(scenario)


def test_recover_stress_caps_at_max(monkeypatch, tmp_path):
    pc_id = _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(140, 50)) as pilot:
            cs = await _open_combat(pilot, app)
            cs.query_one("#sel-add-combatant", Select).value = str(pc_id)
            cs.query_one("#btn-add-combatant").press()
            await pilot.pause()
            cs.query_one("#combat-tabs").active = "tab-conflict"
            await pilot.pause()
            cs.query_one("#sel-hp-target", Select).value = str(pc_id)
            # Drain some Stress, then over-heal; it must cap at stress_max (12).
            cs.query_one("#input-hp-amount", Input).value = "5"
            cs.query_one("#btn-damage").press()
            await pilot.pause()
            cs.query_one("#input-hp-amount", Input).value = "99"
            cs.query_one("#btn-heal").press()
            await pilot.pause()
            assert db.get_entity(pc_id)["fields"]["sheet"]["stress_current"] == 12

    run(scenario)
