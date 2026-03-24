# pyplot/ui/layout.py
import urwid


def get_ram_info():
    try:
        with open('/proc/meminfo') as f:
            lines = {l.split(':')[0]: int(l.split()[1])
                     for l in f if ':' in l}
        total = lines['MemTotal'] // 1024
        available = lines['MemAvailable'] // 1024
        used = total - available
        return f"RAM: {used}MB / {total}MB"
    except Exception:
        return "RAM: N/A"


class Layout:
    MODES = [
        ('F1', 'Functions'),
        ('F2', 'Parametric'),
        ('F3', 'Data'),
        ('F4', 'Derivatives'),
        ('F5', 'Integration'),
    ]

    def __init__(self, inputs, marker_selector, function_list,
                 parametric_inputs, parametric_list,
                 data_inputs, data_table,
                 derivatives_inputs, derivatives_list,
                 integration_inputs):
        self.inputs = inputs
        self.marker_selector = marker_selector
        self.function_list = function_list
        self.parametric_inputs = parametric_inputs
        self.parametric_list = parametric_list
        self.data_inputs = data_inputs
        self.data_table = data_table
        self.derivatives_inputs = derivatives_inputs
        self.derivatives_list = derivatives_list
        self.integration_inputs = integration_inputs
        self.current_mode = 0

        self.plot_text = urwid.Text("", align='left', wrap='clip')
        self.plot_walker = urwid.SimpleFocusListWalker([self.plot_text])
        self.plot_listbox = urwid.ListBox(self.plot_walker)
        self.plot_box = urwid.LineBox(
            self.plot_listbox,
            title="Plot",
            title_align='left'
        )

        self.plot_button = urwid.Button("Plot")
        self.refresh_button = urwid.Button("Refresh plot")
        self.clear_button = urwid.Button("Clear data")
        self.clear_parametric_button = urwid.Button("Clear curves")
        self.fit_button = urwid.Button("Fit")
        self.add_derivative_button = urwid.Button("+ Derivative")
        self.clear_derivatives_button = urwid.Button("Clear")
        self.integrate_button = urwid.Button("Integrate")
        self.exit_button = urwid.Button("Exit")

        self.fit_results_text = urwid.Text("", align='left')
        self.integration_result_text = urwid.Text("", align='left')

        self.panels = {
            0: self._build_functions_panel(),
            1: self._build_parametric_panel(),
            2: self._build_data_panel(),
            3: self._build_derivatives_panel(),
            4: self._build_integration_panel(),
        }

        self.left_placeholder = urwid.WidgetPlaceholder(self.panels[0])

        self.columns = urwid.Columns(
            [
                ("fixed", 40, self.left_placeholder),
                self.plot_box
            ],
            dividechars=1
        )

        title = urwid.Text("pyplot", align='center')
        self.menu_bar = self._build_menu_bar()
        header = urwid.Pile([title, self.menu_bar])

        self.status_text = urwid.Text(get_ram_info(), align='left')
        footer = urwid.AttrMap(self.status_text, None)

        self.frame = urwid.Frame(
            body=self.columns,
            header=header,
            footer=footer
        )

        self._plot_width = 76
        self._plot_height = 30

        # Detektiraj stvarnu veličinu terminala
        try:
            import plotext as plt
            cols, rows = plt.terminal_size()
            if cols > 50 and rows > 10:
                self._plot_width = max(40, cols - 44)
                self._plot_height = max(10, rows - 8)
        except Exception:
            pass

    def _build_functions_panel(self):
        items = []
        items.extend(self.inputs.build_widget())
        items.append(urwid.Divider())
        items.append(self.marker_selector)
        items.append(urwid.Divider())
        items.append(urwid.Columns([self.plot_button, self.refresh_button]))
        items.append(urwid.Divider())
        items.append(urwid.Text(("bold", "Functions:")))
        items.append(urwid.BoxAdapter(urwid.LineBox(self.function_list.get_widget()), 12))
        items.append(urwid.Divider())
        items.append(self.exit_button)
        return urwid.ListBox(urwid.SimpleFocusListWalker(items))

    def _build_parametric_panel(self):
        items = []
        items.extend(self.parametric_inputs.build_widget())
        items.append(urwid.Divider())
        items.append(self.marker_selector)
        items.append(urwid.Divider())
        items.append(urwid.Columns([self.plot_button, self.refresh_button]))
        items.append(urwid.Divider())
        items.append(urwid.Text(("bold", "Curves:")))
        items.append(urwid.BoxAdapter(urwid.LineBox(self.parametric_list.get_widget()), 12))
        items.append(urwid.Divider())
        items.append(self.clear_parametric_button)
        items.append(urwid.Divider())
        items.append(self.exit_button)
        return urwid.ListBox(urwid.SimpleFocusListWalker(items))

    def _build_data_panel(self):
        header = urwid.Columns([
            ('weight', 1, urwid.Text("X", align='center')),
            ('fixed', 1, urwid.Text(" ")),
            ('weight', 1, urwid.Text("Y", align='center')),
        ])
        items = []
        items.extend(self.data_inputs.build_widget())
        items.append(urwid.Divider())
        items.append(self.marker_selector)
        items.append(urwid.Divider())
        items.append(urwid.Columns([self.plot_button, self.refresh_button]))
        items.append(urwid.Divider())
        items.append(urwid.Text(("bold", "Data points:")))
        items.append(header)
        items.append(urwid.Divider('-'))
        items.append(urwid.BoxAdapter(self.data_table.get_widget(), 8))
        items.append(urwid.Divider())
        items.append(urwid.Columns([self.fit_button, self.clear_button]))
        items.append(urwid.Divider())
        items.append(urwid.Text(("bold", "Fit results:")))
        items.append(self.fit_results_text)
        items.append(urwid.Divider())
        items.append(self.exit_button)
        return urwid.ListBox(urwid.SimpleFocusListWalker(items))

    def _build_derivatives_panel(self):
        items = []
        items.extend(self.derivatives_inputs.build_widget())
        items.append(urwid.Divider())
        items.append(self.marker_selector)
        items.append(urwid.Divider())
        items.append(urwid.Columns([self.plot_button, self.refresh_button]))
        items.append(urwid.Divider())
        items.append(self.add_derivative_button)
        items.append(urwid.Divider())
        items.append(urwid.Text(("bold", "Derivatives:")))
        items.append(urwid.BoxAdapter(urwid.LineBox(self.derivatives_list.get_widget()), 10))
        items.append(urwid.Divider())
        items.append(self.clear_derivatives_button)
        items.append(urwid.Divider())
        items.append(self.exit_button)
        return urwid.ListBox(urwid.SimpleFocusListWalker(items))

    def _build_integration_panel(self):
        items = []
        items.extend(self.integration_inputs.build_widget())
        items.append(urwid.Divider())
        items.append(urwid.Columns([self.plot_button, self.refresh_button]))
        items.append(urwid.Divider())
        items.append(self.integrate_button)
        items.append(urwid.Divider())
        items.append(urwid.Text(("bold", "Result:")))
        items.append(self.integration_result_text)
        items.append(urwid.Divider())
        items.append(self.exit_button)
        return urwid.ListBox(urwid.SimpleFocusListWalker(items))

    def _build_menu_bar(self):
        items = []
        for i, (key, name) in enumerate(self.MODES):
            label = f" {key}:{name} "
            if i == self.current_mode:
                btn = urwid.Text(('menu_active', label), align='left')
            else:
                btn = urwid.Text(('menu_inactive', label), align='left')
            items.append(btn)
        return urwid.Columns(items)

    def _refresh_menu_bar(self):
        items = []
        for i, (key, name) in enumerate(self.MODES):
            label = f" {key}:{name} "
            if i == self.current_mode:
                btn = urwid.Text(('menu_active', label), align='left')
            else:
                btn = urwid.Text(('menu_inactive', label), align='left')
            items.append(btn)
        self.menu_bar.contents = [(w, self.menu_bar.options()) for w in items]

    def set_mode(self, index):
        self.current_mode = index % len(self.MODES)
        self._refresh_menu_bar()
        if self.current_mode in self.panels:
            self.left_placeholder.original_widget = self.panels[self.current_mode]

    def get_current_mode(self):
        return self.current_mode

    def get_plot_size(self):
        return self._plot_width, self._plot_height

    def update_plot_size(self, total_cols, total_rows):
        w = max(20, total_cols - 43)
        h = max(5, total_rows - 2)
        self._plot_width = w
        self._plot_height = h

    def update_plot(self, text):
        lines = text.split('\n')
        text_widgets = [urwid.Text(line, wrap='clip') for line in lines]
        if not text_widgets:
            text_widgets = [urwid.Text("No plot to display", wrap='clip')]
        self.plot_walker[:] = text_widgets
        self.plot_listbox._invalidate()

    def update_fit_results(self, text):
        self.fit_results_text.set_text(text)

    def update_integration_result(self, text):
        self.integration_result_text.set_text(text)

    def update_status(self, extra=""):
        ram = get_ram_info()
        text = f"{ram}  {extra}".strip()
        self.status_text.set_text(text)

    def update_ram(self):
        self.update_status()

    def get_widget(self):
        return self.frame
