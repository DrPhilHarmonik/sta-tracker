from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Input, Static, ListView, ListItem, Button, Label, TabbedContent, TabPane
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual import on

import talents as talents_lib
import focuses as focuses_lib
from screens.common import DismissableScreen, tint_border


class ReferenceScreen(DismissableScreen):
    """Manage the user-authored Talent and Focus reference libraries.

    Both ship empty and fill in as the GM plays (the sheets and wizard remember
    what's typed); this screen is where they're browsed, described, and pruned."""

    BINDINGS = [Binding("escape", "dismiss_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="reference-tabs"):
            with TabPane("Talents", id="tab-ref-talents"):
                yield Horizontal(
                    Vertical(
                        Input(placeholder="Search talents...", id="ref-talent-search"),
                        ListView(id="ref-talent-list"),
                        id="ref-talent-left",
                    ),
                    ScrollableContainer(
                        Static("Add or select a Talent.", id="ref-talent-detail"),
                        Label("Name"),
                        Input(id="ref-talent-name"),
                        Label("Description"),
                        Input(id="ref-talent-desc"),
                        Horizontal(
                            Button("Save Talent", id="btn-ref-talent-save", variant="success"),
                            Button("Remove", id="btn-ref-talent-remove", variant="error"),
                            id="ref-talent-actions",
                        ),
                        id="ref-talent-right",
                    ),
                    id="ref-talent-split",
                )
            with TabPane("Focuses", id="tab-ref-focuses"):
                yield Vertical(
                    Input(placeholder="Search focuses...", id="ref-focus-search"),
                    ListView(id="ref-focus-list"),
                    Horizontal(
                        Input(placeholder="New focus, e.g. Astrophysics", id="ref-focus-input"),
                        Button("Add", id="btn-ref-focus-add", variant="success"),
                        Button("Remove Selected", id="btn-ref-focus-remove", variant="error"),
                        id="ref-focus-actions",
                    ),
                    id="ref-focus-wrap",
                )
        yield Footer()

    async def on_mount(self):
        self.title = "Talent & Focus Reference"
        tint_border(self.query_one("#reference-tabs"), "adventurer")
        self._refresh_talents()
        self._refresh_focuses()

    # -- talents ----------------------------------------------------------

    def _refresh_talents(self, query: str = ""):
        results = talents_lib.search(query) if query else talents_lib.all_talents()
        lv = self.query_one("#ref-talent-list", ListView)
        lv.clear()
        for t in results:
            lv.append(ListItem(Label(t["name"]), name=t["name"]))
        detail = self.query_one("#ref-talent-detail", Static)
        if not results:
            detail.update("[dim]No talents yet. Add one below, or they'll accumulate as you play.[/dim]")

    @on(Input.Changed, "#ref-talent-search")
    def _on_talent_search(self, event: Input.Changed):
        self._refresh_talents(event.value)

    @on(ListView.Highlighted, "#ref-talent-list")
    def _on_talent_highlighted(self, event: ListView.Highlighted):
        if event.item is None or not event.item.name:
            return
        talent = talents_lib.find(event.item.name)
        if talent:
            self.query_one("#ref-talent-name", Input).value = talent["name"]
            self.query_one("#ref-talent-desc", Input).value = talent["description"]
            self.query_one("#ref-talent-detail", Static).update(
                f"[bold]{talent['name']}[/bold]\n\n{talent['description'] or '[dim](no description)[/dim]'}"
            )

    def _save_talent(self):
        name = self.query_one("#ref-talent-name", Input).value.strip()
        if not name:
            return
        talents_lib.save(name, self.query_one("#ref-talent-desc", Input).value.strip())
        self._refresh_talents(self.query_one("#ref-talent-search", Input).value)

    def _remove_talent(self):
        name = self.query_one("#ref-talent-name", Input).value.strip()
        if not name:
            return
        talents_lib.remove(name)
        self.query_one("#ref-talent-name", Input).value = ""
        self.query_one("#ref-talent-desc", Input).value = ""
        self._refresh_talents(self.query_one("#ref-talent-search", Input).value)

    # -- focuses ----------------------------------------------------------

    def _refresh_focuses(self, query: str = ""):
        results = focuses_lib.search(query) if query else focuses_lib.all_focuses()
        lv = self.query_one("#ref-focus-list", ListView)
        lv.clear()
        for f in results:
            lv.append(ListItem(Label(f), name=f))

    @on(Input.Changed, "#ref-focus-search")
    def _on_focus_search(self, event: Input.Changed):
        self._refresh_focuses(event.value)

    def _add_focus(self):
        name = self.query_one("#ref-focus-input", Input).value.strip()
        if not name:
            return
        focuses_lib.add(name)
        self.query_one("#ref-focus-input", Input).value = ""
        self._refresh_focuses(self.query_one("#ref-focus-search", Input).value)

    def _remove_focus(self):
        lv = self.query_one("#ref-focus-list", ListView)
        item = lv.highlighted_child
        if item is None or not item.name:
            return
        focuses_lib.remove(item.name)
        self._refresh_focuses(self.query_one("#ref-focus-search", Input).value)

    # -- dispatch ---------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if bid == "btn-ref-talent-save":
            self._save_talent()
        elif bid == "btn-ref-talent-remove":
            self._remove_talent()
        elif bid == "btn-ref-focus-add":
            self._add_focus()
        elif bid == "btn-ref-focus-remove":
            self._remove_focus()
