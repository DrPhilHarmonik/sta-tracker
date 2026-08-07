import theme as theme_mod
import settings
from screens.common import PALETTE
from models import ENTITY_TYPES


# -- the dark theme is the original scheme (no-op to the eye) ------------------

# Every literal hex the stylesheet used before Phase 24, keyed by the variable
# it was replaced with. If any of these drift, the "selecting sta-dark changes
# nothing" guarantee is broken.
ORIGINAL_HEXES = {
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
    "sta-fg":            "#e0e0e0",
    "sta-fg-bright":     "#e2e8f0",
    "sta-text-muted":    "#b2ccd6",
    "sta-text-dim":      "#a0b3c8",
    "sta-text-hint":     "#546e7a",
    "sta-text-faint":    "#566c7f",
    "sta-accent":        "#c792ea",
    "sta-success":       "#c3e88d",
    "sta-info":          "#82aaff",
    "sta-danger":        "#ff5370",
    "sta-warning":       "#f78c6c",
}


def test_dark_theme_preserves_every_original_color():
    variables = theme_mod.STA_DARK.variables
    for name, hexv in ORIGINAL_HEXES.items():
        assert variables[name] == hexv


def test_dark_theme_standard_slots_match_textual_dark():
    from textual.theme import BUILTIN_THEMES
    td = BUILTIN_THEMES["textual-dark"]
    ours = theme_mod.STA_DARK
    for slot in ("primary", "secondary", "warning", "error", "success", "accent", "foreground"):
        assert getattr(ours, slot) == getattr(td, slot)
    assert ours.dark is True


# -- entity accents are their own variable set --------------------------------

def test_entity_accents_cover_every_entity_type():
    for entity_type in ENTITY_TYPES:
        assert entity_type in theme_mod.ENTITY_ACCENTS


def test_palette_is_the_canonical_entity_accents():
    assert PALETTE is theme_mod.ENTITY_ACCENTS


def test_dark_theme_exposes_entity_accents_as_variables():
    variables = theme_mod.STA_DARK.variables
    for entity_type, hexv in theme_mod.ENTITY_ACCENTS.items():
        assert variables[f"sta-entity-{entity_type}"] == hexv


# -- every theme defines the same variable set (coherent toggle) --------------

def test_all_themes_define_the_same_variables():
    # A flip must not leave any $sta-* reference undefined, or the stylesheet
    # fails to parse. Identical keys across every theme guarantees that.
    dark_keys = set(theme_mod.STA_DARK.variables)
    for t in theme_mod.ALL_THEMES:
        assert set(t.variables) == dark_keys, t.name


def test_light_theme_actually_differs_from_dark():
    assert theme_mod.STA_LIGHT.variables != theme_mod.STA_DARK.variables
    assert theme_mod.STA_LIGHT.dark is False


# -- LCARS theme --------------------------------------------------------------

def test_lcars_theme_is_warm_on_black():
    v = theme_mod.STA_LCARS.variables
    assert v["sta-bg"] == "#000000"
    assert v["sta-border"] == "#ff9933"
    assert theme_mod.STA_LCARS.dark is True
    assert theme_mod.STA_LCARS.background == "#000000"


def test_lcars_keeps_entity_accents_semantic():
    # Entity identity should read the same under LCARS as under dark: the
    # entity accents are deliberately unchanged, only the chrome shifts.
    lcars = theme_mod.STA_LCARS.variables
    dark = theme_mod.STA_DARK.variables
    for entity_type in theme_mod.ENTITY_ACCENTS:
        key = f"sta-entity-{entity_type}"
        assert lcars[key] == dark[key]


def test_lcars_chrome_actually_differs_from_dark():
    # ...while the chrome (non-entity) variables do change.
    lcars = theme_mod.STA_LCARS.variables
    dark = theme_mod.STA_DARK.variables
    chrome = [k for k in dark if not k.startswith("sta-entity-")]
    assert any(lcars[k] != dark[k] for k in chrome)


# -- toggle order -------------------------------------------------------------

def test_theme_names_and_default():
    assert theme_mod.THEME_NAMES == ["sta-dark", "sta-light", "sta-lcars"]
    assert theme_mod.DEFAULT_THEME == "sta-dark"


def test_next_theme_cycles_and_wraps():
    assert theme_mod.next_theme("sta-dark") == "sta-light"
    assert theme_mod.next_theme("sta-light") == "sta-lcars"
    assert theme_mod.next_theme("sta-lcars") == "sta-dark"


def test_next_theme_from_unknown_lands_on_first():
    assert theme_mod.next_theme("nord") == "sta-dark"


# -- settings persistence -----------------------------------------------------

def test_settings_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_SETTINGS_PATH", str(tmp_path / "settings.json"))
    assert settings.get_setting("theme", "sta-dark") == "sta-dark"  # default, file absent
    settings.set_setting("theme", "sta-light")
    assert settings.get_setting("theme") == "sta-light"
    assert settings.all_settings() == {"theme": "sta-light"}


def test_settings_set_creates_parent_dirs(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_SETTINGS_PATH", str(tmp_path / "nested" / "deep" / "settings.json"))
    settings.set_setting("theme", "sta-dark")
    assert settings.get_setting("theme") == "sta-dark"


def test_corrupt_settings_file_is_ignored(monkeypatch, tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setenv("STA_SETTINGS_PATH", str(path))
    assert settings.all_settings() == {}
    assert settings.get_setting("theme", "sta-dark") == "sta-dark"
