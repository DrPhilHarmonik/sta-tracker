import asyncio

import db
from app import STAApp
from screens.ship_combat import ShipConflictScreen
from textual.widgets import Select, Input


def run(scenario):
    asyncio.run(scenario())


def _ship_sheet(**over):
    sheet = {
        "systems": {"comms": 8, "computers": 9, "engines": 10, "sensors": 9, "structure": 11, "weapons": 10},
        "departments": {"command": 2, "conn": 3, "engineering": 2, "security": 3, "medicine": 1, "science": 2},
        "scale": 4,
        "shields_max": 14, "shields_current": 14,
        "weapons": [{"name": "Phaser Bank", "damage": 5, "qualities": "Versatile"}],
    }
    sheet.update(over)
    return sheet


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    a = db.create_entity("starship", "USS Reliant", {}, "")
    db.update_entity(a, "USS Reliant", {"sheet": _ship_sheet()}, "")
    b = db.create_entity("starship", "IKS Gr'oth", {}, "")
    db.update_entity(b, "IKS Gr'oth", {"sheet": _ship_sheet(shields_max=12, shields_current=12)}, "")
    enc = db.create_entity("encounter", "Battle", {}, "")
    return a, b, enc


async def _open(pilot, app, enc):
    app.push_screen(ShipConflictScreen(enc))
    for _ in range(8):
        await pilot.pause()
    return app.screen


async def _add_both(cs, pilot, crew_id, adv_id):
    cs.query_one("#sel-add-ship", Select).value = str(crew_id)
    cs.query_one("#ship-add-side", Select).value = "crew"
    cs.query_one("#btn-add-ship").press()
    await pilot.pause()
    cs.query_one("#sel-add-ship", Select).value = str(adv_id)
    cs.query_one("#ship-add-side", Select).value = "adversary"
    cs.query_one("#btn-add-ship").press()
    await pilot.pause()


def test_add_ships_and_start_puts_crew_first_with_full_power(monkeypatch, tmp_path):
    crew_id, adv_id, enc = _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            cs = await _open(pilot, app, enc)
            await _add_both(cs, pilot, crew_id, adv_id)
            cs.query_one("#btn-ship-start").press()
            await pilot.pause()
            assert cs.query_one("#sel-acting-ship", Select).value == str(crew_id)
            # Power filled to Engines (10) at start.
            state = db.get_entity(enc)["fields"]["ship_combat"]
            assert all(s["power"] == 10 for s in state["ships"])

    run(scenario)


def test_spend_power_reduces_the_acting_ships_pool(monkeypatch, tmp_path):
    crew_id, adv_id, enc = _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            cs = await _open(pilot, app, enc)
            await _add_both(cs, pilot, crew_id, adv_id)
            cs.query_one("#btn-ship-start").press()
            await pilot.pause()
            cs.query_one("#ship-power-amount", Input).value = "3"
            cs.query_one("#btn-spend-power").press()
            await pilot.pause()
            state = db.get_entity(enc)["fields"]["ship_combat"]
            crew = next(s for s in state["ships"] if s["entity_id"] == crew_id)
            assert crew["power"] == 7

    run(scenario)


def test_ship_buying_dice_debits_momentum_pool(monkeypatch, tmp_path):
    crew_id, adv_id, enc = _setup(monkeypatch, tmp_path)
    db.set_pools(6, 0)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            cs = await _open(pilot, app, enc)
            await _add_both(cs, pilot, crew_id, adv_id)
            cs.query_one("#btn-ship-start").press()
            await pilot.pause()
            cs.query_one("#ship-task-bonus-dice", Select).value = "2"  # cost 3
            cs.query_one("#btn-ship-roll-task").press()
            await pilot.pause()
            # The ship roll may bank Momentum after the buy; assert the buy report.
            result = str(cs.query_one("#ship-task-result").content)
            assert "bought 2 d20" in result
            assert "spent 3 Momentum" in result

    run(scenario)


def test_ship_spend_momentum_menu_debits_pool(monkeypatch, tmp_path):
    crew_id, adv_id, enc = _setup(monkeypatch, tmp_path)
    db.set_pools(2, 0)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            cs = await _open(pilot, app, enc)
            await _add_both(cs, pilot, crew_id, adv_id)
            cs.query_one("#btn-ship-start").press()
            await pilot.pause()
            cs.query_one("#btn-ship-momentum-spend").press()  # Obtain Information, cost 1
            await pilot.pause()
            assert db.get_pools()["momentum"] == 1

    run(scenario)


def test_weapon_damage_prefills_and_applying_reduces_target_shields(monkeypatch, tmp_path):
    crew_id, adv_id, enc = _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            cs = await _open(pilot, app, enc)
            await _add_both(cs, pilot, crew_id, adv_id)
            cs.query_one("#btn-ship-start").press()
            await pilot.pause()
            cs.query_one("#sel-ship-target", Select).value = str(adv_id)
            await pilot.pause()
            cs.query_one("#btn-ship-roll-damage").press()
            await pilot.pause()
            rolled = int(cs.query_one("#ship-damage-amount").value)
            cs.query_one("#btn-ship-apply-damage").press()
            await pilot.pause()
            # Damage is reduced by Resistance (Scale 4) before hitting shields.
            expected = 12 - max(0, rolled - 4)
            assert db.get_entity(adv_id)["fields"]["sheet"]["shields_current"] == max(0, expected)

    run(scenario)


def test_overflow_damage_becomes_breaches(monkeypatch, tmp_path):
    crew_id, adv_id, enc = _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            cs = await _open(pilot, app, enc)
            await _add_both(cs, pilot, crew_id, adv_id)
            cs.query_one("#btn-ship-start").press()
            await pilot.pause()
            cs.query_one("#sel-ship-target", Select).value = str(adv_id)
            await pilot.pause()
            cs.query_one("#ship-breach-system", Select).value = "engines"
            # 12 shields + 4 resistance = 16 to zero it; 20 leaves 4 overflow.
            cs.query_one("#ship-damage-amount", Input).value = "20"
            cs.query_one("#btn-ship-apply-damage").press()
            await pilot.pause()
            assert db.get_entity(adv_id)["fields"]["sheet"]["shields_current"] == 0
            state = db.get_entity(enc)["fields"]["ship_combat"]
            adv = next(s for s in state["ships"] if s["entity_id"] == adv_id)
            assert adv["breaches"]["engines"] == 4

    run(scenario)


def test_next_turn_alternates_sides_and_next_round_refills_power(monkeypatch, tmp_path):
    crew_id, adv_id, enc = _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            cs = await _open(pilot, app, enc)
            await _add_both(cs, pilot, crew_id, adv_id)
            cs.query_one("#btn-ship-start").press()
            await pilot.pause()
            cs.query_one("#ship-power-amount", Input).value = "5"
            cs.query_one("#btn-spend-power").press()
            await pilot.pause()
            cs.query_one("#btn-ship-next-turn").press()
            await pilot.pause()
            assert cs.query_one("#sel-acting-ship", Select).value == str(adv_id)
            cs.query_one("#btn-ship-next-round").press()
            await pilot.pause()
            state = db.get_entity(enc)["fields"]["ship_combat"]
            assert state["round"] == 2
            assert all(s["power"] == s["power_max"] for s in state["ships"])  # refilled

    run(scenario)


def test_detail_screen_opens_ship_conflict(monkeypatch, tmp_path):
    crew_id, adv_id, enc = _setup(monkeypatch, tmp_path)

    async def scenario():
        from screens.entities import EntityDetailScreen
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            app.push_screen(EntityDetailScreen(enc))
            for _ in range(6):
                await pilot.pause()
            app.screen.action_open_ship_combat()
            for _ in range(8):
                await pilot.pause()
            assert isinstance(app.screen, ShipConflictScreen)

    run(scenario)
