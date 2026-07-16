"""UI interaction tests for the STA conflict tracker's Task rolls and
Challenge-Dice weapon damage (Conflict tab): the acting character defaults to
whoever's turn it is, the first weapon auto-selects, a Task roll reports
success/Difficulty, and a damage roll pre-fills the Stress field so applying
it is one click.
"""
import asyncio

import db
from app import STAApp


def run(scenario):
    asyncio.run(scenario())


def _sta_sheet(**over):
    sheet = {
        "attributes": {"control": 9, "daring": 11, "fitness": 10, "insight": 8, "presence": 9, "reason": 8},
        "departments": {"command": 2, "conn": 1, "engineering": 1, "security": 3, "medicine": 1, "science": 1},
        "stress_max": 13, "stress_current": 13,
        "weapons": [{"name": "Phaser", "damage": 3, "qualities": "Charge"}],
    }
    sheet.update(over)
    return sheet


def _make_combat(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    pc_id = db.create_entity("adventurer", "Brynn Ashforge", {}, "")
    db.update_entity(pc_id, "Brynn Ashforge", {"sheet": _sta_sheet()}, "")
    enemy_id = db.create_entity("enemy", "Klingon Warrior", {}, "")
    db.update_entity(enemy_id, "Klingon Warrior", {
        "sheet": _sta_sheet(weapons=[{"name": "Bat'leth", "damage": 4, "qualities": "Vicious"}]),
    }, "")
    db.create_entity("encounter", "Test Fight", {}, "")
    return pc_id, enemy_id


async def _open_combat_tracker(pilot, app):
    await pilot.press("c")
    await pilot.pause()
    table = app.screen.query_one("#entity-table")
    table.move_cursor(row=0)
    await pilot.pause()
    app.screen.action_open_selected()
    await pilot.pause()
    app.screen.action_open_combat()
    await pilot.pause()
    return app.screen


async def _add_both(cs, pilot, pc_id, enemy_id):
    cs.query_one("#sel-add-combatant").value = str(pc_id)
    cs.query_one("#btn-add-combatant").press()
    await pilot.pause()
    cs.query_one("#sel-add-combatant").value = str(enemy_id)
    cs.query_one("#btn-add-combatant").press()
    await pilot.pause()


def test_actor_defaults_to_current_turn_and_first_weapon_auto_selects(monkeypatch, tmp_path):
    pc_id, enemy_id = _make_combat(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            cs = await _open_combat_tracker(pilot, app)
            await _add_both(cs, pilot, pc_id, enemy_id)
            cs.query_one("#btn-start-encounter").press()
            await pilot.pause()
            # Crew act first; Brynn is the crew member.
            assert cs.query_one("#sel-attack-attacker").value == str(pc_id)
            assert cs.query_one("#sel-weapon").value == "w:0"

    run(scenario)


def test_task_roll_reports_success_and_difficulty(monkeypatch, tmp_path):
    pc_id, enemy_id = _make_combat(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            cs = await _open_combat_tracker(pilot, app)
            await _add_both(cs, pilot, pc_id, enemy_id)
            cs.query_one("#btn-start-encounter").press()
            await pilot.pause()
            cs.query_one("#task-difficulty").value = "1"
            cs.query_one("#btn-roll-task").press()
            await pilot.pause()
            result = str(cs.query_one("#task-result").content)
            assert "Brynn Ashforge" in result
            assert "success" in result.lower()

    run(scenario)


def test_roll_damage_prefills_stress_amount_for_one_click_apply(monkeypatch, tmp_path):
    pc_id, enemy_id = _make_combat(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            cs = await _open_combat_tracker(pilot, app)
            await _add_both(cs, pilot, pc_id, enemy_id)
            cs.query_one("#btn-start-encounter").press()
            await pilot.pause()

            cs.query_one("#sel-hp-target").value = str(enemy_id)
            await pilot.pause()
            cs.query_one("#btn-roll-damage").press()
            await pilot.pause()
            prefilled = cs.query_one("#input-hp-amount").value
            assert prefilled.isdigit()

            cs.query_one("#btn-damage").press()
            await pilot.pause()
            stress = db.get_entity(enemy_id)["fields"]["sheet"]["stress_current"]
            assert stress == 13 - int(prefilled)

    run(scenario)


def test_next_turn_switches_actor_to_the_other_side(monkeypatch, tmp_path):
    pc_id, enemy_id = _make_combat(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            cs = await _open_combat_tracker(pilot, app)
            await _add_both(cs, pilot, pc_id, enemy_id)
            cs.query_one("#btn-start-encounter").press()
            await pilot.pause()
            assert cs.query_one("#sel-attack-attacker").value == str(pc_id)

            cs.query_one("#btn-next-turn").press()
            await pilot.pause()
            assert cs.query_one("#sel-attack-attacker").value == str(enemy_id)
            assert cs.query_one("#sel-weapon").value == "w:0"  # Klingon's Bat'leth

    run(scenario)
