"""115 percent is a fixed user-input flow scenario, not a pump sizing rule."""
import pytest
from engineering.transfer_pump.discharge_scenario import calculate_discharge_115
from engineering.validation import ValidationError
from i18n.translator import Translator


def test_230_m3_at_100_nominal_is_115_and_two_hours():
    result=calculate_discharge_115(230,100)
    assert result.scenario_flow_m3_h==pytest.approx(115)
    assert result.duration_h==pytest.approx(2)


@pytest.mark.parametrize('bad',[None,0,-1,float('nan'),float('inf'),True,'100'])
@pytest.mark.parametrize('field',['volume','nominal'])
def test_invalid_field_is_identified(bad,field):
    args=(bad,100) if field=='volume' else (230,bad)
    with pytest.raises(ValidationError) as error:calculate_discharge_115(*args)
    assert error.value.issue.field_key=='transfer.scenario115.'+field


def test_changed_volume_and_flow_use_current_values():
    assert calculate_discharge_115(460,100).duration_h==pytest.approx(4)
    assert calculate_discharge_115(230,200).duration_h==pytest.approx(1)


def test_scenario_labels_in_both_languages():
    for language in ('tr','en'):
        for key in ('title','notice','volume','nominal','flow','time'):
            assert not Translator(language).translate('transfer.scenario115.'+key).startswith('transfer.')
