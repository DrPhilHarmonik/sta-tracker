"""User-authored adversary reference library for Star Trek Adventures.

STA has no open SRD, so nothing is bundled here -- the library ships empty and
the GM fills it with their own reusable adversary stat blocks. Entries persist
to ``adversaries.json`` alongside the active campaign database (so switching
campaigns keeps the same personal codex within one config directory), and are
spawned into a campaign as ``enemy`` entities carrying a full STA sheet.

This is the STA replacement for the parent's bundled ``srd.py`` monster manual.
"""
import json
from pathlib import Path

import db
import sta_sheet as sta

# STA adversaries are graded by narrative weight rather than a Challenge Rating.
ADVERSARY_KINDS = ["Minor NPC", "Notable NPC", "Major NPC"]
DEFAULT_KIND = "Notable NPC"


def _library_path() -> Path:
    """The library lives next to the campaign DB, not inside it -- adversaries
    are reusable across campaigns within one config directory."""
    return db.db_path().parent / "adversaries.json"


def _clamp(value, low, high, fallback):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(low, min(high, value))


def default_adversary() -> dict:
    return {
        "name": "",
        "kind": DEFAULT_KIND,
        "attributes": {a: sta.DEFAULT_ATTRIBUTE for a in sta.ATTRIBUTES},
        "departments": {d: sta.DEFAULT_DEPARTMENT for d in sta.DEPARTMENTS},
        "stress_max": sta.DEFAULT_ATTRIBUTE + sta.DEFAULT_DEPARTMENT,
        "protection": 0,
        "weapons": [],
        "focuses": [],
        "traits": [],
        "notes": "",
    }


def normalize(raw: dict | None) -> dict:
    """Fill in any missing keys so callers never hit a KeyError."""
    adv = default_adversary()
    raw = raw or {}
    adv["name"] = str(raw.get("name", "") or "")
    adv["kind"] = raw.get("kind") if raw.get("kind") in ADVERSARY_KINDS else DEFAULT_KIND
    attributes = dict(raw.get("attributes") or {})
    adv["attributes"] = {
        a: _clamp(attributes.get(a, sta.DEFAULT_ATTRIBUTE), 1, 20, sta.DEFAULT_ATTRIBUTE)
        for a in sta.ATTRIBUTES
    }
    departments = dict(raw.get("departments") or {})
    adv["departments"] = {
        d: _clamp(departments.get(d, sta.DEFAULT_DEPARTMENT), 0, 10, sta.DEFAULT_DEPARTMENT)
        for d in sta.DEPARTMENTS
    }
    base = adv["attributes"]["fitness"] + adv["departments"]["security"]
    adv["stress_max"] = _clamp(raw.get("stress_max", base), 0, 99, base)
    adv["protection"] = _clamp(raw.get("protection", 0), 0, 99, 0)
    adv["weapons"] = [
        {
            "name": str(w.get("name", "")),
            "damage": _clamp(w.get("damage", 0), 0, 99, 0),
            "qualities": str(w.get("qualities", "")),
        }
        for w in (raw.get("weapons") or [])
    ]
    adv["focuses"] = [str(f) for f in (raw.get("focuses") or []) if str(f).strip()]
    adv["traits"] = [str(t) for t in (raw.get("traits") or []) if str(t).strip()]
    adv["notes"] = str(raw.get("notes", "") or "")
    return adv


def all_adversaries() -> list[dict]:
    """Every stored adversary, sorted by name. Empty when the library is new."""
    try:
        data = json.loads(_library_path().read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return sorted((normalize(a) for a in data), key=lambda a: a["name"].lower())


def _write_all(items: list[dict]) -> None:
    path = _library_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, indent=2), encoding="utf-8")


def save(adversary: dict) -> dict:
    """Insert or replace an adversary by name (case-insensitive). Returns the
    normalized record that was stored."""
    adv = normalize(adversary)
    if not adv["name"].strip():
        raise ValueError("adversary name is required")
    others = [a for a in all_adversaries() if a["name"].lower() != adv["name"].lower()]
    _write_all(others + [adv])
    return adv


def remove(name: str) -> None:
    kept = [a for a in all_adversaries() if a["name"].lower() != name.strip().lower()]
    _write_all(kept)


def search(query: str) -> list[dict]:
    """Adversaries whose name or kind contains the query (case-insensitive)."""
    q = query.strip().lower()
    items = all_adversaries()
    if not q:
        return items
    return [a for a in items if q in a["name"].lower() or q in a["kind"].lower()]


def find(name: str) -> dict | None:
    name_l = name.strip().lower()
    return next((a for a in all_adversaries() if a["name"].lower() == name_l), None)


def from_entity(entity: dict) -> dict:
    """Snapshot an enemy entity's STA sheet into a reusable library template."""
    fields = entity.get("fields", {})
    sheet = sta.normalize_sheet(fields.get("sheet", {}))
    return normalize({
        "name": entity.get("name", ""),
        "kind": fields.get("cr") or DEFAULT_KIND,
        "attributes": sheet["attributes"],
        "departments": sheet["departments"],
        "stress_max": sheet["stress_max"],
        "protection": sheet["protection"],
        "weapons": sheet["weapons"],
        "focuses": sheet["focuses"],
        "traits": sheet.get("values", []),
        "notes": sheet.get("special", ""),
    })


def build_sheet(adversary: dict) -> dict:
    """Build an STA character sheet dict from an adversary template, ready to
    store in a new enemy entity's ``fields["sheet"]``."""
    adv = normalize(adversary)
    sheet = sta.default_sheet()
    sheet["attributes"] = dict(adv["attributes"])
    sheet["departments"] = dict(adv["departments"])
    sheet["stress_max"] = adv["stress_max"]
    sheet["stress_current"] = adv["stress_max"]
    sheet["protection"] = adv["protection"]
    sheet["weapons"] = [dict(w) for w in adv["weapons"]]
    sheet["focuses"] = list(adv["focuses"])
    sheet["special"] = adv["notes"]
    return sheet
