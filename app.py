import os
import re

from textual.app import App
from textual.binding import Binding

import db
import campaign_manager as cm
import settings
import theme as theme_mod
from screens.dashboard import Dashboard


class STAApp(App):
    CSS_PATH = "sta.tcss"
    TITLE = "STA Tracker"
    SCREENS = {"dashboard": Dashboard}
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+n", "quick_capture", "Quick Capture"),
        Binding("ctrl+t", "cycle_theme", "Theme"),
        # `?` is the key people try, and F1 is the one that still works while a
        # text field has focus -- on the entity lists the search Input takes
        # focus on mount, so a bare `?` is typed into it rather than dispatched.
        # Making `?` priority would fix that by breaking the ability to type a
        # question mark anywhere in the app, which is a bad trade for a search
        # box and a notes field.
        Binding("question_mark", "help", "Help"),
        Binding("f1", "help", "Help", show=False),
    ]

    _active_session_id: int | None = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Themes must be registered and the active one selected before the
        # stylesheet parses (which happens during startup, ahead of on_mount),
        # or its $sta-* variable references resolve against the wrong theme.
        theme_mod.register(self)
        saved = settings.get_setting("theme", theme_mod.DEFAULT_THEME)
        self.theme = saved if saved in theme_mod.THEME_NAMES else theme_mod.DEFAULT_THEME

    def watch_theme(self, theme_name: str) -> None:
        # The LCARS layout idioms (round borders, right-aligned headers) live in
        # sta.tcss gated on `App.-theme-lcars`; toggle that class to match the
        # active theme. Fires on the __init__ assignment too, so a saved LCARS
        # theme lands with its idioms already applied.
        self.set_class(theme_name == theme_mod.LCARS_THEME, theme_mod.LCARS_CLASS)

    def action_cycle_theme(self):
        new_theme = theme_mod.next_theme(self.theme)
        self.theme = new_theme
        settings.set_setting("theme", new_theme)
        self.notify(f"Theme: {new_theme}", title="Theme")

    def on_mount(self):
        if not os.environ.get("STA_DB_PATH"):
            path = cm.ensure_default()
            db.set_db_path(path)
        db.init_db()
        self.push_screen("dashboard")

    def _resolve_session(self) -> int | None:
        if self._active_session_id is not None:
            if db.get_entity(self._active_session_id):
                return self._active_session_id
            self._active_session_id = None
        entity = db.latest_session()
        if entity:
            self._active_session_id = entity["id"]
            return entity["id"]
        return None

    def _get_combat_round(self) -> int | None:
        for screen in reversed(self.screen_stack):
            if type(screen).__name__ == "CombatTrackerScreen":
                try:
                    return screen.combat.get("round")
                except Exception:
                    pass
        return None

    def action_help(self):
        """Show the keys the *current* screen answers to.

        The bindings are read here rather than inside HelpScreen because
        pushing the modal makes it the active screen: asked from in there,
        Textual would truthfully answer with the help overlay's own three keys.

        Pressing `?` with the overlay already open closes it, rather than
        stacking a second copy describing the first.
        """
        from screens.help import HelpScreen, binding_rows

        screen = self.screen
        if isinstance(screen, HelpScreen):
            screen.dismiss()
            return
        rows = binding_rows(screen.active_bindings, self.get_key_display,
                            nodes=(screen, self))
        self.push_screen(HelpScreen(rows, type(screen).__name__, self._help_title(screen)))

    @staticmethod
    def _help_title(screen) -> str:
        """A screen's own words for itself, falling back to its class name.

        Screens carry a docstring far more often than any title attribute, and
        its first line is already written for a reader.
        """
        title = getattr(screen, "TITLE", None)
        if title:
            return str(title)
        doc = (type(screen).__doc__ or "").strip()
        if doc:
            return doc.splitlines()[0].rstrip(".")
        # Last resort, and it shows: "EntityListScreen" is a class name, not a
        # place. Split the camel case and drop the redundant "Screen".
        name = re.sub(r"(?<!^)(?=[A-Z])", " ", type(screen).__name__)
        return name.removesuffix(" Screen")

    def action_quick_capture(self):
        from screens.quick_capture import QuickCaptureModal
        session_id = self._resolve_session()
        round_num = self._get_combat_round()
        self.push_screen(
            QuickCaptureModal(session_id, round_num),
            callback=self._on_capture_result,
        )

    def _on_capture_result(self, result: dict | None):
        if result:
            saved = " + ".join(result["saved_to"])
            self.notify(f'Saved to {saved}', title="Captured")


def main():
    app = STAApp()
    app.run()


if __name__ == "__main__":
    main()
