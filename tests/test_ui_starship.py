import asyncio

import db
from app import STAApp
from screens.starship import StarshipSheetScreen
from screens.entities import EntityDetailScreen


def run(scenario):
    asyncio.run(scenario())


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


async def _open_ship_sheet(pilot, app, entity_id):
    app.push_screen(StarshipSheetScreen(entity_id))
    for _ in range(8):
        await pilot.pause()
    return app.screen


def test_starship_type_available_on_dashboard(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            # The dashboard renders a card per entity type.
            assert app.screen.query_one("#card-starship") is not None

    run(scenario)


def test_ship_sheet_renders_system_and_department_widgets(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = db.create_entity("starship", "USS Reliant", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_ship_sheet(pilot, app, eid)
            assert isinstance(screen, StarshipSheetScreen)
            for s in ["comms", "computers", "engines", "sensors", "structure", "weapons"]:
                assert screen.query_one(f"#ship-sys-{s}") is not None
            for d in ["command", "conn", "engineering", "security", "medicine", "science"]:
                assert screen.query_one(f"#ship-dept-{d}") is not None

    run(scenario)


def test_shields_readout_reflects_structure_plus_security(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = db.create_entity("starship", "USS Reliant", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_ship_sheet(pilot, app, eid)
            screen.query_one("#ship-sys-structure").value = "12"
            screen.query_one("#ship-dept-security").value = "3"
            screen.query_one("#btn-ship-recalc").press()
            await pilot.pause()
            readout = str(screen.query_one("#ship-shields-readout").content)
            assert "15" in readout

    run(scenario)


def test_ship_task_roll_produces_a_result(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = db.create_entity("starship", "USS Reliant", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_ship_sheet(pilot, app, eid)
            screen.query_one("#ship-task-difficulty").value = "1"
            screen.query_one("#btn-ship-roll-task").press()
            await pilot.pause()
            result = str(screen.query_one("#ship-task-result").content)
            assert "vs Diff 1" in result

    run(scenario)


def test_saving_ship_sheet_persists_starship_shape(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = db.create_entity("starship", "USS Reliant", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_ship_sheet(pilot, app, eid)
            screen.query_one("#ship-sys-weapons").value = "11"
            screen.query_one("#ship-scale").value = "5"
            screen.query_one("#ship-spaceframe").value = "Constitution"
            screen.query_one("#ship-weapon-name").value = "Phaser Bank"
            screen.query_one("#ship-weapon-damage").value = "6"
            screen.query_one("#btn-ship-add-weapon").press()
            await pilot.pause()
            screen.action_save()
            await pilot.pause()

        sheet = db.get_entity(eid)["fields"]["sheet"]
        assert "systems" in sheet
        assert sheet["systems"]["weapons"] == 11
        assert sheet["scale"] == 5
        assert sheet["spaceframe"] == "Constitution"
        assert sheet["weapons"][0]["name"] == "Phaser Bank"

    run(scenario)


def test_detail_screen_opens_ship_sheet_for_starship(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = db.create_entity("starship", "USS Reliant", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            app.push_screen(EntityDetailScreen(eid))
            for _ in range(6):
                await pilot.pause()
            detail = app.screen
            detail.action_open_sheet()
            for _ in range(8):
                await pilot.pause()
            assert isinstance(app.screen, StarshipSheetScreen)

    run(scenario)


def test_starship_detail_summary_shows_ship_stats(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = db.create_entity("starship", "USS Reliant", {}, "")
    db.update_entity(eid, "USS Reliant", {
        "sheet": {
            "systems": {"comms": 8, "computers": 9, "engines": 10, "sensors": 9, "structure": 11, "weapons": 10},
            "departments": {"command": 2, "conn": 3, "engineering": 2, "security": 3, "medicine": 1, "science": 2},
            "scale": 4,
        },
    }, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            app.push_screen(EntityDetailScreen(eid))
            for _ in range(6):
                await pilot.pause()
            body = str(app.screen.query_one("#detail-body").content)
            assert "Starship Sheet" in body
            assert "Resistance 4" in body
            assert "Structure 11" in body

    run(scenario)
