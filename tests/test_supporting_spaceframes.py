import db
import supporting
import spaceframes
import sta_sheet as sta
import starship as ship


def _fresh(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


# -- supporting characters ----------------------------------------------------

def test_build_sheet_is_sta_shaped_with_role_and_focus():
    sheet = supporting.build_sheet("Vulcan", focus="Logic", role="Transporter Chief")
    assert set(sheet["attributes"]) == set(sta.ATTRIBUTES)
    assert sheet["species"] == "Vulcan"
    assert sheet["role"] == "Transporter Chief"
    assert sheet["focuses"] == ["Logic"]


def test_build_sheet_applies_species_bonuses():
    sheet = supporting.build_sheet("Vulcan")
    base = supporting.BASE_ATTRIBUTES
    # Vulcan grants +1 Control/Fitness/Reason.
    assert sheet["attributes"]["control"] == base["control"] + 1
    assert sheet["attributes"]["reason"] == base["reason"] + 1
    assert sheet["attributes"]["daring"] == base["daring"]


def test_build_sheet_unknown_species_uses_flat_base():
    sheet = supporting.build_sheet("Xindi")
    assert sheet["attributes"] == supporting.BASE_ATTRIBUTES


def test_build_sheet_blank_focus_leaves_none():
    sheet = supporting.build_sheet("Human", focus="  ")
    assert sheet["focuses"] == []


# -- spaceframes --------------------------------------------------------------

def test_spaceframes_ship_empty(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    assert spaceframes.all_spaceframes() == []
    assert spaceframes.find("Constitution") is None


def test_save_find_and_build_sheet(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    spaceframes.save({
        "name": "Constitution",
        "scale": 4,
        "systems": {"comms": 9, "computers": 9, "engines": 9, "sensors": 10, "structure": 9, "weapons": 9},
        "talents": ["Rugged Design"],
    })
    frame = spaceframes.find("constitution")
    assert frame is not None and frame["scale"] == 4
    sheet = spaceframes.build_sheet(frame)
    assert sheet["systems"]["sensors"] == 10
    assert sheet["scale"] == 4
    assert sheet["spaceframe"] == "Constitution"
    # Shields recomputed from Structure(9) + Security(default 1).
    assert sheet["shields_max"] == 9 + ship.DEFAULT_DEPARTMENT
    assert sheet["shields_current"] == sheet["shields_max"]


def test_save_requires_name(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    try:
        spaceframes.save({"name": "  "})
    except ValueError:
        pass
    else:
        assert False, "expected ValueError"


def test_from_entity_snapshots_ship(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    eid = db.create_entity("starship", "USS Reliant", {}, "")
    db.update_entity(eid, "USS Reliant", {
        "sheet": {
            "systems": {"comms": 8, "computers": 9, "engines": 10, "sensors": 9, "structure": 11, "weapons": 10},
            "scale": 4, "talents": ["Improved Warp Drive"],
        },
    }, "")
    frame = spaceframes.from_entity(db.get_entity(eid))
    assert frame["name"] == "USS Reliant"
    assert frame["systems"]["structure"] == 11
    assert frame["talents"] == ["Improved Warp Drive"]


def test_remove_and_isolation(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    spaceframes.save({"name": "Miranda"})
    spaceframes.save({"name": "Excelsior"})
    spaceframes.remove("Miranda")
    assert [f["name"] for f in spaceframes.all_spaceframes()] == ["Excelsior"]
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "other" / "campaign.db"))
    db.init_db()
    assert spaceframes.all_spaceframes() == []
