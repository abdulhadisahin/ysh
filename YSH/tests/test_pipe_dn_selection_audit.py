"""Characterize today's DN selection; these tests do not approve a new sizing rule.

The factory rows match the audited local catalog for DN100/125/150. Their
geometrical ID is checked, without upgrading missing edition/source metadata.
"""
import pytest
from engineering.pipe_design.calculator import PipeDesignCalculator
from engineering.pipe_design.models import PipeDiameterInput
from engineering.pipe_design.selection import actual_velocity, select_pipe_candidate
from engineering.pipe_design.v2_models import PipeCandidate
from engineering.catalog_seeds import d243_rule
from engineering.rule_evaluation import evaluate_rule, applicable_rules
from services.pipe_design_service import PipeDesignService


@pytest.mark.parametrize('flow,diameter,dn,od,wall,inside,rejected',[
    (350,132.98076013381092,'DN150',168.3,4.5,159.3,'DN125'),
    (240,110.11853114821159,'DN125',139.7,4.,131.7,'DN100'),
])
def test_current_page_service_recommendation_is_actual_id_ceiling(
        library_database,material_service,pipe_size_service,engineering_constant_service,
        flow,diameter,dn,od,wall,inside,rejected):
    service=PipeDesignService(material_service,pipe_size_service,engineering_constant_service)
    with library_database.connection() as c:before=tuple(c.iterdump())
    result=service.calculate(diameter=PipeDiameterInput(flow,7),standard_code='EN_10220')
    assert not result.errors
    output=result.diameter
    assert output.diameter_mm==pytest.approx(diameter,abs=1e-9)
    assert (output.recommended_dn,output.recommended_outside_diameter_mm,output.recommended_wall_thickness_mm)==(dn,od,wall)
    assert output.recommended_inside_diameter_mm==pytest.approx(inside)
    assert actual_velocity(flow,inside)<=7
    rows=pipe_size_service.get_pipe_sizes_for_standard('EN_10220')
    rejected_rows=[r for r in rows if r.nominal_diameter==rejected]
    assert rejected_rows and all(r.inside_diameter_mm<diameter for r in rejected_rows)
    assert all(actual_velocity(flow,r.inside_diameter_mm)>7 for r in rejected_rows)
    assert result.trace['pipe_standard_code']=='EN_10220'
    with library_database.connection() as c:assert tuple(c.iterdump())==before


@pytest.mark.parametrize('flow,dn,wall,inside',[(350,'DN150',11.,146.3),(240,'DN125',10.,119.7)])
def test_separate_v2_candidate_policy_is_not_the_visible_diameter_representative(
        pipe_size_service,flow,dn,wall,inside):
    standard=pipe_size_service.get_standard_by_code('EN_10220')
    rows=pipe_size_service.get_pipe_sizes_for_standard(standard.id)
    candidates=tuple(PipeCandidate(id=r.id,standard_id=r.standard_id,standard_code=standard.code,
        nominal_diameter=r.nominal_diameter,outside_diameter_mm=r.outside_diameter_mm,
        wall_thickness_mm=r.wall_thickness_mm,inside_diameter_mm=r.inside_diameter_mm) for r in rows)
    diameter=PipeDesignCalculator().calculate_diameter(PipeDiameterInput(flow,7)).diameter_mm
    selected=select_pipe_candidate(diameter,candidates,standard.id,standard_code='EN_10220')
    assert selected.nominal_diameter==dn and selected.wall_thickness_mm==wall
    assert selected.actual_internal_diameter_mm==pytest.approx(inside)
    assert actual_velocity(flow,selected.actual_internal_diameter_mm)<=7


@pytest.mark.parametrize('dn,od,thicknesses',[
    ('DN100',114.3,(3.6,4.,4.5,5.,5.6,6.3,7.1,8.,8.8)),
    ('DN125',139.7,(4.,4.5,5.,5.6,6.3,7.1,8.,8.8,10.)),
    ('DN150',168.3,(4.5,5.,5.6,6.3,7.1,8.,8.8,10.,11.)),
])
def test_audited_rows_are_geometrically_consistent_not_nominal_bore_values(pipe_size_service,dn,od,thicknesses):
    rows=sorted((r for r in pipe_size_service.get_pipe_sizes_for_standard('EN_10220') if r.nominal_diameter==dn),key=lambda r:r.wall_thickness_mm)
    assert tuple(r.wall_thickness_mm for r in rows)==thicknesses
    assert all(r.outside_diameter_mm==od for r in rows)
    assert all(r.inside_diameter_mm==pytest.approx(od-2*r.wall_thickness_mm) for r in rows)


@pytest.mark.parametrize('flow,inside',[(350,131.7),(240,107.1)])
def test_requested_smaller_dn_exceeds_internal_warning_criterion_not_tl_limit(flow,inside):
    rule=d243_rule()
    assert rule.rule_nature=='D243_CRITERION' and rule.source_authority=='D243'
    assert rule.recommended_max==7 and rule.hard_max is None
    assert not evaluate_rule(rule,7)
    findings=evaluate_rule(rule,actual_velocity(flow,inside))
    assert findings and findings[0].code=='d243.pipe.velocity_max'
    assert findings[0].visual_status=='WARNING'
    assert not applicable_rules((rule,),family='seawater',profile_id=None,fluid_group='SEA_WATER',line_type='')
