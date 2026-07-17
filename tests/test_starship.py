import starship as ship
import db


def test_default_sheet_has_full_shape():
    s = ship.default_sheet()
    assert set(s["systems"]) == set(ship.SYSTEMS)
    assert set(s["departments"]) == set(ship.DEPARTMENTS)
    assert s["scale"] == ship.DEFAULT_SCALE


def test_normalize_fills_missing_and_clamps():
    s = ship.normalize_sheet({"systems": {"engines": 99}, "scale": 40})
    assert s["systems"]["engines"] == 20      # clamped to 1..20
    assert s["systems"]["comms"] == ship.DEFAULT_SYSTEM
    assert s["scale"] == 10                    # clamped to 1..10
    assert set(s["departments"]) == set(ship.DEPARTMENTS)


def test_shields_base_is_structure_plus_security():
    s = ship.normalize_sheet({
        "systems": {"structure": 11},
        "departments": {"security": 3},
    })
    assert ship.shields_base(s) == 14
    # An unset shields_max defaults to the base.
    assert s["shields_max"] == 14
    assert s["shields_current"] == 14


def test_resistance_equals_scale():
    assert ship.resistance(ship.normalize_sheet({"scale": 5})) == 5


def test_target_number_is_system_plus_department():
    s = ship.normalize_sheet({
        "systems": {"sensors": 10},
        "departments": {"science": 3},
    })
    assert ship.target_number(s, "sensors", "science") == 13


def test_target_number_rejects_unknown_names():
    s = ship.default_sheet()
    for bad in (("bogus", "science"), ("sensors", "bogus")):
        try:
            ship.target_number(s, *bad)
        except ValueError:
            pass
        else:
            assert False, f"expected ValueError for {bad}"


def test_weapon_dice_is_rating_plus_scale():
    s = ship.normalize_sheet({"scale": 4})
    assert ship.weapon_dice(s, {"damage": 5}) == 9


def test_db_routes_starship_sheet_by_systems_key(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    eid = db.create_entity("starship", "USS Reliant", {"spaceframe": "Miranda"}, "")
    db.update_entity(eid, "USS Reliant", {
        "spaceframe": "Miranda",
        "sheet": {
            "systems": {"comms": 8, "computers": 9, "engines": 10, "sensors": 9, "structure": 11, "weapons": 10},
            "departments": {"command": 2, "conn": 3, "engineering": 2, "security": 3, "medicine": 1, "science": 2},
            "scale": 4,
        },
    }, "")
    sheet = db.get_entity(eid)["fields"]["sheet"]
    # Round-trips through the starship normalizer, not the character/5e ones.
    assert "systems" in sheet
    assert sheet["systems"]["structure"] == 11
    assert sheet["shields_max"] == 11 + 3  # Structure + Security


def test_character_sheet_still_routes_to_sta(monkeypatch, tmp_path):
    """A sheet with attributes/departments but no systems must not be captured
    by the starship branch."""
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    eid = db.create_entity("adventurer", "Sotek", {}, "")
    db.update_entity(eid, "Sotek", {
        "sheet": {"attributes": {"control": 11}, "departments": {"command": 3}},
    }, "")
    sheet = db.get_entity(eid)["fields"]["sheet"]
    assert "attributes" in sheet
    assert "systems" not in sheet
    assert sheet["attributes"]["control"] == 11
