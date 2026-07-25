"""Phase 21: the Party Overview recovery flow -- restore Stress for all active
PCs, clear a selected PC's Injuries, and carry/reset Threat between missions."""
import asyncio

from textual.widgets import DataTable

import db
import sta_sheet as sta
from app import STAApp
from screens.party_overview import PartyOverviewScreen


def run(scenario):
    asyncio.run(scenario())


def _spent_pc(name):
    return db.create_entity("adventurer", name, {
        "sheet": {
            "attributes": {"fitness": 10}, "departments": {"security": 2},
            "stress_current": 2, "injuries": ["Broken arm"],
        },
    }, "")


def test_recover_stress_all_restores_every_active_pc(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    a = _spent_pc("Aldric")
    b = _spent_pc("Bex")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 45)) as pilot:
            await app.push_screen(PartyOverviewScreen())
            for _ in range(3):
                await pilot.pause()
            app.screen.query_one("#btn-recover-stress-all").press()
            for _ in range(3):
                await pilot.pause()

        for pc in (a, b):
            sheet = sta.normalize_sheet(db.get_entity(pc)["fields"]["sheet"])
            assert sheet["stress_current"] == sheet["stress_max"] == 12
            # stress recovery leaves injuries in place
            assert sheet["injuries"] == ["Broken arm"]

    run(scenario)


def test_clear_injuries_selected_only_touches_that_pc(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    a = _spent_pc("Aldric")   # sorted first
    b = _spent_pc("Bex")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 45)) as pilot:
            await app.push_screen(PartyOverviewScreen())
            for _ in range(3):
                await pilot.pause()
            table = app.screen.query_one("#party-table", DataTable)
            table.move_cursor(row=0)   # Aldric
            await pilot.pause()
            app.screen.query_one("#btn-clear-injuries").press()
            for _ in range(3):
                await pilot.pause()

        assert sta.normalize_sheet(db.get_entity(a)["fields"]["sheet"])["injuries"] == []
        assert sta.normalize_sheet(db.get_entity(b)["fields"]["sheet"])["injuries"] == ["Broken arm"]

    run(scenario)


def test_threat_carry_and_reset(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    db.set_pools(3, 5)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 45)) as pilot:
            await app.push_screen(PartyOverviewScreen())
            for _ in range(3):
                await pilot.pause()
            app.screen.query_one("#btn-threat-carry").press()
            for _ in range(2):
                await pilot.pause()
            assert db.get_pools()["threat"] == 5   # carried, Momentum untouched
            assert db.get_pools()["momentum"] == 3
            app.screen.query_one("#btn-threat-reset").press()
            for _ in range(2):
                await pilot.pause()
            assert db.get_pools()["threat"] == 0
            assert db.get_pools()["momentum"] == 3

    run(scenario)
