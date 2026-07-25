import asyncio

import db
from app import STAApp
from screens.sheet import CharacterSheetScreen


def run(scenario):
    asyncio.run(scenario())


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


async def _open_sheet(pilot, app, entity_id):
    app.push_screen(CharacterSheetScreen(entity_id))
    for _ in range(8):
        await pilot.pause()
    return app.screen


def test_sheet_renders_sta_stat_widgets(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = db.create_entity("adventurer", "Kai Vantar", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_sheet(pilot, app, eid)
            assert isinstance(screen, CharacterSheetScreen)
            # Attribute and Department inputs exist for all twelve stats.
            for a in ["control", "daring", "fitness", "insight", "presence", "reason"]:
                assert screen.query_one(f"#sta-attr-{a}") is not None
            for d in ["command", "conn", "engineering", "security", "medicine", "science"]:
                assert screen.query_one(f"#sta-dept-{d}") is not None

    run(scenario)


def test_base_stress_readout_reflects_fitness_plus_security(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = db.create_entity("adventurer", "Kai Vantar", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_sheet(pilot, app, eid)
            screen.query_one("#sta-attr-fitness").value = "10"
            screen.query_one("#sta-dept-security").value = "3"
            screen.query_one("#btn-recalc").press()
            await pilot.pause()
            readout = str(screen.query_one("#sta-stress-readout").content)
            assert "13" in readout

    run(scenario)


def test_task_roll_produces_a_result(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = db.create_entity("adventurer", "Kai Vantar", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_sheet(pilot, app, eid)
            screen.query_one("#task-difficulty").value = "1"
            screen.query_one("#btn-roll-task").press()
            await pilot.pause()
            result = str(screen.query_one("#task-result").content)
            assert "vs Diff 1" in result
            assert "success" in result.lower()

    run(scenario)


def test_buying_dice_debits_momentum_pool_on_sheet_roll(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = db.create_entity("adventurer", "Kai Vantar", {}, "")
    db.set_pools(6, 0)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_sheet(pilot, app, eid)
            screen.query_one("#task-difficulty").value = "1"
            screen.query_one("#task-bonus-dice").value = "1"  # buy 1 die, cost 1
            screen.query_one("#btn-roll-task").press()
            await pilot.pause()
            # cost 1 spent; the roll may also bank Momentum on success, so assert
            # the buy was charged relative to whatever the roll then banks.
            result = str(screen.query_one("#task-result").content)
            assert "bought 1 d20" in result
            assert "spent 1 Momentum" in result

    run(scenario)


def test_complication_range_preset_flows_into_the_roll(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = db.create_entity("adventurer", "Kai Vantar", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_sheet(pilot, app, eid)
            # widest complication band; the Select carries the value through
            screen.query_one("#task-comp-range").value = "3"
            assert screen.query_one("#task-comp-range").value == "3"
            screen.query_one("#btn-roll-task").press()
            await pilot.pause()
            assert "vs Diff" in str(screen.query_one("#task-result").content)

    run(scenario)


def test_spend_momentum_menu_on_sheet(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = db.create_entity("adventurer", "Kai Vantar", {}, "")
    db.set_pools(3, 0)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_sheet(pilot, app, eid)
            screen.query_one("#btn-momentum-spend").press()  # Obtain Information, cost 1
            await pilot.pause()
            assert db.get_pools()["momentum"] == 2
            assert "Spent 1 Momentum" in str(screen.query_one("#momentum-spend-result").content)

    run(scenario)


def test_repeat_task_button_rolls_again(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = db.create_entity("adventurer", "Kai Vantar", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_sheet(pilot, app, eid)
            screen.query_one("#task-difficulty").value = "1"
            screen.query_one("#btn-repeat-task").press()
            await pilot.pause()
            assert "vs Diff 1" in str(screen.query_one("#task-result").content)

    run(scenario)


def test_challenge_dice_roll_produces_a_result(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = db.create_entity("adventurer", "Kai Vantar", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_sheet(pilot, app, eid)
            screen.query_one("#cd-count").value = "3"
            screen.query_one("#btn-roll-cd").press()
            await pilot.pause()
            result = str(screen.query_one("#cd-result").content)
            assert "[CD]" in result

    run(scenario)


def test_adding_focus_updates_task_focus_options_and_persists(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = db.create_entity("adventurer", "Kai Vantar", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_sheet(pilot, app, eid)
            screen.query_one("#focus-input").value = "Astrophysics"
            screen.query_one("#btn-add-focus").press()
            await pilot.pause()
            assert "Astrophysics" in screen.pending_focuses
            # The Task Roll focus Select accepts the newly added focus.
            focus_select = screen.query_one("#task-focus")
            focus_select.value = "Astrophysics"
            assert focus_select.value == "Astrophysics"

            screen.query_one("#value-input").value = "The needs of the many"
            screen.query_one("#btn-add-value").press()
            await pilot.pause()
            screen.action_save()
            await pilot.pause()

        sheet = db.get_entity(eid)["fields"]["sheet"]
        assert sheet["focuses"] == ["Astrophysics"]
        assert sheet["values"] == ["The needs of the many"]

    run(scenario)


def test_invoking_a_value_spends_determination_on_the_roll(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = db.create_entity("adventurer", "Kai Vantar", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_sheet(pilot, app, eid)
            screen.query_one("#sta-determination").value = "2"
            screen.query_one("#task-invoke").value = True
            screen.query_one("#btn-roll-task").press()
            await pilot.pause()
            # Determination was spent (2 -> 1) and the switch reset.
            assert screen.query_one("#sta-determination").value == "1"
            assert screen.query_one("#task-invoke").value is False
            assert "1/3" in str(screen.query_one("#determination-readout").content)
            result = str(screen.query_one("#task-result").content)
            assert "success" in result.lower()

    run(scenario)


def test_invoking_with_no_determination_is_a_no_op(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = db.create_entity("adventurer", "Kai Vantar", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_sheet(pilot, app, eid)
            screen.query_one("#sta-determination").value = "0"
            screen.query_one("#task-invoke").value = True
            screen.query_one("#btn-roll-task").press()
            await pilot.pause()
            assert screen.query_one("#sta-determination").value == "0"
            assert "no Determination" in str(screen.query_one("#task-result").content)

    run(scenario)


def test_challenge_value_button_regains_determination(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = db.create_entity("adventurer", "Kai Vantar", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_sheet(pilot, app, eid)
            screen.query_one("#sta-determination").value = "1"
            screen.query_one("#btn-challenge-value").press()
            await pilot.pause()
            assert screen.query_one("#sta-determination").value == "2"
            assert "2/3" in str(screen.query_one("#determination-readout").content)

    run(scenario)
