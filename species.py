"""Reference data for Star Trek Adventures 2e species, used by the creation
wizard to seed an Adventurer's Attribute spread at creation time.

This is the STA replacement for the 5e ``races.py``. It ships mechanics and
suggested point spreads only -- no copyrighted flavor text. Each species
grants +1 to a small set of Attributes (a starting suggestion the GM freely
edits afterwards). ``choice_bonus`` marks species whose bonuses are player-
chosen rather than fixed (Humans distribute +1 across three Attributes of
their choice), mirroring the Half-Elf-style pick in the parent's races.py.

``focus_suggestions`` are ordinary skill words offered as a hint on the
Focuses step; nothing here is re-applied after creation, so changing a
character's species later is a manual sheet edit.
"""

import sta_sheet as sta

ATTRIBUTES = sta.ATTRIBUTES

SPECIES: dict[str, dict] = {
    "Human": {
        "attribute_bonuses": {},
        "choice_bonus": 3,
        "focus_suggestions": ["Diplomacy", "Improvisation", "Leadership"],
    },
    "Vulcan": {
        "attribute_bonuses": {"control": 1, "fitness": 1, "reason": 1},
        "choice_bonus": 0,
        "focus_suggestions": ["Logic", "Physical Sciences", "Meditation"],
    },
    "Andorian": {
        "attribute_bonuses": {"control": 1, "daring": 1, "fitness": 1},
        "choice_bonus": 0,
        "focus_suggestions": ["Combat Tactics", "Survival", "Composure"],
    },
    "Tellarite": {
        "attribute_bonuses": {"daring": 1, "insight": 1, "presence": 1},
        "choice_bonus": 0,
        "focus_suggestions": ["Negotiation", "Engineering", "Persuasion"],
    },
    "Denobulan": {
        "attribute_bonuses": {"fitness": 1, "insight": 1, "reason": 1},
        "choice_bonus": 0,
        "focus_suggestions": ["Medicine", "Life Sciences", "Interspecies Relations"],
    },
    "Bajoran": {
        "attribute_bonuses": {"daring": 1, "insight": 1, "presence": 1},
        "choice_bonus": 0,
        "focus_suggestions": ["Resistance Operations", "Willpower", "Faith"],
    },
    "Betazoid": {
        "attribute_bonuses": {"control": 1, "insight": 1, "presence": 1},
        "choice_bonus": 0,
        "focus_suggestions": ["Empathy", "Counseling", "Observation"],
    },
    "Trill": {
        "attribute_bonuses": {"control": 1, "insight": 1, "reason": 1},
        "choice_bonus": 0,
        "focus_suggestions": ["Symbiosis", "History", "Physical Sciences"],
    },
    "Bolian": {
        "attribute_bonuses": {"daring": 1, "fitness": 1, "presence": 1},
        "choice_bonus": 0,
        "focus_suggestions": ["Astrogation", "Cooking", "Small Talk"],
    },
}

SPECIES_NAMES = list(SPECIES.keys())


def attribute_bonus_total(species: str, attribute: str, choice_attributes: list[str] | None = None) -> int:
    """Total +Attribute a species grants, including the Human-style
    'choose N Attributes for +1 each' bonus when applicable."""
    data = SPECIES.get(species)
    if not data:
        return 0
    total = data["attribute_bonuses"].get(attribute, 0)
    if attribute in (choice_attributes or [])[: data.get("choice_bonus", 0)]:
        total += 1
    return total


def apply_bonuses(attributes: dict, species: str, choice_attributes: list[str] | None = None) -> dict:
    """Return a new Attribute dict with this species' bonuses added on top.
    Never mutates the input -- the wizard keeps the raw assigned spread
    separate from the species-adjusted total."""
    return {
        a: attributes.get(a, sta.DEFAULT_ATTRIBUTE) + attribute_bonus_total(species, a, choice_attributes)
        for a in ATTRIBUTES
    }
