"""Shared JSON persistence for the user-authored reference libraries.

Each library (talents, focuses, ...) is a plain JSON file living next to the
active campaign database, so switching campaigns keeps the same personal
reference within one config directory (and tests get an isolated library per
``tmp_path``). This factors out the persistence pattern first established by
``adversaries.py``; the per-library modules layer their own shape on top.
"""
import json
from pathlib import Path

import db

# Every JSON file that sits beside the campaign DB and holds campaign state.
#
# This exists so the backup has one list to consult instead of a hand-kept copy
# that goes stale -- which is exactly what happened: six phases added state here
# and the "full-fidelity" JSON backup carried none of it. `adversaries.json` is
# written by `adversaries.py` through its own path helper rather than through
# this module, and is listed anyway, because what matters here is what a restore
# has to recreate, not which module writes it.
#
# Adding a library? Add it here. `test_export.py` fails if a `.json` side-file
# appears that this list does not name.
CAMPAIGN_FILES = [
    "adversaries.json",
    "extended_tasks.json",
    "focuses.json",
    "scene.json",
    "spaceframes.json",
    "talents.json",
]


def path_for(filename: str) -> Path:
    return db.db_path().parent / filename


def read_raw(filename: str):
    """The file's parsed JSON, whatever shape it is, or None when absent.

    Deliberately shape-agnostic, unlike `load`: the backup copies these files
    through without knowing that talents are dicts and focuses are strings, so a
    library that changes shape later needs no change here.
    """
    try:
        return json.loads(path_for(filename).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def write_raw(filename: str, data) -> None:
    path = path_for(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load(filename: str) -> list:
    """Return the stored list, or [] when the file is missing/corrupt."""
    try:
        data = json.loads(path_for(filename).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def write(filename: str, items: list) -> None:
    path = path_for(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, indent=2), encoding="utf-8")
