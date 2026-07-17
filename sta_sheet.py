"""Star Trek Adventures 2e character sheet: data shape and derived math.

This is the STA replacement for the 5e ``sheet.py``. It is introduced in
parallel: ``sheet.py`` still backs the un-migrated 5e screens, and each
consumer (sheet screen, wizard, combat, export) moves onto this module in a
later roadmap phase. When the last 5e reader is gone, ``sheet.py`` is deleted.

Sheets are stored as a plain JSON dict inside an entity's ``fields["sheet"]``,
exactly like the 5e sheet, so the DB layer and the entity model are unchanged.
Nothing here mutates a sheet in place; callers read normalized copies and
write back whatever they changed.
"""

ATTRIBUTES = ["control", "daring", "fitness", "insight", "presence", "reason"]

ATTRIBUTE_LABELS = {
    "control": "Control",
    "daring": "Daring",
    "fitness": "Fitness",
    "insight": "Insight",
    "presence": "Presence",
    "reason": "Reason",
}

DEPARTMENTS = ["command", "conn", "engineering", "security", "medicine", "science"]

DEPARTMENT_LABELS = {
    "command": "Command",
    "conn": "Conn",
    "engineering": "Engineering",
    "security": "Security",
    "medicine": "Medicine",
    "science": "Science",
}

# Sensible blanks for a freshly created main character. Attributes run ~7-12,
# Departments ~0-5; these are mid-range starting points, not rules minima.
DEFAULT_ATTRIBUTE = 8
DEFAULT_DEPARTMENT = 1

DETERMINATION_MAX = 3

# Entity types that carry a full character sheet (unchanged from the parent;
# "enemy" is the STA adversary until the entity model is reworked).
SHEET_ENTITY_TYPES = ("adventurer", "enemy")


def default_sheet() -> dict:
    fitness = DEFAULT_ATTRIBUTE
    security = DEFAULT_DEPARTMENT
    base = fitness + security
    return {
        "attributes": {a: DEFAULT_ATTRIBUTE for a in ATTRIBUTES},
        "departments": {d: DEFAULT_DEPARTMENT for d in DEPARTMENTS},
        "focuses": [],
        "values": [],
        "talents": [],
        "stress_max": base,
        "stress_current": base,
        "determination": 1,
        "protection": 0,          # armour Soak, reduces incoming injury
        "weapons": [],
        "injuries": [],
        "species": "",
        "rank": "",
        "career": "",             # Cadet / Officer / Veteran (career track)
        "role": "",               # shipboard role, e.g. Chief Engineer
        "equipment": "",
        "special": "",            # freeform notes for anything unmodelled
    }


def _clamp(value, low, high, fallback):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(low, min(high, value))


def normalize_sheet(raw: dict | None) -> dict:
    """Fill in any missing keys so callers never hit a KeyError, including
    for sheets created before a field existed. Lenient by design so old data
    round-trips (the DB validation layer relies on this)."""
    sheet = default_sheet()
    raw = raw or {}
    sheet.update({k: v for k, v in raw.items() if k in sheet})

    attributes = dict(raw.get("attributes") or {})
    sheet["attributes"] = {
        a: _clamp(attributes.get(a, DEFAULT_ATTRIBUTE), 1, 20, DEFAULT_ATTRIBUTE)
        for a in ATTRIBUTES
    }
    departments = dict(raw.get("departments") or {})
    sheet["departments"] = {
        d: _clamp(departments.get(d, DEFAULT_DEPARTMENT), 0, 10, DEFAULT_DEPARTMENT)
        for d in DEPARTMENTS
    }

    sheet["focuses"] = [str(f) for f in (raw.get("focuses") or []) if str(f).strip()]
    sheet["values"] = [str(v) for v in (raw.get("values") or []) if str(v).strip()]
    sheet["talents"] = [str(t) for t in (raw.get("talents") or []) if str(t).strip()]

    base = base_stress(sheet)
    sheet["stress_max"] = _clamp(raw.get("stress_max", base), 0, 99, base)
    sheet["stress_current"] = _clamp(
        raw.get("stress_current", sheet["stress_max"]), 0, sheet["stress_max"], sheet["stress_max"]
    )
    sheet["determination"] = _clamp(raw.get("determination", 1), 0, DETERMINATION_MAX, 1)
    sheet["protection"] = _clamp(raw.get("protection", 0), 0, 99, 0)

    sheet["weapons"] = [
        {
            "name": str(w.get("name", "")),
            "damage": _clamp(w.get("damage", 0), 0, 99, 0),
            "qualities": str(w.get("qualities", "")),
        }
        for w in (raw.get("weapons") or [])
    ]
    sheet["injuries"] = [str(i) for i in (raw.get("injuries") or []) if str(i).strip()]

    for key in ("species", "rank", "career", "role", "equipment", "special"):
        sheet[key] = str(raw.get(key, "") or "")

    return sheet


def adjust_determination(current: int, delta: int) -> int:
    """Change a character's Determination, clamped to 0..DETERMINATION_MAX.

    Spend (a negative delta) by invoking a Value; regain (a positive delta) by
    having a Value challenged. Pure math -- callers persist the result on the
    sheet."""
    return _clamp(int(current) + int(delta), 0, DETERMINATION_MAX, current)


def base_stress(sheet: dict) -> int:
    """A character's base Stress track: Fitness + Security.

    Talents/equipment can raise the actual max; that adjusted value lives in
    ``stress_max`` (which defaults to this base when unset)."""
    attributes = sheet.get("attributes") or {}
    departments = sheet.get("departments") or {}
    fitness = _clamp(attributes.get("fitness", DEFAULT_ATTRIBUTE), 1, 20, DEFAULT_ATTRIBUTE)
    security = _clamp(departments.get("security", DEFAULT_DEPARTMENT), 0, 10, DEFAULT_DEPARTMENT)
    return fitness + security


def target_number(sheet: dict, attribute: str, department: str) -> int:
    """The 2d20 Target Number for a task: Attribute + Department."""
    if attribute not in ATTRIBUTES:
        raise ValueError(f"Unknown attribute: {attribute!r}")
    if department not in DEPARTMENTS:
        raise ValueError(f"Unknown department: {department!r}")
    attr = _clamp((sheet.get("attributes") or {}).get(attribute, DEFAULT_ATTRIBUTE), 1, 20, DEFAULT_ATTRIBUTE)
    dept = _clamp((sheet.get("departments") or {}).get(department, DEFAULT_DEPARTMENT), 0, 10, DEFAULT_DEPARTMENT)
    return attr + dept


def weapon_dice(sheet: dict, weapon: dict) -> int:
    """Challenge Dice a weapon rolls: its damage rating + the wielder's
    Security department."""
    departments = sheet.get("departments") or {}
    security = _clamp(departments.get("security", DEFAULT_DEPARTMENT), 0, 10, DEFAULT_DEPARTMENT)
    rating = _clamp(weapon.get("damage", 0), 0, 99, 0)
    return rating + security


def has_focus(sheet: dict, focus: str) -> bool:
    """Case-insensitive check for an applicable Focus (drives the 2d20
    critical range in dice.roll_task)."""
    needle = str(focus).strip().casefold()
    return any(f.casefold() == needle for f in sheet.get("focuses", []))
