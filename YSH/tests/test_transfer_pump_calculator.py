"""Reference regression tests for transfer-pump estimates."""
from __future__ import annotations
from pytest import approx
from core.pump_reference import PumpReference
from engineering.transfer_pump.calculator import TransferPumpCalculator
from engineering.transfer_pump.models import TransferPumpInput
def test_reference_linear_dataset() -> None:
    """The specified three reference ships yield the specified trendline."""
    records=[PumpReference("A",100,20),PumpReference("B",200,30),PumpReference("C",300,40)]
    result=TransferPumpCalculator().calculate(TransferPumpInput(250,records))
    assert result.regression_model.slope==approx(.1);assert result.regression_model.intercept==approx(10);assert result.regression_model.r_squared==approx(1);assert result.predicted_pump_capacity_m3h==approx(35);assert result.estimated_emptying_time_hours==approx(250/35);assert result.estimated_emptying_time_minutes==approx((250/35)*60)
