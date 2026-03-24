# pyplot/ui/parametric_inputs.py

import urwid

class ParametricInputFields:
    def __init__(self):
        self.xt_edit = urwid.Edit(("bold", "x(t): "), "")
        self.yt_edit = urwid.Edit(("bold", "y(t): "), "")
        self.t_min_edit = urwid.Edit("T min: ", "")
        self.t_max_edit = urwid.Edit("T max: ", "")
        self.t_step_edit = urwid.Edit("T step: ", "0.1")
        self.x_min_edit = urwid.Edit("X min: ", "")
        self.x_max_edit = urwid.Edit("X max: ", "")
        self.y_min_edit = urwid.Edit("Y min: ", "")
        self.y_max_edit = urwid.Edit("Y max: ", "")
        self.title_edit = urwid.Edit("Plot title: ", "")
        self.x_label_edit = urwid.Edit("X label: ", "")
        self.y_label_edit = urwid.Edit("Y label: ", "")

    def get_xt(self):
        return self.xt_edit.edit_text.strip()

    def get_yt(self):
        return self.yt_edit.edit_text.strip()

    def get_t_min(self):
        return self.t_min_edit.edit_text.strip()

    def get_t_max(self):
        return self.t_max_edit.edit_text.strip()

    def get_t_step(self):
        return self.t_step_edit.edit_text.strip()

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

    def clear(self):
        self.xt_edit.set_edit_text("")
        self.yt_edit.set_edit_text("")

    def build_widget(self):
        return [
            self.xt_edit,
            self.yt_edit,
            urwid.Columns([self.t_min_edit, self.t_max_edit]),
            self.t_step_edit,
            urwid.Columns([self.x_min_edit, self.x_max_edit]),
            urwid.Columns([self.y_min_edit, self.y_max_edit]),
            self.title_edit,
            self.x_label_edit,
            self.y_label_edit,
        ]
