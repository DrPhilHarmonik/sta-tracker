"""The shared Task resolver (Phase 28).

`task.resolve` is the rules half of a Task roll, lifted out of the combat
tracker so the `ctrl+r` quick roll cannot disagree with it about what a bought
d20 costs or when Determination is spent. It touches no database, so everything
here is checked with a fixed dice sequence and a plain dict.
"""
import pytest

import sta_sheet as sta
import task


class FixedRng:
    """Rolls the given faces in order, then repeats the last one."""

    def __init__(self, faces):
        self.faces = list(faces)

    def randint(self, low, high):
        return self.faces.pop(0) if len(self.faces) > 1 else self.faces[0]


def a_sheet(**overrides):
    sheet = sta.normalize_sheet({})
    sheet["attributes"]["daring"] = 10
    sheet["departments"]["security"] = 4
    sheet["determination"] = overrides.pop("determination", 1)
    for key, value in overrides.items():
        sheet[key] = value
    return sheet


def pools(momentum=0, threat=0):
    return {"momentum": momentum, "threat": threat}


def resolve(sheet=None, pool=None, **kwargs):
    kwargs.setdefault("attribute", "daring")
    kwargs.setdefault("department", "security")
    return task.resolve(sheet or a_sheet(), pool or pools(), **kwargs)


def test_extra_successes_become_momentum():
    # Two dice under the target of 14: two successes against Difficulty 1.
    outcome = resolve(difficulty=1, rng=FixedRng([5, 6]))

    assert outcome.succeeded
    assert outcome.momentum_delta == outcome.result.momentum > 0
    assert f"+{outcome.result.momentum} Momentum" in " ".join(outcome.notes)


def test_a_complication_becomes_threat():
    outcome = resolve(difficulty=0, rng=FixedRng([20, 20]))

    assert outcome.result.complications == 2
    assert outcome.threat_delta >= 2
    assert "+2 Threat" in " ".join(outcome.notes)


def test_bought_dice_are_paid_from_momentum_first():
    """Two extra d20s cost 3 Momentum; with 3 in the pool nothing hits Threat."""
    outcome = resolve(pool=pools(momentum=3), bonus_dice=2, difficulty=0, rng=FixedRng([5]))

    assert outcome.momentum_spent == 3
    assert outcome.threat_credited == 0
    assert outcome.momentum_delta == -3 + outcome.result.momentum


def test_dice_bought_without_momentum_are_credited_to_threat():
    outcome = resolve(pool=pools(momentum=0), bonus_dice=2, difficulty=0, rng=FixedRng([5]))

    assert outcome.momentum_spent == 0
    assert outcome.threat_credited == 3
    assert outcome.threat_delta >= 3


def test_bought_dice_are_capped_at_three():
    """The rules cap the pool at 5 d20s. Asking for more is not an error at the
    table, it is a miscount -- so it clamps rather than raising."""
    outcome = resolve(pool=pools(momentum=99), bonus_dice=9, difficulty=0, rng=FixedRng([5]))

    assert outcome.momentum_spent == 6  # 1+2+3, the cost of three extra dice


def test_invoking_a_value_spends_one_determination():
    sheet = a_sheet(determination=2)

    outcome = resolve(sheet=sheet, invoke_value=True, difficulty=1, rng=FixedRng([19]))

    assert outcome.determination_spent == 1
    assert task.spend_determination(sheet, outcome)["determination"] == 1


def test_invoking_a_value_with_none_left_is_a_note_not_a_failure():
    """A player who misremembers their sheet should get told, not stopped."""
    sheet = a_sheet(determination=0)

    outcome = resolve(sheet=sheet, invoke_value=True, difficulty=1, rng=FixedRng([5]))

    assert outcome.determination_spent == 0
    assert "no Determination to spend" in " ".join(outcome.notes)
    assert task.spend_determination(sheet, outcome)["determination"] == 0


def test_spend_determination_leaves_the_original_sheet_alone():
    sheet = a_sheet(determination=2)

    outcome = resolve(sheet=sheet, invoke_value=True, difficulty=1, rng=FixedRng([5]))
    updated = task.spend_determination(sheet, outcome)

    assert updated is not sheet
    assert sheet["determination"] == 2


def test_apply_clamps_the_pools_to_their_bounds():
    """Momentum caps at 6; a roll that would overflow it does not bank the rest."""
    outcome = resolve(difficulty=0, rng=FixedRng([1, 1]))

    after = task.apply(outcome, pools(momentum=6, threat=0))

    assert after["momentum"] == 6
    assert after["threat"] >= 0


def test_apply_does_not_mutate_the_pools_it_was_given():
    before = pools(momentum=2, threat=1)
    outcome = resolve(difficulty=0, rng=FixedRng([5, 6]))

    task.apply(outcome, before)

    assert before == {"momentum": 2, "threat": 1}


@pytest.mark.parametrize("attribute,department", [("daring", "security"), ("reason", "science")])
def test_the_roll_reads_the_named_attribute_and_department(attribute, department):
    sheet = sta.normalize_sheet({})
    sheet["attributes"][attribute] = 12
    sheet["departments"][department] = 5

    outcome = resolve(sheet=sheet, attribute=attribute, department=department,
                      difficulty=0, rng=FixedRng([17]))

    assert outcome.result.target_number == 17
