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


def path_for(filename: str) -> Path:
    return db.db_path().parent / filename


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
