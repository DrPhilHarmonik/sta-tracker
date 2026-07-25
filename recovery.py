"""Between-scenes and between-missions recovery -- the pure sheet transforms
for resetting a character after a fight or a mission.

Star Trek Adventures 2e keeps this light: a character's Stress track refreshes
at the end of a scene, and Injuries clear with a Medicine Task or downtime
rather than ticking down automatically. These helpers model only the edit --
who decides to recover, and when, stays with the GM (the screens gate it behind
a button). Pure transforms over the sheet dict, mirroring advancement.py:
callers persist the returned sheet.
"""

import sta_sheet as sta_mod


def recover_stress(sheet: dict) -> dict:
    """Return a normalized copy of the sheet with Stress restored to full --
    the end-of-scene reset."""
    sheet = sta_mod.normalize_sheet(sheet)
    sheet["stress_current"] = sheet["stress_max"]
    return sheet


def clear_injury(sheet: dict, index: int) -> dict:
    """Return a copy of the sheet with the Injury at ``index`` removed (a
    treated wound). Out-of-range indices leave the list unchanged."""
    sheet = sta_mod.normalize_sheet(sheet)
    injuries = list(sheet["injuries"])
    if 0 <= index < len(injuries):
        del injuries[index]
    sheet["injuries"] = injuries
    return sheet


def clear_all_injuries(sheet: dict) -> dict:
    """Return a copy of the sheet with every Injury cleared (full downtime)."""
    sheet = sta_mod.normalize_sheet(sheet)
    sheet["injuries"] = []
    return sheet


def recover_sheet(sheet: dict, *, stress: bool = True, injuries: bool = False) -> dict:
    """Convenience combining the common resets: refresh Stress (default) and,
    when ``injuries`` is set, clear all Injuries too. Returns a new sheet."""
    sheet = sta_mod.normalize_sheet(sheet)
    if stress:
        sheet["stress_current"] = sheet["stress_max"]
    if injuries:
        sheet["injuries"] = []
    return sheet
