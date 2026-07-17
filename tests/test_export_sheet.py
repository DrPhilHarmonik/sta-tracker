import asyncio
from pathlib import Path

import db
import export as exp


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


def _make_adventurer(name="Thorin") -> int:
    return db.create_entity(
        "adventurer",
        name,
        {
            "species": "Human",
            "rank": "Lieutenant",
            "sheet": {
                "attributes": {"control": 11, "daring": 10, "fitness": 10, "insight": 9, "presence": 9, "reason": 8},
                "departments": {"command": 3, "conn": 2, "engineering": 1, "security": 2, "medicine": 1, "science": 1},
            },
        },
        "",
    )


def _make_enemy(name="Klingon Warrior") -> int:
    return db.create_entity(
        "enemy",
        name,
        {
            "kind": "Notable NPC",
            "species": "Klingon",
            "sheet": {
                "attributes": {"control": 9, "daring": 11, "fitness": 11, "insight": 8, "presence": 9, "reason": 8},
                "departments": {"command": 2, "conn": 2, "engineering": 1, "security": 4, "medicine": 1, "science": 1},
            },
        },
        "",
    )


def test_export_creates_file(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_adventurer()
    out = tmp_path / "exports" / "thorin_sheet.md"
    path = exp.export_entity_sheet(eid, out)
    assert path == out
    assert path.exists()


def test_export_contains_entity_name(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_adventurer("Brynn")
    out = tmp_path / "brynn.md"
    exp.export_entity_sheet(eid, out)
    content = out.read_text()
    assert "Brynn" in content


def test_export_contains_sheet_section(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_adventurer()
    out = tmp_path / "sheet.md"
    exp.export_entity_sheet(eid, out)
    content = out.read_text()
    assert "## Character Sheet" in content


def test_export_contains_attributes(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_adventurer()
    out = tmp_path / "attributes.md"
    exp.export_entity_sheet(eid, out)
    content = out.read_text()
    assert "Control" in content
    assert "Reason" in content


def test_export_enemy_contains_stress(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_enemy()
    out = tmp_path / "enemy.md"
    exp.export_entity_sheet(eid, out)
    content = out.read_text()
    assert "Stress" in content


def test_export_default_path_slugified_name(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_adventurer("Zara the Bold")
    out = tmp_path / "zara-the-bold_sheet.md"
    path = exp.export_entity_sheet(eid, out)
    assert path.exists()
    assert "Zara the Bold" in path.read_text()


def test_export_missing_entity_raises(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    import pytest
    with pytest.raises(ValueError, match="not found"):
        exp.export_entity_sheet(9999, tmp_path / "out.md")


def test_export_creates_parent_dirs(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_adventurer()
    deep = tmp_path / "a" / "b" / "c" / "sheet.md"
    exp.export_entity_sheet(eid, deep)
    assert deep.exists()


# -- UI smoke test --

def run(scenario):
    asyncio.run(scenario())


def test_ui_export_sheet_button_exists(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_adventurer("Petra")

    async def scenario():
        from app import STAApp
        from screens.sheet import CharacterSheetScreen
        app = STAApp()
        async with app.run_test(size=(180, 50)) as pilot:
            await pilot.pause()
            app.push_screen(CharacterSheetScreen(eid))
            for _ in range(8):
                await pilot.pause()
            assert isinstance(app.screen, CharacterSheetScreen)
            btn = app.screen.query_one("#btn-export-sheet")
            assert btn is not None

    run(scenario)


def test_export_includes_milestones(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = db.create_entity("adventurer", "Sotek", {"species": "Vulcan"}, "")
    db.update_entity(eid, "Sotek", {
        "species": "Vulcan",
        "sheet": {
            "attributes": {"control": 11, "daring": 8, "fitness": 10, "insight": 9, "presence": 8, "reason": 12},
            "departments": {"command": 2, "conn": 1, "engineering": 2, "security": 2, "medicine": 1, "science": 4},
            "milestones": [{"type": "Arc", "date": "2401-05-02", "note": "Reason +1"}],
        },
    }, "")
    out = tmp_path / "sotek.md"
    exp.export_entity_sheet(eid, out)
    content = out.read_text()
    assert "Milestones" in content
    assert "Arc: Reason +1" in content
