import urwid
from pyplot.core.state import state, MARKERS


class MarkerSelector(urwid.Button):
    """
    A button-like widget that cycles through available markers.
    Updates global state.marker when pressed.
    """
    def __init__(self):
        self.index = MARKERS.index(state.marker)
        super().__init__(self._label_text())
        urwid.connect_signal(self, "click", self._on_click)

    def _label_text(self):
        return f"Marker: {MARKERS[self.index]}"

    def _on_click(self, button):
        self.index = (self.index + 1) % len(MARKERS)
        state.marker = MARKERS[self.index]
        self.set_label(self._label_text())
