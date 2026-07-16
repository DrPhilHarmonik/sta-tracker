import random

import dice


class SeqRandom:
    """Minimal rng stand-in: randint() returns queued values in order,
    letting a test pin exact d20/d6 faces regardless of range."""

    def __init__(self, values):
        self._values = list(values)
        self._i = 0

    def randint(self, a, b):
        value = self._values[self._i]
        self._i += 1
        return value


# -- roll_task ----------------------------------------------------------------

def test_task_counts_successes_at_or_under_target_number():
    # TN = 9 + 3 = 12. Faces 5 and 14 -> one success (5<=12), one miss.
    rng = SeqRandom([5, 14])
    result = dice.roll_task(attribute=9, department=3, difficulty=1, rng=rng)
    assert result.target_number == 12
    assert result.successes == 1
    assert result.succeeded is True
    assert result.momentum == 0
    assert result.complications == 0


def test_task_momentum_is_successes_beyond_difficulty():
    # Both dice under TN -> 2 successes, Difficulty 1 -> 1 Momentum.
    rng = SeqRandom([4, 6])
    result = dice.roll_task(attribute=8, department=4, difficulty=1, rng=rng)
    assert result.successes == 2
    assert result.momentum == 1


def test_task_failure_yields_no_momentum():
    # Both dice over TN=6 -> 0 successes vs Difficulty 1.
    rng = SeqRandom([15, 20])
    result = dice.roll_task(attribute=3, department=3, difficulty=1, rng=rng)
    assert result.successes == 0
    assert result.succeeded is False
    assert result.momentum == 0


def test_natural_one_is_a_critical_worth_two_successes():
    # A 1 always scores 2, even without a Focus. Second die (13) misses TN=10.
    rng = SeqRandom([1, 13])
    result = dice.roll_task(attribute=7, department=3, difficulty=1, focus=False, rng=rng)
    assert result.successes == 2
    assert result.momentum == 1


def test_focus_doubles_dice_at_or_under_department():
    # TN=12, department=3. Face 2 (<=3) with Focus -> 2 successes; face 10 -> 1.
    rng = SeqRandom([2, 10])
    result = dice.roll_task(attribute=9, department=3, difficulty=1, focus=True, rng=rng)
    assert result.successes == 3


def test_focus_does_not_double_above_department():
    # Face 5 is <= TN but > department(3): with Focus it is still 1 success.
    rng = SeqRandom([5, 18])
    result = dice.roll_task(attribute=9, department=3, difficulty=1, focus=True, rng=rng)
    assert result.successes == 1


def test_complication_on_natural_twenty():
    rng = SeqRandom([20, 8])
    result = dice.roll_task(attribute=6, department=4, difficulty=1, rng=rng)
    assert result.complications == 1
    # The 8 still succeeds; a complication can accompany a success.
    assert result.succeeded is True


def test_widened_complication_range_catches_nineteen():
    rng = SeqRandom([19, 8])
    result = dice.roll_task(attribute=6, department=4, difficulty=1,
                            complication_range=2, rng=rng)
    assert result.complications == 1


def test_task_pool_size_clamps_to_max():
    rng = SeqRandom([1, 1, 1, 1, 1, 1, 1])
    result = dice.roll_task(attribute=10, department=2, difficulty=1, dice=9, rng=rng)
    assert len(result.rolls) == dice.MAX_TASK_DICE


def test_extra_dice_are_rolled():
    rng = SeqRandom([5, 5, 5])
    result = dice.roll_task(attribute=8, department=3, difficulty=1, dice=3, rng=rng)
    assert len(result.rolls) == 3
    assert result.successes == 3


# -- roll_challenge -----------------------------------------------------------

def test_challenge_face_values_map_to_successes():
    # 1->1, 2->2, 3->0, 4->0, 5->1, 6->1  == 5 successes total
    rng = SeqRandom([1, 2, 3, 4, 5, 6])
    result = dice.roll_challenge(6, rng=rng)
    assert result.total == 5


def test_challenge_effects_count_only_fives_and_sixes():
    rng = SeqRandom([1, 2, 3, 4, 5, 6])
    result = dice.roll_challenge(6, rng=rng)
    assert result.effects == 2


def test_challenge_zero_dice_is_empty():
    result = dice.roll_challenge(0)
    assert result.total == 0
    assert result.effects == 0
    assert result.rolls == []


def test_challenge_uses_seeded_rng_reproducibly():
    a = dice.roll_challenge(5, rng=random.Random(42))
    b = dice.roll_challenge(5, rng=random.Random(42))
    assert a.rolls == b.rolls
    assert a.total == b.total
