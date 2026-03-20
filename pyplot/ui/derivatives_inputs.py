# pyplot/ui/derivatives_inputs.py

import urwid

class DerivativesInputFields:
    def __init__(self):
        self.function_edit = urwid.Edit(("bold", "Function: "), "")
        self.x_min_edit = urwid.Edit("X min: ", "")
        self.x_max_edit = urwid.Edit("X max: ", "")
        self.y_min_edit = urwid.Edit("Y min: ", "")
        self.y_max_edit = urwid.Edit("Y max: ", "")
        self.title_edit = urwid.Edit("Plot title: ", "")
        self.x_label_edit = urwid.Edit("X label: ", "")
        self.y_label_edit = urwid.Edit("Y label: ", "")

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

    def get_title(self):
        return self.title_edit.edit_text.strip()

    def get_x_label(self):
        return self.x_label_edit.edit_text.strip()

    def get_y_label(self):
        return self.y_label_edit.edit_text.strip()

    def build_widget(self):
        return [
            self.function_edit,
            urwid.Columns([self.x_min_edit, self.x_max_edit]),
            urwid.Columns([self.y_min_edit, self.y_max_edit]),
            self.title_edit,
            self.x_label_edit,
            self.y_label_edit,
        ]
