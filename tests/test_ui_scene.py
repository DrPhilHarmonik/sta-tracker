import asyncio

import db
import extended
import scene
from app import STAApp
from textual.widgets import Input


def run(scenario):
    asyncio.run(scenario())


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


async def _open_scene(pilot, app):
    await pilot.press("D")
    await pilot.pause()
    return app.screen


def test_scene_screen_opens_empty(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(180, 50)) as pilot:
            await pilot.pause()
            screen = await _open_scene(pilot, app)
            from screens.scene import SceneScreen
            assert isinstance(screen, SceneScreen)
            assert screen.query_one("#ext-list").__len__() == 0
            assert screen.query_one("#directive-list").__len__() == 0

    run(scenario)


def test_create_extended_task_and_log_work(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(180, 50)) as pilot:
            await pilot.pause()
            screen = await _open_scene(pilot, app)
            screen.query_one("#ext-name", Input).value = "Repair Warp Core"
            screen.query_one("#ext-work-total", Input).value = "8"
            screen.query_one("#ext-resistance", Input).value = "1"
            screen.query_one("#btn-ext-save").press()
            await pilot.pause()
            assert screen.query_one("#ext-list").__len__() == 1

            screen.query_one("#ext-work-amount", Input).value = "3"
            screen.query_one("#btn-ext-logwork").press()
            await pilot.pause()
            task = extended.find("Repair Warp Core")
            assert task["work_done"] == 3
            assert extended.effective_difficulty(task) == 2  # base 1 + resistance 1

    run(scenario)


def test_add_directive_and_scene_trait(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(180, 50)) as pilot:
            await pilot.pause()
            screen = await _open_scene(pilot, app)
            screen.query_one("#directive-input", Input).value = "Investigate, do not engage"
            screen.query_one("#btn-add-directive").press()
            await pilot.pause()
            screen.query_one("#trait-input", Input).value = "Ion Storm"
            screen.query_one("#btn-add-trait").press()
            await pilot.pause()
            assert scene.directives() == ["Investigate, do not engage"]
            assert scene.traits() == ["Ion Storm"]
            assert screen.query_one("#directive-list").__len__() == 1
            assert screen.query_one("#trait-list").__len__() == 1

    run(scenario)


def test_conflict_tracker_echoes_active_scene(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    scene.add_directive("The Prime Directive applies")
    scene.add_trait("Nebula")
    db.create_entity("encounter", "Standoff", {}, "")

    async def scenario():
        from screens.combat import CombatTrackerScreen
        enc_id = db.list_entities("encounter")[0]["id"]
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            app.push_screen(CombatTrackerScreen(enc_id))
            for _ in range(8):
                await pilot.pause()
            summary = str(app.screen.query_one("#combat-summary").content)
            assert "The Prime Directive applies" in summary
            assert "Nebula" in summary

    run(scenario)
