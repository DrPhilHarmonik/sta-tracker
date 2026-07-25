from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Static, DataTable
from textual.containers import ScrollableContainer
from rich.text import Text

import timeline
from screens.common import DismissableScreen, PALETTE, tint_border


class TimelineScreen(DismissableScreen):
    """A chronological view of the campaign's sessions -- number, Stardate,
    in-game date, real date, primary location and a one-line recap -- ordered
    as they were played. Selecting a row opens that session's detail."""

    BINDINGS = [Binding("escape", "dismiss_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(
            Static("", id="timeline-empty"),
            DataTable(id="timeline-table", cursor_type="row"),
            id="timeline-scroll",
        )
        yield Footer()

    def on_mount(self):
        self.title = "Campaign Timeline"
        tint_border(self.query_one("#timeline-scroll"), "session")
        self.query_one("#timeline-table", DataTable).add_columns(
            "#", "Stardate", "In-Game Date", "Real Date", "Location", "Session", "Recap"
        )
        self._load()

    def _load(self):
        entries = timeline.session_entries()
        empty = self.query_one("#timeline-empty", Static)
        table = self.query_one("#timeline-table", DataTable)
        table.clear()
        if not entries:
            empty.update(
                "[dim]No sessions yet. Create a Session entity (press [b]s[/b] on the "
                "dashboard) to start the campaign timeline.[/dim]"
            )
            table.display = False
            return
        empty.update("")
        table.display = True
        for e in entries:
            table.add_row(
                e["number"] or "—",
                e["stardate"] or "—",
                e["in_game_date"] or "—",
                e["session_date"] or "—",
                e["location"] or "—",
                Text(e["name"], style=f"bold {PALETTE.get('session', '')}"),
                Text(e["recap"]) if e["recap"] else Text("—", style="dim"),
                key=str(e["id"]),
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        from screens.entities import EntityDetailScreen

        entity_id = int(event.row_key.value)
        self.app.push_screen(EntityDetailScreen(entity_id), callback=lambda _: self._load())
