"""Display-independent tests for the transfer-pump regression chart model."""

from __future__ import annotations

from pathlib import Path

from pytest import approx

from core.pump_reference import PumpReference
from engineering.transfer_pump.calculator import TransferPumpCalculator
from engineering.transfer_pump.models import TransferPumpInput
from ui.widgets.transfer_pump_chart import TransferPumpChartModel


ROOT = Path(__file__).resolve().parents[1]


def _references() -> list[PumpReference]:
    """Return a deterministic authoritative reference-data set."""
    return [
        PumpReference("Ship A", 100.0, 20.0),
        PumpReference("Ship B", 200.0, 30.0),
        PumpReference("Ship C", 300.0, 40.0),
    ]


def test_chart_model_maps_each_authoritative_reference_to_one_point() -> None:
    """Chart points retain the existing record coordinates without refitting."""
    references = _references()
    result = TransferPumpCalculator().calculate(TransferPumpInput(250.0, references))

    chart = TransferPumpChartModel.from_authoritative(
        references, result.regression_model
    )

    assert [(point.fuel_capacity_m3, point.pump_capacity_m3h) for point in chart.reference_points] == [
        (100.0, 20.0), (200.0, 30.0), (300.0, 40.0),
    ]
    assert chart.prediction_point is None


def test_chart_model_uses_authoritative_regression_parameters_for_line_values() -> None:
    """The chart applies y=m*x+b only from the supplied service model."""
    references = _references()
    result = TransferPumpCalculator().calculate(TransferPumpInput(250.0, references))
    model = result.regression_model
    assert model is not None

    chart = TransferPumpChartModel.from_authoritative(references, model)

    assert chart.slope == model.slope
    assert chart.intercept == model.intercept
    assert chart.r_squared == model.r_squared
    assert all(y_value == approx((model.slope * x_value) + model.intercept) for x_value, y_value in chart.regression_line)


def test_chart_model_adds_and_removes_only_the_authoritative_prediction() -> None:
    """Prediction markers exist only while a successful estimate is available."""
    references = _references()
    result = TransferPumpCalculator().calculate(TransferPumpInput(250.0, references))
    model = result.regression_model
    assert model is not None

    with_prediction = TransferPumpChartModel.from_authoritative(
        references, model, result, 250.0
    )
    cleared = TransferPumpChartModel.from_authoritative(references, model)

    assert with_prediction.prediction_point is not None
    assert with_prediction.prediction_point.fuel_capacity_m3 == 250.0
    assert with_prediction.prediction_point.pump_capacity_m3h == approx(35.0)
    assert cleared.prediction_point is None
    assert cleared.regression_line


def test_chart_model_handles_insufficient_reference_data_without_a_model() -> None:
    """A partial library remains renderable without fabricated regression values."""
    chart = TransferPumpChartModel.from_authoritative(
        [PumpReference("Only Ship", 100.0, 20.0)], None
    )

    assert len(chart.reference_points) == 1
    assert chart.regression_line == ()
    assert chart.slope is None


def test_chart_widget_uses_tkagg_without_external_windows_or_toolbar() -> None:
    """The renderer remains an embedded dashboard component only."""
    source = (ROOT / "ui/widgets/transfer_pump_chart.py").read_text(encoding="utf-8")

    assert "FigureCanvasTkAgg" in source
    assert "NavigationToolbar" not in source
    assert "pyplot" not in source
    assert 'loc="upper left"' in source
    assert 'marker="D"' in source
