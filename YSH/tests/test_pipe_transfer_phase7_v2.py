"""Phase 7 controlled pipe transfer; dimensions and rules below are test fixtures."""
from dataclasses import FrozenInstanceError, asdict, replace
from datetime import date, datetime, timezone
import json
from uuid import UUID, uuid4

import pytest

from engineering.pipe_design.rules import DesignStatus, RuleValue
from engineering.pipe_design.v2_models import PipeCandidate, PipeSelection, PipeProvenance, WallBreakdown
from engineering.pipe_design.transfer import (
    PipeInputMode, PipeLinkStatus, PipeValues, PipeSelectionSnapshot,
    PipeInputState, PipeTransferProjectState, revise_selection, is_stale,
)
from engineering.pipe_design.transfer_serialization import (
    selection_to_dict, selection_from_dict, transfer_to_dict, transfer_from_dict,
    transfer_json, transfer_from_workspace,
)
from engineering.provenance import EngineeringValue, SourceReference, SourceType, VerificationStatus, OverridePolicy
from services.discharge_head_loss_service import DischargeHeadLossService
from services.suction_npsh_service import SuctionNPSHService
from services.project_persistence_service import ProjectPersistenceService
from repositories.project_state_repository import ProjectStateRepository

STAMP = datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc)
SOURCE = SourceReference(source_type=SourceType.PIPE_STANDARD, document="TEST ONLY",
    effective_date=date(2020, 1, 1), verification_date=date(2026, 1, 1),
    verification_status=VerificationStatus.UNVERIFIED, notes="Synthetic fixture")


def selection(**changes):
    pipe = PipeCandidate(id=UUID(int=2), standard_id=UUID(int=1),
        outside_diameter_mm=110, wall_thickness_mm=4, inside_diameter_mm=101,
        nominal_diameter="DN-test", nps="test-nps", schedule="test-sch", dimension_source=SOURCE)
    return PipeSelection(**(dict(status=DesignStatus.RULE_NOT_CONFIGURED,
        theoretical_internal_diameter_mm=75, design_velocity_m_s=2,
        flow_rate_m3_h=20, selected_standard_id=pipe.standard_id,
        selected_standard_code="TEST", candidate=pipe, selected_pipe=pipe,
        selection_id=UUID(int=100), material_id=UUID(int=10), fluid_id=UUID(int=11),
        system_id=UUID(int=12), circuit_id=UUID(int=13)) | changes))


def linked(source=None):
    return PipeInputState().link_to(source or selection(), applied_at=STAMP)


def changed(source=None):
    source = source or selection()
    return revise_selection(source, replace(source, flow_rate_m3_h=30,
        selected_pipe=replace(source.selected_pipe, inside_diameter_mm=99)))


def test_manual_independent_and_link_requires_explicit_snapshot():
    manual = PipeInputState(manual_values=PipeValues(flow_rate_m3_h=20, actual_internal_diameter_mm=101))
    assert manual.mode is PipeInputMode.MANUAL
    assert manual.observe(changed()) is manual
    assert manual.used_values.hydraulic_values() == (101, 20)
    with pytest.raises(ValueError):
        PipeInputState(mode=PipeInputMode.LINKED)
    with pytest.raises(TypeError):
        manual.link_to()


def test_snapshot_uses_actual_stored_id_and_metadata():
    source = selection()
    state = linked(source)
    assert state.snapshot.source_selection_id == source.selection_id
    assert state.snapshot.source_revision == 1
    assert state.snapshot.applied_at == STAMP
    values = state.used_values
    assert values.actual_internal_diameter_mm == 101  # Neither 75 theoretical nor 102 OD-2t
    assert values.flow_rate_m3_h == 20
    for name in ('material_id', 'fluid_id', 'system_id', 'circuit_id'):
        assert getattr(values, name) == getattr(source, name)
    assert (values.standard_code, values.nominal_diameter, values.nps, values.schedule) == ('TEST','DN-test','test-nps','test-sch')
    assert (values.outside_diameter_mm, values.wall_thickness_mm) == (110, 4)
    assert values.dimension_source == SOURCE
    assert state.snapshot.upstream_status is DesignStatus.RULE_NOT_CONFIGURED
    assert 'theoretical_internal_diameter_mm' not in asdict(values)
    assert 'wall' not in asdict(values)


@pytest.mark.parametrize('target', ['selection','snapshot','values'])
def test_frozen_snapshot_cannot_mutate(target):
    state = linked()
    obj, field = {'selection': (selection(),'flow_rate_m3_h'),
                  'snapshot': (state.snapshot,'source_revision'),
                  'values': (state.used_values,'flow_rate_m3_h')}[target]
    with pytest.raises(FrozenInstanceError):
        setattr(obj, field, 999)


@pytest.mark.parametrize('name,new', [
    ('flow_rate_m3_h', 25), ('selected_standard_id', UUID(int=9)),
    ('selected_standard_code','NEW'), ('material_id',UUID(int=21)),
    ('fluid_id',UUID(int=22)), ('system_id',UUID(int=23)), ('circuit_id',UUID(int=24)),
])
def test_selection_engineering_revision_fields(name, new):
    old = selection()
    revised = revise_selection(old, replace(old, **{name:new}))
    assert revised.selection_id == old.selection_id and revised.revision == 2
    assert is_stale(linked(old).snapshot, revised)
    assert revise_selection(revised, revised).revision == 2


@pytest.mark.parametrize('name,new', [
    ('id',UUID(int=30)), ('inside_diameter_mm',99), ('outside_diameter_mm',112),
    ('wall_thickness_mm',3), ('nominal_diameter','NEW DN'), ('nps','NEW NPS'), ('schedule','NEW SCH'),
])
def test_pipe_engineering_revision_fields(name, new):
    old=selection()
    new=replace(old, selected_pipe=replace(old.selected_pipe, **{name:new}))
    assert revise_selection(old,new).revision == 2


@pytest.mark.parametrize('name,new', [
    ('theoretical_internal_diameter_mm',80), ('design_velocity_m_s',3),
    ('actual_velocity_m_s',2.5), ('design_temperature_c',50),
    ('status',DesignStatus.SUCCESS),
    ('provenance',PipeProvenance(material_standard=replace(SOURCE,notes='Updated presentation note'))),
])
def test_irrelevant_metadata_does_not_invalidate_revision(name, new):
    old=selection()
    result=revise_selection(old,replace(old, **{name:new}))
    assert result.revision == 1 and not is_stale(linked(old).snapshot,result)


def test_revision_lineage_and_read_determinism():
    old=selection(revision=7)
    fresh=replace(changed(old),selection_id=uuid4())
    result=revise_selection(old,fresh)
    assert result.selection_id == old.selection_id and result.revision == 8
    snap=linked(old).snapshot
    for _ in range(5):
        assert not is_stale(snap,old)
    assert old.revision == 7
    assert is_stale(snap,replace(old,revision=6))


@pytest.mark.parametrize('revision',[0,-1,True,1.5])
def test_invalid_revisions_rejected(revision):
    with pytest.raises(ValueError):
        selection(revision=revision)


def test_upstream_changes_only_stale_until_explicit_update_or_keep():
    old=selection(); state=linked(old); new=changed(old)
    stale=state.observe(new)
    assert stale.snapshot is state.snapshot
    assert stale.used_values.hydraulic_values() == (101,20)
    assert stale.status is PipeLinkStatus.LINKED_STALE
    kept=stale.keep_current(new)
    assert kept.kept_current and kept.status is PipeLinkStatus.LINKED_STALE
    assert kept.snapshot is state.snapshot and kept.observed_revision == 2
    assert kept.observe(new).kept_current
    newer=revise_selection(new,replace(new,flow_rate_m3_h=40))
    assert not kept.observe(newer).kept_current
    updated=kept.update(new,applied_at=STAMP)
    assert updated.used_values.hydraulic_values() == (99,30)
    assert updated.snapshot.source_revision == 2 and not updated.kept_current
    assert updated.status is PipeLinkStatus.LINKED_SYNCED
    assert state.used_values.hydraulic_values() == (101,20)


@pytest.mark.parametrize('current,status',[
    (None,PipeLinkStatus.LINKED_SOURCE_MISSING),
    (selection(selection_id=UUID(int=200)),PipeLinkStatus.LINKED_SOURCE_DIFFERENT),
    (selection(selected_pipe=None),PipeLinkStatus.LINKED_SOURCE_UNAVAILABLE),
])
def test_source_problems_retain_values(current,status):
    state=linked().observe(current)
    assert state.status is status
    assert state.used_values.hydraulic_values() == (101,20)
    assert is_stale(state.snapshot,current)
    assert state.keep_current(current).kept_current
    if current is not None:
        with pytest.raises(ValueError):
            state.update(current)


def test_source_replacement_requires_explicit_link_and_manual_detaches():
    old=linked(); different=selection(selection_id=uuid4(),flow_rate_m3_h=50)
    with pytest.raises(ValueError): old.update(different)
    replaced=old.link_to(different,applied_at=STAMP)
    assert replaced.snapshot.source_selection_id == different.selection_id
    manual=replaced.to_manual()
    assert manual.snapshot is None and manual.status is PipeLinkStatus.MANUAL
    assert manual.observe(changed(different)) is manual
    assert manual.used_values.flow_rate_m3_h == 50
    manual=manual.to_manual(PipeValues(flow_rate_m3_h=6,actual_internal_diameter_mm=40))
    assert manual.used_values.hydraulic_values() == (40,6)
    assert manual.link_to(selection()).used_values.hydraulic_values() == (101,20)


def test_project_publish_and_remove_never_apply_or_calculate():
    old=selection(); state=PipeTransferProjectState(selections=(old,),discharge=linked(old),suction=linked(old))
    new=changed(old); observed=state.with_selection(new)
    for item in (observed.discharge,observed.suction):
        assert item.status is PipeLinkStatus.LINKED_STALE
        assert item.used_values.hydraulic_values() == (101,20)
    missing=observed.without_selection(old.selection_id)
    assert missing.discharge.status is PipeLinkStatus.LINKED_SOURCE_MISSING
    assert missing.suction.snapshot == state.suction.snapshot
    with pytest.raises(ValueError): state.with_selection(replace(old,flow_rate_m3_h=500))
    with pytest.raises(ValueError): state.with_selection(replace(old,revision=0))
    with pytest.raises(ValueError): PipeTransferProjectState(selections=(old,old))


def test_full_selection_primitive_json_roundtrip_with_provenance():
    engineering=EngineeringValue(used_value=3,unit='m/s',source=SOURCE,
        override_policy=OverridePolicy.SUGGESTED,recommended_value=2,override_reason='test override')
    result=selection(provenance=PipeProvenance(design_velocity=engineering, material_standard=SOURCE),
        allowable_stress=RuleValue(100,DesignStatus.SUCCESS,SOURCE,'test only'),
        manufacturing_tolerance=RuleValue(None,DesignStatus.SOURCE_REQUIRED),
        minimum_wall=RuleValue(2,DesignStatus.SUCCESS,SOURCE),
        wall=WallBreakdown(1,0,1,None,2,None,2))
    data=selection_to_dict(result)
    assert data['selection_id'] == str(result.selection_id)
    assert data['status'] == result.status.value
    restored=selection_from_dict(json.loads(json.dumps(data,allow_nan=False)))
    assert restored == result
    assert restored.provenance.design_velocity.source.effective_date == date(2020,1,1)
    assert restored.provenance.design_velocity.override_policy is OverridePolicy.SUGGESTED
    assert selection_to_dict(restored) == data
    data['future_field']='ignore safely'
    assert selection_from_dict(data) == result
    del data['selection_id']
    with pytest.raises(ValueError): selection_from_dict(data)


@pytest.mark.parametrize('kind',['sync','stale','kept','missing','different','manual'])
def test_transfer_roundtrip_all_states(kind):
    old=selection(); new=changed(old); state=linked(old)
    sources=(old,)
    if kind in ('stale','kept'):
        sources=(new,);state=state.observe(new)
        if kind=='kept': state=state.keep_current(new)
    if kind=='missing': sources=();state=state.observe(None)
    if kind=='different':
        # Stored source is absent on load; it must become source-missing, not arbitrary relink.
        sources=(selection(selection_id=uuid4()),);state=state.observe(sources[0])
    if kind=='manual': state=state.to_manual()
    project=PipeTransferProjectState(selections=sources,discharge=state,suction=state)
    encoded=transfer_json(project)
    restored=transfer_from_dict(json.loads(encoded))
    assert restored.discharge.used_values == state.used_values
    assert restored.discharge.snapshot == state.snapshot
    if kind != 'different': assert restored.discharge.kept_current == state.kept_current
    if kind=='different': assert restored.discharge.status is PipeLinkStatus.LINKED_SOURCE_MISSING
    else: assert restored.discharge.status is state.status
    assert transfer_json(restored) == transfer_json(restored.refresh())


def test_unknown_namespace_version_rejected_and_unknown_fields_ignored():
    payload=transfer_to_dict(PipeTransferProjectState(discharge=linked(),selections=(selection(),)))
    payload['future']='preserved by opaque legacy persistence'
    payload['discharge']['future']='ignore'
    assert transfer_from_dict(payload).discharge.mode is PipeInputMode.LINKED
    for version in (2,None,True):
        payload['version']=version
        with pytest.raises(ValueError): transfer_from_dict(payload)


@pytest.mark.parametrize('fields', [{'d':'101','q':'20'}, {'d':'101,5','q':'20,5'}, {'d':'bad','q':''}, {}])
def test_legacy_always_manual_even_matching_numbers(fields):
    state=transfer_from_workspace({'schema_version':1,'discharge_head_loss':{'fields':fields}})
    assert state.discharge.mode is PipeInputMode.MANUAL and state.discharge.snapshot is None
    assert state.suction.mode is PipeInputMode.MANUAL
    if fields.get('d')=='101,5': assert state.discharge.used_values.hydraulic_values() == (101.5,20.5)


def test_project_persistence_uses_existing_json_and_preserves_namespace(project_database,project_service):
    repo=ProjectStateRepository(project_database)
    service=ProjectPersistenceService(project_service,repo)
    project=service.create_project('Phase 7 test')
    original={'schema_version':1,'discharge_head_loss':{'fields':{'d':'101','q':'20'}},'future':{'x':1}}
    service.save(original)
    _,payload,manual=service.open_with_pipe_transfer(project.id)
    assert manual.discharge.mode is PipeInputMode.MANUAL and payload==original
    old=selection();new=changed(old)
    transfer=PipeTransferProjectState(selections=(new,),discharge=linked(old).keep_current(new),suction=linked(old))
    service.save_with_pipe_transfer(original,transfer)
    _,payload,restored=service.open_with_pipe_transfer(project.id)
    assert payload['schema_version']==1 and payload['pipe_transfer']['version']==1
    assert restored.discharge.kept_current and restored.discharge.snapshot.source_revision==1
    assert restored.discharge.observed_revision==2
    namespace=payload['pipe_transfer']
    service.save({'schema_version':1,'discharge_head_loss':{'fields':{'q':'50'}}})
    assert repo.get(project.id)['pipe_transfer']==namespace
    service.save_with_pipe_transfer({},PipeTransferProjectState())
    assert service.open_with_pipe_transfer(project.id)[2].discharge.mode is PipeInputMode.MANUAL
    # The legacy reader remains able to carry a future extension opaquely.
    service.save({'schema_version':1,'pipe_transfer':{'version':999,'new':'opaque'}})
    assert service.open(project.id)[1]['pipe_transfer']['new']=='opaque'
    service.save({})
    assert repo.get(project.id)['pipe_transfer']['version']==999
    with pytest.raises(ValueError): service.open_with_pipe_transfer(project.id)


def numerical(result):
    payload=asdict(result);payload.pop('metadata',None)
    return payload


@pytest.mark.parametrize('mode',['manual','sync','stale','kept','missing','detached'])
@pytest.mark.parametrize('module',['discharge','suction','enpy'])
def test_manual_and_linked_hydraulic_results_identical(mode,module):
    old=selection();state=linked(old)
    if mode=='manual': state=PipeInputState(manual_values=state.used_values)
    if mode=='stale': state=state.observe(changed(old))
    if mode=='kept': state=state.keep_current(changed(old))
    if mode=='missing': state=state.observe(None)
    if mode=='detached': state=state.to_manual()
    # object() makes any implicit material/context repository access fail.
    if module=='discharge':
        service=DischargeHeadLossService(object())
        args=dict(kinematic_viscosity_m2s=2e-6,pipe_length_m=20,roughness_mm=.015,geodetic_head_m=2,local_loss_items=[])
        expected=service.calculate(101,20,**args)
        result=service.calculate_with_pipe(state,**args)
    else:
        service=SuctionNPSHService(object())
        args=dict(viscosity=2,viscosity_unit='cSt',length=20,roughness=.015,items=[])
        if module=='enpy':
            args.update(pe=1.2,pe_unit='bar',pb=.03,pb_unit='bar',density=850,height=-2,required=3)
            expected=service.calculate(101,20,**args)
            result=service.calculate_with_pipe(state,**args)
        else:
            expected=service.calculate_suction_loss(101,20,**args)
            result=service.calculate_suction_loss_with_pipe(state,**args)
    assert numerical(result)==numerical(expected)
    assert result.metadata['pipe_transfer']==state.trace()
    if state.snapshot: assert state.trace()['source_revision']==1


def test_missing_manual_values_cannot_calculate():
    with pytest.raises(ValueError):
        PipeInputState().used_values.hydraulic_values()


def test_snapshot_naive_time_rejected_and_no_read_timestamp_generation():
    snap=linked().snapshot
    with pytest.raises(ValueError): replace(snap,applied_at=datetime(2026,1,1))
    state=PipeTransferProjectState(selections=(selection(),),discharge=linked())
    payload=transfer_to_dict(state)
    del payload['discharge']['snapshot']['applied_at']
    restored=transfer_from_dict(payload)
    assert restored.discharge.snapshot.applied_at is None


def test_pipe_design_service_explicit_revision_lineage(material_service,pipe_size_service,engineering_constant_service):
    from services.pipe_design_service import PipeDesignService
    from engineering.pipe_design.v2_models import PipeDesignV2Input
    standard=pipe_size_service.create_standard(code="TRANSFER_TEST",display_name="Synthetic test")
    pipe_size_service.create_pipe_size(standard_id=standard.id,nominal_diameter="TEST",outside_diameter_mm=110,wall_thickness_mm=4,inside_diameter_mm=102)
    service=PipeDesignService(material_service,pipe_size_service,engineering_constant_service)
    request=PipeDesignV2Input(flow_rate_m3_h=20,design_velocity_m_s=2,standard_id=standard.id,
        design_pressure_bar=16,weld_factor=.85,corrosion_allowance_mm=1,yield_strength_mpa=195,safety_factor=1.8)
    first=service.calculate_v2(request)
    same=service.calculate_v2(request,previous_selection=first)
    assert same.selection_id==first.selection_id and same.revision==1
    updated=service.calculate_v2(replace(request,flow_rate_m3_h=25),previous_selection=same)
    assert updated.selection_id==first.selection_id and updated.revision==2
    assert linked(first).observe(updated).used_values.flow_rate_m3_h==20
    assert service.calculate_v2(request).selection_id != first.selection_id


def test_transfer_domain_has_no_ui_or_repository_imports():
    import ast
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]/'engineering/pipe_design'
    for name in ('transfer','transfer_serialization'):
        tree=ast.parse((root/f'{name}.py').read_text(encoding='utf-8-sig'))
        imports={n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}
        imports|={a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names}
        assert not any(i.startswith(('ui','tkinter','sqlite3','database','repositories','matplotlib','PIL')) for i in imports)


def test_persistence_keeps_existing_schema_versions(project_database,library_database):
    for db,version in ((project_database,1),(library_database,5)):
        with db.connection() as connection:
            assert connection.execute('SELECT version FROM schema_version').fetchone()[0]==version


@pytest.mark.parametrize('bad',[{'mode':'LINKED'}, {'snapshot':linked().snapshot}, {'observed_revision':1}, {'kept_current':True}])
def test_invalid_manual_state_rejected(bad):
    with pytest.raises((TypeError,ValueError)): PipeInputState(**bad)
