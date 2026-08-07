"""Theme plumbing for the STA Tracker TUI.

Every bespoke color the app's stylesheet (``sta.tcss``) and screens draw with
is defined here once, as a named theme variable, rather than hardcoded at each
use site. A registered Textual ``Theme`` carries that variable set, so the whole
UI can be re-skinned by swapping the active theme -- the stylesheet references
``$sta-*`` names and never sees a literal hex.

Three themes ship today:

* ``sta-dark`` -- the app's original scheme. Its standard Textual slots
  (primary/secondary/...) are byte-for-byte the built-in ``textual-dark`` theme,
  and its ``sta-*`` variables are the exact hexes the stylesheet used before this
  module existed, so selecting it is a no-op to the eye.
* ``sta-light`` -- a coherent light counterpart that redefines the same variable
  set, proving the toggle re-skins the app as a whole.
* ``sta-lcars`` -- a warm-on-black, LCARS-*flavored* scheme (apricot/orange bars,
  african-violet and ice-blue accents, butterscotch text on true black). This is
  a flavor, not a screen-accurate reproduction: a terminal can't draw LCARS's
  curved elbow sweeps or its condensed Okuda typeface, and Textual CSS has no
  text-transform, so there are no block-char sweeps and no forced ALL-CAPS. The
  LCARS *look* beyond color (round borders, right-aligned amber headers) lives in
  the ``App.-theme-lcars`` rules of ``sta.tcss``, gated by a class the app sets
  when this theme is active.

The ten per-entity accent colors are kept as their own variable group
(``sta-entity-*``) and re-exported as :data:`ENTITY_ACCENTS` for the Python-side
border tinting in ``screens/common.py``. They are deliberately identical across
all three themes: entity identity (enemy=red, location=green, ...) should read
the same whatever the chrome, so LCARS owns the chrome, not the at-a-glance
entity cue.
"""

from textual.theme import Theme

# --- Per-entity accent colors ------------------------------------------------
#
# One accent per entity type, used to tint the borders of every screen reached
# from that entity so it carries a consistent visual identity. This is the
# canonical definition; screens/common.py imports it as PALETTE, and it is also
# folded into each theme's variables below as sta-entity-<type>.
ENTITY_ACCENTS = {
    "npc":        "#c792ea",
    "adventurer": "#89ddff",
    "enemy":      "#ff5370",
    "starship":   "#80cbc4",
    "location":   "#c3e88d",
    "quest":      "#ffcb6b",
    "faction":    "#f78c6c",
    "item":       "#82aaff",
    "session":    "#b2ccd6",
    "encounter":  "#f07178",
}

# Border color used when an entity type has no palette entry. Kept as a plain
# constant (not a theme variable) because it is the last-resort fallback in
# tint_border, which runs without an app/theme in some unit tests.
DEFAULT_BORDER = "#0f3460"

# Light-mode counterparts for the entity accents (darkened for contrast on a
# light background).
_ENTITY_ACCENTS_LIGHT = {
    "npc":        "#8a4fb8",
    "adventurer": "#2477a0",
    "enemy":      "#c0304a",
    "starship":   "#2f8f85",
    "location":   "#4a8a2f",
    "quest":      "#b8862a",
    "faction":    "#c05a2a",
    "item":       "#2a5fcf",
    "session":    "#48607a",
    "encounter":  "#c0455a",
}


def _entity_vars(accents: dict[str, str]) -> dict[str, str]:
    return {f"sta-entity-{k}": v for k, v in accents.items()}


# --- Dark theme (original scheme; selecting it is a no-op to the eye) ---------
_DARK_VARIABLES = {
    # Structural: backgrounds, panels, borders.
    "sta-bg":            "#1a1a2e",
    "sta-panel":         "#16213e",
    "sta-panel-deep":    "#0d1b2a",
    "sta-border":        "#0f3460",
    "sta-border-soft":   "#1e2d45",
    "sta-border-dim":    "#2a3f5f",
    "sta-border-accent": "#4a7fbf",
    "sta-border-danger": "#7b3f3f",
    "sta-input-bg":      "#1e2a3a",
    "sta-bg-danger":     "#1a0a0e",
    # Text.
    "sta-fg":            "#e0e0e0",
    "sta-fg-bright":     "#e2e8f0",
    "sta-text-muted":    "#b2ccd6",
    "sta-text-dim":      "#a0b3c8",
    "sta-text-hint":     "#546e7a",
    "sta-text-faint":    "#566c7f",
    # Semantic accents.
    "sta-accent":        "#c792ea",
    "sta-success":       "#c3e88d",
    "sta-info":          "#82aaff",
    "sta-danger":        "#ff5370",
    "sta-warning":       "#f78c6c",
    **_entity_vars(ENTITY_ACCENTS),
}

# --- Light theme (coherent alternate; redefines the same variable set) --------
_LIGHT_VARIABLES = {
    "sta-bg":            "#eceff4",
    "sta-panel":         "#e0e4ec",
    "sta-panel-deep":    "#d4d9e2",
    "sta-border":        "#b8c2d0",
    "sta-border-soft":   "#cdd4de",
    "sta-border-dim":    "#c0c8d4",
    "sta-border-accent": "#4a7fbf",
    "sta-border-danger": "#c98b8b",
    "sta-input-bg":      "#f4f6fa",
    "sta-bg-danger":     "#f7e4e6",
    "sta-fg":            "#2b2b3a",
    "sta-fg-bright":     "#1a1a24",
    "sta-text-muted":    "#48607a",
    "sta-text-dim":      "#5a6b80",
    "sta-text-hint":     "#8a97a6",
    "sta-text-faint":    "#97a2b0",
    "sta-accent":        "#8a4fb8",
    "sta-success":       "#4a8a2f",
    "sta-info":          "#2a5fcf",
    "sta-danger":        "#c0304a",
    "sta-warning":       "#c05a2a",
    **_entity_vars(_ENTITY_ACCENTS_LIGHT),
}


STA_DARK = Theme(
    name="sta-dark",
    # Standard slots identical to built-in textual-dark, so every widget Textual
    # styles itself (buttons, tabs, inputs, scrollbars) is pixel-unchanged.
    primary="#0178D4",
    secondary="#004578",
    warning="#ffa62b",
    error="#ba3c5b",
    success="#4EBF71",
    accent="#ffa62b",
    foreground="#e0e0e0",
    dark=True,
    variables=dict(_DARK_VARIABLES),
)

STA_LIGHT = Theme(
    name="sta-light",
    # Standard slots identical to built-in textual-light.
    primary="#004578",
    secondary="#0178D4",
    warning="#ffa62b",
    error="#ba3c5b",
    success="#4EBF71",
    accent="#ffa62b",
    background="#E0E0E0",
    surface="#D8D8D8",
    panel="#D0D0D0",
    dark=False,
    variables=dict(_LIGHT_VARIABLES),
)

# --- LCARS theme (warm-on-black; flavor, not screen-accurate) -----------------
# Entity accents stay identical to the dark set (semantic identity, see module
# docstring); only the chrome variables take on LCARS colors.
_LCARS_VARIABLES = {
    # Structural: true black grounds, apricot/orange framing.
    "sta-bg":            "#000000",
    "sta-panel":         "#0d0d0d",
    "sta-panel-deep":    "#050505",
    "sta-border":        "#ff9933",  # LCARS orange -- the signature bar color
    "sta-border-soft":   "#cc7a2e",
    "sta-border-dim":    "#7a4a1c",
    "sta-border-accent": "#9c9cff",  # african-violet / periwinkle
    "sta-border-danger": "#cc6666",  # mars-red, dimmed
    "sta-input-bg":      "#1a1206",
    "sta-bg-danger":     "#1a0505",
    # Text: butterscotch / apricot on black.
    "sta-fg":            "#ffcc99",
    "sta-fg-bright":     "#ffe0c2",
    "sta-text-muted":    "#ffcc66",
    "sta-text-dim":      "#cc9f66",
    "sta-text-hint":     "#99763f",
    "sta-text-faint":    "#806633",
    # Semantic accents.
    "sta-accent":        "#cc99ff",  # violet
    "sta-success":       "#99cc99",
    "sta-info":          "#99ccff",  # ice-blue
    "sta-danger":        "#ff6666",  # mars-red
    "sta-warning":       "#ffcc66",  # butterscotch
    **_entity_vars(ENTITY_ACCENTS),
}

STA_LCARS = Theme(
    name="sta-lcars",
    primary="#ff9933",
    secondary="#cc99ff",
    warning="#ffcc66",
    error="#cc4444",
    success="#88bb88",
    accent="#ff9966",
    foreground="#ffcc99",
    background="#000000",
    surface="#0d0d0d",
    panel="#1a1a1a",
    dark=True,
    variables=dict(_LCARS_VARIABLES),
)

ALL_THEMES = [STA_DARK, STA_LIGHT, STA_LCARS]

# The theme whose active-class drives the extra LCARS layout idioms in sta.tcss.
LCARS_THEME = STA_LCARS.name
LCARS_CLASS = "-theme-lcars"

# Order the /theme toggle cycles through.
THEME_NAMES = [t.name for t in ALL_THEMES]

# The theme selected on a fresh install, before any preference is saved.
DEFAULT_THEME = STA_DARK.name


def register(app) -> None:
    """Register every STA theme on the app."""
    for theme in ALL_THEMES:
        app.register_theme(theme)


def next_theme(current: str) -> str:
    """Return the theme after ``current`` in the toggle order, wrapping around.

    An unknown current name (e.g. a Textual built-in) resolves to the first STA
    theme so the toggle always lands somewhere coherent.
    """
    try:
        idx = THEME_NAMES.index(current)
    except ValueError:
        return THEME_NAMES[0]
    return THEME_NAMES[(idx + 1) % len(THEME_NAMES)]
