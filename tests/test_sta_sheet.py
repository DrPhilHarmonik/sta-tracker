import sta_sheet as sta


def test_default_sheet_has_all_attributes_and_departments():
    sheet = sta.default_sheet()
    assert set(sheet["attributes"]) == set(sta.ATTRIBUTES)
    assert set(sheet["departments"]) == set(sta.DEPARTMENTS)
    assert sheet["determination"] == 1
    assert sheet["focuses"] == []
    assert sheet["values"] == []
    assert sheet["talents"] == []


def test_default_stress_is_fitness_plus_security():
    sheet = sta.default_sheet()
    # defaults: fitness 8 + security 1 = 9
    assert sta.base_stress(sheet) == 9
    assert sheet["stress_max"] == 9
    assert sheet["stress_current"] == 9


def test_normalize_fills_missing_keys():
    sheet = sta.normalize_sheet({"attributes": {"control": 11}})
    assert sheet["attributes"]["control"] == 11
    # untouched attributes fall back to the default
    assert sheet["attributes"]["reason"] == sta.DEFAULT_ATTRIBUTE
    assert "departments" in sheet
    assert "determination" in sheet


def test_normalize_handles_none():
    sheet = sta.normalize_sheet(None)
    assert sheet == sta.default_sheet()


def test_normalize_drops_blank_list_entries():
    sheet = sta.normalize_sheet({
        "focuses": ["Astrophysics", "", "  "],
        "values": ["I will not sacrifice the crew", ""],
    })
    assert sheet["focuses"] == ["Astrophysics"]
    assert sheet["values"] == ["I will not sacrifice the crew"]


def test_normalize_clamps_out_of_range_values():
    sheet = sta.normalize_sheet({
        "determination": 99,
        "departments": {"security": 50},
        "attributes": {"fitness": 0},
    })
    assert sheet["determination"] == sta.DETERMINATION_MAX
    assert sheet["departments"]["security"] == 10
    assert sheet["attributes"]["fitness"] == 1


def test_normalize_recomputes_base_stress_from_stats():
    sheet = sta.normalize_sheet({
        "attributes": {"fitness": 10},
        "departments": {"security": 3},
    })
    # stress_max unset -> defaults to base 10 + 3 = 13
    assert sheet["stress_max"] == 13
    assert sheet["stress_current"] == 13


def test_stress_max_override_is_preserved():
    sheet = sta.normalize_sheet({
        "attributes": {"fitness": 8},
        "departments": {"security": 1},
        "stress_max": 12,   # e.g. a talent bonus
    })
    assert sheet["stress_max"] == 12


def test_stress_current_clamped_to_max():
    sheet = sta.normalize_sheet({"stress_max": 10, "stress_current": 99})
    assert sheet["stress_current"] == 10


def test_target_number_is_attribute_plus_department():
    sheet = sta.normalize_sheet({
        "attributes": {"control": 10},
        "departments": {"science": 4},
    })
    assert sta.target_number(sheet, "control", "science") == 14


def test_target_number_rejects_unknown_names():
    sheet = sta.default_sheet()
    import pytest
    with pytest.raises(ValueError):
        sta.target_number(sheet, "wisdom", "science")
    with pytest.raises(ValueError):
        sta.target_number(sheet, "control", "stealth")


def test_weapon_dice_is_rating_plus_security():
    sheet = sta.normalize_sheet({"departments": {"security": 3}})
    weapon = {"name": "Phaser Type-2", "damage": 3}
    assert sta.weapon_dice(sheet, weapon) == 6


def test_weapons_normalized():
    sheet = sta.normalize_sheet({
        "weapons": [{"name": "Unarmed Strike", "damage": 1, "qualities": "Knockdown"}],
    })
    assert sheet["weapons"][0]["name"] == "Unarmed Strike"
    assert sheet["weapons"][0]["damage"] == 1
    assert sheet["weapons"][0]["qualities"] == "Knockdown"


def test_has_focus_is_case_insensitive():
    sheet = sta.normalize_sheet({"focuses": ["Warp Field Dynamics"]})
    assert sta.has_focus(sheet, "warp field dynamics") is True
    assert sta.has_focus(sheet, "Phaser Calibration") is False


def test_roundtrips_through_dice_target_number():
    # sta_sheet feeds dice.roll_task via target_number; sanity-check the seam.
    import dice
    sheet = sta.normalize_sheet({
        "attributes": {"reason": 10},
        "departments": {"science": 3},
    })
    tn = sta.target_number(sheet, "reason", "science")

    class SeqRandom:
        def __init__(self, values):
            self._values, self._i = list(values), 0

        def randint(self, a, b):
            v = self._values[self._i]
            self._i += 1
            return v

    result = dice.roll_task(
        attribute=sheet["attributes"]["reason"],
        department=sheet["departments"]["science"],
        difficulty=1,
        focus=sta.has_focus(sheet, "Astrophysics"),
        rng=SeqRandom([5, 20]),
    )
    assert result.target_number == tn == 13
    assert result.successes == 1
    assert result.complications == 1
