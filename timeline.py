"""Chronological campaign timeline for Star Trek Adventures 2e.

A read-only view over the campaign's ``session`` entities, ordered as they were
played. Sessions already carry a number, a real-world date, a Stardate, an
in-game date and a primary location (see ``models.py``); this module gathers
them into ordered rows with a one-line recap pulled from each session's notes,
for the timeline screen and the session-log export. Pure aggregation over
db.py -- no new persistence.
"""
import db


def _recap(notes: str) -> str:
    """The first non-blank line of a session's notes, as a one-line summary."""
    for line in (notes or "").splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def _sort_key(entry: dict):
    """Order by session number when it parses as an int; unnumbered sessions
    sort after numbered ones, then by Stardate / real date / name so the order
    stays stable when numbers are missing or shared."""
    try:
        numeric = (0, int(str(entry["number"]).strip()))
    except (TypeError, ValueError):
        numeric = (1, 0)
    return (numeric, entry["stardate"], entry["session_date"], entry["name"].lower())


def session_entries() -> list[dict]:
    """Every ``session`` entity as an ordered timeline row."""
    entries = []
    for s in db.list_entities("session"):
        f = s["fields"]
        entries.append({
            "id": s["id"],
            "name": s["name"],
            "number": str(f.get("session_number", "") or ""),
            "stardate": str(f.get("stardate", "") or ""),
            "in_game_date": str(f.get("in_game_date", "") or ""),
            "session_date": str(f.get("session_date", "") or ""),
            "location": str(f.get("location", "") or ""),
            "recap": _recap(s["notes"]),
        })
    entries.sort(key=_sort_key)
    return entries
