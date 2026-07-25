"""Phase 20: EntityListScreen column filters (by select-type schema fields)
and the GlobalSearchScreen match column that surfaces sheet hits."""
import asyncio

from textual.widgets import DataTable, Input, Select

import db
from app import STAApp
from screens.entities import EntityListScreen, GlobalSearchScreen


def run(scenario):
    asyncio.run(scenario())


def test_status_filter_narrows_the_list(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    db.create_entity("adventurer", "Active One", {"status": "Active"}, "")
    db.create_entity("adventurer", "Retired One", {"status": "Retired"}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await app.push_screen(EntityListScreen("adventurer"))
            for _ in range(4):
                await pilot.pause()
            table = app.screen.query_one("#entity-table", DataTable)
            assert table.row_count == 2
            app.screen.query_one("#filter-status", Select).value = "Retired"
            for _ in range(3):
                await pilot.pause()
            assert table.row_count == 1
            cell_key = table.coordinate_to_cell_key((0, 0))
            assert int(cell_key.row_key.value) is not None
            # clearing the filter restores the full list
            app.screen.query_one("#filter-status", Select).value = Select.NULL
            for _ in range(3):
                await pilot.pause()
            assert table.row_count == 2

    run(scenario)


def test_filter_and_search_combine(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    db.create_entity("adventurer", "Kira Active", {"status": "Active"}, "")
    db.create_entity("adventurer", "Kira Retired", {"status": "Retired"}, "")
    db.create_entity("adventurer", "Dax Active", {"status": "Active"}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await app.push_screen(EntityListScreen("adventurer"))
            for _ in range(4):
                await pilot.pause()
            app.screen.query_one("#search", Input).value = "Kira"
            for _ in range(3):
                await pilot.pause()
            table = app.screen.query_one("#entity-table", DataTable)
            assert table.row_count == 2
            app.screen.query_one("#filter-status", Select).value = "Active"
            for _ in range(3):
                await pilot.pause()
            assert table.row_count == 1

    run(scenario)


def test_global_search_shows_sheet_match_column(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    db.create_entity("adventurer", "Data", {"sheet": {"focuses": ["Warp Field Dynamics"]}}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await app.push_screen(GlobalSearchScreen())
            for _ in range(3):
                await pilot.pause()
            app.screen.query_one("#global-search", Input).value = "warp field"
            for _ in range(3):
                await pilot.pause()
            table = app.screen.query_one("#global-table", DataTable)
            assert table.row_count == 1
            match_cell = table.get_cell_at((0, 2))
            assert "Warp Field Dynamics" in str(match_cell)

    run(scenario)
