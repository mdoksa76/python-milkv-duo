# pyplot/ui/integration_inputs.py

import urwid

class IntegrationInputFields:
    def __init__(self):
        self.function_edit = urwid.Edit(("bold", "Function: "), "")
        self.x_min_edit = urwid.Edit("X min: ", "")
        self.x_max_edit = urwid.Edit("X max: ", "")
        self.y_min_edit = urwid.Edit("Y min: ", "")
        self.y_max_edit = urwid.Edit("Y max: ", "")
        self.a_edit = urwid.Edit("From a: ", "")
        self.b_edit = urwid.Edit("To   b: ", "")
        self.title_edit = urwid.Edit("Plot title: ", "")
        self.x_label_edit = urwid.Edit("X label: ", "")
        self.y_label_edit = urwid.Edit("Y label: ", "")

        # Metoda selector — ciklički gumb
        self._method_keys = ['left', 'right', 'mid', 'simpson']
        self._method_labels = [
            'Left Rectangle',
            'Right Rectangle',
            'Midpoint',
            'Simpson',
        ]
        self._method_index = 3  # default: Simpson
        self.method_button = urwid.Button(self._method_label())
        urwid.connect_signal(self.method_button, 'click', self._on_method_click)

    def _method_label(self):
        return f"Method: {self._method_labels[self._method_index]}"

    def _on_method_click(self, button):
        self._method_index = (self._method_index + 1) % len(self._method_keys)
        self.method_button.set_label(self._method_label())

    def get_function(self):
        return self.function_edit.edit_text.strip()

    def get_x_min(self):
        return self.x_min_edit.edit_text.strip()

    def get_x_max(self):
        return self.x_max_edit.edit_text.strip()

    def get_y_min(self):
        return self.y_min_edit.edit_text.strip()

    def get_y_max(self):
        return self.y_max_edit.edit_text.strip()

    def get_a(self):
        return self.a_edit.edit_text.strip()

    def get_b(self):
        return self.b_edit.edit_text.strip()

    def get_title(self):
        return self.title_edit.edit_text.strip()

    def get_x_label(self):
        return self.x_label_edit.edit_text.strip()

    def get_y_label(self):
        return self.y_label_edit.edit_text.strip()

    def get_method_key(self):
        return self._method_keys[self._method_index]

    def build_widget(self):
        return [
            self.function_edit,
            urwid.Columns([self.x_min_edit, self.x_max_edit]),
            urwid.Columns([self.y_min_edit, self.y_max_edit]),
            urwid.Columns([self.a_edit, self.b_edit]),
            self.method_button,
            self.title_edit,
            self.x_label_edit,
            self.y_label_edit,
        ]
