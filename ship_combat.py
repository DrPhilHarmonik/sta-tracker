"""Starship conflict state management, Star Trek Adventures 2e style.

The ship-scale parallel to combat.py. Ship-conflict state lives in an Encounter
entity's ``fields["ship_combat"]`` as a plain dict; every function here is a
pure transformation the screen persists via ``db.update_entity``.

Like the personal conflict it uses side-alternating turns (crew ships vs
adversary ships, no initiative). The differences are all ship-scale:

* **Power** -- a per-ship pool that refills to the ship's rating at the start of
  each round and is spent on actions.
* **Shields -> Breaches** -- damage first depletes a ship's Shields (which live
  on the ship sheet, like a character's Stress); any overflow becomes Breaches
  in a system, tracked here per encounter.
* **Range** -- a single shared range band (Close / Medium / Long) the GM adjusts.

Situational ship Traits are stored per ship under ``traits``.
"""

CREW = "crew"
ADVERSARY = "adversary"
SIDES = (CREW, ADVERSARY)

RANGES = ["Close", "Medium", "Long"]
DEFAULT_RANGE = "Medium"


def default_ship_combat() -> dict:
    return {
        "round": 1,
        "started": False,
        "active_side": CREW,
        "current_ship_id": None,
        "range": DEFAULT_RANGE,
        "ships": [],
        "log": [],
    }


def _side(value) -> str:
    return value if value in SIDES else ADVERSARY


def normalize_ship_combat(raw: dict | None) -> dict:
    state = default_ship_combat()
    raw = raw or {}
    state["round"] = int(raw.get("round") or 1)
    state["started"] = bool(raw.get("started", False))
    stored_side = raw.get("active_side")
    state["active_side"] = stored_side if stored_side in SIDES else CREW
    current = raw.get("current_ship_id")
    state["current_ship_id"] = int(current) if current is not None else None
    state["range"] = raw.get("range") if raw.get("range") in RANGES else DEFAULT_RANGE
    state["log"] = list(raw.get("log") or [])
    state["ships"] = [
        {
            "entity_id": int(s["entity_id"]),
            "side": _side(s.get("side")),
            "has_acted": bool(s.get("has_acted", False)),
            "power": max(0, int(s.get("power") or 0)),
            "power_max": max(0, int(s.get("power_max") or 0)),
            "breaches": {str(k): max(0, int(v)) for k, v in (s.get("breaches") or {}).items()},
            "traits": [
                {"name": str(t.get("name", "")), "rounds_remaining": t.get("rounds_remaining")}
                for t in (s.get("traits") or [])
            ],
        }
        for s in (raw.get("ships") or [])
    ]
    return state


def add_ship(state: dict, entity_id: int, side: str = ADVERSARY, power_max: int = 0) -> dict:
    state = normalize_ship_combat(state)
    if any(s["entity_id"] == entity_id for s in state["ships"]):
        return state
    state["ships"].append({
        "entity_id": entity_id,
        "side": _side(side),
        "has_acted": False,
        "power": max(0, int(power_max)),
        "power_max": max(0, int(power_max)),
        "breaches": {},
        "traits": [],
    })
    return state


def remove_ship(state: dict, entity_id: int) -> dict:
    state = normalize_ship_combat(state)
    idx = next((i for i, s in enumerate(state["ships"]) if s["entity_id"] == entity_id), None)
    if idx is None:
        return state
    state["ships"].pop(idx)
    if state["current_ship_id"] == entity_id:
        state["current_ship_id"] = None
    if not state["ships"]:
        state["started"] = False
        state["current_ship_id"] = None
    return state


def set_side(state: dict, entity_id: int, side: str) -> dict:
    state = normalize_ship_combat(state)
    for s in state["ships"]:
        if s["entity_id"] == entity_id:
            s["side"] = _side(side)
    return state


def set_range(state: dict, value: str) -> dict:
    state = normalize_ship_combat(state)
    if value in RANGES:
        state["range"] = value
    return state


# -- turn flow (side-alternating, mirrors combat.py) --------------------------

def _first_unacted(state: dict, side: str) -> dict | None:
    return next((s for s in state["ships"] if s["side"] == side and not s["has_acted"]), None)


def _opposite(side: str) -> str:
    return ADVERSARY if side == CREW else CREW


def start_conflict(state: dict) -> dict:
    state = normalize_ship_combat(state)
    state["started"] = True
    state["round"] = 1
    for s in state["ships"]:
        s["has_acted"] = False
        s["power"] = s["power_max"]
    first = _first_unacted(state, CREW) or (state["ships"][0] if state["ships"] else None)
    state["current_ship_id"] = first["entity_id"] if first else None
    state["active_side"] = first["side"] if first else CREW
    return state


def current_ship(state: dict) -> dict | None:
    state = normalize_ship_combat(state)
    cur = state.get("current_ship_id")
    if cur is None:
        return None
    return next((s for s in state["ships"] if s["entity_id"] == cur), None)


def next_turn(state: dict) -> dict:
    state = normalize_ship_combat(state)
    if not state["ships"]:
        return state
    cur_id = state.get("current_ship_id")
    current = next((s for s in state["ships"] if s["entity_id"] == cur_id), None)
    just_side = current["side"] if current else state["active_side"]
    if current:
        current["has_acted"] = True
    nxt = _first_unacted(state, _opposite(just_side)) or _first_unacted(state, just_side)
    if nxt is None:
        return _begin_round(state)
    state["current_ship_id"] = nxt["entity_id"]
    state["active_side"] = nxt["side"]
    return state


def next_round(state: dict) -> dict:
    return _begin_round(normalize_ship_combat(state))


def _begin_round(state: dict) -> dict:
    state["round"] += 1
    for s in state["ships"]:
        s["has_acted"] = False
        s["power"] = s["power_max"]   # Power refills each round
    _tick_traits(state)
    first = _first_unacted(state, CREW) or (state["ships"][0] if state["ships"] else None)
    state["current_ship_id"] = first["entity_id"] if first else None
    state["active_side"] = first["side"] if first else CREW
    return state


def _tick_traits(state: dict):
    for s in state["ships"]:
        kept = []
        for t in s["traits"]:
            if t["rounds_remaining"] is None:
                kept.append(t)
                continue
            t["rounds_remaining"] -= 1
            if t["rounds_remaining"] > 0:
                kept.append(t)
        s["traits"] = kept


# -- Power / damage / breaches (pure) -----------------------------------------

def spend_power(power_current: int, amount: int) -> int:
    """Reduce a ship's Power, floored at 0."""
    return max(0, power_current - amount)


def apply_ship_damage(shields_current: int, amount: int) -> tuple[int, int]:
    """Apply damage to a ship: returns (new_shields, overflow) where overflow is
    the damage beyond the Shields track (which becomes Breaches)."""
    amount = max(0, amount)
    new_shields = max(0, shields_current - amount)
    overflow = max(0, amount - shields_current)
    return new_shields, overflow


def add_breach(state: dict, entity_id: int, system: str, count: int = 1) -> dict:
    state = normalize_ship_combat(state)
    for s in state["ships"]:
        if s["entity_id"] == entity_id:
            s["breaches"][system] = s["breaches"].get(system, 0) + max(0, int(count))
    return state


def total_breaches(ship: dict) -> int:
    return sum((ship.get("breaches") or {}).values())


def add_trait(state: dict, entity_id: int, name: str, rounds_remaining: int | None) -> dict:
    state = normalize_ship_combat(state)
    for s in state["ships"]:
        if s["entity_id"] == entity_id:
            s["traits"].append({"name": name, "rounds_remaining": rounds_remaining})
    return state


def remove_trait(state: dict, entity_id: int, index: int) -> dict:
    state = normalize_ship_combat(state)
    for s in state["ships"]:
        if s["entity_id"] == entity_id and 0 <= index < len(s["traits"]):
            s["traits"].pop(index)
    return state


def log_entry(state: dict, round_: int, message: str) -> dict:
    state.setdefault("log", []).append({"round": round_, "entry": message})
    return state
