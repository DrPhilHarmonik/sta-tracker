"""Common conflict Traits and status conditions for the tracker's picker.

Star Trek Adventures 2e leans on freeform **Traits** rather than a closed list
of conditions, so this is a convenience library, not an exhaustive ruleset:
short, neutrally-worded reminders a GM can drop onto a combatant, plus the
tracker's "Custom..." option for anything not listed. Descriptions are
authored here (mechanics reference only, no copyrighted text)."""

CONDITIONS: dict[str, str] = {
    "Injured": "A serious wound. Increases the Difficulty of many Tasks until treated with a Medicine Task.",
    "Blinded": "Cannot see. Tasks that rely on sight are much harder or impossible; attacks against are easier.",
    "Deafened": "Cannot hear. Tasks that rely on hearing are much harder or impossible.",
    "Restrained": "Held fast. Cannot move, and physical Tasks suffer increased Difficulty until freed.",
    "Prone": "Knocked down. Must spend effort to stand; melee attacks against are easier.",
    "Exposed": "Caught in the open with no cover. Attacks against are easier.",
    "Dazed": "Reeling. The character's next Task suffers increased Difficulty.",
    "On Fire": "Burning. Takes ongoing Stress at the start of each turn until extinguished.",
    "Suffocating": "Without breathable air. Escalating Stress each turn until able to breathe.",
    "Cover": "Benefits from cover. Attacks against the character are harder.",
    "Hidden": "Position is unknown to opponents. Grants advantage until revealed.",
}

CONDITION_NAMES: list[str] = list(CONDITIONS.keys())
