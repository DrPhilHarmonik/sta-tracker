"""Star Trek Adventures 2e starship sheet: data shape and derived math.

A starship is STA's second sheet type. It parallels the character sheet
(sta_sheet.py) but swaps the six Attributes for six ship **Systems** (Comms,
Computers, Engines, Sensors, Structure, Weapons) while sharing the same six
Departments, since ship Tasks roll System + Department. Durability is the
**Shields** track (Structure + Security, mirroring a character's Fitness +
Security Stress), and **Scale** drives Resistance (armour soak) and Crew
Support.

Sheets are stored as a plain JSON dict in an entity's ``fields["sheet"]``.
The DB layer routes to this normalizer when a sheet carries a ``systems`` key
(see db._normalize_sheet_any). Nothing here mutates a sheet in place.
"""

import sta_sheet as sta

SYSTEMS = ["comms", "computers", "engines", "sensors", "structure", "weapons"]

SYSTEM_LABELS = {
    "comms": "Comms",
    "computers": "Computers",
    "engines": "Engines",
    "sensors": "Sensors",
    "structure": "Structure",
    "weapons": "Weapons",
}

# Ships share the character Departments so a Task can roll System + Department.
DEPARTMENTS = sta.DEPARTMENTS
DEPARTMENT_LABELS = sta.DEPARTMENT_LABELS

DEFAULT_SYSTEM = 8
DEFAULT_DEPARTMENT = 1
DEFAULT_SCALE = 3

SHEET_ENTITY_TYPES = ("starship",)


def default_sheet() -> dict:
    base = DEFAULT_SYSTEM + DEFAULT_DEPARTMENT
    return {
        "systems": {s: DEFAULT_SYSTEM for s in SYSTEMS},
        "departments": {d: DEFAULT_DEPARTMENT for d in DEPARTMENTS},
        "scale": DEFAULT_SCALE,
        "shields_max": base,
        "shields_current": base,
        "crew_support": DEFAULT_SCALE,
        "talents": [],
        "weapons": [],
        "traits": [],
        "spaceframe": "",       # class, e.g. Constitution
        "registry": "",         # e.g. NCC-1701
        "service_year": "",
        "mission_profile": "",
        "notes": "",
    }


def _clamp(value, low, high, fallback):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(low, min(high, value))


def normalize_sheet(raw: dict | None) -> dict:
    """Fill in any missing keys so callers never hit a KeyError, including for
    sheets created before a field existed. Lenient by design so old data
    round-trips (the DB validation layer relies on this)."""
    sheet = default_sheet()
    raw = raw or {}

    systems = dict(raw.get("systems") or {})
    sheet["systems"] = {
        s: _clamp(systems.get(s, DEFAULT_SYSTEM), 1, 20, DEFAULT_SYSTEM) for s in SYSTEMS
    }
    departments = dict(raw.get("departments") or {})
    sheet["departments"] = {
        d: _clamp(departments.get(d, DEFAULT_DEPARTMENT), 0, 10, DEFAULT_DEPARTMENT) for d in DEPARTMENTS
    }
    sheet["scale"] = _clamp(raw.get("scale", DEFAULT_SCALE), 1, 10, DEFAULT_SCALE)

    base = shields_base(sheet)
    sheet["shields_max"] = _clamp(raw.get("shields_max", base), 0, 99, base)
    sheet["shields_current"] = _clamp(
        raw.get("shields_current", sheet["shields_max"]), 0, sheet["shields_max"], sheet["shields_max"]
    )
    sheet["crew_support"] = _clamp(raw.get("crew_support", sheet["scale"]), 0, 99, sheet["scale"])

    sheet["talents"] = [str(t) for t in (raw.get("talents") or []) if str(t).strip()]
    sheet["traits"] = [str(t) for t in (raw.get("traits") or []) if str(t).strip()]
    sheet["weapons"] = [
        {
            "name": str(w.get("name", "")),
            "damage": _clamp(w.get("damage", 0), 0, 99, 0),
            "qualities": str(w.get("qualities", "")),
        }
        for w in (raw.get("weapons") or [])
    ]

    for key in ("spaceframe", "registry", "service_year", "mission_profile", "notes"):
        sheet[key] = str(raw.get(key, "") or "")

    return sheet


def shields_base(sheet: dict) -> int:
    """A ship's base Shields track: Structure + Security (mirrors a character's
    Fitness + Security Stress). Talents can raise the actual max."""
    systems = sheet.get("systems") or {}
    departments = sheet.get("departments") or {}
    structure = _clamp(systems.get("structure", DEFAULT_SYSTEM), 1, 20, DEFAULT_SYSTEM)
    security = _clamp(departments.get("security", DEFAULT_DEPARTMENT), 0, 10, DEFAULT_DEPARTMENT)
    return structure + security


def resistance(sheet: dict) -> int:
    """Armour soak subtracted from incoming damage: equal to the ship's Scale."""
    return _clamp((sheet or {}).get("scale", DEFAULT_SCALE), 1, 10, DEFAULT_SCALE)


def target_number(sheet: dict, system: str, department: str) -> int:
    """The 2d20 Target Number for a ship Task: System + Department."""
    if system not in SYSTEMS:
        raise ValueError(f"Unknown system: {system!r}")
    if department not in DEPARTMENTS:
        raise ValueError(f"Unknown department: {department!r}")
    sys_val = _clamp((sheet.get("systems") or {}).get(system, DEFAULT_SYSTEM), 1, 20, DEFAULT_SYSTEM)
    dept = _clamp((sheet.get("departments") or {}).get(department, DEFAULT_DEPARTMENT), 0, 10, DEFAULT_DEPARTMENT)
    return sys_val + dept


def weapon_dice(sheet: dict, weapon: dict) -> int:
    """Challenge Dice a ship weapon rolls: its damage rating + the ship's Scale
    (bigger ships hit harder)."""
    rating = _clamp(weapon.get("damage", 0), 0, 99, 0)
    return rating + resistance(sheet)
