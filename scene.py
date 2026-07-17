"""Mission Directives and scene Traits for Star Trek Adventures 2e.

**Directives** are the mission's guiding orders ("Investigate, do not engage");
**scene Traits** are environmental tags of the current situation ("Ion Storm",
"Zero Gravity"). Both are narrative modifiers the GM keeps table-visible and
factors into a Task's Difficulty. They are current-campaign state (one active
mission / scene at a time), so they live in a single ``scene.json`` dict next to
the campaign DB rather than a reference library.
"""
import json

import library

_FILE = "scene.json"


def _load() -> dict:
    try:
        data = json.loads(library.path_for(_FILE).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"directives": [], "traits": []}
    if not isinstance(data, dict):
        return {"directives": [], "traits": []}
    return {
        "directives": _clean(data.get("directives")),
        "traits": _clean(data.get("traits")),
    }


def _clean(items) -> list[str]:
    seen: dict[str, str] = {}
    for raw in (items or []):
        name = str(raw or "").strip()
        if name:
            seen.setdefault(name.lower(), name)
    return list(seen.values())


def _save(data: dict) -> None:
    path = library.path_for(_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def directives() -> list[str]:
    return _load()["directives"]


def traits() -> list[str]:
    return _load()["traits"]


def summary_lines() -> list[str]:
    """Rich-markup lines echoing the active Directives/Traits, for the conflict
    trackers to keep them table-visible during play. Empty when none are set."""
    data = _load()
    lines = []
    if data["directives"]:
        lines.append("[dim]Directives: " + ", ".join(data["directives"]) + "[/dim]")
    if data["traits"]:
        lines.append("[dim]Scene Traits: " + ", ".join(data["traits"]) + "[/dim]")
    return lines


def add_directive(name: str) -> None:
    data = _load()
    data["directives"] = _clean(data["directives"] + [name])
    _save(data)


def remove_directive(name: str) -> None:
    data = _load()
    data["directives"] = [d for d in data["directives"] if d.lower() != name.strip().lower()]
    _save(data)


def add_trait(name: str) -> None:
    data = _load()
    data["traits"] = _clean(data["traits"] + [name])
    _save(data)


def remove_trait(name: str) -> None:
    data = _load()
    data["traits"] = [t for t in data["traits"] if t.lower() != name.strip().lower()]
    _save(data)
