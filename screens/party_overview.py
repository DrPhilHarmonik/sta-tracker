from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, DataTable, Static
from textual.containers import Container

import db
import sta_sheet as sta
import combat as cbt
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
            DataTable(id="party-table", show_cursor=False),
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
            )

    def action_refresh_data(self):
        self._load_data()


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
