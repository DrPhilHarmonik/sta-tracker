from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Label, Button, Input, Select, Static
from textual.containers import Container

import db
import species as species_mod
import supporting
from screens.common import DismissableScreen, tint_border


class QuickCrewScreen(DismissableScreen):
    """One-step creation of a Supporting Character (quick crew): name, species,
    an optional Focus and role. Builds a light STA sheet and drops you on it."""

    BINDINGS = [Binding("escape", "dismiss_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("[bold]Quick Crew[/]  (a Supporting Character, built in one step)"),
            Label("Name"), Input(id="crew-name"),
            Label("Species"),
            Select([(s, s) for s in species_mod.SPECIES_NAMES], value=species_mod.SPECIES_NAMES[0],
                   id="crew-species", allow_blank=False),
            Label("Focus (optional)"), Input(placeholder="e.g. Transporters", id="crew-focus"),
            Label("Role (optional)"), Input(placeholder="e.g. Transporter Chief", id="crew-role"),
            Static("", id="crew-status"),
            Container(
                Button("Create", id="btn-crew-create", variant="success"),
                Button("Cancel", id="btn-crew-cancel"),
                id="crew-actions",
            ),
            id="crew-container",
        )
        yield Footer()

    async def on_mount(self):
        self.title = "Quick Crew"
        tint_border(self.query_one("#crew-container"), "adventurer")
        self.query_one("#crew-name", Input).focus()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-crew-create":
            self._create()
        elif event.button.id == "btn-crew-cancel":
            self.dismiss()

    def _create(self):
        name = self.query_one("#crew-name", Input).value.strip()
        if not name:
            self.query_one("#crew-status", Static).update("[red]Name is required.[/]")
            return
        species = str(self.query_one("#crew-species", Select).value)
        focus = self.query_one("#crew-focus", Input).value
        role = self.query_one("#crew-role", Input).value.strip()
        sheet = supporting.build_sheet(species, focus=focus, role=role)
        entity_id = db.create_entity("adventurer", name, {
            "species": species, "role": role, "status": "Active", "sheet": sheet,
        }, "")
        from screens.sheet import CharacterSheetScreen
        self.dismiss(entity_id)
        self.app.push_screen(CharacterSheetScreen(entity_id))
