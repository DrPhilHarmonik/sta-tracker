"""Supporting Characters (quick crew) for Star Trek Adventures 2e.

Supporting Characters are the minor crew a player spins up on the spot -- a
transporter chief, a visiting diplomat. They use a lighter spread than a main
character and are built in one step rather than the full lifepath. This module
produces their STA sheet; the QuickCrewScreen wraps it in a fast form.
"""
import species as species_mod
import sta_sheet as sta

# Supporting Characters use a modest, flat spread (mains get the wizard's).
BASE_ATTRIBUTES = {"control": 9, "daring": 8, "fitness": 9, "insight": 8, "presence": 9, "reason": 8}
BASE_DEPARTMENTS = {"command": 1, "conn": 1, "engineering": 1, "security": 2, "medicine": 1, "science": 1}


def build_sheet(species: str = "", focus: str = "", role: str = "") -> dict:
    """Build an STA character sheet for a Supporting Character: the base spread
    with the species' fixed Attribute bonuses applied, plus an optional Focus
    and role."""
    sheet = sta.default_sheet()
    attributes = dict(BASE_ATTRIBUTES)
    if species in species_mod.SPECIES:
        # No player choice attributes for a supporting character (Human, whose
        # bonus is all-choice, simply gets the flat base).
        attributes = species_mod.apply_bonuses(attributes, species, [])
    sheet["attributes"] = attributes
    sheet["departments"] = dict(BASE_DEPARTMENTS)
    sheet["species"] = species
    sheet["role"] = role
    if focus.strip():
        sheet["focuses"] = [focus.strip()]
    return sheet
