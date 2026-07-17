"""Extended Task tracker for Star Trek Adventures 2e.

An Extended Task is a job too big for a single roll -- repairing a warp core,
decrypting a databank. It has a **Work** total the crew whittle down over
several attempts, a **Magnitude** (its scope), a base **Difficulty**, and a
**Resistance** that adds to the Difficulty of every attempt. Each successful
attempt reduces Work (the GM enters the Work done, usually from a Challenge-Dice
roll); the task completes when Work reaches its total.

Tasks persist to ``extended_tasks.json`` next to the campaign DB (see
library.py) and are managed from the Scene screen. This module is pure logic +
persistence.
"""
import library

_FILE = "extended_tasks.json"


def _clamp(value, low, high, fallback):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(low, min(high, value))


def default_task() -> dict:
    return {
        "name": "",
        "magnitude": 1,
        "difficulty": 1,
        "resistance": 0,
        "work_total": 5,
        "work_done": 0,
        "notes": "",
    }


def normalize(raw: dict | None) -> dict:
    task = default_task()
    raw = raw or {}
    task["name"] = str(raw.get("name", "") or "").strip()
    task["magnitude"] = _clamp(raw.get("magnitude", 1), 1, 99, 1)
    task["difficulty"] = _clamp(raw.get("difficulty", 1), 0, 20, 1)
    task["resistance"] = _clamp(raw.get("resistance", 0), 0, 20, 0)
    task["work_total"] = _clamp(raw.get("work_total", 5), 1, 999, 5)
    task["work_done"] = _clamp(raw.get("work_done", 0), 0, task["work_total"], 0)
    task["notes"] = str(raw.get("notes", "") or "")
    return task


def effective_difficulty(task: dict) -> int:
    """Difficulty of a single attempt: base Difficulty + Resistance."""
    return int(task.get("difficulty", 0)) + int(task.get("resistance", 0))


def is_complete(task: dict) -> bool:
    return task.get("work_done", 0) >= task.get("work_total", 0)


def all_tasks() -> list[dict]:
    seen: dict[str, dict] = {}
    for raw in library.load(_FILE):
        task = normalize(raw)
        if task["name"]:
            seen[task["name"].lower()] = task
    return sorted(seen.values(), key=lambda t: t["name"].lower())


def find(name: str) -> dict | None:
    name_l = name.strip().lower()
    return next((t for t in all_tasks() if t["name"].lower() == name_l), None)


def save(task: dict) -> dict:
    """Insert or update an Extended Task by name. Blank name is a no-op."""
    task = normalize(task)
    if not task["name"]:
        return task
    others = [t for t in all_tasks() if t["name"].lower() != task["name"].lower()]
    library.write(_FILE, others + [task])
    return task


def add_work(name: str, amount: int) -> dict | None:
    """Reduce the remaining Work (increase work_done), capped at the total.
    Returns the updated task, or None if not found."""
    task = find(name)
    if task is None:
        return None
    task["work_done"] = min(task["work_total"], max(0, task["work_done"] + int(amount)))
    return save(task)


def remove(name: str) -> None:
    kept = [t for t in all_tasks() if t["name"].lower() != name.strip().lower()]
    library.write(_FILE, kept)
