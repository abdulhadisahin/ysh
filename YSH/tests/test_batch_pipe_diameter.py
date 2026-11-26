"""Batch rows reuse the current diameter formula, catalog and strict velocity cap."""
import math
import pytest

from services.batch_pipe_diameter import calculate_rows
from services.pipe_design_service import PipeDesignService
from engineering.pipe_design.models import PipeDiameterInput
from engineering.pipe_design.selection import actual_velocity


@pytest.fixture
def service(material_service,pipe_size_service,engineering_constant_service):
    return PipeDesignService(material_service,pipe_size_service,engineering_constant_service)


def test_two_confirmed_cases_share_single_catalog_and_unrounded_results(service,pipe_size_service):
    rows=[('Line A','350','7'),('Line B','240','7')]
    results=calculate_rows(service,rows,'EN_10220')
    assert [r.dn for r in results]==['DN150','DN125']
    for row,result in zip(rows,results):
        single=service.calculate(diameter=PipeDiameterInput(float(row[1]),7),standard_code='EN_10220').diameter
        assert result.diameter_mm==single.diameter_mm
        assert result.dn==single.recommended_dn
        eligible=[p for p in pipe_size_service.get_pipe_sizes_for_standard('EN_10220') if p.nominal_diameter==result.dn]
        representative=max(eligible,key=lambda p:p.inside_diameter_mm)
        assert actual_velocity(float(row[1]),representative.inside_diameter_mm)<=7


@pytest.mark.parametrize('flow,velocity',[('', '7'),('350',''),('bad','7'),('0','7'),('-1','7'),('350','0'),('350','-7'),('nan','7'),('350','inf')])
def test_bad_row_does_not_block_valid_row_and_blank_is_skipped(service,flow,velocity):
    results=calculate_rows(service,[('bad',flow,velocity),('', ' ', ''),('valid','240','7')],'EN_10220')
    assert results[0].issue and results[0].diameter_mm is None
    assert results[1].issue is None and results[1].diameter_mm is None
    assert results[2].issue is None and results[2].dn=='DN125'


def test_decimal_comma_and_missing_dn_keep_theoretical_result(service):
    result=calculate_rows(service,[('Free text / line 4','350,5','7,0')],'EN_10220')[0]
    assert result.diameter_mm==math.sqrt(4*(350.5/3600)/(math.pi*7))*1000
    absent=calculate_rows(service,[('Large flow','999999999','7')],'EN_10220')[0]
    assert absent.diameter_mm>0 and absent.dn is None and absent.issue is None
    assert calculate_rows(service,[('A','240','7')],None)[0].issue.code=='pipe_standard_required'


def test_batch_does_not_fall_back_to_another_catalog(service,pipe_size_service):
    standard=pipe_size_service.create_standard(code='BATCH_EMPTY',display_name='Empty test catalog')
    result=calculate_rows(service,[('A','240','7')],standard.code)[0]
    assert result.diameter_mm>0 and result.dn is None


def test_unrounded_actual_velocity_boundary_is_strict():
    from core.pipe_size import PipeSize
    from engineering.pipe_design.calculator import PipeDesignCalculator
    calculator=PipeDesignCalculator()
    q=350.;limit=7.
    theory=calculator.calculate_diameter(PipeDiameterInput(q,limit))
    rows=[PipeSize('too small',140,1,(theory.diameter_mm-1e-9)),PipeSize('adequate',160,2,156)]
    result=calculator.recommend_dn(theory,rows,flow_rate_m3h=q,maximum_velocity_mps=limit)
    assert result.recommended_dn=='adequate'
    assert actual_velocity(q,result.recommended_inside_diameter_mm)<=limit


def test_batch_localization_keys():
    from i18n.translator import Translator
    keys=('title','name','flow','velocity','diameter','dn','calculate','no_dn','guidance','complete')
    for lang in ('tr','en'):
        for key in keys:
            message=Translator(lang).translate('batch.'+key,count=2,errors=1)
            assert message and not message.startswith('batch.')
    assert Translator('tr').translate('batch.no_dn')=='Uygun DN bulunamadı'
