"""Read-side search helpers that reach inside the opaque ``sheet`` blob.

The DB only stores name/notes as plain columns; a character's Focuses, Values,
Talents and species/rank/role, and a starship's Talents/Traits, all live inside
the JSON sheet. These helpers flatten that content into labeled strings and
report the first field a query substring-matches, so global and per-type list
search can find "who has Warp Field Dynamics?" without a schema change. Pure
logic -- no DB access; callers pass entity dicts in.
"""

import sta_sheet as sta_mod
import starship as ship_mod


def _character_terms(sheet: dict) -> list[tuple[str, str]]:
    sheet = sta_mod.normalize_sheet(sheet)
    terms: list[tuple[str, str]] = []
    for label, key in (("Species", "species"), ("Rank", "rank"), ("Role", "role")):
        if sheet.get(key):
            terms.append((label, sheet[key]))
    for focus in sheet.get("focuses", []):
        terms.append(("Focus", focus))
    for value in sheet.get("values", []):
        terms.append(("Value", value))
    for talent in sheet.get("talents", []):
        terms.append(("Talent", talent))
    return terms


def _starship_terms(sheet: dict) -> list[tuple[str, str]]:
    sheet = ship_mod.normalize_sheet(sheet)
    terms: list[tuple[str, str]] = []
    for talent in sheet.get("talents", []):
        terms.append(("Talent", talent))
    for trait in sheet.get("traits", []):
        terms.append(("Trait", trait))
    return terms


def sheet_terms(entity: dict) -> list[tuple[str, str]]:
    """Labeled searchable strings drawn from an entity's sheet blob, or ``[]``
    if it has none. Starship sheets carry ``systems``; character sheets don't."""
    fields = entity.get("fields", {})
    sheet = fields.get("sheet")
    if not isinstance(sheet, dict):
        return []
    if entity.get("type") == "starship" or "systems" in sheet:
        return _starship_terms(sheet)
    return _character_terms(sheet)


def match(entity: dict, query: str) -> str | None:
    """Return a short label describing where ``query`` first matches this
    entity (name, notes, or a sheet field like ``"Focus: Astrophysics"``), or
    ``None`` if it matches nowhere. Case-insensitive substring match."""
    q = (query or "").strip().lower()
    if not q:
        return None
    if q in (entity.get("name") or "").lower():
        return "Name"
    if q in (entity.get("notes") or "").lower():
        return "Notes"
    for label, value in sheet_terms(entity):
        if q in value.lower():
            return f"{label}: {value}"
    return None
