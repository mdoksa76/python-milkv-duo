# pyplot/ui/data_table.py

import urwid

class DataRow(urwid.WidgetWrap):
    """
    Jedan red tablice: dva Edit polja za x i y.
    """
    def __init__(self, on_enter=None):
        self.x_edit = urwid.Edit("", "")
        self.y_edit = urwid.Edit("", "")
        self._on_enter = on_enter

        cols = urwid.Columns([
            ('weight', 1, self.x_edit),
            ('fixed', 1, urwid.Text(" ")),
            ('weight', 1, self.y_edit),
        ])
        super().__init__(cols)

    def get_values(self):
        """Vrati (x_str, y_str) par."""
        return self.x_edit.edit_text.strip(), self.y_edit.edit_text.strip()

    def is_empty(self):
        x, y = self.get_values()
        return x == "" and y == ""

    def keypress(self, size, key):
        if key == 'tab':
            # Prebaci fokus između x i y
            if self._w.focus_position == 0:
                self._w.focus_position = 2
            else:
                self._w.focus_position = 0
            return None
        if key == 'enter' and self._on_enter:
            self._on_enter()
            return None
        return self._w.keypress(size, key)

class DataTable(urwid.WidgetWrap):
    """
    Scrollabilna tablica točaka s headerom X / Y.
    """
    def __init__(self):
        self.walker = urwid.SimpleFocusListWalker([])
        self.listbox = urwid.ListBox(self.walker)
        # Dodaj prvi prazan red
        self._add_empty_row()
        super().__init__(self.listbox)

    def _add_empty_row(self):
        row = DataRow(on_enter=self._on_row_enter)
        self.walker.append(row)

    def _on_row_enter(self):
        """Na Enter u zadnjem redu dodaj novi prazan red."""
        # Provjeri je li trenutni fokus na zadnjem redu
        focus = self.listbox.focus_position
        if focus == len(self.walker) - 1:
            self._add_empty_row()
            # Premjesti fokus na novi red
            self.listbox.focus_position = len(self.walker) - 1

    def get_points(self):
        """
        Vrati listu (x, y) float parova iz svih nepraznih redova.
        Preskoči redove s nevalidnim vrijednostima.
        """
        points = []
        for row in self.walker:
            x_str, y_str = row.get_values()
            if x_str == "" and y_str == "":
                continue
            try:
                x = float(x_str)
                y = float(y_str)
                points.append((x, y))
            except ValueError:
                continue
        return points

    def clear(self):
        """Očisti sve redove i dodaj jedan prazan."""
        self.walker[:] = []
        self._add_empty_row()

    def get_widget(self):
        return self.listbox
