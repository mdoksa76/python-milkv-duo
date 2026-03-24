# pyplot/main.py

import urwid
from pyplot.ui.inputs import InputFields
from pyplot.ui.parametric_inputs import ParametricInputFields
from pyplot.ui.data_inputs import DataInputFields
from pyplot.ui.derivatives_inputs import DerivativesInputFields
from pyplot.ui.integration_inputs import IntegrationInputFields
from pyplot.ui.marker_selector import MarkerSelector
from pyplot.ui.function_list import FunctionList
from pyplot.ui.parametric_list import ParametricList
from pyplot.ui.data_table import DataTable
from pyplot.ui.derivatives_list import DerivativesList
from pyplot.ui.layout import Layout
from pyplot.core.state import state
from pyplot.core.parser import parse_expression
from pyplot.core.plotter import generate_plot
from pyplot.core.parametric_plotter import generate_parametric_plot
from pyplot.core.data_plotter import generate_data_plot
from pyplot.core.derivatives_plotter import generate_derivatives_plot
from pyplot.core.integration_plotter import generate_integration_plot
from pyplot.core.fit import run_fits, format_results
from pyplot.core.integration import integrate, format_result
from pyplot.utils.ranges import parse_range, parse_t_range
import sympy as sp

PALETTE = [
    ('menu_active',   'black',      'light gray'),
    ('menu_inactive', 'light gray', 'black'),
]

class PyPlotApp:
    def __init__(self):
        self.inputs = InputFields()
        self.parametric_inputs = ParametricInputFields()
        self.data_inputs = DataInputFields()
        self.derivatives_inputs = DerivativesInputFields()
        self.integration_inputs = IntegrationInputFields()
        self.marker_selector = MarkerSelector()
        self.function_list = FunctionList()
        self.parametric_list = ParametricList()
        self.data_table = DataTable()
        self.derivatives_list = DerivativesList()

        self._deriv_order = 0
        self._deriv_base_expr = None
        self._integ_sympy_expr = None  # cached parsed expression za integraciju

        self.layout = Layout(
            self.inputs,
            self.marker_selector,
            self.function_list,
            self.parametric_inputs,
            self.parametric_list,
            self.data_inputs,
            self.data_table,
            self.derivatives_inputs,
            self.derivatives_list,
            self.integration_inputs,
        )

        urwid.connect_signal(self.layout.plot_button, "click", self.on_plot_clicked)
        urwid.connect_signal(self.layout.refresh_button, "click", self.on_refresh_clicked)
        urwid.connect_signal(self.layout.clear_button, "click", self.on_clear_clicked)
        urwid.connect_signal(self.layout.clear_parametric_button, "click", self.on_clear_parametric_clicked)
        urwid.connect_signal(self.layout.fit_button, "click", self.on_fit_clicked)
        urwid.connect_signal(self.layout.add_derivative_button, "click", self.on_add_derivative_clicked)
        urwid.connect_signal(self.layout.clear_derivatives_button, "click", self.on_clear_derivatives_clicked)
        urwid.connect_signal(self.layout.integrate_button, "click", self.on_integrate_clicked)
        urwid.connect_signal(self.layout.exit_button, "click", self.on_exit_clicked)

        self.loop = None

    # -----------------------------
    # Event handlers
    # -----------------------------
    def on_plot_clicked(self, button):
        mode = self.layout.get_current_mode()
        if mode == 0:
            self._plot_function()
        elif mode == 1:
            self._plot_parametric()
        elif mode == 2:
            self.refresh_plot()
        elif mode == 3:
            self._plot_derivatives_init()
        elif mode == 4:
            self._plot_integration()

    def _plot_function(self):
        expr_text = self.inputs.get_function()
        if not expr_text:
            self.layout.update_plot("Please enter a function.")
            return
        sympy_expr, err = parse_expression(expr_text)
        if err:
            self.layout.update_plot(err)
            return
        marker = state.next_marker()
        self.function_list.add_function(expr_text, sympy_expr, marker)
        self.inputs.function_edit.set_edit_text("")
        self.refresh_plot()

    def _plot_parametric(self):
        xt_text = self.parametric_inputs.get_xt()
        yt_text = self.parametric_inputs.get_yt()
        if not xt_text or not yt_text:
            self.layout.update_plot("Please enter both x(t) and y(t).")
            return
        xt_sympy, err = parse_expression(xt_text, var='t')
        if err:
            self.layout.update_plot(f"x(t): {err}")
            return
        yt_sympy, err = parse_expression(yt_text, var='t')
        if err:
            self.layout.update_plot(f"y(t): {err}")
            return
        marker = state.next_marker()
        self.parametric_list.add_curve(xt_text, yt_text, xt_sympy, yt_sympy, marker)
        self.parametric_inputs.clear()
        self.refresh_plot()

    def _plot_derivatives_init(self):
        expr_text = self.derivatives_inputs.get_function()
        if not expr_text:
            self.layout.update_plot("Please enter a function.")
            return
        sympy_expr, err = parse_expression(expr_text)
        if err:
            self.layout.update_plot(err)
            return
        self.derivatives_list.clear()
        self._deriv_order = 0
        self._deriv_base_expr = sympy_expr
        marker = state.next_marker()
        self.derivatives_list.add_entry(expr_text, sympy_expr, marker, order=0)
        self.refresh_plot()

    def _plot_integration(self):
        """Parsiraj funkciju i osvježi plot."""
        expr_text = self.integration_inputs.get_function()
        if not expr_text:
            self.layout.update_plot("Please enter a function.")
            return
        sympy_expr, err = parse_expression(expr_text)
        if err:
            self.layout.update_plot(err)
            return
        self._integ_sympy_expr = sympy_expr
        self.refresh_plot()

    def on_integrate_clicked(self, button):
        """Pokreni integraciju i prikaži rezultat."""
        if self._integ_sympy_expr is None:
            # Pokušaj parsirati ako nije još
            expr_text = self.integration_inputs.get_function()
            if not expr_text:
                self.layout.update_integration_result("Please enter a function first.")
                return
            sympy_expr, err = parse_expression(expr_text)
            if err:
                self.layout.update_integration_result(err)
                return
            self._integ_sympy_expr = sympy_expr

        # Parsiraj a i b
        try:
            a = float(self.integration_inputs.get_a())
        except ValueError:
            self.layout.update_integration_result("Invalid value for a.")
            return
        try:
            b = float(self.integration_inputs.get_b())
        except ValueError:
            self.layout.update_integration_result("Invalid value for b.")
            return

        if a >= b:
            self.layout.update_integration_result("a must be less than b.")
            return

        method_key = self.integration_inputs.get_method_key()
        result, error_est, err = integrate(self._integ_sympy_expr, a, b, method_key)

        if err:
            self.layout.update_integration_result(f"Error: {err}")
            return

        text = format_result(result, error_est, method_key)
        self.layout.update_integration_result(text)

        self.layout.update_ram()
        if self.loop is not None:
            self.loop.draw_screen()

    def on_add_derivative_clicked(self, button):
        if self._deriv_base_expr is None:
            self.layout.update_plot("Please plot a function first.")
            return
        x = sp.Symbol('x')
        self._deriv_order += 1
        try:
            deriv_expr = sp.diff(self._deriv_base_expr, x, self._deriv_order)
        except Exception as e:
            self.layout.update_plot(f"Derivative error: {e}")
            return
        deriv_text = str(deriv_expr)
        marker = state.next_marker()
        self.derivatives_list.add_entry(deriv_text, deriv_expr, marker, order=self._deriv_order)
        self.refresh_plot()

    def on_fit_clicked(self, button):
        points = self.data_table.get_points()
        if not points:
            self.layout.update_fit_results("No data points.")
            return
        selected = self.data_inputs.get_selected_fits()
        if not selected:
            self.layout.update_fit_results("No fits selected.")
            return
        results = run_fits(points, selected)
        text = format_results(results)
        self.layout.update_fit_results(text)
        plot_width, plot_height = self.layout.get_plot_size()
        self._refresh_data_with_fits(plot_width, plot_height, results)
        self.layout.update_ram()
        if self.loop is not None:
            self.loop.draw_screen()

    def on_refresh_clicked(self, button):
        self.refresh_plot()

    def on_clear_clicked(self, button):
        self.data_table.clear()
        self.layout.update_plot("")
        self.layout.update_fit_results("")

    def on_clear_parametric_clicked(self, button):
        self.parametric_list.clear()
        self.layout.update_plot("")

    def on_clear_derivatives_clicked(self, button):
        self.derivatives_list.clear()
        self._deriv_order = 0
        self._deriv_base_expr = None
        self.layout.update_plot("")

    def on_exit_clicked(self, button):
        raise urwid.ExitMainLoop()

    # -----------------------------
    # Plotting logic
    # -----------------------------
    def refresh_plot(self):
        mode = self.layout.get_current_mode()
        plot_width, plot_height = self.layout.get_plot_size()

        if mode == 0:
            self._refresh_functions(plot_width, plot_height)
        elif mode == 1:
            self._refresh_parametric(plot_width, plot_height)
        elif mode == 2:
            self._refresh_data(plot_width, plot_height)
        elif mode == 3:
            self._refresh_derivatives(plot_width, plot_height)
        elif mode == 4:
            self._refresh_integration(plot_width, plot_height)

        self.layout.update_ram()
        if self.loop is not None:
            self.loop.draw_screen()

    def _refresh_functions(self, plot_width, plot_height):
        x_min, x_max, y_min, y_max, err = parse_range(
            self.inputs.get_x_min(), self.inputs.get_x_max(),
            self.inputs.get_y_min(), self.inputs.get_y_max()
        )
        if err:
            self.layout.update_plot(err)
            return
        plot_text = generate_plot(
            functions=state.functions, marker=state.marker,
            x_min=x_min, x_max=x_max, y_min=y_min, y_max=y_max,
            plot_title=self.inputs.get_title(),
            x_label=self.inputs.get_x_label(),
            y_label=self.inputs.get_y_label(),
            plot_width=plot_width, plot_height=plot_height,
        )
        self.layout.update_plot(plot_text)

    def _refresh_parametric(self, plot_width, plot_height):
        t_min, t_max, t_step, err = parse_t_range(
            self.parametric_inputs.get_t_min(),
            self.parametric_inputs.get_t_max(),
            self.parametric_inputs.get_t_step()
        )
        if err:
            self.layout.update_plot(err)
            return
        x_min, x_max, y_min, y_max, err = parse_range(
            self.parametric_inputs.get_x_min(), self.parametric_inputs.get_x_max(),
            self.parametric_inputs.get_y_min(), self.parametric_inputs.get_y_max()
        )
        if err:
            self.layout.update_plot(err)
            return
        plot_text = generate_parametric_plot(
            curves=state.parametric, t_min=t_min, t_max=t_max, t_step=t_step,
            plot_title=self.parametric_inputs.get_title(),
            x_label=self.parametric_inputs.get_x_label(),
            y_label=self.parametric_inputs.get_y_label(),
            x_min=x_min, x_max=x_max, y_min=y_min, y_max=y_max,
            plot_width=plot_width, plot_height=plot_height,
        )
        self.layout.update_plot(plot_text)

    def _refresh_data(self, plot_width, plot_height):
        points = self.data_table.get_points()
        if not points:
            self.layout.update_plot("No data points to plot.")
            return
        x_min, x_max, y_min, y_max, err = parse_range(
            self.data_inputs.get_x_min(), self.data_inputs.get_x_max(),
            self.data_inputs.get_y_min(), self.data_inputs.get_y_max()
        )
        if err:
            self.layout.update_plot(err)
            return
        plot_text = generate_data_plot(
            points=points, marker=state.marker,
            plot_title=self.data_inputs.get_title(),
            x_label=self.data_inputs.get_x_label(),
            y_label=self.data_inputs.get_y_label(),
            x_min=x_min, x_max=x_max, y_min=y_min, y_max=y_max,
            plot_width=plot_width, plot_height=plot_height,
        )
        self.layout.update_plot(plot_text)

    def _refresh_data_with_fits(self, plot_width, plot_height, fit_results):
        points = self.data_table.get_points()
        if not points:
            return
        x_min, x_max, y_min, y_max, err = parse_range(
            self.data_inputs.get_x_min(), self.data_inputs.get_x_max(),
            self.data_inputs.get_y_min(), self.data_inputs.get_y_max()
        )
        if err:
            return
        fit_curves = {}
        xs_fit = [x_min + (x_max - x_min) * i / plot_width for i in range(plot_width + 1)]
        for key, result in fit_results.items():
            if result is None:
                continue
            fn = result['fn']
            ys = []
            for x in xs_fit:
                try:
                    y = fn(x)
                    ys.append(y if y is not None and abs(y) < 1e10 else None)
                except Exception:
                    ys.append(None)
            fit_curves[key] = (xs_fit, ys)
        plot_text = generate_data_plot(
            points=points, marker=state.marker,
            plot_title=self.data_inputs.get_title(),
            x_label=self.data_inputs.get_x_label(),
            y_label=self.data_inputs.get_y_label(),
            x_min=x_min, x_max=x_max, y_min=y_min, y_max=y_max,
            plot_width=plot_width, plot_height=plot_height,
            fit_curves=fit_curves,
        )
        self.layout.update_plot(plot_text)

    def _refresh_derivatives(self, plot_width, plot_height):
        if not state.derivatives:
            self.layout.update_plot("No functions to plot.")
            return
        x_min, x_max, y_min, y_max, err = parse_range(
            self.derivatives_inputs.get_x_min(), self.derivatives_inputs.get_x_max(),
            self.derivatives_inputs.get_y_min(), self.derivatives_inputs.get_y_max()
        )
        if err:
            self.layout.update_plot(err)
            return
        plot_text = generate_derivatives_plot(
            entries=state.derivatives,
            x_min=x_min, x_max=x_max, y_min=y_min, y_max=y_max,
            plot_title=self.derivatives_inputs.get_title(),
            x_label=self.derivatives_inputs.get_x_label(),
            y_label=self.derivatives_inputs.get_y_label(),
            plot_width=plot_width, plot_height=plot_height,
        )
        self.layout.update_plot(plot_text)

    def _refresh_integration(self, plot_width, plot_height):
        if self._integ_sympy_expr is None:
            self.layout.update_plot("Please enter and plot a function first.")
            return

        x_min, x_max, y_min, y_max, err = parse_range(
            self.integration_inputs.get_x_min(), self.integration_inputs.get_x_max(),
            self.integration_inputs.get_y_min(), self.integration_inputs.get_y_max()
        )
        if err:
            self.layout.update_plot(err)
            return

        try:
            a = float(self.integration_inputs.get_a())
            b = float(self.integration_inputs.get_b())
        except ValueError:
            a, b = x_min, x_max

        plot_text = generate_integration_plot(
            sympy_expr=self._integ_sympy_expr,
            x_min=x_min, x_max=x_max, y_min=y_min, y_max=y_max,
            a=a, b=b,
            plot_title=self.integration_inputs.get_title(),
            x_label=self.integration_inputs.get_x_label(),
            y_label=self.integration_inputs.get_y_label(),
            plot_width=plot_width, plot_height=plot_height,
        )
        self.layout.update_plot(plot_text)

    # -----------------------------
    # Run application
    # -----------------------------
    def run(self):
        import sys, termios
        try:
            self._term_settings = termios.tcgetattr(sys.stdin.fileno())
        except Exception:
            self._term_settings = None

        self.loop = urwid.MainLoop(
            self.layout.get_widget(),
            palette=PALETTE,
            unhandled_input=self.handle_input
        )
        try:
            self.loop.run()
        finally:
            try:
                self.loop.screen.stop()
            except Exception:
                pass
            try:
                if self._term_settings:
                    termios.tcsetattr(sys.stdin.fileno(), termios.TCSAFLUSH, self._term_settings)
            except Exception:
                pass
            sys.stdout.write('\x1b[?25h\x1b[?1049l')
            sys.stdout.flush()

    def handle_input(self, key):
        if key in ('q', 'Q', 'esc'):
            raise urwid.ExitMainLoop()
        elif key == 'f1':
            self.layout.set_mode(0)
        elif key == 'f2':
            self.layout.set_mode(1)
        elif key == 'f3':
            self.layout.set_mode(2)
        elif key == 'f4':
            self.layout.set_mode(3)
        elif key == 'f5':
            self.layout.set_mode(4)


if __name__ == "__main__":
    PyPlotApp().run()
