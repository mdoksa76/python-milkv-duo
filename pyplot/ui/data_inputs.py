# pyplot/ui/data_inputs.py

import urwid

class DataInputFields:
    def __init__(self):
        self.title_edit = urwid.Edit("Plot title: ", "")
        self.x_label_edit = urwid.Edit("X label: ", "")
        self.y_label_edit = urwid.Edit("Y label: ", "")
        self.x_min_edit = urwid.Edit("X min: ", "")
        self.x_max_edit = urwid.Edit("X max: ", "")
        self.y_min_edit = urwid.Edit("Y min: ", "")
        self.y_max_edit = urwid.Edit("Y max: ", "")

        # Fit checkboxi
        self.fit_linear = urwid.CheckBox("Linear", state=False)
        self.fit_exponential = urwid.CheckBox("Exponential", state=False)
        self.fit_logarithmic = urwid.CheckBox("Logarithmic", state=False)
        self.fit_poly2 = urwid.CheckBox("Polynomial 2°", state=False)

    def get_title(self):
        return self.title_edit.edit_text.strip()

    def get_x_label(self):
        return self.x_label_edit.edit_text.strip()

    def get_y_label(self):
        return self.y_label_edit.edit_text.strip()

    def get_x_min(self):
        return self.x_min_edit.edit_text.strip()

    def get_x_max(self):
        return self.x_max_edit.edit_text.strip()

    def get_y_min(self):
        return self.y_min_edit.edit_text.strip()

    def get_y_max(self):
        return self.y_max_edit.edit_text.strip()

    def get_selected_fits(self):
        """Vrati listu ključeva odabranih fitova."""
        selected = []
        if self.fit_linear.state:
            selected.append('linear')
        if self.fit_exponential.state:
            selected.append('exponential')
        if self.fit_logarithmic.state:
            selected.append('logarithmic')
        if self.fit_poly2.state:
            selected.append('poly2')
        return selected

    def build_widget(self):
        return [
            self.title_edit,
            self.x_label_edit,
            self.y_label_edit,
            urwid.Columns([self.x_min_edit, self.x_max_edit]),
            urwid.Columns([self.y_min_edit, self.y_max_edit]),
            urwid.Divider(),
            urwid.Text(("bold", "Fits:")),
            self.fit_linear,
            self.fit_exponential,
            self.fit_logarithmic,
            self.fit_poly2,
        ]
