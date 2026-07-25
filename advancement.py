"""Milestone advancement math for Star Trek Adventures 2e.

STA has no XP -- characters change through Milestones. This module holds the
pure, validated edits a Milestone can make to a character's Attribute and
Department spreads; the sheet screen and the Milestone screen apply them and log
the change. Focus/Talent/Value changes are ordinary list edits handled by the
sheet, so they aren't duplicated here.

Bounds are the STA character ranges (Attributes 7-12, Departments 0-5): the
"same limits" a starting character is built within. An edit that would break a
bound raises ValueError with a clear message rather than silently clamping, so
the GM sees why it was refused.
"""

import sta_sheet as sta

ATTRIBUTE_MIN, ATTRIBUTE_MAX = 7, 12
DEPARTMENT_MIN, DEPARTMENT_MAX = 0, 5

MILESTONE_TYPES = ["Spotlight", "Arc", "Career"]
DEFAULT_MILESTONE_TYPE = "Spotlight"


def _swap(values: dict, keys: list[str], labels: dict, up: str, down: str, low: int, high: int, noun: str) -> dict:
    if up not in keys or down not in keys:
        raise ValueError(f"Unknown {noun}")
    if up == down:
        raise ValueError(f"Choose two different {noun}s to swap")
    new = dict(values)
    if new[up] + 1 > high:
        raise ValueError(f"{labels[up]} is already at the maximum ({high})")
    if new[down] - 1 < low:
        raise ValueError(f"{labels[down]} is already at the minimum ({low})")
    new[up] += 1
    new[down] -= 1
    return new


def _increase(values: dict, keys: list[str], labels: dict, key: str, high: int, noun: str) -> dict:
    if key not in keys:
        raise ValueError(f"Unknown {noun}")
    new = dict(values)
    if new[key] + 1 > high:
        raise ValueError(f"{labels[key]} is already at the maximum ({high})")
    new[key] += 1
    return new


def swap_attributes(attributes: dict, up: str, down: str) -> dict:
    """Raise one Attribute by 1 and lower another by 1 (a Spotlight-style swap)."""
    return _swap(attributes, sta.ATTRIBUTES, sta.ATTRIBUTE_LABELS, up, down,
                 ATTRIBUTE_MIN, ATTRIBUTE_MAX, "Attribute")


def increase_attribute(attributes: dict, key: str) -> dict:
    """Raise one Attribute by 1 with no decrease (an Arc/Career improvement)."""
    return _increase(attributes, sta.ATTRIBUTES, sta.ATTRIBUTE_LABELS, key, ATTRIBUTE_MAX, "Attribute")


def swap_departments(departments: dict, up: str, down: str) -> dict:
    return _swap(departments, sta.DEPARTMENTS, sta.DEPARTMENT_LABELS, up, down,
                 DEPARTMENT_MIN, DEPARTMENT_MAX, "Department")


def increase_department(departments: dict, key: str) -> dict:
    return _increase(departments, sta.DEPARTMENTS, sta.DEPARTMENT_LABELS, key, DEPARTMENT_MAX, "Department")


# -- Reputation & Reprimands (between missions) -------------------------------
#
# Reputation is a character's standing with Starfleet Command; Reprimands are
# marks against Starfleet's ideals earned during a mission. These are tracked,
# not enforced -- the GM decides the deltas each mission and applies any
# consequences. The helpers just clamp to the tracker's bounds.

# A tool-authored standing ladder over the 0..REPUTATION_MAX range: a legible
# label for a character's current Reputation. These names and thresholds are
# this tracker's own convention (like the 0-20 bound itself), not a reproduced
# table. Ascending; reputation_standing() picks the highest threshold reached.
REPUTATION_STANDINGS = [
    (0, "Untested"),
    (4, "Trusted"),
    (8, "Respected"),
    (12, "Distinguished"),
    (16, "Decorated"),
    (20, "Legendary"),
]


def reputation_standing(reputation: int) -> str:
    """The standing label for a Reputation score (see REPUTATION_STANDINGS)."""
    reputation = int(reputation)
    label = REPUTATION_STANDINGS[0][1]
    for threshold, name in REPUTATION_STANDINGS:
        if reputation >= threshold:
            label = name
        else:
            break
    return label


def mission_reputation_change(*, succeeded: bool, reprimands_gained: int = 0) -> tuple[int, int]:
    """Propose an end-of-mission ``(reputation_delta, reprimand_delta)`` from a
    mission's outcome. Tool convention: completing a mission raises Reputation
    by 1, each Reprimand earned cancels one point of that gain, and the
    Reprimands themselves accrue. Pure arithmetic the GM can still override."""
    reprimands_gained = max(0, int(reprimands_gained))
    base = 1 if succeeded else 0
    return base - reprimands_gained, reprimands_gained


def adjust_reputation(current: int, delta: int) -> int:
    """Shift Reputation by ``delta``, bounded to 0..REPUTATION_MAX."""
    return max(0, min(sta.REPUTATION_MAX, int(current) + int(delta)))


def adjust_reprimands(current: int, delta: int) -> int:
    """Shift the Reprimand count by ``delta``, never below 0."""
    return max(0, int(current) + int(delta))


def end_of_mission(reputation: int, reprimands: int, reputation_delta: int, reprimand_delta: int) -> tuple[int, int]:
    """Apply an end-of-mission adjustment: Reputation shifts by
    ``reputation_delta`` (bounded) and any new Reprimands accrue (floored at 0).
    Returns the updated ``(reputation, reprimands)`` pair."""
    return adjust_reputation(reputation, reputation_delta), adjust_reprimands(reprimands, reprimand_delta)
