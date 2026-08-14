"""The `ctrl+r` Task roll: 2d20 from wherever you are.

STA resolves everything with a Task roll, and most play is not a conflict --
it is scans, repairs, persuasion and forensics. Before this, the only Task
rollers lived in the combat tracker and the ship screen, so rolling for a scene
meant opening a conflict you were not in.

The rules half is `task.resolve`, shared with the combat tracker so the two
cannot drift into disagreeing about what a bought d20 costs. This screen picks
the character, reads the controls, and writes the consequences back.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static, Switch

import db
import sta_sheet as sta
import task

from screens.common import ComplicationPrompt

BONUS_DICE_OPTIONS = [("2 dice (base)", "0"), ("3 dice", "1"), ("4 dice", "2"), ("5 dice", "3")]
COMP_RANGE_OPTIONS = [("Comp. on 20", "1"), ("on 19-20", "2"), ("on 18-20", "3")]


def sheet_bearing_entities() -> list[tuple[str, str]]:
    """Select options for everyone who has a character sheet to roll from."""
    return [
        (entity["name"], str(entity["id"]))
        for entity in db.list_entities()
        if entity["type"] in sta.SHEET_ENTITY_TYPES
    ]


class QuickTaskModal(ModalScreen):
    """Roll a Task"""

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("ctrl+r", "close", "Close"),
    ]

    def __init__(self, default_entity_id: int | None = None):
        super().__init__()
        self.default_entity_id = default_entity_id

    def compose(self) -> ComposeResult:
        options = sheet_bearing_entities()
        attr_options = [(sta.ATTRIBUTE_LABELS[a], a) for a in sta.ATTRIBUTES]
        dept_options = [(sta.DEPARTMENT_LABELS[d], d) for d in sta.DEPARTMENTS]
        yield Container(
            Static("Task Roll", id="qt-header"),
            VerticalScroll(
                Label("Character"),
                Select(options, id="qt-entity", prompt="Choose character..."),
                Horizontal(
                    Select(attr_options, id="qt-attr", allow_blank=False, value="daring"),
                    Select(dept_options, id="qt-dept", allow_blank=False, value="security"),
                    id="qt-selectors",
                ),
                Horizontal(
                    Label("Difficulty"), Input(value="2", id="qt-difficulty", classes="stat-input"),
                    Switch(id="qt-focus"), Label("Focus"),
                    Switch(id="qt-invoke"), Label("Invoke Value"),
                    id="qt-params",
                ),
                Horizontal(
                    Label("Dice"), Select(BONUS_DICE_OPTIONS, value="0", id="qt-bonus-dice", allow_blank=False),
                    Label("Complication"), Select(COMP_RANGE_OPTIONS, value="1", id="qt-comp-range", allow_blank=False),
                    id="qt-dice-params",
                ),
                Horizontal(
                    Button("Roll", id="btn-qt-roll", variant="primary"),
                    Button("Close", id="btn-qt-close"),
                    id="qt-actions",
                ),
                id="qt-body",
            ),
            # Outside the scroll deliberately: the result is the reason the
            # modal was opened, and inside it the roll landed below the fold.
            Static("", id="qt-result"),
            ComplicationPrompt(id="qt-complication"),
            Static("", id="qt-pools"),
            id="qt-box",
        )

    def on_mount(self) -> None:
        if self.default_entity_id is not None:
            # Only preselect a character who is actually in the list; a stale id
            # (the entity was deleted, or is a location) would raise on assign.
            wanted = str(self.default_entity_id)
            if any(wanted == value for _, value in sheet_bearing_entities()):
                self.query_one("#qt-entity", Select).value = wanted
        self._show_pools()

    def _show_pools(self) -> None:
        pools = db.get_pools()
        self.query_one("#qt-pools", Static).update(
            f"[dim]Momentum {pools['momentum']}  ·  Threat {pools['threat']}[/dim]"
        )

    def _acting_entity(self) -> dict | None:
        select = self.query_one("#qt-entity", Select)
        if select.value is Select.NULL:
            return None
        return db.get_entity(int(str(select.value)))

    def _difficulty(self) -> int:
        try:
            return max(0, int(self.query_one("#qt-difficulty", Input).value.strip() or 0))
        except ValueError:
            return 2

    def action_close(self) -> None:
        self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-qt-close":
            self.dismiss()
        elif event.button.id == "btn-qt-roll":
            self.roll()
        elif event.button.id == "qt-complication-add":
            named = self.query_one(ComplicationPrompt).submit()
            if named:
                self.query_one("#qt-result", Static).update(
                    f"[#ffcb6b]Scene Trait added: {named}[/]"
                )

    def roll(self) -> None:
        entity = self._acting_entity()
        if not entity:
            self.query_one("#qt-result", Static).update("[red]Pick a character first.[/]")
            return

        sheet = sta.normalize_sheet(entity["fields"].get("sheet", {}))
        invoke = self.query_one("#qt-invoke", Switch).value
        outcome = task.resolve(
            sheet,
            db.get_pools(),
            attribute=str(self.query_one("#qt-attr", Select).value),
            department=str(self.query_one("#qt-dept", Select).value),
            difficulty=self._difficulty(),
            focus=self.query_one("#qt-focus", Switch).value,
            bonus_dice=int(str(self.query_one("#qt-bonus-dice", Select).value) or 0),
            complication_range=int(str(self.query_one("#qt-comp-range", Select).value) or 1),
            invoke_value=invoke,
        )

        if outcome.momentum_delta or outcome.threat_delta:
            db.set_pools(**task.apply(outcome, db.get_pools()))
        if outcome.determination_spent:
            # Spending Determination changes the character, not just the roll,
            # so it is written back to the sheet the same way the combat tracker
            # writes it -- a quick roll is still a real roll.
            updated = task.spend_determination(sheet, outcome)
            fields = dict(entity["fields"])
            fields["sheet"] = updated
            db.update_entity(entity["id"], entity["name"], fields, entity["notes"])
            self.query_one("#qt-invoke", Switch).value = False

        colour = "#c3e88d" if outcome.succeeded else "#ff5370"
        detail = f"{entity['name']}: {outcome.result.detail}"
        for note in outcome.notes:
            detail += f"  --  {note}"
        self.query_one("#qt-result", Static).update(f"[{colour}]{detail}[/]")
        # A Complication is something that is now true in the scene; offer to
        # write it down while the table still remembers what it was.
        self.query_one(ComplicationPrompt).show_for(outcome.result.complications)
        self._show_pools()
