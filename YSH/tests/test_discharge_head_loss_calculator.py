"""Tests for canonical SI Darcy-Weisbach results."""
from __future__ import annotations
from pytest import approx
from core.local_loss_item import LocalLossItem
from engineering.head_loss.calculator import DischargeHeadLossCalculator
from engineering.head_loss.models import DischargeHeadLossInput
def test_zero_loss_case() -> None:
    """Zero length and K produce no hydraulic loss."""
    result=DischargeHeadLossCalculator().calculate(DischargeHeadLossInput(100,10,1e-6,0,.045,7,[]))
    assert result.total_hydraulic_loss_m==approx(0);assert result.system_head_m==approx(7)

def test_second_excel_coefficient_case() -> None:
    """The confirmed Excel case validates YSH D4/D5 coefficient formulas."""
    d=254;q=532;length=343;factor=.0153374;total_k=113.95
    local=6400*total_k*q**2/d**4
    pipe=6.4e6*factor*length*q**2/d**5
    assert local==approx(49.588697543072)
    assert pipe==approx(9.013231371893)
    assert local+pipe==approx(58.601928914965)
    assert 17+local+pipe==approx(75.601928914965)
