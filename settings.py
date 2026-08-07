"""User-global UI settings, persisted as a small JSON file.

These are app-wide preferences (currently just the active theme), not campaign
data, so they live alongside the campaign manager DB rather than inside any
campaign file. The ``STA_SETTINGS_PATH`` env var overrides the location, which
keeps tests isolated the same way ``STA_DB_PATH`` does for the database.

Reads are defensive: a missing or corrupt file yields an empty settings dict
rather than raising, so a hand-mangled file never blocks startup.
"""
import json
import os
from pathlib import Path

import campaign_manager as cm


def _path() -> Path:
    override = os.environ.get("STA_SETTINGS_PATH")
    if override:
        return Path(override)
    return cm.MANAGER_DIR / "settings.json"


def all_settings() -> dict:
    path = _path()
    try:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def get_setting(key: str, default=None):
    return all_settings().get(key, default)


def set_setting(key: str, value) -> None:
    data = all_settings()
    data[key] = value
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
