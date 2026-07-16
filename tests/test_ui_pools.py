import asyncio

import db
from app import STAApp
from screens.pools import PoolBar
from screens.sheet import CharacterSheetScreen


def run(scenario):
    asyncio.run(scenario())


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


def test_dashboard_shows_pool_bar(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    db.set_pools(2, 5)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            bar = app.screen.query_one("#pool-bar", PoolBar)
            readout = str(bar.query_one("#pool-readout").content)
            assert "Momentum 2/6" in readout
            assert "Threat 5" in readout

    run(scenario)


def test_pool_bar_buttons_adjust_pools(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            bar = app.screen.query_one("#pool-bar", PoolBar)
            bar.query_one("#btn-mom-inc").press()
            bar.query_one("#btn-mom-inc").press()
            bar.query_one("#btn-thr-inc").press()
            await pilot.pause()
            assert db.get_pools() == {"momentum": 2, "threat": 1}
            readout = str(bar.query_one("#pool-readout").content)
            assert "Momentum 2/6" in readout
            assert "Threat 1" in readout

    run(scenario)


def test_task_roll_banks_generated_momentum_into_pool(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    # A high Attribute + Department against Difficulty 0 makes a task roll very
    # likely to leave surplus successes, i.e. Momentum, which should flow into
    # the shared pool.
    eid = db.create_entity("adventurer", "Kai Vantar", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            app.push_screen(CharacterSheetScreen(eid))
            for _ in range(8):
                await pilot.pause()
            screen = app.screen
            screen.query_one("#sta-attr-control").value = "12"
            screen.query_one("#sta-dept-command").value = "5"
            screen.query_one("#task-attr").value = "control"
            screen.query_one("#task-dept").value = "command"
            screen.query_one("#task-difficulty").value = "0"
            screen.query_one("#task-bonus-dice").value = "3"  # roll 5 dice
            screen.query_one("#btn-roll-task").press()
            await pilot.pause()

        # With TN 17 across 5 dice at Difficulty 0, surplus successes are
        # near-certain; the pool should have grown from zero.
        assert db.get_pools()["momentum"] > 0

    run(scenario)


def test_seed_button_sets_threat_from_party(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    db.create_entity("adventurer", "Kira", {}, "")
    db.create_entity("adventurer", "Bashir", {}, "")
    db.create_entity("adventurer", "Dax", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            bar = app.screen.query_one("#pool-bar", PoolBar)
            bar.query_one("#btn-thr-seed").press()
            await pilot.pause()
            assert db.get_pools()["threat"] == 6  # three adventurers x2
            assert "Threat 6" in str(bar.query_one("#pool-readout").content)

    run(scenario)


def test_pool_bar_refreshes_on_dashboard_resume(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            dashboard = app.screen
            # Push a screen, mutate pools underneath it, then pop back.
            app.push_screen(CharacterSheetScreen(db.create_entity("adventurer", "X", {}, "")))
            for _ in range(4):
                await pilot.pause()
            db.set_pools(4, 2)
            app.pop_screen()
            for _ in range(4):
                await pilot.pause()
            readout = str(dashboard.query_one("#pool-readout").content)
            assert "Momentum 4/6" in readout
            assert "Threat 2" in readout

    run(scenario)
