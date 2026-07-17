"""User-authored spaceframe (starship class) library for Star Trek Adventures.

A spaceframe is a reusable starship template -- a Constitution class, a Bird-of-
Prey. STA ships no stat blocks, so this library ships **empty** and the GM fills
it with their own frames (Systems spread, Scale, Talents, Traits). Frames
persist to ``spaceframes.json`` next to the campaign DB (see library.py) and are
either snapshotted from an existing starship or spawned into a campaign as a new
starship entity carrying a built ship sheet.

Mirrors the adversary library (adversaries.py); the ship parallel.
"""
import library
import starship as ship


def _clamp(value, low, high, fallback):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(low, min(high, value))


def default_spaceframe() -> dict:
    return {
        "name": "",
        "scale": ship.DEFAULT_SCALE,
        "systems": {s: ship.DEFAULT_SYSTEM for s in ship.SYSTEMS},
        "talents": [],
        "traits": [],
        "notes": "",
    }


def normalize(raw: dict | None) -> dict:
    frame = default_spaceframe()
    raw = raw or {}
    frame["name"] = str(raw.get("name", "") or "").strip()
    frame["scale"] = _clamp(raw.get("scale", ship.DEFAULT_SCALE), 1, 10, ship.DEFAULT_SCALE)
    systems = dict(raw.get("systems") or {})
    frame["systems"] = {
        s: _clamp(systems.get(s, ship.DEFAULT_SYSTEM), 1, 20, ship.DEFAULT_SYSTEM) for s in ship.SYSTEMS
    }
    frame["talents"] = [str(t) for t in (raw.get("talents") or []) if str(t).strip()]
    frame["traits"] = [str(t) for t in (raw.get("traits") or []) if str(t).strip()]
    frame["notes"] = str(raw.get("notes", "") or "")
    return frame


def all_spaceframes() -> list[dict]:
    seen: dict[str, dict] = {}
    for raw in library.load("spaceframes.json"):
        frame = normalize(raw)
        if frame["name"]:
            seen[frame["name"].lower()] = frame
    return sorted(seen.values(), key=lambda f: f["name"].lower())


def find(name: str) -> dict | None:
    name_l = name.strip().lower()
    return next((f for f in all_spaceframes() if f["name"].lower() == name_l), None)


def search(query: str) -> list[dict]:
    q = query.strip().lower()
    items = all_spaceframes()
    return items if not q else [f for f in items if q in f["name"].lower()]


def save(frame: dict) -> dict:
    frame = normalize(frame)
    if not frame["name"]:
        raise ValueError("spaceframe name is required")
    others = [f for f in all_spaceframes() if f["name"].lower() != frame["name"].lower()]
    library.write("spaceframes.json", others + [frame])
    return frame


def remove(name: str) -> None:
    kept = [f for f in all_spaceframes() if f["name"].lower() != name.strip().lower()]
    library.write("spaceframes.json", kept)


def from_entity(entity: dict) -> dict:
    """Snapshot a starship entity's sheet into a reusable spaceframe template.
    Uses the ship's own name as the frame name (the GM can rename)."""
    sheet = ship.normalize_sheet(entity.get("fields", {}).get("sheet", {}))
    return normalize({
        "name": entity.get("name", ""),
        "scale": sheet["scale"],
        "systems": sheet["systems"],
        "talents": sheet["talents"],
        "traits": sheet["traits"],
        "notes": sheet.get("notes", ""),
    })


def build_sheet(frame: dict) -> dict:
    """Build a starship sheet from a spaceframe template, ready to store in a new
    starship entity's ``fields["sheet"]``. Departments are left at defaults --
    they come from the ship's crew, not the frame."""
    frame = normalize(frame)
    sheet = ship.default_sheet()
    sheet["systems"] = dict(frame["systems"])
    sheet["scale"] = frame["scale"]
    sheet["talents"] = list(frame["talents"])
    sheet["traits"] = list(frame["traits"])
    sheet["spaceframe"] = frame["name"]
    sheet["notes"] = frame["notes"]
    # Recompute the Shields track for the new Systems (Structure + Security).
    base = ship.shields_base(sheet)
    sheet["shields_max"] = base
    sheet["shields_current"] = base
    return sheet
