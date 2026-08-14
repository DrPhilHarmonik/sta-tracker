"""The `?` overlay: every key the current screen answers to.

Built from `Screen.active_bindings` -- what Textual will *actually* dispatch
right now -- rather than a hand-written list, which would start accurate and
drift by the next phase.

The overlay earns its place because the footer is not the whole story. The
dashboard alone carries nine `show=False` bindings (`n`, `a`, `x`, `l`, `q`,
`f`, `i`, `s`, `c` -- one per entity type), which is fast once you know it and
invisible until someone tells you. Those are exactly the keys this lists.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

# Bindings Textual contributes to every app. They are the framework's, not this
# app's, and a play aid should list what the tracker does.
#
# Filtered by action rather than by `Binding.system`, which sounds like the
# right hook and is `False` on every one of these in Textual 8.0 -- checked
# against a live screen, not assumed. `press` is the focused Button's own
# binding, so it comes and goes with focus and describes the widget rather than
# the screen.
FRAMEWORK_ACTIONS = frozenset({
    "app.focus_next",
    "app.focus_previous",
    "screen.copy_text",
    "command_palette",
    "app.command_palette",
    "press",
})


def binding_rows(bindings: dict, key_display=None, nodes=None) -> list[tuple[str, str, str]]:
    """(key, description, where it comes from) for each active binding.

    Takes the mapping from `Screen.active_bindings`, which is keyed by key, so
    a screen binding that shadows an app one appears once -- as the screen's,
    which is the one that would fire.

    `nodes` limits the result to bindings declared by those objects -- pass the
    screen and the app. Without it the overlay is unusable on any screen with a
    focused text field: `active_bindings` merges in the focused widget's own
    chain, and a plain `Input` contributes thirty rows of "Delete character
    left" and "Move cursor right a word and select" that bury the four keys the
    screen actually offers. Every `BINDINGS` in this app is declared on a screen
    or on the app, so nothing of ours is lost by scoping to them.

    `key_display` should be `App.get_key_display`. Without it the keys read
    wrong rather than merely plain: Textual normalises `/` to `slash` and `?` to
    `question_mark` internally, and `binding.key` holds the normalised form.

    Two keys for one action are merged into a single row (`? / F1`) rather than
    listed twice, since they are one thing you can do.
    """
    merged: dict[tuple[str, str], list[str]] = {}
    for active in bindings.values():
        binding: Binding = active.binding
        if nodes is not None and not any(active.node is node for node in nodes):
            continue
        if binding.action in FRAMEWORK_ACTIONS:
            continue
        if not binding.description:
            continue  # an unlabelled binding has nothing to say to a reader
        if key_display is not None:
            shown = key_display(binding)
        else:
            shown = binding.key_display or binding.key
        source = type(active.node).__name__
        merged.setdefault((binding.description, source), []).append(shown)
    return [(" / ".join(keys), description, source)
            for (description, source), keys in merged.items()]


def group_rows(rows, screen_name: str) -> list[tuple[str, list[tuple[str, str]]]]:
    """Split the rows into 'this screen' and 'everywhere', in that order.

    The distinction is the useful one in play: which of these keys will still
    work after I press escape?
    """
    here = [(key, desc) for key, desc, source in rows if source == screen_name]
    everywhere = [(key, desc) for key, desc, source in rows if source != screen_name]
    groups = []
    if here:
        groups.append(("This screen", sorted(here, key=lambda r: r[1].lower())))
    if everywhere:
        groups.append(("Everywhere", sorted(everywhere, key=lambda r: r[1].lower())))
    return groups


class HelpScreen(ModalScreen):
    """Keyboard help for whichever screen was active when `?` was pressed.

    The bindings are captured by the caller and passed in, not read here:
    pushing this modal makes *it* the active screen, so reading
    `active_bindings` from inside would faithfully describe the help overlay
    and nothing else.
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("question_mark", "close", "Close"),
        Binding("q", "close", "Close"),
    ]

    def __init__(self, rows, screen_name: str, title: str = ""):
        super().__init__()
        self.rows = rows
        self.screen_name = screen_name
        self.help_title = title or screen_name

    def compose(self) -> ComposeResult:
        groups = group_rows(self.rows, self.screen_name)
        body = VerticalScroll(id="help-body")
        yield Container(
            Static(f"Keys — {self.help_title}", id="help-title"),
            body,
            Static("escape or ? to close", id="help-hint"),
            id="help-box",
        )

    def on_mount(self) -> None:
        body = self.query_one("#help-body")
        for heading, entries in group_rows(self.rows, self.screen_name):
            body.mount(Static(heading, classes="help-group"))
            for key, description in entries:
                body.mount(Static(f"  {key:<12}  {description}", classes="help-row"))
        if not self.rows:
            body.mount(Static("  (no keys bound on this screen)", classes="help-row"))

    def action_close(self) -> None:
        self.dismiss()
