from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Label, Button, Input, Select, Static
from textual.containers import Container, Horizontal, ScrollableContainer

import db
import sta_sheet as sta
import advancement as adv
import talents as talents_lib
import focuses as focuses_lib

from screens.common import DismissableScreen, tint_border

# Operation -> label for the advancement picker.
OPERATIONS = [
    ("Swap two Attributes (+1 / -1)", "swap_attr"),
    ("Increase one Attribute (+1)", "increase_attr"),
    ("Swap two Departments (+1 / -1)", "swap_dept"),
    ("Increase one Department (+1)", "increase_dept"),
    ("Add a Focus", "add_focus"),
    ("Add a Talent", "add_talent"),
    ("Record a note only", "note_only"),
]


class MilestoneScreen(DismissableScreen):
    """Record Milestones and apply the character advancement they grant.

    STA has no XP: a character changes by spending a Milestone on a small,
    validated edit (see advancement.py). Every application is logged on the
    sheet with its type, date, and a summary of what changed."""

    BINDINGS = [Binding("escape", "dismiss_screen", "Back")]

    def __init__(self, entity_id: int):
        super().__init__()
        self.entity_id = entity_id

    def compose(self) -> ComposeResult:
        attr_options = [(sta.ATTRIBUTE_LABELS[a], a) for a in sta.ATTRIBUTES]
        dept_options = [(sta.DEPARTMENT_LABELS[d], d) for d in sta.DEPARTMENTS]
        yield Header()
        yield ScrollableContainer(
            Static("[bold]Apply a Milestone[/]"),
            Horizontal(
                Container(Label("Milestone Type"),
                          Select([(t, t) for t in adv.MILESTONE_TYPES], value=adv.DEFAULT_MILESTONE_TYPE,
                                 id="milestone-type", allow_blank=False)),
                Container(Label("Advancement"),
                          Select(OPERATIONS, value="swap_attr", id="milestone-op", allow_blank=False)),
                id="milestone-row1",
            ),
            Horizontal(
                Container(Label("Attribute +1"), Select(attr_options, value="control", id="milestone-attr-up", allow_blank=False)),
                Container(Label("Attribute -1"), Select(attr_options, value="daring", id="milestone-attr-down", allow_blank=False)),
                id="milestone-row2",
            ),
            Horizontal(
                Container(Label("Department +1"), Select(dept_options, value="command", id="milestone-dept-up", allow_blank=False)),
                Container(Label("Department -1"), Select(dept_options, value="conn", id="milestone-dept-down", allow_blank=False)),
                id="milestone-row3",
            ),
            Label("New Focus (for 'Add a Focus')"),
            Input(placeholder="e.g. Warp Field Dynamics", id="milestone-focus"),
            Label("New Talent (for 'Add a Talent')"),
            Input(placeholder="Talent name", id="milestone-talent"),
            Label("Note (optional; required for note-only)"),
            Input(placeholder="What happened?", id="milestone-note"),
            Horizontal(
                Button("Apply Milestone", id="btn-apply-milestone", variant="success"),
                Button("Back", id="btn-milestone-close"),
                id="milestone-actions",
            ),
            Static("", id="milestone-status"),
            Static("[bold]Milestone Log[/]"),
            Static("", id="milestone-log"),
            id="milestone-scroll",
        )
        yield Footer()

    async def on_mount(self):
        entity = db.get_entity(self.entity_id)
        self.title = f"{entity['name']} - Milestones" if entity else "Milestones"
        tint_border(self.query_one("#milestone-scroll"), "adventurer")
        self._refresh_log()

    # -- log --------------------------------------------------------------

    def _sheet(self) -> dict:
        entity = db.get_entity(self.entity_id)
        return sta.normalize_sheet(entity["fields"].get("sheet", {}))

    def _refresh_log(self):
        milestones = self._sheet()["milestones"]
        if not milestones:
            self.query_one("#milestone-log", Static).update("[dim]No milestones recorded yet.[/dim]")
            return
        lines = []
        for m in reversed(milestones):
            when = f"[dim]{m['date']}[/dim] " if m["date"] else ""
            lines.append(f"{when}[bold]{m['type']}[/] — {m['note']}")
        self.query_one("#milestone-log", Static).update("\n".join(lines))

    # -- apply ------------------------------------------------------------

    def _apply_operation(self, op: str, sheet: dict) -> str:
        """Mutate the sheet for the chosen operation; return a human summary or
        raise ValueError with a reason to show the GM."""
        if op == "swap_attr":
            up = str(self.query_one("#milestone-attr-up", Select).value)
            down = str(self.query_one("#milestone-attr-down", Select).value)
            sheet["attributes"] = adv.swap_attributes(sheet["attributes"], up, down)
            return f"{sta.ATTRIBUTE_LABELS[up]} +1 / {sta.ATTRIBUTE_LABELS[down]} -1"
        if op == "increase_attr":
            key = str(self.query_one("#milestone-attr-up", Select).value)
            sheet["attributes"] = adv.increase_attribute(sheet["attributes"], key)
            return f"{sta.ATTRIBUTE_LABELS[key]} +1"
        if op == "swap_dept":
            up = str(self.query_one("#milestone-dept-up", Select).value)
            down = str(self.query_one("#milestone-dept-down", Select).value)
            sheet["departments"] = adv.swap_departments(sheet["departments"], up, down)
            return f"{sta.DEPARTMENT_LABELS[up]} +1 / {sta.DEPARTMENT_LABELS[down]} -1"
        if op == "increase_dept":
            key = str(self.query_one("#milestone-dept-up", Select).value)
            sheet["departments"] = adv.increase_department(sheet["departments"], key)
            return f"{sta.DEPARTMENT_LABELS[key]} +1"
        if op == "add_focus":
            name = self.query_one("#milestone-focus", Input).value.strip()
            if not name:
                raise ValueError("Enter a Focus to add")
            if any(f.lower() == name.lower() for f in sheet["focuses"]):
                raise ValueError(f"Already has the Focus '{name}'")
            sheet["focuses"] = sheet["focuses"] + [name]
            focuses_lib.add(name)
            return f"Focus: {name}"
        if op == "add_talent":
            name = self.query_one("#milestone-talent", Input).value.strip()
            if not name:
                raise ValueError("Enter a Talent to add")
            sheet["talents"] = sheet["talents"] + [name]
            talents_lib.save(name)
            return f"Talent: {name}"
        return ""  # note_only

    def _apply(self):
        entity = db.get_entity(self.entity_id)
        sheet = sta.normalize_sheet(entity["fields"].get("sheet", {}))
        op = str(self.query_one("#milestone-op", Select).value)
        mtype = str(self.query_one("#milestone-type", Select).value)
        user_note = self.query_one("#milestone-note", Input).value.strip()

        try:
            summary = self._apply_operation(op, sheet)
        except ValueError as exc:
            self.query_one("#milestone-status", Static).update(f"[red]{exc}[/]")
            return
        if op == "note_only" and not user_note:
            self.query_one("#milestone-status", Static).update("[red]Enter a note for a note-only milestone[/]")
            return

        note = " — ".join(part for part in (summary, user_note) if part)
        sheet["milestones"] = sheet["milestones"] + [{"type": mtype, "date": date.today().isoformat(), "note": note}]
        fields = dict(entity["fields"])
        fields["sheet"] = sheet
        db.update_entity(self.entity_id, entity["name"], fields, entity["notes"])

        self.query_one("#milestone-note", Input).value = ""
        self.query_one("#milestone-focus", Input).value = ""
        self.query_one("#milestone-talent", Input).value = ""
        self.query_one("#milestone-status", Static).update(f"[#c3e88d]Recorded {mtype} Milestone: {note}[/]")
        self._refresh_log()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-apply-milestone":
            self._apply()
        elif event.button.id == "btn-milestone-close":
            self.dismiss()
