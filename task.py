"""Resolving a Task roll: the dice, and everything that follows from them.

`dice.roll_task` answers "how many successes"; this answers "and what does that
do to the table". Extra successes become Momentum, Complications become Threat,
bought d20s are paid out of the pools (Momentum first, the shortfall credited to
Threat), and invoking a Value spends a point of Determination.

Kept apart from the screens because two of them now roll Tasks -- the combat
tracker and the `ctrl+r` quick roll -- and rules that live in a screen are rules
the other screen does not have. Nothing here touches the database: the caller
applies the deltas, which also lets tests read the consequences of a roll
without a campaign on disk.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

import dice
import momentum as momentum_mod
import sta_sheet as sta


@dataclass
class TaskOutcome:
    """What a Task roll did, and what the caller now has to write down."""

    result: dice.TaskResult
    momentum_delta: int = 0          # from extra successes
    threat_delta: int = 0            # from Complications, plus bought dice on credit
    determination_spent: int = 0     # 1 when a Value was successfully invoked
    momentum_spent: int = 0          # paid for bought d20s
    threat_credited: int = 0         # the unpaid remainder of bought d20s
    notes: list[str] = field(default_factory=list)

    @property
    def succeeded(self) -> bool:
        return self.result.succeeded


def resolve(
    sheet: dict,
    pools: dict,
    *,
    attribute: str,
    department: str,
    difficulty: int = 2,
    focus: bool = False,
    bonus_dice: int = 0,
    complication_range: int = 1,
    invoke_value: bool = False,
    rng=None,
) -> TaskOutcome:
    """Roll a Task and work out its consequences.

    `sheet` is a normalized character sheet; `pools` the campaign's current
    Momentum/Threat. Returns the outcome -- the caller writes the deltas back,
    because a roll in the combat tracker also logs and persists, and a quick
    roll does not.

    Invoking a Value only spends Determination when there is some to spend;
    asking for it with an empty pool is a no-op with a note, not an error, since
    the player has usually just misremembered their sheet.
    """
    bonus_dice = max(0, min(int(bonus_dice), 3))
    spend = 1 if invoke_value and sheet["determination"] >= 1 else 0

    result = dice.roll_task(
        attribute=sheet["attributes"][attribute],
        department=sheet["departments"][department],
        difficulty=max(0, int(difficulty)),
        focus=bool(focus),
        dice=2 + bonus_dice,
        complication_range=max(1, int(complication_range)),
        determination=spend,
        rng=rng if rng is not None else random,
    )

    outcome = TaskOutcome(result=result, determination_spent=spend)

    if bonus_dice > 0:
        _, _, paid, credited = momentum_mod.pay_for_bonus_dice(
            pools["momentum"], pools["threat"], bonus_dice
        )
        outcome.momentum_spent = paid
        outcome.threat_credited = credited
        outcome.momentum_delta -= paid
        outcome.threat_delta += credited
        cost_bits = [b for b in (f"spent {paid} Momentum" if paid else "",
                                 f"+{credited} Threat" if credited else "") if b]
        outcome.notes.append(f"bought {bonus_dice} d20 ({', '.join(cost_bits) or 'free'})")

    if invoke_value and not spend:
        outcome.notes.append("no Determination to spend")

    if result.momentum > 0:
        outcome.momentum_delta += result.momentum
        outcome.notes.append(f"+{result.momentum} Momentum")

    if result.complications > 0:
        outcome.threat_delta += result.complications
        outcome.notes.append(f"+{result.complications} Threat")

    return outcome


def apply(outcome: TaskOutcome, pools: dict) -> dict:
    """The pools after `outcome`, clamped to their rules bounds.

    Returned rather than written so the caller decides when it hits the
    database -- and so the arithmetic can be checked without one.
    """
    return {
        "momentum": momentum_mod.clamp_momentum(pools["momentum"] + outcome.momentum_delta),
        "threat": momentum_mod.clamp_threat(pools["threat"] + outcome.threat_delta),
    }


def spend_determination(sheet: dict, outcome: TaskOutcome) -> dict:
    """The sheet's new Determination after any invoked Value."""
    if not outcome.determination_spent:
        return sheet
    sheet = dict(sheet)
    sheet["determination"] = sta.adjust_determination(
        sheet["determination"], -outcome.determination_spent
    )
    return sheet
