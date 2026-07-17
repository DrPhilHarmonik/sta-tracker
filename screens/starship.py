from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Label, Button, Input, Select, Static, ListView, ListItem, TabbedContent, TabPane
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer

import db
import starship as ship
import dice

from screens.common import tint_border


class StarshipSheetScreen(Screen):
    """Star Trek Adventures 2e starship sheet editor."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Save"),
    ]

    def __init__(self, entity_id: int):
        super().__init__()
        self.entity_id = entity_id
        entity = db.get_entity(entity_id)
        self.sheet = ship.normalize_sheet(entity["fields"].get("sheet", {}))
        self.pending_talents: list[str] = list(self.sheet["talents"])
        self.pending_traits: list[str] = list(self.sheet["traits"])
        self.pending_weapons: list[dict] = list(self.sheet["weapons"])

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="ship-tabs"):
            with TabPane("Systems", id="tab-systems"):
                yield ScrollableContainer(Container(id="systems-fields"), id="systems-scroll")
            with TabPane("Profile", id="tab-ship-profile"):
                yield ScrollableContainer(Container(id="ship-profile-fields"), id="ship-profile-scroll")
            with TabPane("Talents & Weapons", id="tab-ship-loadout"):
                yield ScrollableContainer(Container(id="ship-loadout-fields"), id="ship-loadout-scroll")
            with TabPane("Task Roll", id="tab-ship-task"):
                yield ScrollableContainer(Container(id="ship-task-fields"), id="ship-task-scroll")
        yield Horizontal(
            Button("Recalculate", id="btn-ship-recalc", variant="primary"),
            Button("Save (Ctrl+S)", id="btn-ship-save", variant="success"),
            Button("Cancel", id="btn-ship-cancel", variant="default"),
            id="ship-actions",
        )
        yield Footer()

    async def on_mount(self):
        entity = db.get_entity(self.entity_id)
        self.title = f"{entity['name']} - Starship Sheet"
        tint_border(self.query_one("#ship-tabs"), "starship")
        await self._build_systems_tab()
        await self._build_profile_tab()
        await self._build_loadout_tab()
        await self._build_task_tab()
        self._refresh_computed_displays()
        self._refresh_talents_list()
        self._refresh_traits_list()
        self._refresh_weapons_list()

    # -- tab builders --------------------------------------------------

    async def _build_systems_tab(self):
        container = self.query_one("#systems-fields")
        sys_rows = [
            Horizontal(
                *[
                    Vertical(
                        Label(ship.SYSTEM_LABELS[s], classes="ability-cell-label"),
                        Input(value=str(self.sheet["systems"][s]), id=f"ship-sys-{s}", classes="ability-input"),
                        classes="ability-cell",
                    )
                    for s in ship.SYSTEMS[i : i + 3]
                ],
                classes="ability-grid-row",
            )
            for i in range(0, 6, 3)
        ]
        dept_rows = [
            Horizontal(
                *[
                    Vertical(
                        Label(ship.DEPARTMENT_LABELS[d], classes="ability-cell-label"),
                        Input(value=str(self.sheet["departments"][d]), id=f"ship-dept-{d}", classes="ability-input"),
                        classes="ability-cell",
                    )
                    for d in ship.DEPARTMENTS[i : i + 3]
                ],
                classes="ability-grid-row",
            )
            for i in range(0, 6, 3)
        ]
        await container.mount(
            Static("[bold]Systems[/]  (7-12)"), *sys_rows,
            Static("[bold]Departments[/]  (0-5)"), *dept_rows,
            Static("", id="ship-shields-readout"),
        )

    async def _build_profile_tab(self):
        container = self.query_one("#ship-profile-fields")
        await container.mount(
            Label("Spaceframe / Class"), Input(value=self.sheet["spaceframe"], id="ship-spaceframe"),
            Label("Registry"), Input(value=self.sheet["registry"], id="ship-registry"),
            Label("Service Year"), Input(value=self.sheet["service_year"], id="ship-service-year"),
            Label("Mission Profile"), Input(value=self.sheet["mission_profile"], id="ship-mission"),
            Label("Scale (1-10; sets Resistance)"), Input(value=str(self.sheet["scale"]), id="ship-scale", classes="stat-input"),
            Label("Shields Max (blank = Structure + Security)"), Input(value=str(self.sheet["shields_max"]), id="ship-shields-max", classes="stat-input"),
            Label("Shields Current"), Input(value=str(self.sheet["shields_current"]), id="ship-shields-current", classes="stat-input"),
            Label("Crew Support"), Input(value=str(self.sheet["crew_support"]), id="ship-crew-support", classes="stat-input"),
            Label("Notes"), Input(value=self.sheet["notes"], id="ship-notes"),
        )

    async def _build_loadout_tab(self):
        container = self.query_one("#ship-loadout-fields")
        await container.mount(
            Static("[bold]Talents[/]"),
            Horizontal(
                Input(placeholder="Talent name", id="ship-talent-input"),
                Button("+ Add", id="btn-ship-add-talent"),
                Button("Remove Selected", id="btn-ship-remove-talent"),
                id="ship-talent-actions",
            ),
            ListView(id="ship-list-talents"),
            Static("[bold]Traits[/]  (e.g. Federation Starship, Cloaking Device)"),
            Horizontal(
                Input(placeholder="Trait", id="ship-trait-input"),
                Button("+ Add", id="btn-ship-add-trait"),
                Button("Remove Selected", id="btn-ship-remove-trait"),
                id="ship-trait-actions",
            ),
            ListView(id="ship-list-traits"),
            Static("[bold]Weapons[/]  (damage dice = rating + Scale)"),
            Horizontal(
                Input(placeholder="Name", id="ship-weapon-name"),
                Input(placeholder="Damage rating", id="ship-weapon-damage", classes="stat-input"),
                Input(placeholder="Qualities", id="ship-weapon-qualities"),
                id="ship-weapon-inputs",
            ),
            Horizontal(
                Button("+ Add Weapon", id="btn-ship-add-weapon"),
                Button("Remove Selected", id="btn-ship-remove-weapon"),
                id="ship-weapon-actions",
            ),
            ListView(id="ship-list-weapons"),
        )

    async def _build_task_tab(self):
        container = self.query_one("#ship-task-fields")
        sys_options = [(ship.SYSTEM_LABELS[s], s) for s in ship.SYSTEMS]
        dept_options = [(ship.DEPARTMENT_LABELS[d], d) for d in ship.DEPARTMENTS]
        await container.mount(
            Static("[bold]Ship Task Roll[/]  (2d20 vs System + Department)"),
            Horizontal(
                Vertical(Label("System"), Select(sys_options, value="engines", id="ship-task-sys", allow_blank=False)),
                Vertical(Label("Department"), Select(dept_options, value="conn", id="ship-task-dept", allow_blank=False)),
                Vertical(Label("Difficulty"), Input(value="1", id="ship-task-difficulty", classes="stat-input")),
                id="ship-task-row",
            ),
            Button("Roll Task", id="btn-ship-roll-task", variant="primary"),
            Static("", id="ship-task-result"),
            Static("[bold]Challenge Dice[/]", classes="section-head"),
            Horizontal(
                Vertical(Label("Number of [CD]"), Input(value="1", id="ship-cd-count", classes="stat-input")),
                Button("Roll Challenge Dice", id="btn-ship-roll-cd", variant="default"),
                id="ship-cd-row",
            ),
            Static("", id="ship-cd-result"),
        )

    # -- list management -----------------------------------------------

    def _refresh_simple_list(self, list_id: str, items: list[str]):
        lv = self.query_one(f"#{list_id}", ListView)
        lv.clear()
        for item in items:
            lv.append(ListItem(Label(item)))

    def _refresh_talents_list(self):
        self._refresh_simple_list("ship-list-talents", self.pending_talents)

    def _refresh_traits_list(self):
        self._refresh_simple_list("ship-list-traits", self.pending_traits)

    def _refresh_weapons_list(self):
        lv = self.query_one("#ship-list-weapons", ListView)
        lv.clear()
        sheet = self._collect_sheet_from_widgets()
        for w in self.pending_weapons:
            dice_count = ship.weapon_dice(sheet, w)
            qualities = f" [{w['qualities']}]" if w.get("qualities") else ""
            lv.append(ListItem(Label(f"{w['name']} — {dice_count}[CD]{qualities}")))

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
        name = self.query_one("#ship-weapon-name", Input).value.strip()
        if not name:
            return
        raw = self.query_one("#ship-weapon-damage", Input).value.strip()
        try:
            damage = max(0, int(raw)) if raw else 0
        except ValueError:
            damage = 0
        qualities = self.query_one("#ship-weapon-qualities", Input).value.strip()
        self.pending_weapons.append({"name": name, "damage": damage, "qualities": qualities})
        for wid in ("#ship-weapon-name", "#ship-weapon-damage", "#ship-weapon-qualities"):
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
        systems = {s: self._to_int(f"ship-sys-{s}", ship.DEFAULT_SYSTEM) for s in ship.SYSTEMS}
        departments = {d: self._to_int(f"ship-dept-{d}", ship.DEFAULT_DEPARTMENT) for d in ship.DEPARTMENTS}
        sheet = dict(self.sheet)
        sheet.update({
            "systems": systems,
            "departments": departments,
            "scale": self._to_int("ship-scale", ship.DEFAULT_SCALE),
            "shields_max": self._to_int("ship-shields-max", 0),
            "shields_current": self._to_int("ship-shields-current", 0),
            "crew_support": self._to_int("ship-crew-support", 0),
            "talents": list(self.pending_talents),
            "traits": list(self.pending_traits),
            "weapons": list(self.pending_weapons),
            "spaceframe": self._to_text("ship-spaceframe"),
            "registry": self._to_text("ship-registry"),
            "service_year": self._to_text("ship-service-year"),
            "mission_profile": self._to_text("ship-mission"),
            "notes": self._to_text("ship-notes"),
        })
        return sheet

    def _refresh_computed_displays(self):
        sheet = self._collect_sheet_from_widgets()
        base = ship.shields_base(sheet)
        self.query_one("#ship-shields-readout", Static).update(
            f"[bold]Base Shields[/] (Structure + Security): {base}    "
            f"[bold]Resistance[/] (Scale): {ship.resistance(sheet)}"
        )
        self.sheet = sheet

    # -- actions ----------------------------------------------------------

    def _do_roll_task(self):
        sys_key = str(self.query_one("#ship-task-sys", Select).value)
        dept_key = str(self.query_one("#ship-task-dept", Select).value)
        difficulty = max(0, self._to_int("ship-task-difficulty", 1))
        sheet = self._collect_sheet_from_widgets()
        result = dice.roll_task(
            attribute=sheet["systems"][sys_key],
            department=sheet["departments"][dept_key],
            difficulty=difficulty,
        )
        colour = "#c3e88d" if result.succeeded else "#ff5370"
        detail = result.detail
        if result.momentum > 0:
            pools = db.adjust_momentum(result.momentum)
            detail += f"  --  banked {result.momentum} Momentum (pool {pools['momentum']})"
        self.query_one("#ship-task-result", Static).update(f"[{colour}]{detail}[/]")

    def _do_roll_cd(self):
        count = max(0, self._to_int("ship-cd-count", 1))
        result = dice.roll_challenge(count)
        self.query_one("#ship-cd-result", Static).update(result.detail)

    def action_save(self):
        sheet = self._collect_sheet_from_widgets()
        entity = db.get_entity(self.entity_id)
        fields = dict(entity["fields"])
        fields["sheet"] = sheet
        db.update_entity(self.entity_id, entity["name"], fields, entity["notes"])
        self.dismiss(True)

    def action_cancel(self):
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if bid == "btn-ship-save":
            self.action_save()
        elif bid == "btn-ship-cancel":
            self.action_cancel()
        elif bid == "btn-ship-recalc":
            self._refresh_computed_displays()
            self._refresh_weapons_list()
        elif bid == "btn-ship-roll-task":
            self._do_roll_task()
        elif bid == "btn-ship-roll-cd":
            self._do_roll_cd()
        elif bid == "btn-ship-add-talent":
            self._add_simple("ship-talent-input", self.pending_talents, self._refresh_talents_list)
        elif bid == "btn-ship-remove-talent":
            self._remove_selected("ship-list-talents", self.pending_talents, self._refresh_talents_list)
        elif bid == "btn-ship-add-trait":
            self._add_simple("ship-trait-input", self.pending_traits, self._refresh_traits_list)
        elif bid == "btn-ship-remove-trait":
            self._remove_selected("ship-list-traits", self.pending_traits, self._refresh_traits_list)
        elif bid == "btn-ship-add-weapon":
            self._add_weapon()
        elif bid == "btn-ship-remove-weapon":
            self._remove_selected("ship-list-weapons", self.pending_weapons, self._refresh_weapons_list)
