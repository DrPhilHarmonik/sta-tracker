from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Label, Button, Input, Select, Static, ListView, ListItem, TabbedContent, TabPane, Switch
from textual.containers import Container, Horizontal, ScrollableContainer
from textual import on

import db
import sta_sheet as sta
import dice
import combat as cbt
import conditions as cnd
import scene as scene_lib
from models import ENTITY_LABELS

from screens.common import DismissableScreen, PALETTE, tint_border
from screens.pools import PoolBar
from screens.wizard import WizardScreen

INFINITY = chr(0x221e)


class CombatTrackerScreen(DismissableScreen):
    """STA 2e conflict tracker: side-alternating turns, Stress/Injury tracking,
    Task rolls and Challenge-Dice damage, situational Traits, and the shared
    Momentum/Threat pools surfaced inline."""

    BINDINGS = [Binding("escape", "dismiss_screen", "Back")]

    def __init__(self, entity_id: int):
        super().__init__()
        self.entity_id = entity_id
        entity = db.get_entity(entity_id)
        self.combat = cbt.normalize_combat(entity["fields"].get("combat", {}))

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="combat-tabs"):
            with TabPane("Combatants", id="tab-combatants"):
                yield ScrollableContainer(Container(id="combatants-fields"), id="combatants-scroll")
            with TabPane("Conflict", id="tab-conflict"):
                yield ScrollableContainer(Container(id="conflict-fields"), id="conflict-scroll")
            with TabPane("Turn Controls", id="tab-turn-controls"):
                yield ScrollableContainer(Container(id="turn-controls-fields"), id="turn-controls-scroll")
            with TabPane("Log", id="tab-log"):
                yield ScrollableContainer(Static(id="combat-log-body"), id="combat-log-scroll")
        yield ScrollableContainer(Static(id="combat-summary"), id="combat-summary-scroll")
        yield Footer()

    async def on_mount(self):
        entity = db.get_entity(self.entity_id)
        self.title = f"{entity['name']} - Conflict Tracker"
        tint_border(self.query_one("#combat-tabs"), "encounter")
        tint_border(self.query_one("#combat-summary-scroll"), "encounter")
        await self._build_combatants_tab()
        await self._build_conflict_tab()
        await self._build_turn_controls_tab()
        self.query_one("#input-condition-custom").display = False
        self._refresh_summary()
        self._refresh_log()
        self._sync_attacker_to_current_turn()

    # -- option helpers ---------------------------------------------------

    def _side_for_entity(self, entity: dict) -> str:
        return cbt.CREW if entity and entity["type"] == "adventurer" else cbt.ADVERSARY

    def _combatant_options(self):
        options = []
        for c in self.combat["combatants"]:
            entity = db.get_entity(c["entity_id"])
            if entity:
                options.append((f"{entity['name']} ({ENTITY_LABELS[entity['type']]})", str(c["entity_id"])))
        return options

    def _available_entity_options(self):
        in_combat = {c["entity_id"] for c in self.combat["combatants"]}
        return [
            (f"{e['name']} ({ENTITY_LABELS[e['type']]})", str(e["id"]))
            for e in db.list_entities()
            if e["type"] in sta.SHEET_ENTITY_TYPES and e["id"] not in in_combat
        ]

    def _set_options_preserving_selection(self, select: Select, options: list[tuple[str, str]]):
        previous = select.value
        select.set_options(options)
        if previous is not Select.NULL and any(previous == value for _, value in options):
            select.value = previous

    def _refresh_combatant_selects(self):
        options = self._combatant_options()
        for select_id in ("#sel-remove-combatant", "#sel-hp-target", "#sel-attack-attacker", "#sel-summon-caster"):
            self._set_options_preserving_selection(self.query_one(select_id, Select), options)
        self._set_options_preserving_selection(self.query_one("#sel-add-combatant", Select), self._available_entity_options())
        self._refresh_weapon_choices()

    # -- tab builders -------------------------------------------------

    async def _build_combatants_tab(self):
        container = self.query_one("#combatants-fields")
        await container.mount(
            Label("Add Combatant (adventurers join the crew, enemies the adversaries)"),
            Select(self._available_entity_options(), id="sel-add-combatant", prompt="Choose adventurer/enemy..."),
            Button("+ Add to Conflict", id="btn-add-combatant"),
            Label("Remove Combatant"),
            Select(self._combatant_options(), id="sel-remove-combatant", prompt="Choose combatant..."),
            Button("Remove from Conflict", id="btn-remove-combatant", variant="error"),
        )

    async def _build_conflict_tab(self):
        container = self.query_one("#conflict-fields")
        attr_options = [(sta.ATTRIBUTE_LABELS[a], a) for a in sta.ATTRIBUTES]
        dept_options = [(sta.DEPARTMENT_LABELS[d], d) for d in sta.DEPARTMENTS]
        await container.mount(
            Label("Acting Character (defaults to whoever's turn it is)"),
            Select(self._combatant_options(), id="sel-attack-attacker", prompt="Choose character..."),
            Static("[bold]Task Roll[/]"),
            Horizontal(
                Select(attr_options, id="task-attr", allow_blank=False, value="daring"),
                Select(dept_options, id="task-dept", allow_blank=False, value="security"),
                id="task-selectors",
            ),
            Horizontal(
                Label("Difficulty"), Input(value="2", id="task-difficulty", classes="stat-input"),
                Switch(id="task-focus"), Label("Focus applies"),
                Switch(id="task-invoke"), Label("Invoke Value (spend 1 Det)"),
                id="task-params",
            ),
            Horizontal(
                Button("Roll Task (2d20)", id="btn-roll-task", variant="primary"),
                Button("Challenge Value (+1 Det)", id="btn-combat-challenge-value"),
                id="task-actions",
            ),
            Static("Pick a character, set the Task, then roll.", id="task-result"),
            Static("[bold]Weapon Damage[/]"),
            Select([], id="sel-weapon", prompt="Choose weapon..."),
            Button("Roll Damage ([CD])", id="btn-roll-damage", variant="warning"),
            Static("", id="damage-result"),
            Label("Target (also used for Apply/Recover Stress)"),
            Select(self._combatant_options(), id="sel-hp-target", prompt="Choose combatant..."),
            Label("Stress Amount"),
            Input(placeholder="Amount", id="input-hp-amount"),
            Horizontal(
                Button("Apply Stress", id="btn-damage", variant="error"),
                Button("Recover Stress", id="btn-heal", variant="success"),
                id="hp-actions",
            ),
            Label("Add Trait / Condition"),
            Select(
                [(name, name) for name in cnd.CONDITION_NAMES] + [("Custom...", "__custom__")],
                id="sel-condition-name",
                prompt="Choose trait...",
                allow_blank=True,
            ),
            Static("", id="condition-desc"),
            Input(placeholder="Custom trait name", id="input-condition-custom"),
            Input(placeholder="Rounds remaining (blank = until removed)", id="input-condition-rounds"),
            Button("Add Trait", id="btn-add-condition"),
            Label("Current Traits (select one, then Remove)"),
            ListView(id="list-conditions"),
            Button("Remove Selected Trait", id="btn-remove-condition", variant="error"),
        )

    async def _build_turn_controls_tab(self):
        container = self.query_one("#turn-controls-fields")
        await container.mount(
            Static("[bold]Momentum / Threat[/]"),
            PoolBar(id="combat-pool-bar"),
            Button("Begin Conflict", id="btn-start-encounter", variant="primary"),
            Horizontal(
                Button("Next Turn", id="btn-next-turn", variant="primary"),
                Button("Next Round", id="btn-next-round", variant="primary"),
                id="turn-advance-actions",
            ),
            Button("End Conflict", id="btn-end-encounter", variant="error"),
            Static("[bold]Summon Creature[/]", id="summon-heading"),
            Label("Summoner"),
            Select(self._combatant_options(), id="sel-summon-caster", prompt="Choose summoner..."),
            Button("Open Summon Wizard", id="btn-summon", variant="warning"),
        )

    # -- persistence + summary --------------------------------------------

    def _persist(self):
        entity = db.get_entity(self.entity_id)
        fields = dict(entity["fields"])
        fields["combat"] = self.combat
        db.update_entity(self.entity_id, entity["name"], fields, entity["notes"])
        self._refresh_summary()
        self._refresh_combatant_selects()
        self._refresh_log()

    def _set_encounter_status(self, status: str):
        entity = db.get_entity(self.entity_id)
        fields = dict(entity["fields"])
        fields["status"] = status
        db.update_entity(self.entity_id, entity["name"], fields, entity["notes"])

    def _sheet_for(self, entity: dict) -> dict:
        return sta.normalize_sheet(entity["fields"].get("sheet", {}))

    def _refresh_summary(self):
        self.query_one("#btn-start-encounter", Button).disabled = self.combat["started"]
        side_label = "Crew" if self.combat["active_side"] == cbt.CREW else "Adversaries"
        header = f"[bold]Round {self.combat['round']}[/]  -  {'In Progress' if self.combat['started'] else 'Not Started'}"
        if self.combat["started"]:
            header += f"  -  {side_label}' turn"
        lines = [header, ""]
        current = cbt.current_combatant(self.combat) if self.combat["started"] else None
        for c in self.combat["combatants"]:
            entity = db.get_entity(c["entity_id"])
            if not entity:
                continue
            sheet = self._sheet_for(entity)
            marker = "-> " if current and current["entity_id"] == c["entity_id"] else "   "
            color = PALETTE.get(entity["type"], "#ffffff")
            side = "Crew" if c["side"] == cbt.CREW else "Adv"
            cond_str = ", ".join(
                f"{cd['name']}({cd['rounds_remaining'] if cd['rounds_remaining'] is not None else INFINITY})"
                for cd in c["conditions"]
            ) or "none"
            acted = "  [dim](acted)[/]" if c["has_acted"] and self.combat["started"] else ""
            injuries = f"  Injuries: {len(sheet['injuries'])}" if sheet["injuries"] else ""
            lines.append(
                f"{marker}[bold {color}]{entity['name']}[/] [{side}] - "
                f"Stress {sheet['stress_current']}/{sheet['stress_max']}{injuries} - "
                f"Traits: {cond_str}{acted}"
            )
        if not self.combat["combatants"]:
            lines.append("[dim]No combatants yet. Add some on the Combatants tab.[/dim]")
        lines.extend(scene_lib.summary_lines())
        self.query_one("#combat-summary", Static).update("\n".join(lines))

    def _log(self, message: str):
        self.combat = cbt.log_entry(self.combat, self.combat["round"], message)

    def _refresh_log(self):
        entries = self.combat.get("log", [])
        if not entries:
            self.query_one("#combat-log-body", Static).update("[dim]No events logged yet.[/dim]")
            return
        lines = [f"[dim][R{e['round']}][/dim] {e['entry']}" for e in reversed(entries)]
        self.query_one("#combat-log-body", Static).update("\n".join(lines))

    def _refresh_conditions_list(self, entity_id: int):
        lv = self.query_one("#list-conditions", ListView)
        lv.clear()
        target = next((c for c in self.combat["combatants"] if c["entity_id"] == entity_id), None)
        if not target:
            return
        for cond in target["conditions"]:
            suffix = f"{cond['rounds_remaining']} rounds left" if cond["rounds_remaining"] is not None else "until removed"
            lv.append(ListItem(Label(f"{cond['name']} ({suffix})")))

    # -- combatant management ---------------------------------------------

    def _add_combatant(self):
        sel = self.query_one("#sel-add-combatant", Select)
        if sel.value is Select.NULL:
            return
        entity_id = int(str(sel.value))
        entity = db.get_entity(entity_id)
        self.combat = cbt.add_combatant(self.combat, entity_id, self._side_for_entity(entity))
        self._persist()

    def _remove_combatant(self):
        sel = self.query_one("#sel-remove-combatant", Select)
        if sel.value is Select.NULL:
            return
        self.combat = cbt.remove_combatant(self.combat, int(str(sel.value)))
        self._persist()

    # -- task rolling / weapon damage -------------------------------------

    def _weapon_options_for(self, entity_id: int):
        entity = db.get_entity(entity_id)
        if not entity:
            return []
        sheet = self._sheet_for(entity)
        options = []
        for i, w in enumerate(sheet["weapons"]):
            dice_count = sta.weapon_dice(sheet, w)
            options.append((f"{w.get('name', '?')} ({dice_count}[CD])", f"w:{i}"))
        return options

    def _refresh_weapon_choices(self):
        attacker_sel = self.query_one("#sel-attack-attacker", Select)
        options = [] if attacker_sel.value is Select.NULL else self._weapon_options_for(int(str(attacker_sel.value)))
        select = self.query_one("#sel-weapon", Select)
        self._set_options_preserving_selection(select, options)
        if select.value is Select.NULL and options:
            select.value = options[0][1]

    def _sync_attacker_to_current_turn(self):
        current = cbt.current_combatant(self.combat) if self.combat["started"] else None
        if current is None:
            self._refresh_weapon_choices()
            return
        sel = self.query_one("#sel-attack-attacker", Select)
        entity_id_str = str(current["entity_id"])
        if any(value == entity_id_str for _, value in self._combatant_options()):
            sel.value = entity_id_str
        self._refresh_weapon_choices()

    def _acting_entity(self) -> dict | None:
        sel = self.query_one("#sel-attack-attacker", Select)
        if sel.value is Select.NULL:
            return None
        return db.get_entity(int(str(sel.value)))

    def _roll_task(self):
        entity = self._acting_entity()
        if not entity:
            self.query_one("#task-result", Static).update("[red]Pick an acting character first.[/]")
            return
        sheet = self._sheet_for(entity)
        attr = str(self.query_one("#task-attr", Select).value)
        dept = str(self.query_one("#task-dept", Select).value)
        try:
            difficulty = max(0, int(self.query_one("#task-difficulty", Input).value.strip() or 0))
        except ValueError:
            difficulty = 2
        focus = self.query_one("#task-focus", Switch).value

        # Invoking a Value spends 1 Determination from the acting character's
        # sheet for an automatic bonus success.
        invoke = self.query_one("#task-invoke", Switch).value
        spend = 1 if invoke and sheet["determination"] >= 1 else 0

        result = dice.roll_task(
            attribute=sheet["attributes"][attr],
            department=sheet["departments"][dept],
            difficulty=difficulty,
            focus=focus,
            determination=spend,
        )
        colour = "#c3e88d" if result.succeeded else "#ff5370"
        detail = f"{entity['name']}: {result.detail}"
        if spend:
            self._set_determination(entity, sta.adjust_determination(sheet["determination"], -1))
            self.query_one("#task-invoke", Switch).value = False
            self._log(f"{entity['name']} invoked a Value (spent 1 Determination)")
        elif invoke:
            detail += "  --  no Determination to spend"
        if result.momentum > 0:
            pools = db.adjust_momentum(result.momentum)
            detail += f"  --  +{result.momentum} Momentum (pool {pools['momentum']})"
            self._refresh_pool_bar()
        if result.complications > 0:
            pools = db.adjust_threat(result.complications)
            detail += f"  --  +{result.complications} Threat (pool {pools['threat']})"
            self._refresh_pool_bar()
        self.query_one("#task-result", Static).update(f"[{colour}]{detail}[/]")
        self._log(f"{entity['name']} rolled a Task: {result.successes} success(es) vs Difficulty {difficulty}")
        self._persist()

    def _set_determination(self, entity: dict, value: int):
        """Persist a new Determination value onto an acting character's sheet."""
        sheet = self._sheet_for(entity)
        sheet["determination"] = value
        fields = dict(entity["fields"])
        fields["sheet"] = sheet
        db.update_entity(entity["id"], entity["name"], fields, entity["notes"])

    def _challenge_value(self):
        entity = self._acting_entity()
        if not entity:
            self.query_one("#task-result", Static).update("[red]Pick an acting character first.[/]")
            return
        sheet = self._sheet_for(entity)
        new_det = sta.adjust_determination(sheet["determination"], 1)
        self._set_determination(entity, new_det)
        self._log(f"{entity['name']} challenged a Value (regained Determination -> {new_det})")
        self.query_one("#task-result", Static).update(
            f"{entity['name']} challenged a Value -- Determination now {new_det}/{sta.DETERMINATION_MAX}"
        )
        self._persist()

    def _roll_damage(self):
        entity = self._acting_entity()
        weapon_sel = self.query_one("#sel-weapon", Select)
        if not entity or weapon_sel.value is Select.NULL:
            self.query_one("#damage-result", Static).update("[red]Pick a character and a weapon.[/]")
            return
        sheet = self._sheet_for(entity)
        index = int(str(weapon_sel.value)[2:])
        if index >= len(sheet["weapons"]):
            return
        weapon = sheet["weapons"][index]
        count = sta.weapon_dice(sheet, weapon)
        result = dice.roll_challenge(count)
        text = f"{weapon.get('name', '?')}: {result.detail}"
        if result.effects:
            text += f"  ({result.effects} Effect{'s' if result.effects != 1 else ''})"
        self.query_one("#damage-result", Static).update(text)
        self.query_one("#input-hp-amount", Input).value = str(result.total)

    def _refresh_pool_bar(self):
        try:
            self.query_one("#combat-pool-bar", PoolBar).refresh_pools()
        except Exception:
            pass

    # -- stress -----------------------------------------------------------

    def _apply_stress_delta(self, damage: bool):
        sel = self.query_one("#sel-hp-target", Select)
        if sel.value is Select.NULL:
            return
        try:
            amount = int(self.query_one("#input-hp-amount", Input).value.strip())
        except ValueError:
            return
        entity_id = int(str(sel.value))
        entity = db.get_entity(entity_id)
        if not entity:
            return
        sheet = self._sheet_for(entity)
        before = sheet["stress_current"]
        if damage:
            sheet["stress_current"] = cbt.apply_stress(before, amount)
            self._log(f"{entity['name']} took {amount} Stress (Stress: {before} -> {sheet['stress_current']})")
            if sheet["stress_current"] == 0 and before > 0:
                sheet["injuries"] = list(sheet["injuries"]) + ["Injury (taken in conflict)"]
                self.combat = cbt.add_condition(self.combat, entity_id, "Injured", None)
                self._log(f"{entity['name']} hit 0 Stress and took an Injury!")
        else:
            sheet["stress_current"] = cbt.recover_stress(before, sheet["stress_max"], amount)
            self._log(f"{entity['name']} recovered {amount} Stress (Stress: {before} -> {sheet['stress_current']})")
        fields = dict(entity["fields"])
        fields["sheet"] = sheet
        db.update_entity(entity_id, entity["name"], fields, entity["notes"])
        self._persist()
        self._refresh_conditions_list(entity_id)

    # -- traits -----------------------------------------------------------

    @on(Select.Changed, "#sel-condition-name")
    def _on_condition_name_changed(self, event: Select.Changed):
        custom_input = self.query_one("#input-condition-custom", Input)
        desc = self.query_one("#condition-desc", Static)
        if event.value is Select.NULL:
            custom_input.display = False
            desc.update("")
            return
        name = str(event.value)
        if name == "__custom__":
            custom_input.display = True
            desc.update("")
        else:
            custom_input.display = False
            desc.update(cnd.CONDITIONS.get(name, ""))

    @on(Select.Changed, "#sel-attack-attacker")
    def _on_attacker_changed(self, event: Select.Changed):
        self._refresh_weapon_choices()

    @on(Select.Changed, "#sel-hp-target")
    def _on_hp_target_changed(self, event: Select.Changed):
        if event.value is Select.NULL:
            return
        self._refresh_conditions_list(int(str(event.value)))

    def _add_condition(self):
        target_sel = self.query_one("#sel-hp-target", Select)
        if target_sel.value is Select.NULL:
            return
        cond_sel = self.query_one("#sel-condition-name", Select)
        if cond_sel.value is Select.NULL:
            return
        if str(cond_sel.value) == "__custom__":
            name = self.query_one("#input-condition-custom", Input).value.strip()
        else:
            name = str(cond_sel.value)
        if not name:
            return
        rounds_raw = self.query_one("#input-condition-rounds", Input).value.strip()
        rounds = int(rounds_raw) if rounds_raw else None
        entity_id = int(str(target_sel.value))
        self.combat = cbt.add_condition(self.combat, entity_id, name, rounds)
        entity = db.get_entity(entity_id)
        suffix = f" ({rounds} rounds)" if rounds else ""
        self._log(f"{entity['name'] if entity else entity_id} gained Trait: {name}{suffix}")
        self.query_one("#input-condition-custom", Input).value = ""
        self.query_one("#input-condition-rounds", Input).value = ""
        self._persist()
        self._refresh_conditions_list(entity_id)

    def _remove_condition(self):
        sel = self.query_one("#sel-hp-target", Select)
        if sel.value is Select.NULL:
            return
        lv = self.query_one("#list-conditions", ListView)
        if lv.index is None:
            return
        entity_id = int(str(sel.value))
        entity = db.get_entity(entity_id)
        combatant = next((c for c in self.combat["combatants"] if c["entity_id"] == entity_id), None)
        if combatant and 0 <= lv.index < len(combatant["conditions"]):
            cond_name = combatant["conditions"][lv.index]["name"]
            self._log(f"{entity['name'] if entity else entity_id} lost Trait: {cond_name}")
        self.combat = cbt.remove_condition(self.combat, entity_id, lv.index)
        self._persist()
        self._refresh_conditions_list(entity_id)

    # -- turn flow --------------------------------------------------------

    def _start_encounter(self):
        self.combat = cbt.start_conflict(self.combat)
        self._set_encounter_status("Active")
        self._log("Conflict began")
        self._persist()

    def _end_encounter(self):
        self._log("Conflict ended")
        self._set_encounter_status("Complete")
        self._persist()

    def _next_turn(self):
        self.combat = cbt.next_turn(self.combat)
        current = cbt.current_combatant(self.combat)
        if current:
            e = db.get_entity(current["entity_id"])
            self._log(f"Round {self.combat['round']}: {e['name'] if e else '?'}'s turn")
        self._persist()
        self._sync_attacker_to_current_turn()

    def _next_round(self):
        self.combat = cbt.next_round(self.combat)
        self._log(f"-- Round {self.combat['round']} begins --")
        self._persist()
        self._sync_attacker_to_current_turn()

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if bid == "btn-add-combatant":
            self._add_combatant()
        elif bid == "btn-remove-combatant":
            self._remove_combatant()
        elif bid == "btn-start-encounter":
            self._start_encounter()
            self._sync_attacker_to_current_turn()
        elif bid == "btn-next-turn":
            self._next_turn()
        elif bid == "btn-next-round":
            self._next_round()
        elif bid == "btn-end-encounter":
            self._end_encounter()
        elif bid == "btn-roll-task":
            self._roll_task()
        elif bid == "btn-combat-challenge-value":
            self._challenge_value()
        elif bid == "btn-roll-damage":
            self._roll_damage()
        elif bid == "btn-damage":
            self._apply_stress_delta(damage=True)
        elif bid == "btn-heal":
            self._apply_stress_delta(damage=False)
        elif bid == "btn-add-condition":
            self._add_condition()
        elif bid == "btn-remove-condition":
            self._remove_condition()
        elif bid == "btn-summon":
            self._summon_creature()

    # -- summon (unchanged plumbing; opens the STA enemy wizard) -----------

    def _summon_creature(self):
        sel = self.query_one("#sel-summon-caster", Select)
        if sel.value is Select.NULL:
            return
        summoner_id = int(str(sel.value))
        summoner = db.get_entity(summoner_id)
        if not summoner:
            return
        self._pending_summoner_id = summoner_id
        self.app.push_screen(
            WizardScreen("enemy", "quick", prefill={"name": "Summoned Creature"}),
            callback=self._on_summon_created,
        )

    def _on_summon_created(self, entity_id: int | None):
        if not entity_id:
            return
        db.create_relationship(entity_id, self._pending_summoner_id, "summoned by", "")
        self.combat = cbt.add_combatant(self.combat, entity_id, cbt.ADVERSARY)
        self._persist()
        summoner = db.get_entity(self._pending_summoner_id)
        summoner_name = summoner["name"] if summoner else "summoner"
        self.app.notify(f"Summoned creature added to conflict (linked to {summoner_name})")
