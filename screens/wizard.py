from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Label, Button, Input, Select, Static, ListView, ListItem
from textual.containers import Container, Horizontal, ScrollableContainer
from textual import on

import db
import sta_sheet as sta
import species as species_mod
from models import ENTITY_LABELS

from screens.common import DismissableScreen, entity_ref_options, schema_choices, tint_border

# The only entity types the wizard knows how to build: a lifepath-guided flow
# for adventurer/enemy, and a basic-info-only flow for npc. Everything else
# (location, quest, faction, item, session, encounter) already has an adequate
# single-screen "+ Add" form and has no wizard steps defined.
WIZARD_ENTITY_TYPES = ("npc", "adventurer", "enemy")

# Suggested starting Attribute spread (STA 2e Attributes run ~7-12). The GM
# freely edits these on the Attributes step; species bonuses stack on top.
DEFAULT_ATTRIBUTE_SPREAD = {
    "control": 9, "daring": 8, "fitness": 9,
    "insight": 8, "presence": 10, "reason": 8,
}
# Suggested starting Department spread (Departments run 0-5).
DEFAULT_DEPARTMENT_SPREAD = {
    "command": 2, "conn": 1, "engineering": 1,
    "security": 2, "medicine": 1, "science": 1,
}


class WizardScreen(DismissableScreen):
    """Guided multi-step character creation, STA 2e lifepath style.

    NPCs get a single "basic info" step since they carry no stat block.
    Adventurers and Enemies walk Basic Info -> Species -> Attributes ->
    Departments -> (advanced mode only: Focuses & Values, Talents & Profile)
    -> Review & Create. The real character data is written into an STA sheet
    blob; the flat entity fields carry only what the list views need.
    """

    BINDINGS = [Binding("escape", "dismiss_screen", "Back")]

    def __init__(self, entity_type: str, mode: str = "quick", prefill: dict | None = None, link_to_npc_id: int | None = None, link_rel_type: str = "hostile form of"):
        super().__init__()
        self.entity_type = entity_type
        self.mode = mode
        self.link_to_npc_id = link_to_npc_id
        self.link_rel_type = link_rel_type
        self.data = {
            "name": "", "player_name": "", "role": "", "status": "", "location": "",
            "species": species_mod.SPECIES_NAMES[0], "species_choice_attrs": [],
            "attributes": dict(DEFAULT_ATTRIBUTE_SPREAD),
            "departments": dict(DEFAULT_DEPARTMENT_SPREAD),
            "focuses": [], "values": [], "talents": [],
            "rank": "", "career": "", "determination": 1,
            # enemy-only flat carry-overs (may arrive via prefill)
            "creature_type": "", "alignment": "",
        }
        if prefill:
            self.data.update(prefill)
        self.pending_focuses: list[str] = list(self.data["focuses"])
        self.pending_values: list[str] = list(self.data["values"])
        self.pending_talents: list[str] = list(self.data["talents"])
        self.steps = self._build_steps()
        self.step_index = 0
        self._species_step_built_for = None

    def _build_steps(self) -> list[str]:
        if self.entity_type == "npc":
            return ["basic_npc", "review"]
        steps = ["basic", "species", "attributes", "departments"]
        if self.mode == "advanced":
            steps += ["focuses_values", "talents_profile"]
        steps.append("review")
        return steps

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(Container(id="wizard-step"), id="wizard-scroll")
        yield Container(
            Static("", id="wizard-error"),
            Horizontal(
                Button("< Back", id="btn-wiz-back"),
                Button("Next >", id="btn-wiz-next", variant="primary"),
                id="wizard-nav",
            ),
            id="wizard-actions",
        )
        yield Footer()

    async def on_mount(self):
        mode_label = "Quick" if self.mode == "quick" else "Advanced"
        self.title = f"Create {ENTITY_LABELS[self.entity_type]} ({mode_label} Wizard)"
        tint_border(self.query_one("#wizard-scroll"), self.entity_type)
        await self._render_step()

    # -- navigation -------------------------------------------------------

    async def _render_step(self):
        container = self.query_one("#wizard-step")
        await container.remove_children()
        step = self.steps[self.step_index]
        await getattr(self, f"_build_step_{step}")(container)
        self.query_one("#btn-wiz-back", Button).disabled = self.step_index == 0
        self.query_one("#btn-wiz-next", Button).label = "Create Character" if step == "review" else "Next >"
        self.query_one("#wizard-error", Static).update("")

    async def _go_back(self):
        if self.step_index == 0:
            return
        self.step_index -= 1
        await self._render_step()

    async def _go_next(self):
        step = self.steps[self.step_index]
        collector = getattr(self, f"_collect_step_{step}", None)
        if collector:
            error = collector()
            if error:
                self.query_one("#wizard-error", Static).update(f"[red]{error}[/red]")
                return
        if step == "review":
            self._create_entity()
            return
        self.step_index += 1
        await self._render_step()

    async def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if bid == "btn-wiz-back":
            await self._go_back()
        elif bid == "btn-wiz-next":
            await self._go_next()
        elif bid == "btn-wiz-reset-attrs":
            self._reset_inputs(DEFAULT_ATTRIBUTE_SPREAD, "wiz-attr")
        elif bid == "btn-wiz-reset-depts":
            self._reset_inputs(DEFAULT_DEPARTMENT_SPREAD, "wiz-dept")
        elif bid == "btn-wiz-add-focus":
            self._add_simple("wiz-focus-input", self.pending_focuses, "wiz-list-focuses")
        elif bid == "btn-wiz-remove-focus":
            self._remove_simple(self.pending_focuses, "wiz-list-focuses")
        elif bid == "btn-wiz-add-value":
            self._add_simple("wiz-value-input", self.pending_values, "wiz-list-values")
        elif bid == "btn-wiz-remove-value":
            self._remove_simple(self.pending_values, "wiz-list-values")
        elif bid == "btn-wiz-add-talent":
            self._add_simple("wiz-talent-input", self.pending_talents, "wiz-list-talents")
        elif bid == "btn-wiz-remove-talent":
            self._remove_simple(self.pending_talents, "wiz-list-talents")

    # -- step builders ------------------------------------------------

    async def _build_step_basic_npc(self, container):
        status_choices = schema_choices("npc", "status")
        await container.mount(
            Static("[bold]Basic Info[/]"),
            Label("Name"), Input(value=self.data["name"], id="wiz-name"),
            Label("Species"), Input(value=self.data.get("species_text", ""), id="wiz-species-text"),
            Label("Role / Title"), Input(value=self.data["role"], id="wiz-role"),
            Label("Status"),
            Select([(s, s) for s in status_choices], id="wiz-status",
                   value=self.data["status"] or Select.NULL, allow_blank=True, prompt="Select status..."),
            Label("Current Location"),
            Select(entity_ref_options("location", self.data["location"]), id="wiz-location",
                   value=self.data["location"] or Select.NULL, allow_blank=True, prompt="Select location..."),
        )

    async def _build_step_basic(self, container):
        widgets = [
            Static("[bold]Basic Info[/]"),
            Label("Name"), Input(value=self.data["name"], id="wiz-name"),
        ]
        if self.entity_type == "adventurer":
            widgets += [Label("Player Name"), Input(value=self.data["player_name"], id="wiz-player-name")]
        await container.mount(*widgets)

    async def _build_step_species(self, container):
        current = self.data["species"] if self.data["species"] in species_mod.SPECIES else species_mod.SPECIES_NAMES[0]
        self._species_step_built_for = current
        data = species_mod.SPECIES[current]
        widgets = [
            Static("[bold]Species[/]"),
            Label("Species"),
            Select([(name, name) for name in species_mod.SPECIES_NAMES], id="wiz-species-select",
                   allow_blank=False, value=current),
        ]
        choice_bonus = data.get("choice_bonus", 0)
        if choice_bonus:
            attr_options = [(sta.ATTRIBUTE_LABELS[a], a) for a in sta.ATTRIBUTES]
            chosen = self.data["species_choice_attrs"]
            widgets.append(Static(f"[dim]Choose {choice_bonus} different Attributes to each get +1[/]"))
            defaults = ["control", "presence", "fitness"]
            for i in range(choice_bonus):
                widgets += [
                    Label(f"Bonus Attribute {i + 1}"),
                    Select(attr_options, id=f"wiz-species-choice-{i}", allow_blank=False,
                           value=chosen[i] if i < len(chosen) else defaults[i % len(defaults)]),
                ]
        else:
            parts = [f"{sta.ATTRIBUTE_LABELS[a]} +{b}" for a, b in data["attribute_bonuses"].items()]
            widgets.append(Static(f"[dim]Attribute bonuses: {', '.join(parts)}[/]"))
        if data.get("focus_suggestions"):
            widgets.append(Static(f"[dim]Suggested Focuses: {', '.join(data['focus_suggestions'])}[/]"))
        await container.mount(*widgets)

    @on(Select.Changed, "#wiz-species-select")
    async def _on_species_changed(self, event: Select.Changed):
        if self.steps[self.step_index] != "species":
            return
        new_species = str(event.value)
        # Select fires Changed on its own initial mount; only re-render on an
        # actual user-driven change, or this re-enters _render_step() while the
        # original mount is still in progress and corrupts later widgets.
        if new_species == self._species_step_built_for:
            return
        self.data["species"] = new_species
        await self._render_step()

    async def _build_step_attributes(self, container):
        rows = []
        for a in sta.ATTRIBUTES:
            bonus = species_mod.attribute_bonus_total(self.data["species"], a, self.data["species_choice_attrs"]) if self.entity_type == "adventurer" else 0
            rows.append(Horizontal(
                Label(sta.ATTRIBUTE_LABELS[a], classes="ability-label"),
                Input(value=str(self.data["attributes"][a]), id=f"wiz-attr-{a}", classes="ability-input"),
                Static(f"+{bonus} species" if bonus else "", classes="race-bonus-badge"),
                classes="ability-row",
            ))
        await container.mount(
            Static("[bold]Attributes[/] - assign values (7-12); species bonuses stack on top"),
            *rows,
            Button("Reset to Suggested Spread", id="btn-wiz-reset-attrs"),
        )

    async def _build_step_departments(self, container):
        rows = [
            Horizontal(
                Label(sta.DEPARTMENT_LABELS[d], classes="ability-label"),
                Input(value=str(self.data["departments"][d]), id=f"wiz-dept-{d}", classes="ability-input"),
                classes="ability-row",
            )
            for d in sta.DEPARTMENTS
        ]
        await container.mount(
            Static("[bold]Departments[/] - assign values (0-5)"),
            *rows,
            Button("Reset to Suggested Spread", id="btn-wiz-reset-depts"),
        )

    async def _build_step_focuses_values(self, container):
        await container.mount(
            Static("[bold]Focuses[/] (areas of expertise that sharpen a Task roll)"),
            Horizontal(
                Input(placeholder="e.g. Astrophysics", id="wiz-focus-input"),
                Button("+ Add", id="btn-wiz-add-focus"),
                Button("Remove Selected", id="btn-wiz-remove-focus"),
            ),
            ListView(id="wiz-list-focuses"),
            Static("[bold]Values[/] (beliefs that can be invoked or challenged)"),
            Horizontal(
                Input(placeholder="e.g. The needs of the many", id="wiz-value-input"),
                Button("+ Add", id="btn-wiz-add-value"),
                Button("Remove Selected", id="btn-wiz-remove-value"),
            ),
            ListView(id="wiz-list-values"),
        )
        self._refresh_list(self.pending_focuses, "wiz-list-focuses")
        self._refresh_list(self.pending_values, "wiz-list-values")

    async def _build_step_talents_profile(self, container):
        await container.mount(
            Static("[bold]Talents[/]"),
            Horizontal(
                Input(placeholder="Talent name", id="wiz-talent-input"),
                Button("+ Add", id="btn-wiz-add-talent"),
                Button("Remove Selected", id="btn-wiz-remove-talent"),
            ),
            ListView(id="wiz-list-talents"),
            Static("[bold]Profile[/]"),
            Label("Rank"), Input(value=self.data["rank"], id="wiz-rank", placeholder="e.g. Lieutenant"),
            Label("Career / Track"), Input(value=self.data["career"], id="wiz-career", placeholder="e.g. Officer"),
            Label("Role"), Input(value=self.data["role"], id="wiz-role", placeholder="e.g. Chief Engineer"),
        )
        self._refresh_list(self.pending_talents, "wiz-list-talents")

    async def _build_step_review(self, container):
        if self.entity_type == "npc":
            lines = [
                f"[bold]{self.data['name'] or '(unnamed)'}[/] - NPC",
                f"  Species: {self.data.get('species_text', '')}   Role: {self.data['role']}",
                f"  Status: {self.data['status']}   Location: {self.data['location']}",
            ]
            await container.mount(
                Static("[bold]Review & Create[/]"),
                Static("\n".join(lines), id="wiz-review-summary"),
            )
            return

        attributes = self._effective_attributes()
        fitness = attributes["fitness"]
        security = self.data["departments"]["security"]
        lines = [f"[bold]{self.data['name'] or '(unnamed)'}[/] - {ENTITY_LABELS[self.entity_type]}"]
        attr_parts = [f"{sta.ATTRIBUTE_LABELS[a]} {attributes[a]}" for a in sta.ATTRIBUTES]
        lines.append("  " + "   ".join(attr_parts))
        dept_parts = [f"{sta.DEPARTMENT_LABELS[d]} {self.data['departments'][d]}" for d in sta.DEPARTMENTS]
        lines.append("  " + "   ".join(dept_parts))
        if self.entity_type == "adventurer":
            lines.append(f"  Species: {self.data['species']}   Base Stress: {fitness + security} (Fitness + Security)")
        else:
            lines.append(f"  Species: {self.data['species']}   Base Stress: {fitness + security}")
        if self.pending_focuses:
            lines.append(f"  Focuses: {', '.join(self.pending_focuses)}")
        if self.pending_values:
            lines.append(f"  Values: {', '.join(self.pending_values)}")
        if self.pending_talents:
            lines.append(f"  Talents: {', '.join(self.pending_talents)}")

        await container.mount(
            Static("[bold]Review & Create[/]"),
            Static("\n".join(lines), id="wiz-review-summary"),
            Label("Starting Determination (0-3)"),
            Input(value=str(self.data["determination"]), id="wiz-determination", classes="ability-input"),
        )

    # -- step data collection ------------------------------------------

    def _collect_step_basic_npc(self):
        self.data["name"] = self.query_one("#wiz-name", Input).value.strip()
        self.data["species_text"] = self.query_one("#wiz-species-text", Input).value.strip()
        self.data["role"] = self.query_one("#wiz-role", Input).value.strip()
        status = self.query_one("#wiz-status", Select).value
        self.data["status"] = "" if status is Select.NULL else str(status)
        location = self.query_one("#wiz-location", Select).value
        self.data["location"] = "" if location is Select.NULL else str(location)
        if not self.data["name"]:
            return "Name is required."
        return None

    def _collect_step_basic(self):
        self.data["name"] = self.query_one("#wiz-name", Input).value.strip()
        if self.entity_type == "adventurer":
            self.data["player_name"] = self.query_one("#wiz-player-name", Input).value.strip()
        if not self.data["name"]:
            return "Name is required."
        return None

    def _collect_step_species(self):
        self.data["species"] = str(self.query_one("#wiz-species-select", Select).value)
        choice_bonus = species_mod.SPECIES.get(self.data["species"], {}).get("choice_bonus", 0)
        if choice_bonus:
            chosen = [str(self.query_one(f"#wiz-species-choice-{i}", Select).value) for i in range(choice_bonus)]
            if len(set(chosen)) != len(chosen):
                return f"Choose {choice_bonus} different Attributes for the species bonus."
            self.data["species_choice_attrs"] = chosen
        else:
            self.data["species_choice_attrs"] = []
        return None

    def _collect_step_attributes(self):
        scores = {}
        for a in sta.ATTRIBUTES:
            raw = self.query_one(f"#wiz-attr-{a}", Input).value.strip()
            try:
                value = int(raw)
            except ValueError:
                return "Attributes must be whole numbers."
            if not 1 <= value <= 20:
                return "Attributes must be between 1 and 20."
            scores[a] = value
        self.data["attributes"] = scores
        return None

    def _collect_step_departments(self):
        scores = {}
        for d in sta.DEPARTMENTS:
            raw = self.query_one(f"#wiz-dept-{d}", Input).value.strip()
            try:
                value = int(raw)
            except ValueError:
                return "Departments must be whole numbers."
            if not 0 <= value <= 10:
                return "Departments must be between 0 and 10."
            scores[d] = value
        self.data["departments"] = scores
        return None

    def _collect_step_focuses_values(self):
        self.data["focuses"] = list(self.pending_focuses)
        self.data["values"] = list(self.pending_values)
        return None

    def _collect_step_talents_profile(self):
        self.data["talents"] = list(self.pending_talents)
        self.data["rank"] = self.query_one("#wiz-rank", Input).value.strip()
        self.data["career"] = self.query_one("#wiz-career", Input).value.strip()
        self.data["role"] = self.query_one("#wiz-role", Input).value.strip()
        return None

    def _collect_step_review(self):
        if self.entity_type == "npc":
            return None
        raw = self.query_one("#wiz-determination", Input).value.strip()
        try:
            det = int(raw)
        except ValueError:
            return "Determination must be a whole number."
        self.data["determination"] = max(0, min(sta.DETERMINATION_MAX, det))
        return None

    # -- list helpers ---------------------------------------------------

    def _add_simple(self, input_id: str, target: list, list_id: str):
        widget = self.query_one(f"#{input_id}", Input)
        text = widget.value.strip()
        if text:
            target.append(text)
            widget.value = ""
            self._refresh_list(target, list_id)

    def _remove_simple(self, target: list, list_id: str):
        lv = self.query_one(f"#{list_id}", ListView)
        if lv.index is not None and lv.index < len(target):
            del target[lv.index]
            self._refresh_list(target, list_id)

    def _refresh_list(self, items: list, list_id: str):
        lv = self.query_one(f"#{list_id}", ListView)
        lv.clear()
        for item in items:
            lv.append(ListItem(Label(str(item))))

    def _reset_inputs(self, spread: dict, prefix: str):
        for key, value in spread.items():
            self.query_one(f"#{prefix}-{key}", Input).value = str(value)

    # -- helpers --------------------------------------------------------

    def _effective_attributes(self) -> dict:
        """The raw assigned spread stays untouched in self.data so going Back
        and forward still validates; species bonuses are only ever applied to
        a derived copy, computed on demand here."""
        if self.entity_type == "adventurer" and self.data["species"] in species_mod.SPECIES:
            return species_mod.apply_bonuses(self.data["attributes"], self.data["species"], self.data["species_choice_attrs"])
        return dict(self.data["attributes"])

    # -- final creation ---------------------------------------------------

    def _create_entity(self):
        from screens.entities import EntityDetailScreen
        from screens.sheet import CharacterSheetScreen

        if self.entity_type == "npc":
            fields = {
                "species": self.data.get("species_text", ""),
                "role": self.data["role"],
                "status": self.data["status"] or "Alive",
                "location": self.data["location"],
            }
            entity_id = db.create_entity("npc", self.data["name"], fields, "")
            self.dismiss(entity_id)
            self.app.push_screen(EntityDetailScreen(entity_id))
            return

        sheet = sta.default_sheet()
        sheet["attributes"] = self._effective_attributes()
        sheet["departments"] = dict(self.data["departments"])
        sheet["focuses"] = list(self.pending_focuses)
        sheet["values"] = list(self.pending_values)
        sheet["talents"] = list(self.pending_talents)
        sheet["species"] = self.data["species"]
        sheet["rank"] = self.data["rank"]
        sheet["career"] = self.data["career"]
        sheet["role"] = self.data["role"]
        sheet["determination"] = self.data["determination"]

        if self.entity_type == "adventurer":
            # Flat fields drive the list views; the STA sheet is the source of
            # truth and carries the rest.
            flat_fields = {
                "species": self.data["species"],
                "rank": self.data["rank"],
                "role": self.data["role"],
                "player_name": self.data["player_name"],
                "status": "Active",
            }
        else:
            flat_fields = {
                "species": self.data.get("species") or self.data.get("creature_type", ""),
                "role": self.data["role"],
                "status": "Alive",
            }
        flat_fields["sheet"] = sheet
        entity_id = db.create_entity(self.entity_type, self.data["name"], flat_fields, "")

        if self.link_to_npc_id:
            db.create_relationship(entity_id, self.link_to_npc_id, self.link_rel_type, "")

        self.dismiss(entity_id)
        if self.mode == "quick":
            self.app.push_screen(CharacterSheetScreen(entity_id))
        else:
            self.app.push_screen(EntityDetailScreen(entity_id))
