import json

import yaml
from textual.screen import Screen

import db
from models import ENTITY_SCHEMAS
from theme import ENTITY_ACCENTS, DEFAULT_BORDER

# The per-entity accent colors live in theme.py as the canonical "entity accent"
# variable set (also exposed to the stylesheet as $sta-entity-*). Kept aliased
# here under the long-standing name the screens import.
PALETTE = ENTITY_ACCENTS


class DismissableScreen(Screen):
    """Screen base for the common 'Escape to go back' binding.

    Plain app.pop_screen() silently discards any callback registered via
    push_screen(..., callback=...) without calling it -- only
    Screen.dismiss() actually invokes it. Screens that need their caller to
    refresh on return must dismiss(), not pop_screen(), so this is the
    binding target every such screen should use instead.
    """

    def action_dismiss_screen(self):
        self.dismiss()


def schema_choices(entity_type: str, key: str) -> list[str]:
    for field_key, _, _, choices in ENTITY_SCHEMAS.get(entity_type, []):
        if field_key == key:
            return choices or []
    return []


def entity_ref_options(referenced_type: str, current_value: str = "") -> list[tuple[str, str]]:
    """Select options for an 'entity_ref' field: every entity of the
    referenced type, by name. If the field's current value doesn't match
    any of them (stale text from before this field was a picker, or the
    referenced entity was since renamed/deleted), it's kept as its own
    option rather than silently dropped, so opening the form never loses
    data the DM hasn't actually touched."""
    options = [(e["name"], e["name"]) for e in db.list_entities(referenced_type)]
    names = {name for _, name in options}
    if current_value and current_value not in names:
        options.append((f"{current_value} (not found)", current_value))
    return options


def tint_border(widget, entity_type: str):
    """Accent a container's border with its entity type's palette color, so
    every screen reachable from a given entity carries the same visual
    identity (e.g. all of an Enemy's screens show red, not just its name)."""
    widget.styles.border = ("solid", PALETTE.get(entity_type, DEFAULT_BORDER))


def format_io_error(ex: Exception) -> str:
    """Categorize export/import/backup failures into a clearer UI message.

    json.JSONDecodeError is a ValueError subclass, so it's checked first;
    the permission/missing-path/directory cases are all OSError subclasses
    and likewise need to come before the generic OSError fallback.
    """
    if isinstance(ex, json.JSONDecodeError):
        return f"Could not parse JSON: {ex}"
    if isinstance(ex, yaml.YAMLError):
        return f"Could not parse vault YAML frontmatter: {ex}"
    if isinstance(ex, PermissionError):
        return f"Permission denied: {ex.filename or ex}"
    if isinstance(ex, FileNotFoundError):
        return f"Path not found: {ex.filename or ex}"
    if isinstance(ex, IsADirectoryError):
        return f"Expected a file but found a directory: {ex.filename or ex}"
    if isinstance(ex, NotADirectoryError):
        return f"Expected a directory but found a file: {ex.filename or ex}"
    if isinstance(ex, ValueError):
        return f"Validation error: {ex}"
    if isinstance(ex, OSError):
        return f"Filesystem error: {ex}"
    return f"Unexpected error: {ex}"
