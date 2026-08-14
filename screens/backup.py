from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Label, Button, Input, Static, Switch
from textual.containers import Container, Horizontal, ScrollableContainer
from pathlib import Path

import export as exp

from screens.common import DismissableScreen, format_io_error
from screens.modals import ConfirmScreen

class ExportScreen(DismissableScreen):
    BINDINGS = [Binding("escape", "dismiss_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("Export Campaign to Obsidian Vault", id="export-title"),
            Label("Output directory:"),
            Input(value=str(Path.home() / "campaign_vault"), id="export-path"),
            Horizontal(
                Switch(value=True, id="export-include-stats"),
                Label("Include character & starship sheets"),
                id="export-stats-row",
            ),
            Horizontal(
                Button("Export", id="btn-export", variant="success"),
                Button("Export Session Log", id="btn-export-log", variant="primary"),
                Button("Play Aids", id="btn-export-play-aids", variant="primary"),
                Button("Cancel", id="btn-cancel"),
                id="export-actions",
            ),
            Static("", id="export-status"),
            id="export-container",
        )
        yield Footer()

    def on_mount(self):
        self.title = "Export to Markdown"

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-export":
            path_str = self.query_one("#export-path", Input).value.strip()
            out_path = Path(path_str).expanduser()
            include_stats = self.query_one("#export-include-stats", Switch).value
            try:
                count = exp.export_vault(out_path, include_stats=include_stats)
                self.query_one("#export-status", Static).update(
                    f"[green]Exported {count} entities to {out_path}[/green]"
                )
            except Exception as ex:
                self.query_one("#export-status", Static).update(f"[red]{format_io_error(ex)}[/red]")
        elif event.button.id == "btn-export-log":
            path_str = self.query_one("#export-path", Input).value.strip()
            log_path = Path(path_str).expanduser() / "Session Log.md"
            try:
                count = exp.export_session_log(log_path)
                self.query_one("#export-status", Static).update(
                    f"[green]Wrote {count} session{'' if count == 1 else 's'} to {log_path}[/green]"
                )
            except Exception as ex:
                self.query_one("#export-status", Static).update(f"[red]{format_io_error(ex)}[/red]")
        elif event.button.id == "btn-export-play-aids":
            path_str = self.query_one("#export-path", Input).value.strip()
            aids_dir = Path(path_str).expanduser() / "Play Aids"
            try:
                count = exp.export_all_play_aids(aids_dir)
                self.query_one("#export-status", Static).update(
                    f"[green]Wrote {count} play aid{'' if count == 1 else 's'} to {aids_dir}[/green]"
                )
            except Exception as ex:
                self.query_one("#export-status", Static).update(f"[red]{format_io_error(ex)}[/red]")
        elif event.button.id == "btn-cancel":
            self.dismiss()


# ---------------------------------------------------------------------------
# Backup / Restore
# ---------------------------------------------------------------------------

class BackupScreen(DismissableScreen):
    BINDINGS = [Binding("escape", "dismiss_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(
            Container(
                Static("Backup & Restore (JSON)", id="backup-title"),
                Label("Backup file path:"),
                Input(value=str(Path.home() / "campaign_backup.json"), id="backup-path"),
                Button("Backup Now", id="btn-backup", variant="success"),
                Static("", id="backup-status"),
                Label("Restore file path:"),
                Input(value=str(Path.home() / "campaign_backup.json"), id="restore-path"),
                Horizontal(
                    Button("Restore (into empty DB)", id="btn-restore", variant="primary"),
                    Button("Restore & Replace All Data", id="btn-restore-replace", variant="error"),
                    id="restore-actions",
                ),
                Static("", id="restore-status"),
                Static("Import Markdown Vault", id="vault-import-title"),
                Label("Vault directory (must have been exported by this app):"),
                Input(value=str(Path.home() / "campaign_vault"), id="vault-import-path"),
                Horizontal(
                    Button("Import (into empty DB)", id="btn-vault-import", variant="primary"),
                    Button("Import & Replace All Data", id="btn-vault-import-replace", variant="error"),
                    id="vault-import-actions",
                ),
                Static("", id="vault-import-status"),
                Button("Back", id="btn-back"),
                id="backup-container",
            ),
            id="backup-scroll",
        )
        yield Footer()

    def on_mount(self):
        self.title = "Backup & Restore"

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-backup":
            self._do_backup()
        elif event.button.id == "btn-restore":
            self._do_restore(replace=False)
        elif event.button.id == "btn-restore-replace":
            self.app.push_screen(
                ConfirmScreen("This will ERASE all current data and replace it with the backup. Continue?"),
                callback=self._on_replace_confirmed,
            )
        elif event.button.id == "btn-vault-import":
            self._do_vault_import(replace=False)
        elif event.button.id == "btn-vault-import-replace":
            self.app.push_screen(
                ConfirmScreen("This will ERASE all current data and replace it with the imported vault. Continue?"),
                callback=self._on_vault_replace_confirmed,
            )
        elif event.button.id == "btn-back":
            self.dismiss()

    def _on_replace_confirmed(self, confirmed: bool):
        if confirmed:
            self._do_restore(replace=True)

    def _on_vault_replace_confirmed(self, confirmed: bool):
        if confirmed:
            self._do_vault_import(replace=True)

    def _do_backup(self):
        path = Path(self.query_one("#backup-path", Input).value.strip()).expanduser()
        try:
            count = exp.export_json_backup(path)
            self.query_one("#backup-status", Static).update(f"[green]Backed up {count} entities to {path}[/green]")
        except Exception as ex:
            self.query_one("#backup-status", Static).update(f"[red]{format_io_error(ex)}[/red]")

    def _do_restore(self, replace: bool):
        path = Path(self.query_one("#restore-path", Input).value.strip()).expanduser()
        try:
            result = exp.import_json_backup(path, replace=replace)
            # The library count is worth showing rather than implying: a v1
            # backup restores zero of them, and that number is the difference
            # between "your reference library came back" and "it did not".
            summary = (
                f"Restored {result['entities']} entities and "
                f"{result['relationships']} relationships"
            )
            if result["libraries"]:
                summary += f", plus {result['libraries']} librar{'y' if result['libraries'] == 1 else 'ies'}"
            self.query_one("#restore-status", Static).update(f"[green]{summary}[/green]")
        except Exception as ex:
            self.query_one("#restore-status", Static).update(f"[red]{format_io_error(ex)}[/red]")

    def _do_vault_import(self, replace: bool):
        path = Path(self.query_one("#vault-import-path", Input).value.strip()).expanduser()
        try:
            result = exp.import_vault(path, replace=replace)
            self.query_one("#vault-import-status", Static).update(
                f"[green]Imported {result['entities']} entities and {result['relationships']} relationships[/green]"
            )
        except Exception as ex:
            self.query_one("#vault-import-status", Static).update(f"[red]{format_io_error(ex)}[/red]")
