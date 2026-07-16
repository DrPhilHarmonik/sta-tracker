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
