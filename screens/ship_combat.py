from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Label, Button, Input, Select, Static, ListView, ListItem, TabbedContent, TabPane
from textual.containers import Container, Horizontal, ScrollableContainer
from textual import on

import db
import starship as ship
import dice
import ship_combat as sc
import scene as scene_lib
from models import ENTITY_LABELS

from screens.common import DismissableScreen, PALETTE, tint_border
from screens.pools import PoolBar

INFINITY = chr(0x221e)


class ShipConflictScreen(DismissableScreen):
    """STA 2e starship conflict tracker: side-alternating ship turns, a shared
    range band, per-ship Power that refills each round, Shields -> Breaches
    damage, ship Traits, and the shared Momentum/Threat pools inline."""

    BINDINGS = [Binding("escape", "dismiss_screen", "Back")]

    def __init__(self, entity_id: int):
        super().__init__()
        self.entity_id = entity_id
        entity = db.get_entity(entity_id)
        self.state = sc.normalize_ship_combat(entity["fields"].get("ship_combat", {}))

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="ship-combat-tabs"):
            with TabPane("Ships", id="ship-tab-ships"):
                yield ScrollableContainer(Container(id="ship-ships-fields"), id="ship-ships-scroll")
            with TabPane("Conflict", id="ship-tab-conflict"):
                yield ScrollableContainer(Container(id="ship-conflict-fields"), id="ship-conflict-scroll")
            with TabPane("Turn Controls", id="ship-tab-turns"):
                yield ScrollableContainer(Container(id="ship-turns-fields"), id="ship-turns-scroll")
            with TabPane("Log", id="ship-tab-log"):
                yield ScrollableContainer(Static(id="ship-combat-log-body"), id="ship-combat-log-scroll")
        yield ScrollableContainer(Static(id="ship-combat-summary"), id="ship-combat-summary-scroll")
        yield Footer()

    async def on_mount(self):
        entity = db.get_entity(self.entity_id)
        self.title = f"{entity['name']} - Ship Conflict"
        tint_border(self.query_one("#ship-combat-tabs"), "starship")
        tint_border(self.query_one("#ship-combat-summary-scroll"), "starship")
        await self._build_ships_tab()
        await self._build_conflict_tab()
        await self._build_turns_tab()
        self._refresh_summary()
        self._refresh_log()
        self._sync_actor_to_current_turn()

    # -- options ----------------------------------------------------------

    def _ship_options(self):
        options = []
        for s in self.state["ships"]:
            entity = db.get_entity(s["entity_id"])
            if entity:
                options.append((entity["name"], str(s["entity_id"])))
        return options

    def _available_ship_options(self):
        in_combat = {s["entity_id"] for s in self.state["ships"]}
        return [(e["name"], str(e["id"])) for e in db.list_entities("starship") if e["id"] not in in_combat]

    def _set_options_preserving_selection(self, select: Select, options):
        previous = select.value
        select.set_options(options)
        if previous is not Select.NULL and any(previous == v for _, v in options):
            select.value = previous

    def _refresh_ship_selects(self):
        options = self._ship_options()
        for sid in ("#sel-acting-ship", "#sel-remove-ship", "#sel-ship-target"):
            self._set_options_preserving_selection(self.query_one(sid, Select), options)
        self._set_options_preserving_selection(self.query_one("#sel-add-ship", Select), self._available_ship_options())
        self._refresh_weapon_choices()

    # -- tab builders -----------------------------------------------------

    async def _build_ships_tab(self):
        container = self.query_one("#ship-ships-fields")
        await container.mount(
            Label("Add Ship"),
            Select(self._available_ship_options(), id="sel-add-ship", prompt="Choose a starship..."),
            Horizontal(
                Select([("Crew", sc.CREW), ("Adversary", sc.ADVERSARY)], value=sc.ADVERSARY, id="ship-add-side", allow_blank=False),
                Button("+ Add to Conflict", id="btn-add-ship"),
                id="ship-add-actions",
            ),
            Label("Remove Ship"),
            Select(self._ship_options(), id="sel-remove-ship", prompt="Choose a ship..."),
            Button("Remove from Conflict", id="btn-remove-ship", variant="error"),
        )

    async def _build_conflict_tab(self):
        container = self.query_one("#ship-conflict-fields")
        sys_options = [(ship.SYSTEM_LABELS[s], s) for s in ship.SYSTEMS]
        dept_options = [(ship.DEPARTMENT_LABELS[d], d) for d in ship.DEPARTMENTS]
        await container.mount(
            Label("Acting Ship (defaults to whoever's turn it is)"),
            Select(self._ship_options(), id="sel-acting-ship", prompt="Choose a ship..."),
            Horizontal(
                Label("Range"),
                Select([(r, r) for r in sc.RANGES], value=self.state["range"], id="ship-range", allow_blank=False),
                Static("", id="ship-power-readout"),
                id="ship-range-row",
            ),
            Horizontal(
                Label("Spend Power"), Input(placeholder="Amount", id="ship-power-amount", classes="stat-input"),
                Button("Spend", id="btn-spend-power"),
                id="ship-power-row",
            ),
            Static("[bold]Ship Task Roll[/]  (2d20 vs System + Department)"),
            Horizontal(
                Select(sys_options, id="ship-task-sys", allow_blank=False, value="engines"),
                Select(dept_options, id="ship-task-dept", allow_blank=False, value="conn"),
                Label("Difficulty"), Input(value="2", id="ship-task-difficulty", classes="stat-input"),
                id="ship-task-row",
            ),
            Button("Roll Task", id="btn-ship-roll-task", variant="primary"),
            Static("Pick an acting ship, then roll.", id="ship-task-result"),
            Static("[bold]Weapon Damage[/]"),
            Select([], id="ship-weapon", prompt="Choose weapon..."),
            Button("Roll Damage ([CD])", id="btn-ship-roll-damage", variant="warning"),
            Static("", id="ship-damage-result"),
            Label("Target Ship"),
            Select(self._ship_options(), id="sel-ship-target", prompt="Choose a target..."),
            Horizontal(
                Label("Damage"), Input(placeholder="Amount", id="ship-damage-amount", classes="stat-input"),
                Label("Overflow hits"),
                Select(sys_options, id="ship-breach-system", allow_blank=False, value="structure"),
                Button("Apply to Shields", id="btn-ship-apply-damage", variant="error"),
                id="ship-damage-row",
            ),
            Horizontal(
                Button("+1 Breach to system above", id="btn-ship-add-breach"),
                id="ship-breach-row",
            ),
            Label("Add Trait to Target"),
            Horizontal(
                Input(placeholder="Trait, e.g. Hull Breach", id="ship-trait-name"),
                Input(placeholder="Rounds (blank = until removed)", id="ship-trait-rounds"),
                Button("Add Trait", id="btn-ship-add-trait"),
                id="ship-trait-actions",
            ),
            ListView(id="ship-trait-list"),
            Button("Remove Selected Trait", id="btn-ship-remove-trait", variant="error"),
        )

    async def _build_turns_tab(self):
        container = self.query_one("#ship-turns-fields")
        await container.mount(
            Static("[bold]Momentum / Threat[/]"),
            PoolBar(id="ship-combat-pool-bar"),
            Button("Begin Conflict", id="btn-ship-start", variant="primary"),
            Horizontal(
                Button("Next Turn", id="btn-ship-next-turn", variant="primary"),
                Button("Next Round (refills Power)", id="btn-ship-next-round", variant="primary"),
                id="ship-turn-advance",
            ),
            Button("End Conflict", id="btn-ship-end", variant="error"),
        )

    # -- persistence + summary --------------------------------------------

    def _persist(self):
        entity = db.get_entity(self.entity_id)
        fields = dict(entity["fields"])
        fields["ship_combat"] = self.state
        db.update_entity(self.entity_id, entity["name"], fields, entity["notes"])
        self._refresh_summary()
        self._refresh_ship_selects()
        self._refresh_log()

    def _set_encounter_status(self, status: str):
        entity = db.get_entity(self.entity_id)
        fields = dict(entity["fields"])
        fields["status"] = status
        db.update_entity(self.entity_id, entity["name"], fields, entity["notes"])

    def _ship_sheet(self, entity: dict) -> dict:
        return ship.normalize_sheet(entity["fields"].get("sheet", {}))

    def _refresh_summary(self):
        self.query_one("#btn-ship-start", Button).disabled = self.state["started"]
        side_label = "Crew" if self.state["active_side"] == sc.CREW else "Adversary"
        header = f"[bold]Round {self.state['round']}[/]  -  {'In Progress' if self.state['started'] else 'Not Started'}"
        header += f"  -  Range: {self.state['range']}"
        if self.state["started"]:
            header += f"  -  {side_label} turn"
        lines = [header, ""]
        current = sc.current_ship(self.state) if self.state["started"] else None
        for s in self.state["ships"]:
            entity = db.get_entity(s["entity_id"])
            if not entity:
                continue
            sheet = self._ship_sheet(entity)
            marker = "-> " if current and current["entity_id"] == s["entity_id"] else "   "
            color = PALETTE.get("starship", "#ffffff")
            side = "Crew" if s["side"] == sc.CREW else "Adv"
            breaches = sc.total_breaches(s)
            breach_str = f"  Breaches {breaches}" if breaches else ""
            traits = ", ".join(
                f"{t['name']}({t['rounds_remaining'] if t['rounds_remaining'] is not None else INFINITY})"
                for t in s["traits"]
            ) or "none"
            acted = "  [dim](acted)[/]" if s["has_acted"] and self.state["started"] else ""
            lines.append(
                f"{marker}[bold {color}]{entity['name']}[/] [{side}] - "
                f"Shields {sheet['shields_current']}/{sheet['shields_max']} - "
                f"Power {s['power']}/{s['power_max']}{breach_str} - Traits: {traits}{acted}"
            )
        if not self.state["ships"]:
            lines.append("[dim]No ships yet. Add some on the Ships tab.[/dim]")
        lines.extend(scene_lib.summary_lines())
        self.query_one("#ship-combat-summary", Static).update("\n".join(lines))

    def _log(self, message: str):
        self.state = sc.log_entry(self.state, self.state["round"], message)

    def _refresh_log(self):
        entries = self.state.get("log", [])
        if not entries:
            self.query_one("#ship-combat-log-body", Static).update("[dim]No events logged yet.[/dim]")
            return
        lines = [f"[dim][R{e['round']}][/dim] {e['entry']}" for e in reversed(entries)]
        self.query_one("#ship-combat-log-body", Static).update("\n".join(lines))

    def _refresh_power_readout(self):
        ship_state = self._acting_ship_state()
        if ship_state is None:
            self.query_one("#ship-power-readout", Static).update("")
            return
        self.query_one("#ship-power-readout", Static).update(
            f"   [bold]Power[/] {ship_state['power']}/{ship_state['power_max']}"
        )

    def _refresh_trait_list(self, entity_id: int):
        lv = self.query_one("#ship-trait-list", ListView)
        lv.clear()
        target = next((s for s in self.state["ships"] if s["entity_id"] == entity_id), None)
        if not target:
            return
        for t in target["traits"]:
            suffix = f"{t['rounds_remaining']} rounds" if t["rounds_remaining"] is not None else "until removed"
            lv.append(ListItem(Label(f"{t['name']} ({suffix})")))

    # -- lookups ----------------------------------------------------------

    def _acting_entity(self) -> dict | None:
        sel = self.query_one("#sel-acting-ship", Select)
        return None if sel.value is Select.NULL else db.get_entity(int(str(sel.value)))

    def _acting_ship_state(self) -> dict | None:
        sel = self.query_one("#sel-acting-ship", Select)
        if sel.value is Select.NULL:
            return None
        sid = int(str(sel.value))
        return next((s for s in self.state["ships"] if s["entity_id"] == sid), None)

    def _target_entity(self) -> dict | None:
        sel = self.query_one("#sel-ship-target", Select)
        return None if sel.value is Select.NULL else db.get_entity(int(str(sel.value)))

    def _weapon_options_for(self, entity_id: int):
        entity = db.get_entity(entity_id)
        if not entity:
            return []
        sheet = self._ship_sheet(entity)
        return [(f"{w.get('name', '?')} ({ship.weapon_dice(sheet, w)}[CD])", f"w:{i}") for i, w in enumerate(sheet["weapons"])]

    def _refresh_weapon_choices(self):
        sel = self.query_one("#sel-acting-ship", Select)
        options = [] if sel.value is Select.NULL else self._weapon_options_for(int(str(sel.value)))
        weapon = self.query_one("#ship-weapon", Select)
        self._set_options_preserving_selection(weapon, options)
        if weapon.value is Select.NULL and options:
            weapon.value = options[0][1]

    def _sync_actor_to_current_turn(self):
        current = sc.current_ship(self.state) if self.state["started"] else None
        if current is not None:
            sel = self.query_one("#sel-acting-ship", Select)
            sid = str(current["entity_id"])
            if any(v == sid for _, v in self._ship_options()):
                sel.value = sid
        self._refresh_weapon_choices()
        self._refresh_power_readout()

    # -- ship management --------------------------------------------------

    def _add_ship(self):
        sel = self.query_one("#sel-add-ship", Select)
        if sel.value is Select.NULL:
            return
        entity_id = int(str(sel.value))
        entity = db.get_entity(entity_id)
        side = str(self.query_one("#ship-add-side", Select).value)
        power_max = self._ship_sheet(entity)["systems"]["engines"] if entity else 0
        self.state = sc.add_ship(self.state, entity_id, side, power_max=power_max)
        self._persist()

    def _remove_ship(self):
        sel = self.query_one("#sel-remove-ship", Select)
        if sel.value is Select.NULL:
            return
        self.state = sc.remove_ship(self.state, int(str(sel.value)))
        self._persist()

    # -- power / rolls / damage -------------------------------------------

    def _spend_power(self):
        ship_state = self._acting_ship_state()
        if ship_state is None:
            return
        try:
            amount = int(self.query_one("#ship-power-amount", Input).value.strip())
        except ValueError:
            return
        ship_state["power"] = sc.spend_power(ship_state["power"], amount)
        entity = self._acting_entity()
        self._log(f"{entity['name'] if entity else '?'} spent {amount} Power ({ship_state['power']}/{ship_state['power_max']} left)")
        self._persist()
        self._refresh_power_readout()

    def _roll_task(self):
        entity = self._acting_entity()
        if not entity:
            self.query_one("#ship-task-result", Static).update("[red]Pick an acting ship first.[/]")
            return
        sheet = self._ship_sheet(entity)
        sys_key = str(self.query_one("#ship-task-sys", Select).value)
        dept_key = str(self.query_one("#ship-task-dept", Select).value)
        try:
            difficulty = max(0, int(self.query_one("#ship-task-difficulty", Input).value.strip() or 0))
        except ValueError:
            difficulty = 2
        result = dice.roll_task(
            attribute=sheet["systems"][sys_key],
            department=sheet["departments"][dept_key],
            difficulty=difficulty,
        )
        colour = "#c3e88d" if result.succeeded else "#ff5370"
        detail = f"{entity['name']}: {result.detail}"
        if result.momentum > 0:
            pools = db.adjust_momentum(result.momentum)
            detail += f"  --  +{result.momentum} Momentum (pool {pools['momentum']})"
            self._refresh_pool_bar()
        if result.complications > 0:
            pools = db.adjust_threat(result.complications)
            detail += f"  --  +{result.complications} Threat (pool {pools['threat']})"
            self._refresh_pool_bar()
        self.query_one("#ship-task-result", Static).update(f"[{colour}]{detail}[/]")
        self._log(f"{entity['name']} rolled a ship Task: {result.successes} success(es) vs Difficulty {difficulty}")
        self._persist()

    def _roll_damage(self):
        entity = self._acting_entity()
        weapon_sel = self.query_one("#ship-weapon", Select)
        if not entity or weapon_sel.value is Select.NULL:
            self.query_one("#ship-damage-result", Static).update("[red]Pick a ship and a weapon.[/]")
            return
        sheet = self._ship_sheet(entity)
        index = int(str(weapon_sel.value)[2:])
        if index >= len(sheet["weapons"]):
            return
        weapon = sheet["weapons"][index]
        result = dice.roll_challenge(ship.weapon_dice(sheet, weapon))
        text = f"{weapon.get('name', '?')}: {result.detail}"
        if result.effects:
            text += f"  ({result.effects} Effect{'s' if result.effects != 1 else ''})"
        self.query_one("#ship-damage-result", Static).update(text)
        self.query_one("#ship-damage-amount", Input).value = str(result.total)

    def _apply_damage(self):
        entity = self._target_entity()
        if not entity:
            return
        try:
            amount = int(self.query_one("#ship-damage-amount", Input).value.strip())
        except ValueError:
            return
        sheet = self._ship_sheet(entity)
        # Resistance (= Scale) reduces incoming damage before it hits Shields.
        effective = max(0, amount - ship.resistance(sheet))
        new_shields, overflow = sc.apply_ship_damage(sheet["shields_current"], effective)
        sheet["shields_current"] = new_shields
        fields = dict(entity["fields"])
        fields["sheet"] = sheet
        db.update_entity(entity["id"], entity["name"], fields, entity["notes"])
        msg = f"{entity['name']} took {effective} damage (Shields -> {new_shields})"
        if overflow > 0:
            system = str(self.query_one("#ship-breach-system", Select).value)
            self.state = sc.add_breach(self.state, entity["id"], system, overflow)
            msg += f", {overflow} overflow -> {overflow} Breach(es) in {ship.SYSTEM_LABELS[system]}!"
        self._log(msg)
        self._persist()

    def _add_breach(self):
        entity = self._target_entity()
        if not entity:
            return
        system = str(self.query_one("#ship-breach-system", Select).value)
        self.state = sc.add_breach(self.state, entity["id"], system, 1)
        self._log(f"{entity['name']} took a Breach in {ship.SYSTEM_LABELS[system]}")
        self._persist()

    def _refresh_pool_bar(self):
        try:
            self.query_one("#ship-combat-pool-bar", PoolBar).refresh_pools()
        except Exception:
            pass

    # -- traits -----------------------------------------------------------

    def _add_trait(self):
        entity = self._target_entity()
        if not entity:
            return
        name = self.query_one("#ship-trait-name", Input).value.strip()
        if not name:
            return
        rounds_raw = self.query_one("#ship-trait-rounds", Input).value.strip()
        rounds = int(rounds_raw) if rounds_raw else None
        self.state = sc.add_trait(self.state, entity["id"], name, rounds)
        self.query_one("#ship-trait-name", Input).value = ""
        self.query_one("#ship-trait-rounds", Input).value = ""
        self._log(f"{entity['name']} gained Trait: {name}")
        self._persist()
        self._refresh_trait_list(entity["id"])

    def _remove_trait(self):
        entity = self._target_entity()
        if not entity:
            return
        lv = self.query_one("#ship-trait-list", ListView)
        if lv.index is None:
            return
        self.state = sc.remove_trait(self.state, entity["id"], lv.index)
        self._persist()
        self._refresh_trait_list(entity["id"])

    @on(Select.Changed, "#sel-acting-ship")
    def _on_acting_changed(self, event: Select.Changed):
        self._refresh_weapon_choices()
        self._refresh_power_readout()

    @on(Select.Changed, "#sel-ship-target")
    def _on_target_changed(self, event: Select.Changed):
        if event.value is not Select.NULL:
            self._refresh_trait_list(int(str(event.value)))

    @on(Select.Changed, "#ship-range")
    def _on_range_changed(self, event: Select.Changed):
        if event.value is not Select.NULL:
            self.state = sc.set_range(self.state, str(event.value))
            self._persist()

    # -- turn flow --------------------------------------------------------

    def _start(self):
        self.state = sc.start_conflict(self.state)
        self._set_encounter_status("Active")
        self._log("Ship conflict began")
        self._persist()
        self._sync_actor_to_current_turn()

    def _next_turn(self):
        self.state = sc.next_turn(self.state)
        current = sc.current_ship(self.state)
        if current:
            e = db.get_entity(current["entity_id"])
            self._log(f"Round {self.state['round']}: {e['name'] if e else '?'}'s turn")
        self._persist()
        self._sync_actor_to_current_turn()

    def _next_round(self):
        self.state = sc.next_round(self.state)
        self._log(f"-- Round {self.state['round']} begins (Power refilled) --")
        self._persist()
        self._sync_actor_to_current_turn()

    def _end(self):
        self._log("Ship conflict ended")
        self._set_encounter_status("Complete")
        self._persist()

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if bid == "btn-add-ship":
            self._add_ship()
        elif bid == "btn-remove-ship":
            self._remove_ship()
        elif bid == "btn-spend-power":
            self._spend_power()
        elif bid == "btn-ship-roll-task":
            self._roll_task()
        elif bid == "btn-ship-roll-damage":
            self._roll_damage()
        elif bid == "btn-ship-apply-damage":
            self._apply_damage()
        elif bid == "btn-ship-add-breach":
            self._add_breach()
        elif bid == "btn-ship-add-trait":
            self._add_trait()
        elif bid == "btn-ship-remove-trait":
            self._remove_trait()
        elif bid == "btn-ship-start":
            self._start()
        elif bid == "btn-ship-next-turn":
            self._next_turn()
        elif bid == "btn-ship-next-round":
            self._next_round()
        elif bid == "btn-ship-end":
            self._end()
