import asyncio

import db
import spaceframes
from app import STAApp
from screens.entities import EntityListScreen
from textual.widgets import Select, Input


def run(scenario):
    asyncio.run(scenario())


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


async def _open_list(pilot, app, type_):
    app.push_screen(EntityListScreen(type_))
    for _ in range(6):
        await pilot.pause()
    return app.screen


# -- quick crew ---------------------------------------------------------------

def test_quick_crew_button_shows_on_adventurer_list(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_list(pilot, app, "adventurer")
            assert screen.query_one("#btn-quick-crew") is not None

    run(scenario)


def test_quick_crew_creates_a_supporting_character(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        from screens.quick_crew import QuickCrewScreen
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_list(pilot, app, "adventurer")
            screen.action_quick_crew()
            for _ in range(6):
                await pilot.pause()
            crew = app.screen
            assert isinstance(crew, QuickCrewScreen)
            crew.query_one("#crew-name", Input).value = "Ensign Ro"
            crew.query_one("#crew-species", Select).value = "Bajoran"
            crew.query_one("#crew-focus", Input).value = "Piloting"
            crew.query_one("#crew-role", Input).value = "Flight Controller"
            crew.query_one("#btn-crew-create").press()
            for _ in range(6):
                await pilot.pause()

        adv = db.list_entities("adventurer")
        assert len(adv) == 1
        sheet = db.get_entity(adv[0]["id"])["fields"]["sheet"]
        assert sheet["species"] == "Bajoran"
        assert sheet["role"] == "Flight Controller"
        assert sheet["focuses"] == ["Piloting"]

    run(scenario)


def test_quick_crew_requires_a_name(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_list(pilot, app, "adventurer")
            screen.action_quick_crew()
            for _ in range(6):
                await pilot.pause()
            crew = app.screen
            crew.query_one("#btn-crew-create").press()
            await pilot.pause()
            assert "required" in str(crew.query_one("#crew-status").content).lower()
        assert db.list_entities("adventurer") == []

    run(scenario)


# -- spaceframes --------------------------------------------------------------

def test_spaceframes_button_shows_on_starship_list(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_list(pilot, app, "starship")
            assert screen.query_one("#btn-spaceframes") is not None

    run(scenario)


def test_save_ship_to_library_then_build_new_ship(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    sid = db.create_entity("starship", "USS Reliant", {}, "")
    db.update_entity(sid, "USS Reliant", {
        "sheet": {
            "systems": {"comms": 8, "computers": 9, "engines": 10, "sensors": 9, "structure": 11, "weapons": 10},
            "scale": 4,
        },
    }, "")

    async def scenario():
        from screens.spaceframe import SpaceframeScreen
        app = STAApp()
        async with app.run_test(size=(180, 50)) as pilot:
            await pilot.pause()
            app.push_screen(SpaceframeScreen())
            for _ in range(6):
                await pilot.pause()
            screen = app.screen
            assert screen.query_one("#frame-list").__len__() == 0
            screen.query_one("#sel-import-ship", Select).value = str(sid)
            screen.query_one("#btn-save-frame").press()
            await pilot.pause()
            assert screen.query_one("#frame-list").__len__() == 1
            assert spaceframes.find("USS Reliant") is not None

            # Build a new ship from the saved frame.
            screen.query_one("#btn-build-ship").press()
            for _ in range(6):
                await pilot.pause()

        ships = db.list_entities("starship")
        assert len(ships) == 2  # original + built
        built = [s for s in ships if s["name"].startswith("New ")][0]
        sheet = db.get_entity(built["id"])["fields"]["sheet"]
        assert sheet["systems"]["structure"] == 11
        assert sheet["scale"] == 4

    run(scenario)
