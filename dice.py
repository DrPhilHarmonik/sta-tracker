"""Dice notation parsing/rolling for the STA fork.

Contains three layers:

- A generic dice-notation parser (``roll``) that is system-agnostic and stays.
- The Star Trek Adventures 2d20 engine (``roll_task``) and Challenge Dice
  roller (``roll_challenge``) -- the mechanical heart of the fork.
- Transitional 5e stat-aware helpers (``roll_d20``, ``roll_ability_check``,
  ...) still consumed by the combat/roll screens until those screens are
  rewritten for STA (roadmap Phases 4/7). They will be removed then.

Every public roll function accepts an optional ``rng`` (defaults to the
``random`` module) so tests can pass a seeded ``random.Random`` instance.
"""
import random
import re
from dataclasses import dataclass, field

import sheet as shm

DICE_TERM_RE = re.compile(r"^(\d*)d(\d+)(?:(kh|kl)(\d+))?$", re.IGNORECASE)


@dataclass
class RollResult:
    total: int
    detail: str
    rolls: list[int] = field(default_factory=list)


def _split_terms(expression: str) -> list[str]:
    expression = expression.replace(" ", "")
    if not expression:
        raise ValueError("Empty dice expression")
    if expression[0] not in "+-":
        expression = "+" + expression
    return re.findall(r"[+-][^+-]+", expression)


def _roll_dice_term(count: int, sides: int, keep_mode: str | None, keep_count: int | None, rng) -> tuple[int, str, list[int]]:
    if count < 1 or sides < 1:
        raise ValueError("Dice count and sides must be positive")
    rolls = [rng.randint(1, sides) for _ in range(count)]
    kept = rolls
    if keep_mode and keep_count:
        kept = sorted(rolls, reverse=(keep_mode == "kh"))[:keep_count]
    label = f"{count}d{sides}"
    if keep_mode:
        label += f"{keep_mode}{keep_count}"
    detail = f"{label}({','.join(str(r) for r in rolls)})"
    return sum(kept), detail, kept


def roll(expression: str, rng=random) -> RollResult:
    """Roll a dice expression like ``2d6+3`` or ``4d6kh3``."""
    terms = _split_terms(expression)
    total = 0
    parts = []
    all_rolls: list[int] = []

    for index, term in enumerate(terms):
        sign = -1 if term[0] == "-" else 1
        body = term[1:]
        match = DICE_TERM_RE.match(body)
        if match:
            count_str, sides_str, keep_mode, keep_count_str = match.groups()
            count = int(count_str) if count_str else 1
            sides = int(sides_str)
            keep_mode = keep_mode.lower() if keep_mode else None
            keep_count = int(keep_count_str) if keep_count_str else None
            value, detail, kept = _roll_dice_term(count, sides, keep_mode, keep_count, rng)
            all_rolls.extend(kept)
        else:
            try:
                value = int(body)
            except ValueError:
                raise ValueError(f"Invalid dice term: {term}")
            detail = str(value)

        total += sign * value
        if index == 0:
            parts.append(detail if sign > 0 else f"-{detail}")
        else:
            parts.append(f"{'+' if sign > 0 else '-'} {detail}")

    return RollResult(total=total, detail=" ".join(parts) + f" = {total}", rolls=all_rolls)


def roll_d20(modifier: int = 0, advantage: bool = False, disadvantage: bool = False, rng=random) -> RollResult:
    """Roll a single d20, or 2d20 keep best/worst for advantage/disadvantage."""
    if advantage and disadvantage:
        advantage = disadvantage = False

    if advantage or disadvantage:
        a, b = rng.randint(1, 20), rng.randint(1, 20)
        die = max(a, b) if advantage else min(a, b)
        mode = "adv" if advantage else "dis"
        rolls = [a, b]
        detail = f"d20({a},{b} {mode})"
    else:
        die = rng.randint(1, 20)
        rolls = [die]
        detail = f"d20({die})"

    total = die + modifier
    if modifier:
        detail += f" {'+' if modifier >= 0 else '-'} {abs(modifier)}"
    detail += f" = {total}"
    return RollResult(total=total, detail=detail, rolls=rolls)


def roll_ability_check(sheet: dict, ability: str, advantage: bool = False, disadvantage: bool = False, rng=random) -> RollResult:
    mod = shm.ability_modifier(sheet["abilities"][ability])
    return roll_d20(mod, advantage, disadvantage, rng)


def roll_saving_throw(sheet: dict, entity_type: str, ability: str, advantage: bool = False, disadvantage: bool = False, rng=random) -> RollResult:
    pb = shm.proficiency_bonus(entity_type, sheet)
    bonus = shm.saving_throw_bonus(sheet, ability, pb)
    return roll_d20(bonus, advantage, disadvantage, rng)


def roll_skill_check(sheet: dict, entity_type: str, skill: str, advantage: bool = False, disadvantage: bool = False, rng=random) -> RollResult:
    pb = shm.proficiency_bonus(entity_type, sheet)
    bonus = shm.skill_bonus(sheet, skill, pb)
    return roll_d20(bonus, advantage, disadvantage, rng)


def roll_attack(attack: dict, advantage: bool = False, disadvantage: bool = False, rng=random) -> RollResult:
    bonus = int(attack.get("bonus", 0) or 0)
    return roll_d20(bonus, advantage, disadvantage, rng)


def roll_damage(attack: dict, rng=random) -> RollResult:
    return roll(attack.get("damage") or "0", rng=rng)


# ---------------------------------------------------------------------------
# Star Trek Adventures 2e engine
#
# Task resolution: roll a pool of d20s against a Target Number (TN) equal to
# the acting Attribute + Department. Each die at or under the TN scores a
# success. A natural 1 is always a critical (2 successes); with an applicable
# Focus, any die at or under the Department rating also scores 2. A die in the
# complication range (a natural 20 by default) generates a Complication.
# Successes beyond the Difficulty become Momentum.
# ---------------------------------------------------------------------------

MAX_TASK_DICE = 5  # 2 base + up to 3 bought with Momentum/Threat


@dataclass
class TaskResult:
    successes: int
    complications: int
    succeeded: bool
    momentum: int
    target_number: int
    rolls: list[int] = field(default_factory=list)
    detail: str = ""


def _die_successes(value: int, target_number: int, department: int, focus: bool) -> int:
    """Successes a single d20 face contributes under STA task rules."""
    if value == 1 or (focus and value <= department):
        return 2
    if value <= target_number:
        return 1
    return 0


def roll_task(
    attribute: int,
    department: int,
    difficulty: int = 1,
    focus: bool = False,
    dice: int = 2,
    complication_range: int = 1,
    rng=random,
) -> TaskResult:
    """Resolve a 2d20 task.

    ``dice`` is the total d20 pool (2 base, clamped to ``MAX_TASK_DICE``).
    ``complication_range`` is how many high faces trigger a Complication
    (1 -> only a 20; 2 -> 19-20; ...).
    """
    dice = max(1, min(int(dice), MAX_TASK_DICE))
    target_number = int(attribute) + int(department)
    complication_floor = 21 - max(1, int(complication_range))

    rolls = [rng.randint(1, 20) for _ in range(dice)]
    successes = sum(_die_successes(v, target_number, department, focus) for v in rolls)
    complications = sum(1 for v in rolls if v >= complication_floor)

    succeeded = successes >= difficulty
    momentum = successes - difficulty if succeeded else 0

    outcome = "SUCCESS" if succeeded else "FAILURE"
    detail = (
        f"TN {target_number} | {rolls} -> {successes} success"
        f"{'es' if successes != 1 else ''} vs Diff {difficulty}: {outcome}"
    )
    if momentum:
        detail += f" (+{momentum} Momentum)"
    if complications:
        detail += f" [{complications} Complication{'s' if complications != 1 else ''}]"

    return TaskResult(
        successes=successes,
        complications=complications,
        succeeded=succeeded,
        momentum=momentum,
        target_number=target_number,
        rolls=rolls,
        detail=detail,
    )


# Challenge Dice ([CD]) are d6s read by icon, not pip value:
#   1 -> 1 success                5 -> 1 success + 1 Effect
#   2 -> 2 successes              6 -> 1 success + 1 Effect
#   3, 4 -> 0 successes
_CHALLENGE_FACES = {1: (1, False), 2: (2, False), 3: (0, False),
                    4: (0, False), 5: (1, True), 6: (1, True)}


@dataclass
class ChallengeResult:
    total: int          # successes summed (e.g. damage dealt)
    effects: int        # number of Effect icons rolled (5s and 6s)
    rolls: list[int] = field(default_factory=list)
    detail: str = ""


def roll_challenge(count: int, rng=random) -> ChallengeResult:
    """Roll ``count`` Challenge Dice, summing successes and counting Effects."""
    count = max(0, int(count))
    rolls = [rng.randint(1, 6) for _ in range(count)]
    total = 0
    effects = 0
    for value in rolls:
        successes, is_effect = _CHALLENGE_FACES[value]
        total += successes
        effects += 1 if is_effect else 0
    detail = f"{count}[CD] {rolls} -> {total} success{'es' if total != 1 else ''}"
    if effects:
        detail += f", {effects} Effect{'s' if effects != 1 else ''}"
    return ChallengeResult(total=total, effects=effects, rolls=rolls, detail=detail)
