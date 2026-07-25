"""Momentum and Threat -- the two shared, table-level metacurrency pools of
Star Trek Adventures 2e.

Momentum is the players' pool: successes rolled beyond a task's Difficulty
become Momentum, which the group later spends to buy extra dice, information,
or narrative advantage. Threat is the gamemaster's matching pool, spent to
complicate scenes and power adversaries. Neither belongs to any one character
sheet -- they are properties of the whole table, so db.py persists them in a
single campaign-state row rather than in an entity blob.

This module holds only the *rules* (bounds and Threat seeding); db.py holds
the persistence.
"""

# The group Momentum pool caps at 6; anything generated beyond that is lost.
# Threat has no upper bound in the rules.
MOMENTUM_MAX = 6


def clamp_momentum(value: int) -> int:
    """Momentum never drops below 0 or rises above the group maximum."""
    return max(0, min(MOMENTUM_MAX, int(value)))


def clamp_threat(value: int) -> int:
    """Threat never drops below 0 and has no ceiling."""
    return max(0, int(value))


def seed_threat(num_players: int) -> int:
    """Threat is seeded at the start of a session to twice the number of
    player characters at the table."""
    return 2 * max(0, int(num_players))


def threat_between_missions(threat: int, carry: bool) -> int:
    """The GM's reset-or-carry decision at the end of a mission: keep the pool
    (clamped) when ``carry`` is True, otherwise reset it to 0. Threat is not
    reseeded here -- that is start-of-session seeding (see seed_threat)."""
    return clamp_threat(threat) if carry else 0


# -- Buying bonus d20s -------------------------------------------------------
#
# Before a Task, the group may buy up to 3 extra d20s (2d20 base -> 5 max). The
# cost escalates: the first extra die costs 1 Momentum, the second 2, the third
# 3 -- so buying N of them costs 1+2+...+N. A group short on Momentum may buy on
# credit instead, adding that many points to Threat. This is rules math (not
# copyrightable); the pools live in db.py.

def bonus_dice_cost(num_bought: int) -> int:
    """Total Momentum cost to buy ``num_bought`` extra d20s (0..3)."""
    n = max(0, min(int(num_bought), 3))
    return n * (n + 1) // 2


def pay_for_bonus_dice(momentum: int, threat: int, num_bought: int) -> tuple[int, int, int, int]:
    """Pay for extra d20s from the pools: spend Momentum first, then buy any
    remainder on credit by adding to Threat. Returns
    ``(new_momentum, new_threat, spent_momentum, credited_threat)``."""
    cost = bonus_dice_cost(num_bought)
    spent = min(cost, max(0, int(momentum)))
    credited = cost - spent
    return (int(momentum) - spent, int(threat) + credited, spent, credited)


# Common Immediate Momentum spends surfaced as one-click reminders. Labels and
# costs are ordinary 2d20 play conventions; the tool just debits the pool and
# logs the choice -- it enforces nothing. For anything else, adjust the pool
# directly on the PoolBar.
MOMENTUM_SPENDS = [
    ("Obtain Information", 1),
    ("Bonus Damage (+1 [CD])", 1),
    ("Keep the Initiative", 1),
    ("Create Advantage (scene Trait)", 2),
]
