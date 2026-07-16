from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Label, Button, Input, Select, Static, ListView, ListItem, TabbedContent, TabPane
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer

import db
import export as exp
import sta_sheet as sta
import dice

from screens.common import tint_border

# Bonus d20s bought with Momentum/Threat, on top of the base 2.
BONUS_DICE_OPTIONS = [("2 dice (base)", "0"), ("3 dice", "1"), ("4 dice", "2"), ("5 dice", "3")]


class CharacterSheetScreen(Screen):
    """Star Trek Adventures 2e character sheet editor."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Save"),
        Binding("ctrl+e", "export_sheet", "Export Sheet"),
    ]

    def __init__(self, entity_id: int):
        super().__init__()
        self.entity_id = entity_id
        entity = db.get_entity(entity_id)
        self.entity_type = entity["type"]
        self.sheet = sta.normalize_sheet(entity["fields"].get("sheet", {}))
        # Mutable working copies of the list-valued fields.
        self.pending_focuses: list[str] = list(self.sheet["focuses"])
        self.pending_values: list[str] = list(self.sheet["values"])
        self.pending_talents: list[str] = list(self.sheet["talents"])
        self.pending_weapons: list[dict] = list(self.sheet["weapons"])
        self.pending_injuries: list[str] = list(self.sheet["injuries"])

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="sheet-tabs"):
            with TabPane("Stats", id="tab-stats"):
                yield ScrollableContainer(Container(id="stats-fields"), id="stats-scroll")
            with TabPane("Profile", id="tab-profile"):
                yield ScrollableContainer(Container(id="profile-fields"), id="profile-scroll")
            with TabPane("Focuses & Values", id="tab-focuses"):
                yield ScrollableContainer(Container(id="focuses-fields"), id="focuses-scroll")
            with TabPane("Talents & Weapons", id="tab-loadout"):
                yield ScrollableContainer(Container(id="loadout-fields"), id="loadout-scroll")
            with TabPane("Task Roll", id="tab-task"):
                yield ScrollableContainer(Container(id="task-fields"), id="task-scroll")
        yield Horizontal(
            Button("Recalculate", id="btn-recalc", variant="primary"),
            Button("Save (Ctrl+S)", id="btn-save", variant="success"),
            Button("Export Sheet", id="btn-export-sheet", variant="default"),
            Button("Cancel", id="btn-cancel", variant="default"),
            id="sheet-actions",
        )
        yield Footer()

    async def on_mount(self):
        entity = db.get_entity(self.entity_id)
        self.title = f"{entity['name']} - Character Sheet"
        tint_border(self.query_one("#sheet-tabs"), self.entity_type)
        await self._build_stats_tab()
        await self._build_profile_tab()
        await self._build_focuses_tab()
        await self._build_loadout_tab()
        await self._build_task_tab()
        self._refresh_computed_displays()
        self._refresh_focuses_list()
        self._refresh_values_list()
        self._refresh_talents_list()
        self._refresh_weapons_list()
        self._refresh_injuries_list()

    # -- tab builders --------------------------------------------------

    async def _build_stats_tab(self):
        container = self.query_one("#stats-fields")
        attr_rows = [
            Horizontal(
                *[
                    Vertical(
                        Label(sta.ATTRIBUTE_LABELS[a], classes="ability-cell-label"),
                        Input(value=str(self.sheet["attributes"][a]), id=f"sta-attr-{a}", classes="ability-input"),
                        classes="ability-cell",
                    )
                    for a in sta.ATTRIBUTES[i : i + 3]
                ],
                classes="ability-grid-row",
            )
            for i in range(0, 6, 3)
        ]
        dept_rows = [
            Horizontal(
                *[
                    Vertical(
                        Label(sta.DEPARTMENT_LABELS[d], classes="ability-cell-label"),
                        Input(value=str(self.sheet["departments"][d]), id=f"sta-dept-{d}", classes="ability-input"),
                        classes="ability-cell",
                    )
                    for d in sta.DEPARTMENTS[i : i + 3]
                ],
                classes="ability-grid-row",
            )
            for i in range(0, 6, 3)
        ]
        await container.mount(
            Static("[bold]Attributes[/]  (7-12)"), *attr_rows,
            Static("[bold]Departments[/]  (0-5)"), *dept_rows,
            Static("", id="sta-stress-readout"),
        )

    async def _build_profile_tab(self):
        container = self.query_one("#profile-fields")
        await container.mount(
            Label("Species"), Input(value=self.sheet["species"], id="sta-species"),
            Label("Rank"), Input(value=self.sheet["rank"], id="sta-rank"),
            Label("Career (Cadet / Officer / Veteran)"), Input(value=self.sheet["career"], id="sta-career"),
            Label("Role (e.g. Chief Engineer)"), Input(value=self.sheet["role"], id="sta-role"),
            Label("Determination (0-3)"), Input(value=str(self.sheet["determination"]), id="sta-determination", classes="stat-input"),
            Label("Protection / Soak"), Input(value=str(self.sheet["protection"]), id="sta-protection", classes="stat-input"),
            Label("Stress Max (blank = Fitness + Security)"), Input(value=str(self.sheet["stress_max"]), id="sta-stress-max", classes="stat-input"),
            Label("Stress Current"), Input(value=str(self.sheet["stress_current"]), id="sta-stress-current", classes="stat-input"),
            Label("Equipment"), Input(value=self.sheet["equipment"], id="sta-equipment"),
            Label("Special / Notes"), Input(value=self.sheet["special"], id="sta-special"),
        )

    async def _build_focuses_tab(self):
        container = self.query_one("#focuses-fields")
        await container.mount(
            Static("[bold]Focuses[/]  (a relevant Focus scores criticals at or under the Department)"),
            Horizontal(
                Input(placeholder="Focus, e.g. Warp Field Dynamics", id="focus-input"),
                Button("+ Add", id="btn-add-focus"),
                Button("Remove Selected", id="btn-remove-focus"),
                id="focus-actions",
            ),
            ListView(id="list-focuses"),
            Static("[bold]Values[/]  (narrative statements; may be invoked or challenged)"),
            Horizontal(
                Input(placeholder="Value statement", id="value-input"),
                Button("+ Add", id="btn-add-value"),
                Button("Remove Selected", id="btn-remove-value"),
                id="value-actions",
            ),
            ListView(id="list-values"),
        )

    async def _build_loadout_tab(self):
        container = self.query_one("#loadout-fields")
        await container.mount(
            Static("[bold]Talents[/]"),
            Horizontal(
                Input(placeholder="Talent name", id="talent-input"),
                Button("+ Add", id="btn-add-talent"),
                Button("Remove Selected", id="btn-remove-talent"),
                id="talent-actions",
            ),
            ListView(id="list-talents"),
            Static("[bold]Weapons[/]  (damage dice = rating + Security)"),
            Horizontal(
                Input(placeholder="Name", id="weapon-name"),
                Input(placeholder="Damage rating", id="weapon-damage", classes="stat-input"),
                Input(placeholder="Qualities", id="weapon-qualities"),
                id="weapon-inputs",
            ),
            Horizontal(
                Button("+ Add Weapon", id="btn-add-weapon"),
                Button("Remove Selected", id="btn-remove-weapon"),
                id="weapon-actions",
            ),
            ListView(id="list-weapons"),
            Static("[bold]Injuries[/]"),
            Horizontal(
                Input(placeholder="Injury / complication", id="injury-input"),
                Button("+ Add", id="btn-add-injury"),
                Button("Remove Selected", id="btn-remove-injury"),
                id="injury-actions",
            ),
            ListView(id="list-injuries"),
        )

    async def _build_task_tab(self):
        container = self.query_one("#task-fields")
        attr_options = [(sta.ATTRIBUTE_LABELS[a], a) for a in sta.ATTRIBUTES]
        dept_options = [(sta.DEPARTMENT_LABELS[d], d) for d in sta.DEPARTMENTS]
        await container.mount(
            Static("[bold]Task Roll[/]  (2d20 vs Attribute + Department)"),
            Horizontal(
                Vertical(Label("Attribute"), Select(attr_options, value="control", id="task-attr", allow_blank=False)),
                Vertical(Label("Department"), Select(dept_options, value="command", id="task-dept", allow_blank=False)),
                id="task-row1",
            ),
            Horizontal(
                Vertical(Label("Difficulty"), Input(value="1", id="task-difficulty", classes="stat-input")),
                Vertical(Label("Focus"), Select([("(no focus)", "")], value="", id="task-focus", allow_blank=False)),
                Vertical(Label("Dice"), Select(BONUS_DICE_OPTIONS, value="0", id="task-bonus-dice", allow_blank=False)),
                id="task-row2",
            ),
            Button("Roll Task", id="btn-roll-task", variant="primary"),
            Static("", id="task-result"),
            Static("[bold]Challenge Dice[/]", classes="section-head"),
            Horizontal(
                Vertical(Label("Number of [CD]"), Input(value="1", id="cd-count", classes="stat-input")),
                Button("Roll Challenge Dice", id="btn-roll-cd", variant="default"),
                id="cd-row",
            ),
            Static("", id="cd-result"),
        )
        self._refresh_focus_options()

    # -- list management -----------------------------------------------

    def _refresh_simple_list(self, list_id: str, items: list[str]):
        lv = self.query_one(f"#{list_id}", ListView)
        lv.clear()
        for item in items:
            lv.append(ListItem(Label(item)))

    def _refresh_focuses_list(self):
        self._refresh_simple_list("list-focuses", self.pending_focuses)
        self._refresh_focus_options()

    def _refresh_values_list(self):
        self._refresh_simple_list("list-values", self.pending_values)

    def _refresh_talents_list(self):
        self._refresh_simple_list("list-talents", self.pending_talents)

    def _refresh_injuries_list(self):
        self._refresh_simple_list("list-injuries", self.pending_injuries)

    def _refresh_weapons_list(self):
        lv = self.query_one("#list-weapons", ListView)
        lv.clear()
        for w in self.pending_weapons:
            dice_count = sta.weapon_dice(self._collect_sheet_from_widgets(), w)
            qualities = f" [{w['qualities']}]" if w.get("qualities") else ""
            lv.append(ListItem(Label(f"{w['name']} — {dice_count}[CD]{qualities}")))

    def _refresh_focus_options(self):
        try:
            select = self.query_one("#task-focus", Select)
        except Exception:
            return
        previous = select.value
        options = [("(no focus)", "")] + [(f, f) for f in self.pending_focuses]
        select.set_options(options)
        if previous in ("",) or any(previous == v for _, v in options):
            select.value = previous if previous is not Select.BLANK else ""

    def _add_simple(self, input_id: str, target: list[str], refresh):
        value = self.query_one(f"#{input_id}", Input).value.strip()
        if not value:
            return
        target.append(value)
        self.query_one(f"#{input_id}", Input).value = ""
        refresh()

    def _remove_selected(self, list_id: str, target: list, refresh):
        lv = self.query_one(f"#{list_id}", ListView)
        if lv.index is not None and lv.index < len(target):
            del target[lv.index]
            refresh()

    def _add_weapon(self):
        name = self.query_one("#weapon-name", Input).value.strip()
        if not name:
            return
        raw = self.query_one("#weapon-damage", Input).value.strip()
        try:
            damage = max(0, int(raw)) if raw else 0
        except ValueError:
            damage = 0
        qualities = self.query_one("#weapon-qualities", Input).value.strip()
        self.pending_weapons.append({"name": name, "damage": damage, "qualities": qualities})
        for wid in ("#weapon-name", "#weapon-damage", "#weapon-qualities"):
            self.query_one(wid, Input).value = ""
        self._refresh_weapons_list()

    # -- collecting + computed display ----------------------------------

    def _to_int(self, widget_id: str, default: int = 0) -> int:
        raw = self.query_one(f"#{widget_id}", Input).value.strip()
        try:
            return int(raw) if raw else default
        except ValueError:
            return default

    def _to_text(self, widget_id: str) -> str:
        return self.query_one(f"#{widget_id}", Input).value.strip()

    def _collect_sheet_from_widgets(self) -> dict:
        attributes = {a: self._to_int(f"sta-attr-{a}", sta.DEFAULT_ATTRIBUTE) for a in sta.ATTRIBUTES}
        departments = {d: self._to_int(f"sta-dept-{d}", sta.DEFAULT_DEPARTMENT) for d in sta.DEPARTMENTS}
        sheet = dict(self.sheet)
        sheet.update({
            "attributes": attributes,
            "departments": departments,
            "focuses": list(self.pending_focuses),
            "values": list(self.pending_values),
            "talents": list(self.pending_talents),
            "weapons": list(self.pending_weapons),
            "injuries": list(self.pending_injuries),
            "determination": self._to_int("sta-determination", 1),
            "protection": self._to_int("sta-protection", 0),
            "stress_max": self._to_int("sta-stress-max", 0),
            "stress_current": self._to_int("sta-stress-current", 0),
            "species": self._to_text("sta-species"),
            "rank": self._to_text("sta-rank"),
            "career": self._to_text("sta-career"),
            "role": self._to_text("sta-role"),
            "equipment": self._to_text("sta-equipment"),
            "special": self._to_text("sta-special"),
        })
        return sheet

    def _refresh_computed_displays(self):
        sheet = self._collect_sheet_from_widgets()
        base = sta.base_stress(sheet)
        self.query_one("#sta-stress-readout", Static).update(
            f"[bold]Base Stress[/] (Fitness + Security): {base}"
        )
        self.sheet = sheet

    # -- actions ----------------------------------------------------------

    def _do_roll_task(self):
        attr_key = str(self.query_one("#task-attr", Select).value)
        dept_key = str(self.query_one("#task-dept", Select).value)
        difficulty = self._to_int("task-difficulty", 1)
        focus_value = self.query_one("#task-focus", Select).value
        focus = bool(focus_value) and focus_value is not Select.BLANK
        bonus = int(str(self.query_one("#task-bonus-dice", Select).value) or 0)

        sheet = self._collect_sheet_from_widgets()
        result = dice.roll_task(
            attribute=sheet["attributes"][attr_key],
            department=sheet["departments"][dept_key],
            difficulty=max(0, difficulty),
            focus=focus,
            dice=2 + bonus,
        )
        colour = "#c3e88d" if result.succeeded else "#ff5370"
        detail = result.detail
        # Successes beyond the Difficulty become Momentum, which belongs to the
        # shared table pool rather than this character (see momentum.py). Bank
        # it automatically and report the pool's new level.
        if result.momentum > 0:
            pools = db.adjust_momentum(result.momentum)
            detail += f"  --  banked {result.momentum} Momentum (pool {pools['momentum']})"
        self.query_one("#task-result", Static).update(f"[{colour}]{detail}[/]")

    def _do_roll_cd(self):
        count = self._to_int("cd-count", 1)
        result = dice.roll_challenge(max(0, count))
        self.query_one("#cd-result", Static).update(result.detail)

    def action_save(self):
        sheet = self._collect_sheet_from_widgets()
        entity = db.get_entity(self.entity_id)
        fields = dict(entity["fields"])
        fields["sheet"] = sheet
        db.update_entity(self.entity_id, entity["name"], fields, entity["notes"])
        self.dismiss(True)

    def action_cancel(self):
        self.dismiss(False)

    def action_export_sheet(self):
        try:
            path = exp.export_entity_sheet(self.entity_id)
            self.app.notify(f"Exported to {path}", severity="information")
        except Exception as exc:
            self.app.notify(f"Export failed: {exc}", severity="error")

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if bid == "btn-save":
            self.action_save()
        elif bid == "btn-export-sheet":
            self.action_export_sheet()
        elif bid == "btn-cancel":
            self.action_cancel()
        elif bid == "btn-recalc":
            self._refresh_computed_displays()
            self._refresh_weapons_list()
        elif bid == "btn-roll-task":
            self._do_roll_task()
        elif bid == "btn-roll-cd":
            self._do_roll_cd()
        elif bid == "btn-add-focus":
            self._add_simple("focus-input", self.pending_focuses, self._refresh_focuses_list)
        elif bid == "btn-remove-focus":
            self._remove_selected("list-focuses", self.pending_focuses, self._refresh_focuses_list)
        elif bid == "btn-add-value":
            self._add_simple("value-input", self.pending_values, self._refresh_values_list)
        elif bid == "btn-remove-value":
            self._remove_selected("list-values", self.pending_values, self._refresh_values_list)
        elif bid == "btn-add-talent":
            self._add_simple("talent-input", self.pending_talents, self._refresh_talents_list)
        elif bid == "btn-remove-talent":
            self._remove_selected("list-talents", self.pending_talents, self._refresh_talents_list)
        elif bid == "btn-add-weapon":
            self._add_weapon()
        elif bid == "btn-remove-weapon":
            self._remove_selected("list-weapons", self.pending_weapons, self._refresh_weapons_list)
        elif bid == "btn-add-injury":
            self._add_simple("injury-input", self.pending_injuries, self._refresh_injuries_list)
        elif bid == "btn-remove-injury":
            self._remove_selected("list-injuries", self.pending_injuries, self._refresh_injuries_list)
