import recovery
import momentum
import sta_sheet as sta


def _wounded_sheet():
    sheet = sta.normalize_sheet({
        "attributes": {"fitness": 10}, "departments": {"security": 2},
        "injuries": ["Broken arm", "Concussion"],
    })
    # a full track is fitness(10)+security(2) = 12; spend some Stress
    sheet["stress_current"] = 3
    return sheet


def test_recover_stress_restores_to_max():
    sheet = recovery.recover_stress(_wounded_sheet())
    assert sheet["stress_current"] == sheet["stress_max"] == 12


def test_recover_stress_leaves_injuries_alone():
    sheet = recovery.recover_stress(_wounded_sheet())
    assert sheet["injuries"] == ["Broken arm", "Concussion"]


def test_recover_stress_is_pure():
    original = _wounded_sheet()
    recovery.recover_stress(original)
    assert original["stress_current"] == 3  # untouched


def test_clear_injury_removes_one_by_index():
    sheet = recovery.clear_injury(_wounded_sheet(), 0)
    assert sheet["injuries"] == ["Concussion"]


def test_clear_injury_out_of_range_is_noop():
    sheet = recovery.clear_injury(_wounded_sheet(), 9)
    assert sheet["injuries"] == ["Broken arm", "Concussion"]


def test_clear_all_injuries():
    sheet = recovery.clear_all_injuries(_wounded_sheet())
    assert sheet["injuries"] == []


def test_recover_sheet_stress_only_by_default():
    sheet = recovery.recover_sheet(_wounded_sheet())
    assert sheet["stress_current"] == 12
    assert sheet["injuries"] == ["Broken arm", "Concussion"]


def test_recover_sheet_can_clear_injuries_too():
    sheet = recovery.recover_sheet(_wounded_sheet(), stress=True, injuries=True)
    assert sheet["stress_current"] == 12
    assert sheet["injuries"] == []


def test_recover_sheet_can_skip_stress():
    sheet = recovery.recover_sheet(_wounded_sheet(), stress=False, injuries=True)
    assert sheet["stress_current"] == 3
    assert sheet["injuries"] == []


def test_threat_between_missions_carry_keeps_pool():
    assert momentum.threat_between_missions(7, carry=True) == 7


def test_threat_between_missions_reset_zeroes_pool():
    assert momentum.threat_between_missions(7, carry=False) == 0


def test_threat_between_missions_carry_clamps_negative():
    assert momentum.threat_between_missions(-3, carry=True) == 0
