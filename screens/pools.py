from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Static

import db
import momentum as momentum_mod


class PoolBar(Horizontal):
    """Always-visible Momentum/Threat counters with spend/add controls.

    Momentum and Threat are table-level shared pools (see momentum.py), not
    character stats, so the bar reads and writes the singleton campaign-state
    row directly through db rather than any entity. Mount it anywhere a GM
    needs the pools in view; call ``refresh_pools()`` after external changes
    (e.g. Momentum banked by a task roll on another screen)."""

    DEFAULT_CSS = """
    PoolBar {
        height: 3;
        align-vertical: middle;
        border: round #3a3a5a;
        padding: 0 1;
    }
    PoolBar #pool-readout {
        width: 1fr;
        content-align: left middle;
    }
    PoolBar .pool-btn {
        min-width: 6;
        margin: 0 1 0 0;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("", id="pool-readout")
        yield Button("- Mom", id="btn-mom-dec", classes="pool-btn")
        yield Button("+ Mom", id="btn-mom-inc", classes="pool-btn")
        yield Button("- Thr", id="btn-thr-dec", classes="pool-btn")
        yield Button("+ Thr", id="btn-thr-inc", classes="pool-btn")
        yield Button("Seed", id="btn-thr-seed", classes="pool-btn")

    def on_mount(self) -> None:
        self.refresh_pools()

    def refresh_pools(self) -> None:
        pools = db.get_pools()
        self.query_one("#pool-readout", Static).update(
            f"[b #82aaff]Momentum {pools['momentum']}/{momentum_mod.MOMENTUM_MAX}[/]"
            f"    [b #ff5370]Threat {pools['threat']}[/]"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "btn-mom-inc":
            db.adjust_momentum(1)
        elif bid == "btn-mom-dec":
            db.adjust_momentum(-1)
        elif bid == "btn-thr-inc":
            db.adjust_threat(1)
        elif bid == "btn-thr-dec":
            db.adjust_threat(-1)
        elif bid == "btn-thr-seed":
            db.seed_threat()
        else:
            return
        event.stop()
        self.refresh_pools()
