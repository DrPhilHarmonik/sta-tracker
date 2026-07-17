from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Input, Static, ListView, ListItem, Button, Label, Select
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual import on

import db
import spaceframes as sf
import starship as ship
from screens.common import DismissableScreen, tint_border

EMPTY_MESSAGE = (
    "[dim]Your spaceframe library is empty.\n\n"
    "STA ships no starship classes -- build a ship in the campaign, then pick it "
    "below and 'Save to Library' to keep a reusable spaceframe. Saved frames can "
    "be built into a new ship in any campaign.[/dim]"
)


class SpaceframeScreen(DismissableScreen):
    """User-authored spaceframe (starship class) library. Ships empty; the GM
    snapshots frames from ships they build and spawns new ships from them."""

    BINDINGS = [Binding("escape", "dismiss_screen", "Back")]

    def __init__(self):
        super().__init__()
        self._selected: dict | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Vertical(
                Input(placeholder="Search spaceframes...", id="frame-search"),
                ListView(id="frame-list"),
                id="frame-left",
            ),
            ScrollableContainer(Static(EMPTY_MESSAGE, id="frame-detail"), id="frame-right"),
            id="frame-split",
        )
        yield Horizontal(
            Label("Save campaign ship:"),
            Select(self._ship_options(), id="sel-import-ship", prompt="Choose starship..."),
            Button("Save to Library", id="btn-save-frame", variant="primary"),
            id="frame-import",
        )
        yield Horizontal(
            Button("Build New Ship", id="btn-build-ship", variant="success"),
            Button("Remove from Library", id="btn-remove-frame", variant="error"),
            Button("Back", id="btn-frame-back", variant="default"),
            id="frame-actions",
        )
        yield Footer()

    async def on_mount(self):
        self.title = "Spaceframe Library"
        tint_border(self.query_one("#frame-split"), "starship")
        self._refresh_list()
        self.query_one("#frame-search").focus()

    def _ship_options(self):
        return [(e["name"], str(e["id"])) for e in db.list_entities("starship")]

    def _refresh_list(self, query: str = ""):
        results = sf.search(query) if query else sf.all_spaceframes()
        lv = self.query_one("#frame-list", ListView)
        lv.clear()
        for f in results:
            lv.append(ListItem(Label(f"{f['name']}  [dim](Scale {f['scale']})[/dim]"), name=f["name"]))
        self._selected = results[0] if results else None
        if self._selected:
            self._show_detail(self._selected)
        else:
            self.query_one("#frame-detail", Static).update(EMPTY_MESSAGE)

    @on(Input.Changed, "#frame-search")
    def _on_search(self, event: Input.Changed):
        self._refresh_list(event.value)

    @on(ListView.Highlighted, "#frame-list")
    def _on_highlighted(self, event: ListView.Highlighted):
        if event.item is None or not event.item.name:
            return
        frame = sf.find(event.item.name)
        if frame:
            self._selected = frame
            self._show_detail(frame)

    def _show_detail(self, f: dict):
        lines = [
            f"[bold]{f['name']}[/bold]  --  Scale {f['scale']}",
            "",
            "  ".join(f"{ship.SYSTEM_LABELS[s]} {f['systems'][s]}" for s in ship.SYSTEMS),
        ]
        if f["talents"]:
            lines.append(f"Talents: {', '.join(f['talents'])}")
        if f["traits"]:
            lines.append(f"Traits: {', '.join(f['traits'])}")
        if f["notes"]:
            lines.append("")
            lines.append(f["notes"])
        self.query_one("#frame-detail", Static).update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if bid == "btn-save-frame":
            self._save_from_ship()
        elif bid == "btn-build-ship":
            self._build_ship()
        elif bid == "btn-remove-frame":
            self._remove()
        else:
            self.action_dismiss_screen()

    def _save_from_ship(self):
        sel = self.query_one("#sel-import-ship", Select)
        if sel.value is Select.NULL:
            self.app.notify("Choose a campaign ship to save.", severity="warning")
            return
        entity = db.get_entity(int(str(sel.value)))
        if not entity:
            return
        frame = sf.save(sf.from_entity(entity))
        self._refresh_list()
        self.app.notify(f"Saved {frame['name']} to the spaceframe library.")

    def _build_ship(self):
        if not self._selected:
            self.app.notify("Select a spaceframe first.", severity="warning")
            return
        from screens.starship import StarshipSheetScreen
        sheet = sf.build_sheet(self._selected)
        entity_id = db.create_entity(
            "starship",
            f"New {self._selected['name']}",
            {"spaceframe": self._selected["name"], "scale": str(self._selected["scale"]), "sheet": sheet},
            "",
        )
        self.app.notify(f"Built a new {self._selected['name']}.")
        self.app.push_screen(StarshipSheetScreen(entity_id))

    def _remove(self):
        if not self._selected:
            return
        name = self._selected["name"]
        sf.remove(name)
        self._refresh_list(self.query_one("#frame-search", Input).value)
        self.app.notify(f"Removed {name} from the library.")
