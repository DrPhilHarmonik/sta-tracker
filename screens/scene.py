from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Input, Static, ListView, ListItem, Button, Label, TabbedContent, TabPane
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual import on

import extended
import scene as scene_lib
from screens.common import DismissableScreen, tint_border


class SceneScreen(DismissableScreen):
    """Manage the current mission's Directives, the current scene's Traits, and
    any Extended Tasks in play. All three are narrative modifiers the GM keeps
    table-visible; the conflict tracker echoes the active Directives/Traits so
    they can be factored into a Task's Difficulty."""

    BINDINGS = [Binding("escape", "dismiss_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="scene-tabs"):
            with TabPane("Extended Tasks", id="tab-extended"):
                yield Horizontal(
                    Vertical(ListView(id="ext-list"), id="ext-left"),
                    ScrollableContainer(
                        Static("Add or select an Extended Task.", id="ext-detail"),
                        Label("Name"), Input(id="ext-name"),
                        Horizontal(
                            Vertical(Label("Magnitude"), Input(value="1", id="ext-magnitude", classes="stat-input")),
                            Vertical(Label("Difficulty"), Input(value="1", id="ext-difficulty", classes="stat-input")),
                            Vertical(Label("Resistance"), Input(value="0", id="ext-resistance", classes="stat-input")),
                            Vertical(Label("Work Total"), Input(value="5", id="ext-work-total", classes="stat-input")),
                            id="ext-fields",
                        ),
                        Horizontal(
                            Button("Save Task", id="btn-ext-save", variant="success"),
                            Button("Remove", id="btn-ext-remove", variant="error"),
                            id="ext-save-actions",
                        ),
                        Horizontal(
                            Label("Log Work"), Input(placeholder="Amount", id="ext-work-amount", classes="stat-input"),
                            Button("Add Work", id="btn-ext-logwork", variant="primary"),
                            id="ext-work-actions",
                        ),
                        id="ext-right",
                    ),
                    id="ext-split",
                )
            with TabPane("Directives & Scene Traits", id="tab-scene"):
                yield Vertical(
                    Static("[bold]Mission Directives[/]"),
                    Horizontal(
                        Input(placeholder="e.g. Investigate, do not engage", id="directive-input"),
                        Button("Add", id="btn-add-directive", variant="success"),
                        Button("Remove Selected", id="btn-remove-directive", variant="error"),
                        id="directive-actions",
                    ),
                    ListView(id="directive-list"),
                    Static("[bold]Scene Traits[/]"),
                    Horizontal(
                        Input(placeholder="e.g. Ion Storm", id="trait-input"),
                        Button("Add", id="btn-add-trait", variant="success"),
                        Button("Remove Selected", id="btn-remove-trait", variant="error"),
                        id="trait-actions",
                    ),
                    ListView(id="trait-list"),
                    id="scene-wrap",
                )
        yield Footer()

    async def on_mount(self):
        self.title = "Scene: Directives, Traits & Extended Tasks"
        tint_border(self.query_one("#scene-tabs"), "quest")
        self._refresh_extended()
        self._refresh_directives()
        self._refresh_traits()

    # -- extended tasks ---------------------------------------------------

    def _refresh_extended(self):
        lv = self.query_one("#ext-list", ListView)
        lv.clear()
        for t in extended.all_tasks():
            done = "✓ " if extended.is_complete(t) else ""
            lv.append(ListItem(Label(f"{done}{t['name']}  ({t['work_done']}/{t['work_total']})"), name=t["name"]))

    @on(ListView.Highlighted, "#ext-list")
    def _on_ext_highlighted(self, event: ListView.Highlighted):
        if event.item is not None and event.item.name:
            self._show_task_detail(event.item.name)

    def _show_task_detail(self, name: str):
        task = extended.find(name)
        if not task:
            return
        self.query_one("#ext-name", Input).value = task["name"]
        self.query_one("#ext-magnitude", Input).value = str(task["magnitude"])
        self.query_one("#ext-difficulty", Input).value = str(task["difficulty"])
        self.query_one("#ext-resistance", Input).value = str(task["resistance"])
        self.query_one("#ext-work-total", Input).value = str(task["work_total"])
        status = "COMPLETE" if extended.is_complete(task) else "in progress"
        self.query_one("#ext-detail", Static).update(
            f"[bold]{task['name']}[/bold] — {status}\n"
            f"Work {task['work_done']}/{task['work_total']}  ·  "
            f"Magnitude {task['magnitude']}  ·  Attempt Difficulty {extended.effective_difficulty(task)} "
            f"(base {task['difficulty']} + Resistance {task['resistance']})"
        )

    def _int(self, widget_id: str, default: int) -> int:
        try:
            return int(self.query_one(f"#{widget_id}", Input).value.strip())
        except ValueError:
            return default

    def _save_task(self):
        name = self.query_one("#ext-name", Input).value.strip()
        if not name:
            return
        existing = extended.find(name)
        work_done = existing["work_done"] if existing else 0
        extended.save({
            "name": name,
            "magnitude": self._int("ext-magnitude", 1),
            "difficulty": self._int("ext-difficulty", 1),
            "resistance": self._int("ext-resistance", 0),
            "work_total": self._int("ext-work-total", 5),
            "work_done": work_done,
        })
        self._refresh_extended()

    def _log_work(self):
        name = self.query_one("#ext-name", Input).value.strip()
        try:
            amount = int(self.query_one("#ext-work-amount", Input).value.strip())
        except ValueError:
            return
        if extended.add_work(name, amount) is not None:
            self.query_one("#ext-work-amount", Input).value = ""
            self._refresh_extended()
            self._show_task_detail(name)

    def _remove_task(self):
        name = self.query_one("#ext-name", Input).value.strip()
        if name:
            extended.remove(name)
            self.query_one("#ext-name", Input).value = ""
            self._refresh_extended()

    # -- directives & traits ---------------------------------------------

    def _refresh_directives(self):
        lv = self.query_one("#directive-list", ListView)
        lv.clear()
        for d in scene_lib.directives():
            lv.append(ListItem(Label(d), name=d))

    def _refresh_traits(self):
        lv = self.query_one("#trait-list", ListView)
        lv.clear()
        for t in scene_lib.traits():
            lv.append(ListItem(Label(t), name=t))

    def _add_directive(self):
        name = self.query_one("#directive-input", Input).value.strip()
        if name:
            scene_lib.add_directive(name)
            self.query_one("#directive-input", Input).value = ""
            self._refresh_directives()

    def _remove_directive(self):
        item = self.query_one("#directive-list", ListView).highlighted_child
        if item is not None and item.name:
            scene_lib.remove_directive(item.name)
            self._refresh_directives()

    def _add_trait(self):
        name = self.query_one("#trait-input", Input).value.strip()
        if name:
            scene_lib.add_trait(name)
            self.query_one("#trait-input", Input).value = ""
            self._refresh_traits()

    def _remove_trait(self):
        item = self.query_one("#trait-list", ListView).highlighted_child
        if item is not None and item.name:
            scene_lib.remove_trait(item.name)
            self._refresh_traits()

    # -- dispatch ---------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if bid == "btn-ext-save":
            self._save_task()
        elif bid == "btn-ext-logwork":
            self._log_work()
        elif bid == "btn-ext-remove":
            self._remove_task()
        elif bid == "btn-add-directive":
            self._add_directive()
        elif bid == "btn-remove-directive":
            self._remove_directive()
        elif bid == "btn-add-trait":
            self._add_trait()
        elif bid == "btn-remove-trait":
            self._remove_trait()
