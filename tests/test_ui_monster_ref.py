"""UI tests for the STA Adversary Reference: it opens with an empty library,
a campaign enemy can be saved into it, and a saved adversary can be spawned
back into the campaign as an enemy entity."""
import asyncio

import adversaries as adv
import db
from app import STAApp
from textual.widgets import Select, Input


def run(scenario):
    asyncio.run(scenario())


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


def _make_enemy(name="Klingon Warrior"):
    eid = db.create_entity("enemy", name, {"kind": "Notable NPC"}, "")
    db.update_entity(eid, name, {
        "kind": "Notable NPC",
        "sheet": {
            "attributes": {"control": 9, "daring": 11, "fitness": 11, "insight": 8, "presence": 9, "reason": 8},
            "departments": {"command": 2, "conn": 2, "engineering": 1, "security": 4, "medicine": 1, "science": 1},
            "weapons": [{"name": "Bat'leth", "damage": 4, "qualities": "Vicious"}],
        },
    }, "")
    return eid


async def _open_ref(pilot, app):
    await pilot.press("m")
    await pilot.pause()
    return app.screen


def test_reference_opens_empty(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(180, 50)) as pilot:
            await pilot.pause()
            screen = await _open_ref(pilot, app)
            from screens.monster_ref import MonsterRefScreen
            assert isinstance(screen, MonsterRefScreen)
            assert screen.query_one("#monster-list").__len__() == 0
            detail = str(screen.query_one("#monster-detail").content)
            assert "empty" in detail.lower()

    run(scenario)


def test_saving_a_campaign_enemy_populates_the_library(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _make_enemy()

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(180, 50)) as pilot:
            await pilot.pause()
            screen = await _open_ref(pilot, app)
            assert screen.query_one("#monster-list").__len__() == 0
            enemy_id = db.list_entities("enemy")[0]["id"]
            screen.query_one("#sel-import-enemy", Select).value = str(enemy_id)
            screen.query_one("#btn-save-to-library").press()
            await pilot.pause()
            assert screen.query_one("#monster-list").__len__() == 1
            assert adv.find("Klingon Warrior") is not None

    run(scenario)


def test_search_filters_library(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    adv.save({"name": "Klingon Warrior", "kind": "Notable NPC"})
    adv.save({"name": "Ferengi Trader", "kind": "Minor NPC"})

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(180, 50)) as pilot:
            await pilot.pause()
            screen = await _open_ref(pilot, app)
            assert screen.query_one("#monster-list").__len__() == 2
            screen.query_one("#monster-search", Input).value = "ferengi"
            await pilot.pause()
            assert screen.query_one("#monster-list").__len__() == 1

    run(scenario)


def test_add_to_campaign_creates_enemy_entity(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    adv.save({
        "name": "Klingon Warrior", "kind": "Notable NPC",
        "attributes": {"control": 9, "daring": 11, "fitness": 11, "insight": 8, "presence": 9, "reason": 8},
        "departments": {"command": 2, "conn": 2, "engineering": 1, "security": 4, "medicine": 1, "science": 1},
        "weapons": [{"name": "Bat'leth", "damage": 4, "qualities": "Vicious"}],
    })

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(180, 50)) as pilot:
            await pilot.pause()
            screen = await _open_ref(pilot, app)
            screen.query_one("#btn-add-monster").press()
            for _ in range(6):
                await pilot.pause()

        enemies = db.list_entities("enemy")
        assert len(enemies) == 1
        sheet = db.get_entity(enemies[0]["id"])["fields"]["sheet"]
        assert sheet["attributes"]["fitness"] == 11
        assert sheet["stress_current"] == sheet["stress_max"]
        assert sheet["weapons"][0]["name"] == "Bat'leth"

    run(scenario)


def test_remove_from_library(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    adv.save({"name": "Gorn", "kind": "Major NPC"})

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(180, 50)) as pilot:
            await pilot.pause()
            screen = await _open_ref(pilot, app)
            assert screen.query_one("#monster-list").__len__() == 1
            screen.query_one("#btn-remove-from-library").press()
            await pilot.pause()
            assert screen.query_one("#monster-list").__len__() == 0
            assert adv.all_adversaries() == []

    run(scenario)
