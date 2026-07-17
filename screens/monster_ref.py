from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Input, Static, ListView, ListItem, Button, Label, Select
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual import on

import db
import adversaries as adv
import sta_sheet as sta
from screens.common import DismissableScreen, tint_border

EMPTY_MESSAGE = (
    "[dim]Your adversary library is empty.\n\n"
    "STA ships no stat blocks -- build an enemy in the campaign (or via the "
    "creation wizard), then pick it below and 'Save to Library' to keep a "
    "reusable copy here. Saved adversaries can be dropped into any campaign.[/dim]"
)


class MonsterRefScreen(DismissableScreen):
    """User-authored STA adversary reference. Ships empty; the GM populates it
    from enemies they build, and spawns saved adversaries into a campaign."""

    BINDINGS = [
        Binding("escape", "dismiss_screen", "Back"),
        Binding("ctrl+a", "add_to_campaign", "Add to Campaign"),
    ]

    def __init__(self):
        super().__init__()
        self._selected: dict | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Vertical(
                Input(placeholder="Search by name or kind...", id="monster-search"),
                ListView(id="monster-list"),
                id="monster-left",
            ),
            ScrollableContainer(
                Static(EMPTY_MESSAGE, id="monster-detail"),
                id="monster-right",
            ),
            id="monster-split",
        )
        yield Horizontal(
            Label("Save campaign enemy:"),
            Select(self._enemy_options(), id="sel-import-enemy", prompt="Choose enemy..."),
            Button("Save to Library", id="btn-save-to-library", variant="primary"),
            id="monster-import",
        )
        yield Horizontal(
            Button("Add to Campaign", id="btn-add-monster", variant="success"),
            Button("Remove from Library", id="btn-remove-from-library", variant="error"),
            Button("Back", id="btn-back", variant="default"),
            id="monster-actions",
        )
        yield Footer()

    async def on_mount(self):
        self.title = "Adversary Reference"
        tint_border(self.query_one("#monster-split"), "enemy")
        self._refresh_list()
        self.query_one("#monster-search").focus()

    # -- data --------------------------------------------------------------

    def _enemy_options(self):
        return [(e["name"], str(e["id"])) for e in db.list_entities("enemy")]

    def _refresh_list(self, query: str = ""):
        results = adv.search(query) if query else adv.all_adversaries()
        lv = self.query_one("#monster-list", ListView)
        lv.clear()
        for a in results:
            lv.append(ListItem(Label(f"{a['name']}  [dim]({a['kind']})[/dim]"), name=a["name"]))
        self._selected = results[0] if results else None
        if self._selected:
            self._show_detail(self._selected)
        else:
            self.query_one("#monster-detail", Static).update(EMPTY_MESSAGE)

    @on(Input.Changed, "#monster-search")
    def on_search(self, event: Input.Changed):
        self._refresh_list(event.value)

    @on(ListView.Highlighted, "#monster-list")
    def on_list_highlighted(self, event: ListView.Highlighted):
        if event.item is None:
            return
        name = event.item.name
        adversary = adv.find(name) if name else None
        if adversary:
            self._selected = adversary
            self._show_detail(adversary)

    def _show_detail(self, a: dict):
        lines = [
            f"[bold]{a['name']}[/bold]  --  {a['kind']}",
            "",
            "  ".join(f"{sta.ATTRIBUTE_LABELS[k]} {a['attributes'][k]}" for k in sta.ATTRIBUTES),
            "  ".join(f"{sta.DEPARTMENT_LABELS[k]} {a['departments'][k]}" for k in sta.DEPARTMENTS),
            "",
            f"Stress {a['stress_max']}   Protection {a['protection']}",
        ]
        if a["focuses"]:
            lines.append(f"Focuses: {', '.join(a['focuses'])}")
        if a["traits"]:
            lines.append(f"Traits: {', '.join(a['traits'])}")
        if a["weapons"]:
            lines.append("")
            lines.append("[bold]Weapons[/bold]")
            for w in a["weapons"]:
                qual = f"  [dim]{w['qualities']}[/dim]" if w["qualities"] else ""
                lines.append(f"  {w['name']}  ({w['damage']} damage rating){qual}")
        if a["notes"]:
            lines.append("")
            lines.append(a["notes"])
        self.query_one("#monster-detail", Static).update("\n".join(lines))

    # -- actions -----------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if bid == "btn-add-monster":
            self.action_add_to_campaign()
        elif bid == "btn-save-to-library":
            self._save_enemy_to_library()
        elif bid == "btn-remove-from-library":
            self._remove_selected()
        else:
            self.action_dismiss_screen()

    def _save_enemy_to_library(self):
        sel = self.query_one("#sel-import-enemy", Select)
        if sel.value is Select.NULL:
            self.app.notify("Choose a campaign enemy to save.", severity="warning")
            return
        entity = db.get_entity(int(str(sel.value)))
        if not entity:
            return
        template = adv.save(adv.from_entity(entity))
        self._refresh_list()
        self.app.notify(f"Saved {template['name']} to the adversary library.")

    def _remove_selected(self):
        if not self._selected:
            return
        name = self._selected["name"]
        adv.remove(name)
        self._refresh_list(self.query_one("#monster-search", Input).value)
        self.app.notify(f"Removed {name} from the library.")

    def action_add_to_campaign(self):
        if not self._selected:
            self.app.notify("Select an adversary first.", severity="warning")
            return
        from screens.sheet import CharacterSheetScreen
        sheet = adv.build_sheet(self._selected)
        entity_id = db.create_entity(
            "enemy",
            self._selected["name"],
            {"kind": self._selected["kind"], "status": "Alive", "sheet": sheet},
            "",
        )
        self.app.notify(f"Added {self._selected['name']} to the campaign.")
        self.app.push_screen(CharacterSheetScreen(entity_id))
