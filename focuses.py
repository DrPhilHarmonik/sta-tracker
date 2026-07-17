"""User-authored Focus suggestion library for Star Trek Adventures.

Focuses are bare strings (areas of expertise like "Astrophysics" or "Warp Field
Dynamics"). This library ships **empty** and accumulates the Focuses the GM
actually uses -- the sheet and wizard remember each Focus as it is entered, then
offer the growing list as autocomplete. Persists to ``focuses.json`` next to the
campaign DB (see library.py).
"""
import library

_FILE = "focuses.json"


def all_focuses() -> list[str]:
    """Every stored Focus, de-duplicated (case-insensitively) and sorted."""
    seen: dict[str, str] = {}
    for raw in library.load(_FILE):
        name = str(raw or "").strip()
        if name:
            seen.setdefault(name.lower(), name)
    return sorted(seen.values(), key=str.lower)


def search(query: str) -> list[str]:
    q = query.strip().lower()
    items = all_focuses()
    return items if not q else [f for f in items if q in f.lower()]


def add(name: str) -> None:
    """Remember a Focus. Blank or duplicate (case-insensitive) names are no-ops,
    so 'remember what I just typed' hooks can call this unconditionally."""
    name = str(name or "").strip()
    if not name:
        return
    existing = all_focuses()
    if any(f.lower() == name.lower() for f in existing):
        return
    library.write(_FILE, existing + [name])


def remove(name: str) -> None:
    kept = [f for f in all_focuses() if f.lower() != name.strip().lower()]
    library.write(_FILE, kept)
