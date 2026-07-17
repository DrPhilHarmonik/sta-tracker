"""User-authored Talent reference library for Star Trek Adventures.

STA ships no open Talent text, so this library ships **empty** and the GM fills
it with their own Talents (name + a short description they write). Entries
persist to ``talents.json`` next to the campaign DB (see library.py) and feed
autocomplete on the character/starship sheets and the creation wizard.

A Talent is ``{"name": str, "description": str}``.
"""
import library

_FILE = "talents.json"


def normalize(raw: dict | str) -> dict:
    if isinstance(raw, str):
        return {"name": raw.strip(), "description": ""}
    return {
        "name": str(raw.get("name", "") or "").strip(),
        "description": str(raw.get("description", "") or ""),
    }


def all_talents() -> list[dict]:
    """Every stored Talent, sorted by name. Empty when the library is new."""
    seen: dict[str, dict] = {}
    for raw in library.load(_FILE):
        talent = normalize(raw)
        if talent["name"]:
            seen[talent["name"].lower()] = talent
    return sorted(seen.values(), key=lambda t: t["name"].lower())


def names() -> list[str]:
    return [t["name"] for t in all_talents()]


def find(name: str) -> dict | None:
    name_l = name.strip().lower()
    return next((t for t in all_talents() if t["name"].lower() == name_l), None)


def search(query: str) -> list[dict]:
    q = query.strip().lower()
    items = all_talents()
    if not q:
        return items
    return [t for t in items if q in t["name"].lower() or q in t["description"].lower()]


def save(name: str, description: str = "") -> dict:
    """Insert or update a Talent by name (case-insensitive). A blank name is a
    no-op so 'remember what I just typed' hooks can call it unconditionally."""
    talent = normalize({"name": name, "description": description})
    if not talent["name"]:
        return talent
    others = [t for t in all_talents() if t["name"].lower() != talent["name"].lower()]
    library.write(_FILE, others + [talent])
    return talent


def remove(name: str) -> None:
    kept = [t for t in all_talents() if t["name"].lower() != name.strip().lower()]
    library.write(_FILE, kept)
