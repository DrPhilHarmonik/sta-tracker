"""Conflict (combat) state management, Star Trek Adventures 2e style.

Conflict state lives in an Encounter entity's ``fields["combat"]`` as a plain
dict. Every function here is a pure transformation -- callers persist the
returned dict via ``db.update_entity``.

STA has no initiative sort and no hit-point pool. Instead:

* Turns alternate between two sides -- the player **crew** and the GM's
  **adversaries**. After one character acts, a character from the opposing
  side goes next; when a side has no one left to act, the other side takes the
  remaining turns; when everyone has acted the round ends.
* A character's durability is their **Stress** track, which lives on the
  character sheet (see sta_sheet.py) so there is one source of truth. Reaching
  0 Stress means an Injury, tracked on the sheet.

Situational tags (STA "Traits", plus a few status conditions) are stored per
combatant under ``conditions`` -- the field keeps its parent name so the
party-overview reader and the DB normalizer stay unchanged.
"""

CREW = "crew"
ADVERSARY = "adversary"
SIDES = (CREW, ADVERSARY)


def default_combat() -> dict:
    return {
        "round": 1,
        "started": False,
        "active_side": CREW,
        "current_entity_id": None,
        "combatants": [],
        "log": [],
    }


def _normalize_side(value) -> str:
    return value if value in SIDES else ADVERSARY


def normalize_combat(raw: dict | None) -> dict:
    combat = default_combat()
    raw = raw or {}
    combat["round"] = int(raw.get("round") or 1)
    combat["started"] = bool(raw.get("started", False))
    # The crew hold the initiative by default; only an explicit stored value
    # flips this. (Combatant side, in contrast, defaults to adversary.)
    stored_side = raw.get("active_side")
    combat["active_side"] = stored_side if stored_side in SIDES else CREW
    current = raw.get("current_entity_id")
    combat["current_entity_id"] = int(current) if current is not None else None
    combat["log"] = list(raw.get("log") or [])
    combat["combatants"] = [
        {
            "entity_id": int(c["entity_id"]),
            "side": _normalize_side(c.get("side")),
            "has_acted": bool(c.get("has_acted", False)),
            "conditions": [
                {"name": str(cond.get("name", "")), "rounds_remaining": cond.get("rounds_remaining")}
                for cond in (c.get("conditions") or [])
            ],
        }
        for c in (raw.get("combatants") or [])
    ]
    return combat


def add_combatant(combat: dict, entity_id: int, side: str = ADVERSARY) -> dict:
    combat = normalize_combat(combat)
    if any(c["entity_id"] == entity_id for c in combat["combatants"]):
        return combat
    combat["combatants"].append({
        "entity_id": entity_id,
        "side": _normalize_side(side),
        "has_acted": False,
        "conditions": [],
    })
    return combat


def remove_combatant(combat: dict, entity_id: int) -> dict:
    combat = normalize_combat(combat)
    idx = next((i for i, c in enumerate(combat["combatants"]) if c["entity_id"] == entity_id), None)
    if idx is None:
        return combat
    combat["combatants"].pop(idx)
    if combat["current_entity_id"] == entity_id:
        combat["current_entity_id"] = None
    if not combat["combatants"]:
        combat["started"] = False
        combat["current_entity_id"] = None
    return combat


def set_side(combat: dict, entity_id: int, side: str) -> dict:
    combat = normalize_combat(combat)
    for c in combat["combatants"]:
        if c["entity_id"] == entity_id:
            c["side"] = _normalize_side(side)
    return combat


def _first_unacted(combat: dict, side: str) -> dict | None:
    return next((c for c in combat["combatants"] if c["side"] == side and not c["has_acted"]), None)


def _opposite(side: str) -> str:
    return ADVERSARY if side == CREW else CREW


def start_conflict(combat: dict) -> dict:
    """Begin the conflict: the crew act first, no initiative sort."""
    combat = normalize_combat(combat)
    combat["started"] = True
    combat["round"] = 1
    for c in combat["combatants"]:
        c["has_acted"] = False
    first = _first_unacted(combat, CREW) or (combat["combatants"][0] if combat["combatants"] else None)
    combat["current_entity_id"] = first["entity_id"] if first else None
    combat["active_side"] = first["side"] if first else CREW
    return combat


def current_combatant(combat: dict) -> dict | None:
    combat = normalize_combat(combat)
    cur = combat.get("current_entity_id")
    if cur is None:
        return None
    return next((c for c in combat["combatants"] if c["entity_id"] == cur), None)


def next_turn(combat: dict) -> dict:
    """Advance to the next turn, alternating sides where possible.

    The character whose turn is ending is marked as having acted; the next
    character is drawn from the opposing side first, then the same side, and
    when everyone has acted the round rolls over (Traits tick, all sides reset,
    crew act first again)."""
    combat = normalize_combat(combat)
    if not combat["combatants"]:
        return combat

    # Find the acting combatant within this (already-normalized) combat dict --
    # not via current_combatant(), which returns one from a fresh copy, so
    # marking it acted would be lost.
    cur_id = combat.get("current_entity_id")
    current = next((c for c in combat["combatants"] if c["entity_id"] == cur_id), None)
    just_side = current["side"] if current else combat["active_side"]
    if current:
        current["has_acted"] = True

    nxt = _first_unacted(combat, _opposite(just_side)) or _first_unacted(combat, just_side)
    if nxt is None:
        return _begin_round(combat)

    combat["current_entity_id"] = nxt["entity_id"]
    combat["active_side"] = nxt["side"]
    return combat


def next_round(combat: dict) -> dict:
    """Skip any remaining turns and start a fresh round."""
    return _begin_round(normalize_combat(combat))


def _begin_round(combat: dict) -> dict:
    combat["round"] += 1
    for c in combat["combatants"]:
        c["has_acted"] = False
    _tick_conditions(combat)
    first = _first_unacted(combat, CREW) or (combat["combatants"][0] if combat["combatants"] else None)
    combat["current_entity_id"] = first["entity_id"] if first else None
    combat["active_side"] = first["side"] if first else CREW
    return combat


def _tick_conditions(combat: dict):
    for c in combat["combatants"]:
        kept = []
        for cond in c["conditions"]:
            if cond["rounds_remaining"] is None:
                kept.append(cond)
                continue
            cond["rounds_remaining"] -= 1
            if cond["rounds_remaining"] > 0:
                kept.append(cond)
        c["conditions"] = kept


def add_condition(combat: dict, entity_id: int, name: str, rounds_remaining: int | None) -> dict:
    combat = normalize_combat(combat)
    for c in combat["combatants"]:
        if c["entity_id"] == entity_id:
            c["conditions"].append({"name": name, "rounds_remaining": rounds_remaining})
    return combat


def remove_condition(combat: dict, entity_id: int, index: int) -> dict:
    combat = normalize_combat(combat)
    for c in combat["combatants"]:
        if c["entity_id"] == entity_id and 0 <= index < len(c["conditions"]):
            c["conditions"].pop(index)
    return combat


# -- Stress track transforms (the sheet owns the numbers; these are pure math) -

def apply_stress(stress_current: int, amount: int) -> int:
    """Reduce a character's remaining Stress, floored at 0."""
    return max(0, stress_current - amount)


def recover_stress(stress_current: int, stress_max: int, amount: int) -> int:
    """Restore remaining Stress, capped at the track maximum."""
    return min(stress_max, stress_current + amount)


def log_entry(combat: dict, round_: int, message: str) -> dict:
    """Append a log entry and return the combat dict."""
    combat.setdefault("log", []).append({"round": round_, "entry": message})
    return combat
