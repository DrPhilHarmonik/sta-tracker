import asyncio
import db
from app import STAApp
from screens.party_overview import _stress_cell, _get_combat_traits


def run(scenario):
    asyncio.run(scenario())


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


# -- unit tests for helpers --------------------------------------------------

def test_stress_cell_green_above_half():
    t = _stress_cell(10, 12)
    assert "10/12" in t.plain
    assert t.style == "green"


def test_stress_cell_yellow_between_quarter_and_half():
    t = _stress_cell(4, 12)
    assert t.style == "yellow"


def test_stress_cell_red_at_quarter_or_below():
    t = _stress_cell(2, 12)
    assert t.style == "red"


def test_stress_cell_bold_red_at_zero():
    t = _stress_cell(0, 12)
    assert t.style == "bold red"


def test_stress_cell_dim_when_max_zero():
    t = _stress_cell(0, 0)
    assert t.style == "dim"


def test_get_combat_traits_only_from_started_conflicts(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    pc_id = db.create_entity("adventurer", "Sotek", {}, "")
    db.create_entity("encounter", "Enc1", {
        "combat": {
            "round": 1, "started": False,
            "combatants": [{"entity_id": pc_id, "side": "crew", "has_acted": False,
                            "conditions": [{"name": "Exposed", "rounds_remaining": None}]}],
        }
    }, "")
    assert pc_id not in _get_combat_traits()


def test_get_combat_traits_returns_traits_from_started_conflict(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    pc_id = db.create_entity("adventurer", "Kira", {}, "")
    db.create_entity("encounter", "Enc1", {
        "combat": {
            "round": 2, "started": True,
            "combatants": [{"entity_id": pc_id, "side": "crew", "has_acted": False,
                            "conditions": [{"name": "Injured", "rounds_remaining": None}]}],
        }
    }, "")
    result = _get_combat_traits()
    assert pc_id in result
    assert result[pc_id][0]["name"] == "Injured"


# -- UI integration tests ----------------------------------------------------

def test_party_overview_renders_table(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    db.create_entity("adventurer", "Aldric", {
        "sheet": {"attributes": {"fitness": 10}, "departments": {"security": 2}, "rank": "Ensign"},
    }, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.pause()
            await pilot.press("p")
            await pilot.pause()
            from screens.party_overview import PartyOverviewScreen
            assert isinstance(app.screen, PartyOverviewScreen)
            table = app.screen.query_one("#party-table")
            assert table.row_count == 1

    run(scenario)


def test_party_overview_shows_no_adventurers_message(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.pause()
            await pilot.press("p")
            await pilot.pause()
            status = app.screen.query_one("#overview-status").content
            assert "No active" in str(status)

    run(scenario)


def test_party_overview_excludes_dead_adventurers(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    db.create_entity("adventurer", "Live One", {"status": "Active"}, "")
    db.create_entity("adventurer", "Dead Hero", {"status": "Dead"}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.pause()
            await pilot.press("p")
            await pilot.pause()
            table = app.screen.query_one("#party-table")
            assert table.row_count == 1

    run(scenario)
