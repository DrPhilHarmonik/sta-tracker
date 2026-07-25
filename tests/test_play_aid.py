import db
import export as exp


def _fresh(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


def _adventurer(name="Thorin"):
    return db.create_entity("adventurer", name, {
        "species": "Human", "rank": "Lieutenant",
        "sheet": {
            "attributes": {"control": 11, "daring": 10, "fitness": 10, "insight": 9, "presence": 9, "reason": 8},
            "departments": {"command": 3, "conn": 2, "engineering": 1, "security": 2, "medicine": 1, "science": 1},
            "focuses": ["Astrophysics"], "values": ["Duty above all"],
            "reputation": 4, "reprimands": 1,
            "milestones": [{"type": "Spotlight", "date": "2401-01-01", "note": "Saved the day"}],
        },
    }, "Backstory dump that should not appear.")


def test_export_play_aid_writes_compact_character(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    aid_id = _adventurer()
    out = tmp_path / "aid.md"
    path = exp.export_play_aid(aid_id, out)
    assert path == out
    text = out.read_text(encoding="utf-8")
    # header + play-critical content present
    assert text.startswith("# Thorin")
    assert "*Adventurer*" in text
    assert "**Attributes:**" in text
    assert "Astrophysics" in text
    assert "Duty above all" in text
    # trimmed: no reputation line, no milestone log, no notes dump, no ## heading
    assert "Reputation" not in text
    assert "Milestone" not in text
    assert "Backstory dump" not in text
    assert "## Character Sheet" not in text


def test_export_play_aid_starship_uses_ship_block(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    ship_id = db.create_entity("starship", "USS Reliant", {
        "sheet": {"systems": {"engines": 9}, "talents": ["Ablative Armor"], "traits": ["Federation Starship"]},
    }, "")
    out = tmp_path / "ship.md"
    exp.export_play_aid(ship_id, out)
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# USS Reliant")
    assert "*Starship*" in text
    assert "**Systems:**" in text
    assert "Ablative Armor" in text
    assert "## Starship Sheet" not in text


def test_export_play_aid_missing_entity_raises(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    import pytest
    with pytest.raises(ValueError, match="not found"):
        exp.export_play_aid(999, tmp_path / "x.md")


def test_export_all_play_aids_only_pcs_and_ships(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    _adventurer("Kirk")
    db.create_entity("starship", "Enterprise", {"sheet": {"systems": {}}}, "")
    db.create_entity("npc", "Barkeep", {}, "")   # excluded
    db.create_entity("quest", "Find the relic", {}, "")  # excluded

    out_dir = tmp_path / "Play Aids"
    count = exp.export_all_play_aids(out_dir)
    assert count == 2
    written = sorted(p.name for p in out_dir.glob("*.md"))
    assert written == ["Enterprise.md", "Kirk.md"]


def test_export_all_play_aids_empty_returns_zero(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    assert exp.export_all_play_aids(tmp_path / "aids") == 0
