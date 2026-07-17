import adversaries as adv
import db


def _fresh(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


def test_library_ships_empty(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    assert adv.all_adversaries() == []
    assert adv.search("") == []
    assert adv.find("Anything") is None


def test_default_adversary_has_full_sta_shape():
    a = adv.default_adversary()
    assert set(a["attributes"]) == set(__import__("sta_sheet").ATTRIBUTES)
    assert set(a["departments"]) == set(__import__("sta_sheet").DEPARTMENTS)
    assert a["kind"] in adv.ADVERSARY_KINDS


def test_save_and_find_roundtrip(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    adv.save({
        "name": "Klingon Warrior", "kind": "Notable NPC",
        "attributes": {"control": 9, "daring": 11, "fitness": 11, "insight": 8, "presence": 9, "reason": 8},
        "departments": {"command": 2, "conn": 2, "engineering": 1, "security": 4, "medicine": 1, "science": 1},
        "weapons": [{"name": "Bat'leth", "damage": 4, "qualities": "Vicious"}],
        "focuses": ["Combat Tactics"],
    })
    found = adv.find("klingon warrior")
    assert found is not None
    assert found["attributes"]["fitness"] == 11
    assert found["weapons"][0]["name"] == "Bat'leth"
    # Stress defaults to Fitness + Security when unset.
    assert found["stress_max"] == 11 + 4


def test_save_replaces_by_name_case_insensitively(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    adv.save({"name": "Romulan", "kind": "Minor NPC"})
    adv.save({"name": "romulan", "kind": "Major NPC"})
    all_ = adv.all_adversaries()
    assert len(all_) == 1
    assert all_[0]["kind"] == "Major NPC"


def test_remove(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    adv.save({"name": "Gorn"})
    adv.save({"name": "Tholian"})
    adv.remove("Gorn")
    names = [a["name"] for a in adv.all_adversaries()]
    assert names == ["Tholian"]


def test_save_requires_a_name(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    try:
        adv.save({"name": "  "})
    except ValueError:
        pass
    else:
        assert False, "expected ValueError for a blank name"


def test_search_matches_name_and_kind(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    adv.save({"name": "Borg Drone", "kind": "Notable NPC"})
    adv.save({"name": "Ferengi", "kind": "Minor NPC"})
    assert [a["name"] for a in adv.search("borg")] == ["Borg Drone"]
    assert {a["name"] for a in adv.search("minor")} == {"Ferengi"}


def test_from_entity_snapshots_sheet(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    eid = db.create_entity("enemy", "Jem'Hadar", {"cr": "Major NPC"}, "")
    db.update_entity(eid, "Jem'Hadar", {
        "cr": "Major NPC",
        "sheet": {
            "attributes": {"control": 10, "daring": 11, "fitness": 12, "insight": 8, "presence": 9, "reason": 8},
            "departments": {"command": 2, "conn": 2, "engineering": 1, "security": 5, "medicine": 1, "science": 1},
            "stress_max": 17, "weapons": [{"name": "Plasma Rifle", "damage": 5, "qualities": ""}],
        },
    }, "")
    template = adv.from_entity(db.get_entity(eid))
    assert template["name"] == "Jem'Hadar"
    assert template["kind"] == "Major NPC"
    assert template["attributes"]["fitness"] == 12
    assert template["weapons"][0]["name"] == "Plasma Rifle"


def test_build_sheet_produces_sta_sheet_with_full_stress(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    template = adv.normalize({
        "name": "Cardassian", "stress_max": 14,
        "attributes": {"control": 10, "daring": 9, "fitness": 10, "insight": 9, "presence": 10, "reason": 10},
        "departments": {"command": 3, "conn": 1, "engineering": 2, "security": 3, "medicine": 1, "science": 2},
    })
    sheet = adv.build_sheet(template)
    assert "attributes" in sheet and "departments" in sheet
    assert sheet["stress_max"] == 14
    assert sheet["stress_current"] == 14
    assert sheet["attributes"]["control"] == 10


def test_library_is_isolated_per_config_dir(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    adv.save({"name": "Q"})
    # A different DB dir sees a fresh, empty library.
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "other" / "campaign.db"))
    db.init_db()
    assert adv.all_adversaries() == []
