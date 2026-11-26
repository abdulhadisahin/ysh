"""Scoped UI/source corrections: no new DN or warning thresholds."""
from dataclasses import replace
from uuid import uuid4

import pytest

from engineering.pipe_design.models import WallThicknessInput, WallThicknessResult
from engineering.pipe_design.wall_standards import (
    auxiliary_cuni_stress, minimum_wall, recommend_wall, verified_nominal_walls,
)
from engineering.validation import ValidationError
from services.pipe_design_service import PipeDesignService
from i18n.translator import Translator


@pytest.mark.parametrize('designation',['CuNiFe10','CuNi10Fe'])
@pytest.mark.parametrize('diameter',[20.,108.,159.,508.])
def test_cuni_allowable_stress_is_direct(material_service,pipe_size_service,engineering_constant_service,designation,diameter):
    material=material_service.create_material(name='Alloy '+str(uuid4()),designation=designation,yield_strength_mpa=200.,roughness_mm=.0015)
    service=PipeDesignService(material_service,pipe_size_service,engineering_constant_service)
    result=service.calculate(wall=WallThicknessInput(diameter,8.,200.,1.8,1.,.5),material_id=material.id,
                             system_family='seawater',design_temperature_c=50.)
    assert result.wall_thickness.allowable_stress_mpa==68.
    assert result.wall_thickness.base_wall_thickness_mm==diameter*8/(20*68+8)
    assert result.trace['allowable_stress_rule']['tl_temperature_verified']
    # Only EEMUA 144 (16 bar) ODs have a recorded nominal wall; others stay unresolved.
    assert result.wall_thickness.selected_standard_wall_thickness_mm=={108.:3.,159.:3.}.get(diameter)
    from engineering.formula.pipe import legacy_pipe_steps
    stress=next(s for s in legacy_pipe_steps(result) if s.step_id=='pipe.stress')
    assert stress.formula_text=='σallow = 68 MPa'
    assert not stress.variables


def test_stress_scope_and_other_materials_unchanged():
    assert auxiliary_cuni_stress('316L','seawater',50) is None
    assert auxiliary_cuni_stress('CuNi10Fe','fuel',50) is None
    assert not auxiliary_cuni_stress('CuNi10Fe','seawater',None)['tl_temperature_verified']
    assert auxiliary_cuni_stress('CuNi10Fe','seawater',75)['value_mpa']==68
    with pytest.raises(ValidationError):auxiliary_cuni_stress('CuNi10Fe','seawater',100)


def test_scoped_cuni_choice_needs_no_invented_library_properties(material_service,pipe_size_service,engineering_constant_service):
    service=PipeDesignService(material_service,pipe_size_service,engineering_constant_service)
    before=tuple(m.to_dict() for m in material_service.get_all_materials())
    from engineering.pipe_design.wall_standards import cuni_wall_material
    reference=cuni_wall_material()
    assert reference not in service.get_all_materials(system_family='fuel')
    assert reference in service.get_all_materials(system_family='seawater')
    result=service.calculate(wall=WallThicknessInput(159,8,None,1.8,1,.5),material_id=reference.id,system_family='seawater')
    assert result.wall_thickness.allowable_stress_mpa==68
    assert result.trace['allowable_stress_rule']['source']=='DPO Standardı'
    assert tuple(m.to_dict() for m in material_service.get_all_materials())==before


def test_minimum_is_not_nominal_and_exact_unrounded_comparison():
    records=verified_nominal_walls('316L',168.3,'seawater')
    assert minimum_wall('CuNi10Fe',159)==(2.5,'8.7')
    assert minimum_wall('CuNi10Fe',168.3)==(None,'8.7')  # Never bridge table gaps.
    for required,expected in [(2.299999999999,2.6),(2.6,3.2),(3.199999999999,3.2),(3.2,4.5)]:
        basis=recommend_wall(required,'316L',168.3,'seawater',records)
        assert basis['nominal_wall_mm']==expected
        assert basis['nominal_wall_mm']>required
        assert basis['nominal_wall_mm']>=basis['minimum_wall_mm']
    assert recommend_wall(2,'CuNi10Fe',168.3,'seawater',records)['nominal_wall_mm'] is None
    assert recommend_wall(2,'316L',168.3,'fuel',records)['nominal_wall_mm'] is None
    assert not verified_nominal_walls('CuNi10Fe',168.3,'seawater')
    assert not verified_nominal_walls('316L',159,'seawater')


def test_legacy_null_wall_round_trip():
    result=WallThicknessResult(100,1,0,1,2)
    assert WallThicknessResult.from_dict(result.to_dict())==result
    invalid=result.to_dict();invalid['allowable_stress_mpa']=None
    with pytest.raises(TypeError):WallThicknessResult.from_dict(invalid)


def test_selection_wording_does_not_rename_sources():
    assert Translator('tr').translate('selection.standard')=='Standart'
    assert Translator('en').translate('selection.standard')=='Standard'
    assert 'Kütüphane' in Translator('tr').translate('result.source_library')


@pytest.mark.parametrize('value,status',[(7,'OK'),(7.1,'WARNING'),(7.7,'WARNING'),(7.71,'OUT_OF_RANGE'),(35,'CRITICAL'),(99,'CRITICAL')])
def test_historical_colour_thresholds_unchanged(value,status):
    from engineering.catalog_seeds import d243_rule
    from engineering.rule_evaluation import rule_status
    assert rule_status(d243_rule(),value)==status


def test_cuni10_nominal_wall_from_eemua_144_for_seawater_only():
    records=verified_nominal_walls('CuNi10Fe',159,'seawater')
    assert [r.thickness_mm for r in records]==[3.0]
    basis=recommend_wall(1.801754,'CuNi10Fe',159,'seawater',records)
    assert basis['nominal_wall_mm']==3.0 and basis['status']=='MATCH'
    assert basis['nominal_standard'].startswith('EEMUA 234')
    assert basis['nominal_note']=='pipe.nominal_secondary_source' and basis['nominal_publication_date']=='2016'
    assert basis['nominal_wall_mm']>=basis['minimum_wall_mm']==2.5
    # A wall at or above the table value gives no recommendation, never a guess.
    assert recommend_wall(3.0,'CuNi10Fe',159,'seawater',records)['nominal_wall_mm'] is None
    assert not verified_nominal_walls('CuNi10Fe',159,'fuel')
    assert not verified_nominal_walls('CuNi10Fe',160,'seawater')
