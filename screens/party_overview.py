from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, DataTable, Static, Button
from textual.containers import Container, Horizontal

import db
import sta_sheet as sta
import combat as cbt
import recovery as recovery_mod
import momentum as momentum_mod
from screens.common import DismissableScreen, tint_border


class PartyOverviewScreen(DismissableScreen):
    BINDINGS = [
        Binding("escape", "dismiss_screen", "Back"),
        Binding("r", "refresh_data", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("", id="overview-status"),
            DataTable(id="party-table", cursor_type="row"),
            Static("[bold]Between Scenes / Recovery[/]", id="recovery-heading"),
            Horizontal(
                Button("Recover Stress — All", id="btn-recover-stress-all", variant="success"),
                Button("Clear Injuries — Selected", id="btn-clear-injuries", variant="warning"),
                Button("Threat: Carry Over", id="btn-threat-carry", variant="default"),
                Button("Threat: Reset to 0", id="btn-threat-reset", variant="error"),
                id="recovery-actions",
            ),
            Static("", id="recovery-status"),
            id="overview-wrap",
        )
        yield Footer()

    async def on_mount(self):
        self.title = "Party Overview"
        tint_border(self.query_one("#overview-wrap"), "adventurer")
        table = self.query_one("#party-table", DataTable)
        table.add_columns(
            "Name", "Rank", "Stress", "Det", "Focuses", "Traits", "Injuries",
        )
        self._load_data()

    async def on_screen_resume(self):
        self._load_data()

    def _load_data(self):
        table = self.query_one("#party-table", DataTable)
        table.clear()

        adventurers = db.active_adventurers()
        if not adventurers:
            self.query_one("#overview-status", Static).update(
                "[dim]No active adventurers.[/dim]"
            )
            return
        self.query_one("#overview-status", Static).update("")

        traits_by_id = _get_combat_traits()

        for adv in adventurers:
            sheet = sta.normalize_sheet(adv["fields"].get("sheet", {}))

            stress_text = _stress_cell(sheet["stress_current"], sheet["stress_max"])
            rank = sheet["rank"] or "—"
            focuses = ", ".join(sheet["focuses"]) if sheet["focuses"] else "—"

            traits = traits_by_id.get(adv["id"], [])
            trait_str = ", ".join(c["name"] for c in traits) if traits else "—"

            injuries = ", ".join(sheet["injuries"]) if sheet["injuries"] else "—"

            table.add_row(
                adv["name"],
                rank,
                stress_text,
                str(sheet["determination"]),
                focuses,
                trait_str,
                injuries,
                key=str(adv["id"]),
            )

    def action_refresh_data(self):
        self._load_data()

    # -- recovery ---------------------------------------------------------

    def _selected_entity_id(self) -> int | None:
        table = self.query_one("#party-table", DataTable)
        if table.row_count == 0 or table.cursor_row is None:
            return None
        cell_key = table.coordinate_to_cell_key(table.cursor_coordinate)
        return int(cell_key.row_key.value)

    def _recover_stress_all(self):
        adventurers = db.active_adventurers()
        if not adventurers:
            self._recovery_status("[dim]No active adventurers to recover.[/dim]")
            return
        for adv in adventurers:
            fields = dict(adv["fields"])
            fields["sheet"] = recovery_mod.recover_stress(adv["fields"].get("sheet", {}))
            db.update_entity(adv["id"], adv["name"], fields, adv["notes"])
        self._load_data()
        self._recovery_status(f"[#c3e88d]Stress restored for {len(adventurers)} active PC(s).[/]")

    def _clear_injuries_selected(self):
        entity_id = self._selected_entity_id()
        if entity_id is None:
            self._recovery_status("[red]Select a PC in the table first.[/]")
            return
        entity = db.get_entity(entity_id)
        if entity is None:
            return
        sheet = sta.normalize_sheet(entity["fields"].get("sheet", {}))
        if not sheet["injuries"]:
            self._recovery_status(f"[dim]{entity['name']} has no Injuries to clear.[/dim]")
            return
        fields = dict(entity["fields"])
        fields["sheet"] = recovery_mod.clear_all_injuries(sheet)
        db.update_entity(entity_id, entity["name"], fields, entity["notes"])
        self._load_data()
        self._recovery_status(f"[#c3e88d]Cleared all Injuries for {entity['name']}.[/]")

    def _threat_between_missions(self, carry: bool):
        pools = db.get_pools()
        new_threat = momentum_mod.threat_between_missions(pools["threat"], carry)
        db.set_pools(pools["momentum"], new_threat)
        if carry:
            self._recovery_status(f"[#c3e88d]Threat carried over ({new_threat}).[/]")
        else:
            self._recovery_status("[#c3e88d]Threat reset to 0 for the next mission.[/]")

    def _recovery_status(self, message: str):
        self.query_one("#recovery-status", Static).update(message)

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if bid == "btn-recover-stress-all":
            self._recover_stress_all()
        elif bid == "btn-clear-injuries":
            self._clear_injuries_selected()
        elif bid == "btn-threat-carry":
            self._threat_between_missions(carry=True)
        elif bid == "btn-threat-reset":
            self._threat_between_missions(carry=False)


# -- helpers ------------------------------------------------------------------

def _stress_cell(current: int, maximum: int) -> Text:
    label = f"{current}/{maximum}"
    if maximum == 0:
        return Text(label, style="dim")
    pct = current / maximum
    if current == 0:
        color = "bold red"
    elif pct > 0.5:
        color = "green"
    elif pct > 0.25:
        color = "yellow"
    else:
        color = "red"
    return Text(label, style=color)


def _get_combat_traits() -> dict[int, list[dict]]:
    """Return {entity_id: [trait,...]} for combatants in any started conflict."""
    result: dict[int, list[dict]] = {}
    for enc in db.list_entities("encounter"):
        combat = cbt.normalize_combat(enc["fields"].get("combat"))
        if not combat["started"]:
            continue
        for combatant in combat["combatants"]:
            if combatant["conditions"]:
                result[combatant["entity_id"]] = combatant["conditions"]
    return result
