from textual.app import ComposeResult
from textual.widgets import Button, Static
from textual.screen import ModalScreen
from textual.containers import Container, Horizontal


class ConfirmScreen(ModalScreen):
    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        yield Container(
            Static(self.message),
            Horizontal(
                Button("Yes", id="btn-yes", variant="error"),
                Button("No", id="btn-no", variant="default"),
            ),
            id="confirm-box",
        )

    def on_button_pressed(self, event: Button.Pressed):
        self.dismiss(event.button.id == "btn-yes")
