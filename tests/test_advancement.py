import pytest

import advancement as adv
import sta_sheet as sta


def _attrs(**over):
    base = {a: 9 for a in sta.ATTRIBUTES}
    base.update(over)
    return base


def _depts(**over):
    base = {d: 2 for d in sta.DEPARTMENTS}
    base.update(over)
    return base


# -- attribute swaps / increases ----------------------------------------------

def test_swap_attributes_moves_one_point():
    result = adv.swap_attributes(_attrs(control=10, daring=8), "control", "daring")
    assert result["control"] == 11
    assert result["daring"] == 7
    # total is conserved
    assert sum(result.values()) == sum(_attrs(control=10, daring=8).values())


def test_swap_attributes_does_not_mutate_input():
    src = _attrs(control=10, daring=8)
    adv.swap_attributes(src, "control", "daring")
    assert src["control"] == 10 and src["daring"] == 8


def test_swap_attributes_rejects_same_key():
    with pytest.raises(ValueError, match="two different"):
        adv.swap_attributes(_attrs(), "control", "control")


def test_swap_attributes_respects_ceiling():
    with pytest.raises(ValueError, match="maximum"):
        adv.swap_attributes(_attrs(control=12, daring=9), "control", "daring")


def test_swap_attributes_respects_floor():
    with pytest.raises(ValueError, match="minimum"):
        adv.swap_attributes(_attrs(control=9, daring=7), "control", "daring")


def test_increase_attribute():
    result = adv.increase_attribute(_attrs(reason=10), "reason")
    assert result["reason"] == 11


def test_increase_attribute_respects_ceiling():
    with pytest.raises(ValueError, match="maximum"):
        adv.increase_attribute(_attrs(reason=12), "reason")


# -- department swaps / increases ---------------------------------------------

def test_swap_departments_moves_one_point():
    result = adv.swap_departments(_depts(command=3, conn=1), "command", "conn")
    assert result["command"] == 4
    assert result["conn"] == 0


def test_swap_departments_respects_floor():
    with pytest.raises(ValueError, match="minimum"):
        adv.swap_departments(_depts(command=3, conn=0), "command", "conn")


def test_increase_department_respects_ceiling():
    with pytest.raises(ValueError, match="maximum"):
        adv.increase_department(_depts(security=5), "security")


# -- sheet shape --------------------------------------------------------------

def test_sheet_has_milestones_and_normalizes():
    sheet = sta.normalize_sheet({"milestones": [
        {"type": "Arc", "date": "2401-05-02", "note": "Reason +1"},
        {"bogus": True},  # coerced to blanks, kept
        "not a dict",     # dropped
    ]})
    assert sheet["milestones"][0]["type"] == "Arc"
    assert sheet["milestones"][0]["note"] == "Reason +1"
    assert sheet["milestones"][1] == {"type": "", "date": "", "note": ""}
    assert len(sheet["milestones"]) == 2


def test_default_sheet_milestones_empty():
    assert sta.default_sheet()["milestones"] == []


# -- reputation & reprimands --------------------------------------------------

def test_default_sheet_reputation_and_reprimands():
    sheet = sta.default_sheet()
    assert sheet["reputation"] == 1
    assert sheet["reprimands"] == 0


def test_reputation_normalizes_within_bounds():
    assert sta.normalize_sheet({"reputation": 999})["reputation"] == sta.REPUTATION_MAX
    assert sta.normalize_sheet({"reputation": -5})["reputation"] == 0
    assert sta.normalize_sheet({"reprimands": -3})["reprimands"] == 0
    # garbage falls back to the default
    assert sta.normalize_sheet({"reputation": "nope"})["reputation"] == 1


def test_adjust_reputation_clamps_to_bounds():
    assert adv.adjust_reputation(5, 3) == 8
    assert adv.adjust_reputation(0, -2) == 0
    assert adv.adjust_reputation(sta.REPUTATION_MAX, 5) == sta.REPUTATION_MAX


def test_adjust_reprimands_floors_at_zero():
    assert adv.adjust_reprimands(2, 1) == 3
    assert adv.adjust_reprimands(1, -5) == 0


def test_end_of_mission_applies_both_deltas():
    assert adv.end_of_mission(4, 1, 2, 1) == (6, 2)
    # Reputation can fall, Reprimands never go negative
    assert adv.end_of_mission(1, 0, -5, -5) == (0, 0)
