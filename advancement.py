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
