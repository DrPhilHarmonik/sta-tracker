import asyncio

import db
from app import STAApp
from textual.widgets import DataTable


def run(scenario):
    asyncio.run(scenario())


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


async def _open_timeline(pilot, app):
    await pilot.press("L")
    await pilot.pause()
    return app.screen


def test_timeline_screen_opens_empty(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(180, 50)) as pilot:
            await pilot.pause()
            screen = await _open_timeline(pilot, app)
            from screens.timeline import TimelineScreen
            assert isinstance(screen, TimelineScreen)
            assert screen.query_one("#timeline-table", DataTable).row_count == 0

    run(scenario)


def test_timeline_lists_sessions_in_order(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    db.create_entity("session", "Second", {"session_number": "2"}, "Warp core breach.")
    db.create_entity("session", "First", {"session_number": "1"}, "First contact.")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(180, 50)) as pilot:
            await pilot.pause()
            screen = await _open_timeline(pilot, app)
            table = screen.query_one("#timeline-table", DataTable)
            assert table.row_count == 2
            first_cell = table.get_cell_at((0, 5))
            assert str(first_cell) == "First"

    run(scenario)
