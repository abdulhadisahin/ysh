"""Exact Excel gravity and pressure conversion without hydraulic formula changes."""
import pytest
from engineering.head_loss.pressure import pressure_equivalent_bar
from engineering.validation import ValidationError


def test_excel_example_full_precision():
    head=17+24.76676
    assert pressure_equivalent_bar(830,head)==830*9.81*head/100000
    assert pressure_equivalent_bar(830,head)==pytest.approx(3.40077550248)


@pytest.mark.parametrize('density',[None,0,-1,float('nan'),float('inf'),True])
def test_density_must_be_positive_and_finite(density):
    with pytest.raises(ValidationError):pressure_equivalent_bar(density,41.76676)


def test_density_and_head_changes_are_not_rounded():
    assert pressure_equivalent_bar(1000,10)==.981
    assert pressure_equivalent_bar(830,20)==830*9.81*20/100000
    assert pressure_equivalent_bar(1024.9,10.123456789)==1024.9*9.81*10.123456789/100000
    assert pressure_equivalent_bar(830,-2)==830*9.81*(-2)/100000


def test_943m_and_830_density_gives_077_bar_on_display():
    from ui.formatting import format_user_number
    result=pressure_equivalent_bar(830,9.43)
    assert result==pytest.approx(.76781889)
    assert format_user_number(result)=="0,77"
