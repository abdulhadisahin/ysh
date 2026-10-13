"""Embedded Matplotlib visualization for authoritative transfer-pump results."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from tkinter import Misc, StringVar
from tkinter import ttk

from core.pump_reference import PumpReference
from engineering.transfer_pump.models import LinearRegressionModel, TransferPumpResult
from ui.formatting import format_user_number
from ui.theme import colors
from ui.theme.spacing import SM
from i18n.translator import Translator


@dataclass(frozen=True, slots=True)
class TransferPumpChartPoint:
    """One render-ready fuel-capacity and pump-capacity coordinate."""

    label: str
    fuel_capacity_m3: float
    pump_capacity_m3h: float


@dataclass(frozen=True, slots=True)
class TransferPumpChartModel:
    """Render-only projection of saved references and authoritative regression data."""

    reference_points: tuple[TransferPumpChartPoint, ...]
    regression_line: tuple[tuple[float, float], ...]
    prediction_point: TransferPumpChartPoint | None
    slope: float | None
    intercept: float | None
    r_squared: float | None

    @classmethod
    def from_authoritative(
        cls,
        references: Sequence[PumpReference],
        regression_model: LinearRegressionModel | None,
        estimate: TransferPumpResult | None = None,
        estimate_capacity_m3: float | None = None,
    ) -> "TransferPumpChartModel":
        """Create display data without calculating or refitting a regression."""
        points = tuple(
            TransferPumpChartPoint(
                reference.ship_name,
                reference.fuel_capacity_m3,
                reference.pump_capacity_m3h,
            )
            for reference in references
        )
        prediction = cls._prediction_from_result(estimate, estimate_capacity_m3)
        if regression_model is None:
            return cls(points, (), prediction, None, None, None)

        line_x = cls._line_x_coordinates(points, prediction)
        line = tuple(
            (x_value, (regression_model.slope * x_value) + regression_model.intercept)
            for x_value in line_x
        )
        return cls(
            points,
            line,
            prediction,
            regression_model.slope,
            regression_model.intercept,
            regression_model.r_squared,
        )

    @staticmethod
    def _prediction_from_result(
        estimate: TransferPumpResult | None,
        estimate_capacity_m3: float | None,
    ) -> TransferPumpChartPoint | None:
        """Return a prediction marker only for one valid authoritative estimate."""
        if (
            estimate is None
            or not estimate.is_successful
            or estimate_capacity_m3 is None
            or estimate.predicted_pump_capacity_m3h is None
        ):
            return None
        return TransferPumpChartPoint(
            "New Ship Prediction",
            estimate_capacity_m3,
            estimate.predicted_pump_capacity_m3h,
        )

    @staticmethod
    def _line_x_coordinates(
        points: Sequence[TransferPumpChartPoint],
        prediction: TransferPumpChartPoint | None,
    ) -> tuple[float, float]:
        """Return a padded visible range for the already-authoritative line."""
        x_values = [point.fuel_capacity_m3 for point in points]
        if prediction is not None:
            x_values.append(prediction.fuel_capacity_m3)
        minimum = min(x_values)
        maximum = max(x_values)
        span = maximum - minimum
        padding = max(span * 0.05, maximum * 0.05, 1.0)
        return minimum - padding, maximum + padding


class TransferPumpChart(ttk.Frame):
    """Render a clean embedded regression chart without a navigation toolbar."""

    def __init__(
        self,
        parent: Misc,
        decimal_places: int = 2,
        translate: Callable[[str], str] | None = None,
    ) -> None:
        """Create one reusable Figure and its TkAgg canvas."""
        super().__init__(parent)
        self._decimal_places = decimal_places
        self._translate = translate or Translator().translate
        self._last_model: TransferPumpChartModel | None = None
        self.columnconfigure(0, weight=1)
        self._figure = Figure(figsize=(7.5, 3.6), dpi=100, facecolor=colors.SURFACE)
        self._axes = self._figure.add_subplot(111)
        self._canvas = FigureCanvasTkAgg(self._figure, master=self)
        self._canvas.get_tk_widget().grid(row=0, column=0, sticky="ew")
        self._summary = StringVar(master=self, value="")
        self._summary_label = ttk.Label(
            self,
            textvariable=self._summary,
            justify="left",
            style="ChartSummary.TLabel",
        )
        self._summary_label.grid(row=1, column=0, sticky="w", pady=(SM // 2, 0))

    def render(self, model: TransferPumpChartModel) -> None:
        """Redraw the existing canvas from prepared authoritative chart data."""
        self._last_model = model
        axes = self._axes
        axes.clear()
        self._configure_axes(axes)
        if model.reference_points:
            axes.scatter(
                [point.fuel_capacity_m3 for point in model.reference_points],
                [point.pump_capacity_m3h for point in model.reference_points],
                color=colors.NAVY,
                marker="o",
                label=self._translate("chart.reference_ships"),
                zorder=3,
            )
        if model.regression_line:
            axes.plot(
                [point[0] for point in model.regression_line],
                [point[1] for point in model.regression_line],
                color=colors.GOLD,
                linewidth=2,
                label=self._translate("chart.linear_regression"),
                zorder=2,
            )
        if model.prediction_point is not None:
            axes.scatter(
                [model.prediction_point.fuel_capacity_m3],
                [model.prediction_point.pump_capacity_m3h],
                color=colors.GOLD_DARK,
                marker="D",
                edgecolors=colors.TEXT_PRIMARY,
                linewidths=0.8,
                label=self._translate("chart.new_ship_prediction"),
                zorder=4,
            )
        if len(model.reference_points) < 2:
            axes.text(
                0.5,
                0.5,
                self._translate("chart.insufficient_reference_ships"),
                transform=axes.transAxes,
                ha="center",
                va="center",
                color=colors.TEXT_SECONDARY,
            )
        if model.reference_points or model.prediction_point is not None:
            axes.legend(loc="upper left", frameon=False)
        self._summary.set(self._summary_text(model))
        self._figure.tight_layout(pad=1.4)
        self._canvas.draw_idle()

    def set_translate(self, translate: Callable[[str], str]) -> None:
        """Update chart labels and legend using the existing figure and canvas."""
        self._translate = translate
        if self._last_model is not None:
            self.render(self._last_model)

    def _configure_axes(self, axes: Axes) -> None:
        """Apply the restrained engineering chart style to an axes instance."""
        axes.set_facecolor(colors.SURFACE_ALT)
        axes.set_xlabel(self._translate("chart.fuel_capacity"))
        axes.set_ylabel(self._translate("chart.pump_capacity"))
        axes.grid(True, color=colors.DIVIDER, linewidth=0.7, alpha=0.8)
        axes.spines["top"].set_visible(False)
        axes.spines["right"].set_visible(False)
        axes.spines["left"].set_color(colors.BORDER)
        axes.spines["bottom"].set_color(colors.BORDER)
        axes.tick_params(axis="both", labelsize=9, colors=colors.TEXT_SECONDARY)
        axes.ticklabel_format(axis="both", style="plain", useOffset=False)

    def _summary_text(self, model: TransferPumpChartModel) -> str:
        """Return concise model information displayed below, never inside, the chart."""
        if model.slope is None or model.intercept is None or model.r_squared is None:
            return self._translate("chart.model_unavailable")
        return self._translate(
            "chart.model_summary",
            slope=format_user_number(model.slope),
            intercept=format_user_number(model.intercept),
            r_squared=format_user_number(model.r_squared),
        )
