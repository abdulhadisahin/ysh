"""Tests for ENPY calculation composed with head loss."""
from __future__ import annotations
from pytest import approx
from core.local_loss_item import LocalLossItem
from engineering.suction_npsh.calculator import SuctionNPSHCalculator
from engineering.suction_npsh.models import SuctionNPSHInput
def test_reference_enpy_case() -> None:
    """ENPY follows the approved pressure-head and suction-loss equation."""
    value=SuctionNPSHInput(100,20,2e-6,20,.015,[LocalLossItem("X",1,3)],120000,3000,850,2)
    result=SuctionNPSHCalculator().calculate(value)
    assert result.enpym_available_m==approx(result.suction_pressure_head_m-result.vapour_pressure_head_m-2-result.suction_line_loss_m)
