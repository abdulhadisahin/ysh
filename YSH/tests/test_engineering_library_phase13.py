"""Engineering library safety against isolated databases and display-free controllers."""
from dataclasses import fields, replace
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4
import json

import pytest

from core.material import Material
from core.pipe_standard import PipeStandard
from core.pipe_size import PipeSize
from core.engineering_constant import EngineeringConstant
from core.corrosion_allowance_circuit import CorrosionAllowanceCircuit
from core.pump_reference import PumpReference
from engineering.provenance import SourceReference, SourceType, VerificationStatus
from repositories.v2_models import SourceRecord, RuleSet, System, Circuit, Fluid, FluidProperty, MaterialProperty
from repositories.v2_models import PipeSizeMetadata, PipeStandardMetadata, EngineeringConstantMetadata, CorrosionSourceLink
from services.engineering_library_service import EngineeringLibraryService, LibraryError
from services.library_catalog import CATEGORIES, CATEGORY_BY_CODE
from ui.library_controller import LibraryController, EditMode
from ui.dialogs.engineering_library_workspace import EngineeringLibraryWorkspace, record_label
from ui.widgets.formula_steps import source_rows, step_sections
from engineering.formula.suction import suction_steps
from engineering.formula.discharge import hydraulic_steps
from services.discharge_head_loss_service import DischargeHeadLossService
from services.suction_npsh_service import SuctionNPSHService
from services.system_context_service import SystemContextService
from i18n.messages_tr import MESSAGES as TR
from i18n.messages_en import MESSAGES as EN
from ui.main_window import MainWindow
from .test_discharge_v2_phase8 import inputs
from .test_suction_v2_phase9 import suction_input, enpy_input
from .test_project_persistence_workflow import _service as persistence


@pytest.fixture
def library(library_database):
    """Seed only synthetic test fixtures, never application production records."""
    service=EngineeringLibraryService(library_database);r=service._repos
    source=r['sources'].create(SourceRecord(reference=SourceReference(source_type=SourceType.USER_INPUT,
        document='Synthetic source',source_organization='Test organization',revision='A',
        effective_date=date(2025,1,1),verification_date=date(2025,2,1),
        verification_status=VerificationStatus.USER_SUPPLIED)))
    system=r['systems'].create(System(code='TEST',name_tr='Test system'))
    circuit=r['circuits'].create(Circuit(system_id=system.id,code='TEST',name_tr='Test circuit'))
    fluid=r['fluids'].create(Fluid(code='TEST',name_tr='Test fluid'))
    material=r['materials'].create(Material(name='Test',designation='SYNTHETIC',yield_strength_mpa=123,roughness_mm=.123456789))
    rule=r['rule_sets'].create(RuleSet(code='TEST',name='Synthetic rule metadata',source_id=source.id,
                                       verification_status=VerificationStatus.USER_SUPPLIED))
    fp=r['fluid_properties'].create(FluidProperty(fluid_id=fluid.id,property_name='density',value=850.123456789,
        unit='kg/m³',source_id=source.id,verification_status=VerificationStatus.USER_SUPPLIED))
    mp=r['material_properties'].create(MaterialProperty(material_id=material.id,property_name='Rp0.2',value=123.123456,
        unit='MPa',reference_temperature_c=25,source_id=source.id,rule_set_id=rule.id,verification_status=VerificationStatus.USER_SUPPLIED))
    standard=r['pipe_standards'].create_standard(PipeStandard(code='SYNTHETIC',display_name='Test dimension standard'))
    pipe=r['pipe_sizes'].create(PipeSize(standard_id=standard.id,nominal_diameter='DN TEST',outside_diameter_mm=110,
                                         wall_thickness_mm=4,inside_diameter_mm=101,is_system=True))
    pipe=r['pipe_sizes'].get(pipe.id)
    sm=r['pipe_standard_metadata'].create(PipeStandardMetadata(standard_id=standard.id,standard_family='TEST',source_id=source.id))
    pm=r['pipe_size_metadata'].create(PipeSizeMetadata(pipe_size_id=pipe.id,nps='TEST NPS',schedule='TEST SCH',source_id=source.id))
    constant=r['constants'].create(EngineeringConstant(key='synthetic_value',display_name='Test value',value=1.23456789,unit='mm'))
    cm=r['constant_metadata'].create(EngineeringConstantMetadata(constant_id=constant.id,source_id=source.id,
        system_id=system.id,circuit_id=circuit.id,rule_set_id=rule.id))
    corrosion=r['corrosion'].create(CorrosionAllowanceCircuit(code='TEST LIBRARY',display_name='Test corrosion',default_corrosion_allowance_mm=.12345))
    cs=r['corrosion_sources'].create(CorrosionSourceLink(corrosion_circuit_id=corrosion.id,source_id=source.id,rule_set_id=rule.id,circuit_id=circuit.id))
    pump=r['pump_references'].create(PumpReference(ship_name='Synthetic reference',fuel_capacity_m3=100,pump_capacity_m3h=20))
    return service,dict(sources=source,systems=system,circuits=circuit,fluids=fluid,materials=material,rule_sets=rule,
        fluid_properties=fp,material_properties=mp,pipe_standards=standard,pipe_sizes=pipe,pipe_standard_metadata=sm,
        pipe_size_metadata=pm,constants=constant,constant_metadata=cm,corrosion=corrosion,corrosion_sources=cs,pump_references=pump)


@pytest.mark.parametrize('category',[c.code for c in CATEGORIES])
def test_each_engineering_category_lists_and_inspects_existing_data(library,category) -> None:
    service,rows=library;definition=CATEGORY_BY_CODE[category]
    parent=getattr(rows[definition.parent],CATEGORY_BY_CODE[definition.parent].key_field) if definition.parent else None
    listed=service.list_records(category,parent)
    assert rows[category] in listed
    detail=service.details(category,rows[category])
    assert detail.values and dict(detail.values).get('id',True)


def test_constructor_and_repeated_browsing_never_seed_or_write(library_database,monkeypatch) -> None:
    with library_database.connection() as conn:
        before=conn.total_changes
    service=EngineeringLibraryService(library_database)
    for repo in service._repos.values():
        for name in ('create','update','create_standard'):
            if hasattr(repo,name): monkeypatch.setattr(repo,name,lambda *a,**k:pytest.fail('browse wrote data'))
    for _ in range(3):
        for category in CATEGORIES: service.list_records(category.code)
    assert service._repos['systems'].get_all()==()
    assert service._repos['fluids'].get_all()==()
    assert service._repos['sources'].get_all()==()
    assert len(service.list_records('systems'))==3
    assert not hasattr(service,'delete') and not hasattr(service,'remove')


def test_user_create_duplicate_edit_and_inactive_preservation(library) -> None:
    service,_=library
    created=service.save('systems',dict(code='USER',name_tr='Created',name_en=None,is_active=True))
    with pytest.raises(LibraryError,match='duplicate'):
        service.save('systems',dict(code='user',name_tr='Duplicate',is_active=True))
    values=service.form_values('systems',created);values.update(name_tr='Changed',is_active=False)
    changed=service.save('systems',values,created.id)
    assert changed.id==created.id and not changed.is_active
    assert service.get_record('systems',created.id)==changed
    controller=LibraryController(service);controller.browse('systems')
    assert changed in controller.filtered(active=False)
    assert changed not in controller.filtered(active=True)
    values['is_active']=True
    assert service.save('systems',values,created.id).is_active


def test_circuit_relationship_and_invalid_fk_are_rejected_atomically(library) -> None:
    service,rows=library
    values=dict(system_id=rows['systems'].id,code='USER',name_tr='User circuit',is_active=True)
    created=service.save('circuits',values)
    assert created in service.list_records('circuits',rows['systems'].id)
    before=service.list_records('circuits',rows['systems'].id)
    with pytest.raises(LibraryError,match='reference'): service.save('circuits',{**values,'system_id':uuid4()})
    assert service.list_records('circuits',rows['systems'].id)==before
    fallback=next(r for r in service.list_records('systems') if service.ownership('systems',r)=='application')
    with pytest.raises(LibraryError,match='reference'): service.save('circuits',{**values,'system_id':fallback.id})


def test_property_create_source_link_nullable_temperature_and_precision(library) -> None:
    service,rows=library
    fluid=service.save('fluids',dict(code='USER',name_tr='New fluid',name_en=None,is_active=True))
    raw='1,2345678901234567'
    prop=service.save('fluid_properties',dict(fluid_id=fluid.id,property_name='kinematic_viscosity',value=raw,
        unit='m²/s',reference_temperature_c=None,source_id=rows['sources'].id,verification_status='USER_SUPPLIED'))
    assert prop.value==1.2345678901234567 and prop.reference_temperature_c is None
    assert prop.source_id==rows['sources'].id
    values=service.form_values('fluid_properties',prop);values['value']='2.345678901234567'
    changed=service.save('fluid_properties',values,prop.id)
    assert changed.value==2.345678901234567
    material=service.save('material_properties',dict(material_id=rows['materials'].id,property_name='roughness',
        value='.0123456789',unit='mm',reference_temperature_c='-20',source_id=None,verification_status='USER_SUPPLIED',rule_set_id=None))
    assert material.source_id is None and material.reference_temperature_c==-20


@pytest.mark.parametrize('bad',['nan','inf','-inf','True',True,'1,2.3'])
def test_invalid_numbers_never_write_a_property(library,bad) -> None:
    service,rows=library
    values=service.form_values('fluid_properties',rows['fluid_properties']);values['value']=bad
    with pytest.raises(LibraryError): service.save('fluid_properties',values,rows['fluid_properties'].id)
    assert service.get_record('fluid_properties',rows['fluid_properties'].id)==rows['fluid_properties']


@pytest.mark.parametrize('category',['systems','fluids','circuits','materials','constants'])
def test_factory_identity_and_values_are_protected(library,category) -> None:
    service,rows=library;row=rows[category]
    factory=replace(row,**({'is_factory':True} if hasattr(row,'is_factory') else {'is_system':True}))
    service._repos[category].update(factory)
    assert not service.can_edit(category,factory)
    with pytest.raises(LibraryError,match='protected'): service.save(category,service.form_values(category,factory),factory.id)
    assert service.get_record(category,factory.id)==factory


@pytest.mark.parametrize('status',[None,'VERIFIED','PARTIALLY_VERIFIED','DEPRECATED'])
def test_unknown_or_verified_source_ownership_is_conservatively_readonly(library,status) -> None:
    service,rows=library
    src=replace(rows['sources'],reference=replace(rows['sources'].reference,
                verification_status=VerificationStatus(status) if status else None))
    service._repos['sources'].update(src)
    assert not service.can_edit('sources',src)
    with pytest.raises(LibraryError,match='protected'): service.save('sources',service.form_values('sources',src),src.id)


def test_source_metadata_dates_nulls_and_user_edit(library) -> None:
    service,rows=library
    source=service.save('sources',dict(source_type='USER_INPUT',document='New source',verification_status='USER_SUPPLIED'))
    assert source.reference.source_organization is None and source.reference.verification_date is None
    for messages in (TR,EN):
        shown=source_rows(source.reference,messages.__getitem__)
        assert len(shown)==3
    values=service.form_values('sources',source)
    values.update(revision='R2',effective_date='2025-01-02',verification_date='2025-02-03')
    updated=service.save('sources',values,source.id)
    assert updated.reference.effective_date==date(2025,1,2)
    assert updated.reference.verification_date==date(2025,2,3)
    assert updated.reference.revision=='R2'
    for name,bad in (('effective_date','2025-02-30'),('source_type','INVALID'),('verification_status','INVALID')):
        with pytest.raises(LibraryError): service.save('sources',{**values,name:bad},source.id)
    assert service.get_record('sources',source.id)==updated


def test_source_details_are_lazy_cached_and_do_not_infer_verification(library,monkeypatch) -> None:
    service,rows=library;calls=[];repo=service._repos['sources'];original=repo.get
    monkeypatch.setattr(repo,'get',lambda identity:calls.append(identity) or original(identity))
    service.list_records('fluid_properties',rows['fluids'].id)
    assert calls==[]
    for _ in range(3):
        details=service.details('fluid_properties',rows['fluid_properties'])
        assert details.sources==(rows['sources'].reference,)
    assert calls==[rows['sources'].id]
    values=dict(details.values)
    assert values['verification_status'] is VerificationStatus.USER_SUPPLIED
    service.refresh();service.details('fluid_properties',rows['fluid_properties'])
    assert len(calls)==2


def test_pipe_metadata_is_exact_and_reference_geometry_is_browse_only(library) -> None:
    service,rows=library
    before=service.get_record('pipe_sizes',rows['pipe_sizes'].id)
    detail=service.details('pipe_sizes',before)
    assert dict(detail.values)['nps']=='TEST NPS' and dict(detail.values)['schedule']=='TEST SCH'
    assert 'manufacturing_tolerance' not in dict(detail.values)
    assert not detail.editable
    with pytest.raises(LibraryError,match='protected'): service.save('pipe_sizes',{'outside_diameter_mm':999},before.id)
    assert service.get_record('pipe_sizes',before.id)==before
    for _ in range(3): assert service.list_records('pipe_sizes',rows['pipe_standards'].id)==(before,)


def test_constant_metadata_relationship_and_single_record_write(library,monkeypatch) -> None:
    service,rows=library;row=rows['constant_metadata']
    values=service.form_values('constant_metadata',row);values['selection_reason']='Explicit project source'
    repo=service._repos['constant_metadata'];original=repo.update;calls=[]
    monkeypatch.setattr(repo,'update',lambda item:calls.append(item) or original(item))
    saved=service.save('constant_metadata',values,row.constant_id)
    assert len(calls)==1 and saved.source_id==rows['sources'].id
    with pytest.raises(LibraryError,match='reference'):
        service.save('constant_metadata',{**values,'system_id':None},row.constant_id)
    assert len(calls)==1


def test_metadata_primary_identity_cannot_be_redirected_to_overwrite_another_row(library) -> None:
    service,rows=library
    other=service.save('constants',dict(key='other_user',display_name='Other',value=2,unit='mm'))
    second=service.save('constant_metadata',dict(constant_id=other.id,source_id=None,rule_set_id=None,
                                                system_id=None,circuit_id=None,selection_reason='Original other'))
    first=rows['constant_metadata']
    draft=service.form_values('constant_metadata',first);draft['constant_id']=other.id
    with pytest.raises(LibraryError,match='validation'):
        service.save('constant_metadata',draft,first.constant_id)
    assert service.get_record('constant_metadata',other.id)==second
    assert service.get_record('constant_metadata',first.constant_id)==first


def test_controller_browse_select_edit_cancel_and_failed_save_preserve_draft(library,monkeypatch) -> None:
    service,rows=library;c=LibraryController(service)
    assert c.records==() and c.mode is EditMode.BROWSE
    c.browse('systems');c.select(rows['systems'].id);c.begin(create=False)
    c.draft['code']=''
    before=c.draft.copy()
    with pytest.raises(LibraryError,match='finish_edit'): c.browse('fluids')
    assert not c.save() and c.mode is EditMode.EDIT and c.draft==before and c.error_key
    c.cancel();assert c.draft=={} and c.mode is EditMode.BROWSE
    assert service.get_record('systems',rows['systems'].id)==rows['systems']
    c.begin(create=False);c.draft['name_tr']='Saved change';calls=[];original=service.save
    monkeypatch.setattr(service,'save',lambda *a,**k:calls.append((a,k)) or original(*a,**k))
    assert c.save() and len(calls)==1 and c.mode is EditMode.BROWSE
    c.browse('fluids');assert c.category=='fluids'


def test_controller_create_filters_and_reference_vessel_classification(library) -> None:
    service,rows=library;c=LibraryController(service);c.browse('systems')
    assert c.filtered(search='Test system')==(rows['systems'],)
    c.begin(create=True);c.draft.update(code='NEW',name_tr='New',name_en=None)
    assert c.save()
    c.browse('sources')
    assert c.filtered(verification='USER_SUPPLIED')==(rows['sources'],)
    detail=service.details('pump_references',rows['pump_references'])
    assert detail.sources[0].source_type is SourceType.REFERENCE_VESSEL_DATA
    assert detail.sources[0].verification_status is None


def test_library_edits_cannot_rewrite_calculations_formula_steps_or_project_state(library,tmp_path) -> None:
    service,rows=library
    discharge=DischargeHeadLossService(object()).calculate_v2(inputs())
    suction=SuctionNPSHService(object()).calculate_v2(suction_input(),enpy_input())
    steps=(*hydraulic_steps(discharge),*suction_steps(suction))
    before=tuple(step_sections(s,TR.__getitem__) for s in steps)
    p=persistence(tmp_path);project=p.create_project('Historical')
    state={'schema_version':1,'suction_npsh':{'ρ':850,'ν':2e-6,'Pb':3000},'discharge_head_loss':{'ν':2e-6}}
    p.save(state);saved=json.dumps(p.open(project.id)[1],sort_keys=True)
    for property_name,value,unit in (('density',999,'kg/m³'),('kinematic_viscosity',.9,'m²/s'),('vapor_pressure',99999,'Pa')):
        service.save('fluid_properties',dict(fluid_id=rows['fluids'].id,property_name=property_name,value=value,
            unit=unit,reference_temperature_c=None,source_id=None,verification_status='USER_SUPPLIED'))
    values=service.form_values('materials',rows['materials']);values['roughness_mm']=99
    service.save('materials',values,rows['materials'].id)
    assert tuple(step_sections(s,TR.__getitem__) for s in steps)==before
    assert json.dumps(p.open(project.id)[1],sort_keys=True)==saved
    assert suction.input.density_kg_m3==850 and suction.metadata['vapour_pressure_pa']==3000
    assert discharge.input.kinematic_viscosity_m2s==2e-6


def test_ui_contracts_localization_lazy_loading_and_existing_entrypoints(library) -> None:
    service,rows=library
    for messages in (TR,EN):
        for category in CATEGORIES:
            assert messages[f'library2.group.{category.group}'] and messages[f'library2.category.{category.code}']
            for field in category.fields:
                key=f'formula2.source.{field.name}' if category.code=='sources' else f'library2.field.{field.name}'
                assert messages[key]
        for category,row in rows.items():
            for key,value in service.details(category,row).values: assert messages[f'library2.field.{key}']
    root=Path(__file__).parents[1]
    workspace=(root/'ui/dialogs/engineering_library_workspace.py').read_text(encoding='utf-8')
    assert 'sqlite3' not in workspace and '.execute(' not in workspace
    assert 'grab_set' not in workspace and 'wait_window' not in workspace
    assert not any(word in workspace for word in ('delete_record','delete_item','delete_reference'))
    calls=[]
    fake=SimpleNamespace(_library_service_factory=lambda:pytest.fail('eager service'),_open_engineering_library=calls.append)
    for method,category in ((MainWindow._open_material_library,'materials'),(MainWindow._open_pipe_size_library,'pipe_standards'),
                            (MainWindow._open_constants_library,'constants'),(MainWindow._open_corrosion_allowance_circuit_library,'corrosion')):
        method(fake);assert calls[-1]==category


def test_constructor_performs_no_database_reads(library_database,monkeypatch) -> None:
    monkeypatch.setattr(library_database,'connection',lambda:pytest.fail('eager read at composition'))
    service=EngineeringLibraryService(library_database)
    controller=LibraryController(service)
    assert controller.records==()


def test_repository_read_errors_are_mapped_without_exposing_database_text(library,monkeypatch) -> None:
    from repositories.v2_errors import RepositoryError
    service,_=library
    def fail(): raise RepositoryError('RAW SQLITE DETAILS')
    monkeypatch.setattr(service._repos['fluids'],'get_all',fail)
    with pytest.raises(LibraryError) as caught: service.list_records('fluids')
    assert str(caught.value)=='library2.error.storage'


def test_duplicate_pump_and_source_link_failure_never_leave_partial_data(library) -> None:
    service,rows=library
    values=service.form_values('pump_references',rows['pump_references'])
    with pytest.raises(LibraryError,match='duplicate'): service.save('pump_references',values)
    before=service.list_records('fluid_properties',rows['fluids'].id)
    values=service.form_values('fluid_properties',rows['fluid_properties']);values['source_id']=uuid4()
    with pytest.raises(LibraryError,match='reference'): service.save('fluid_properties',values)
    assert service.list_records('fluid_properties',rows['fluids'].id)==before


def test_material_and_constant_user_core_edits_preserve_precision(library) -> None:
    service,rows=library
    for category,name,value in (('materials','roughness_mm',.987654321012345),('constants','value',9.87654321012345)):
        row=rows[category];draft=service.form_values(category,row);draft[name]=repr(value)
        saved=service.save(category,draft,row.id)
        assert getattr(saved,name)==value
        assert getattr(service.get_record(category,row.id),name)==value


def test_ruleset_user_metadata_edit_does_not_add_rules(library) -> None:
    service,rows=library;row=rows['rule_sets']
    draft=service.form_values('rule_sets',row);draft.update(revision='User revision',is_active=False)
    changed=service.save('rule_sets',draft,row.id)
    assert changed.revision=='User revision' and not changed.is_active and changed.source_id==row.source_id
    assert not hasattr(changed,'coefficients')


def editor_stub(library,category,monkeypatch):
    """Exercise actual editor methods with native-widget substitutes, without pixels."""
    import ui.dialogs.engineering_library_workspace as view
    service,rows=library
    created=[]
    class Widget:
        def __init__(self,parent=None,**kwargs):
            self.parent=parent;self.children=[];self.options=kwargs;self.visible=False
            if parent is not None and hasattr(parent,'children'): parent.children.append(self)
            created.append(self)
        def configure(self,**kwargs): self.options.update(kwargs)
        def grid(self,**kwargs): self.visible=True
        def grid_remove(self): self.visible=False
        def winfo_manager(self): return 'grid' if self.visible else ''
        def winfo_children(self): return tuple(self.children)
        def destroy(self):
            if self.parent and self in self.parent.children: self.parent.children.remove(self)
        def bind(self,*args): pass
    class Variable:
        def __init__(self,value=None): self.value=value
        def get(self): return self.value
        def set(self,value): self.value=value
    for name in ('Label','Frame','Entry','Combobox','Checkbutton','Button'):
        monkeypatch.setattr(view.ttk,name,Widget)
    monkeypatch.setattr(view.tk,'StringVar',Variable);monkeypatch.setattr(view.tk,'BooleanVar',Variable)
    window=EngineeringLibraryWorkspace.__new__(EngineeringLibraryWorkspace)
    window._controller=LibraryController(service)
    parent=CATEGORY_BY_CODE[category].parent
    parent_id=getattr(rows[parent],CATEGORY_BY_CODE[parent].key_field) if parent else None
    window._controller.browse(category,parent_id)
    window._controller.select(getattr(rows[category],CATEGORY_BY_CODE[category].key_field))
    window._controller.begin(create=False)
    window._translate=TR.__getitem__;window._body=Widget();window._status=Variable()
    window._choice_cache={};window._edit_vars={};window._edit_choices={}
    window._buttons={key:Widget() for key in ('new','edit','save','cancel','refresh')}
    window._group_box=Widget();window._category_box=Widget();window._parent_box=Widget();window._tree=Widget()
    window._events=[];window.refresh_texts=lambda:window._events.append('refresh')
    window._render_editor()
    return window,created


def test_source_editor_failure_keeps_form_and_cancel_never_writes(library,monkeypatch) -> None:
    window,_=editor_stub(library,'sources',monkeypatch)
    service,rows=library
    assert window._tree.options['selectmode']=='none'
    assert all(box.options['state']=='disabled' for box in (window._group_box,window._category_box,window._parent_box))
    window._edit_vars['effective_date'].set('2025-02-30')
    window._edit_vars['document'].set('Unsaved source title')
    variables=window._edit_vars.copy()
    window._save()
    assert window._controller.mode is EditMode.EDIT
    assert window._edit_vars==variables and window._edit_vars['document'].get()=='Unsaved source title'
    assert window._status.get()==TR['library2.error.validation']
    window._cancel()
    assert window._controller.mode is EditMode.BROWSE
    assert service.get_record('sources',rows['sources'].id)==rows['sources']


def test_actual_property_editor_raw_precision_and_single_save(library,monkeypatch) -> None:
    window,_=editor_stub(library,'fluid_properties',monkeypatch)
    service,rows=library
    assert window._edit_vars['value'].get()==repr(rows['fluid_properties'].value)
    window._edit_vars['value'].set('850,1234567890123')
    original=service.save;calls=[]
    monkeypatch.setattr(service,'save',lambda *a,**k:calls.append((a,k)) or original(*a,**k))
    window._save()
    assert len(calls)==1 and window._controller.mode is EditMode.BROWSE
    assert service.get_record('fluid_properties',rows['fluid_properties'].id).value==850.1234567890123


def test_explicit_context_catalog_refresh_preserves_context_and_applied_values(library,monkeypatch) -> None:
    service,rows=library
    from engineering.system_context import SystemContext
    from services.system_context_service import reference
    ctx=SystemContext(system=reference(rows['systems']))
    context_service=SystemContextService(service._repos['systems'],service._repos['circuits'],service._repos['fluids'])
    service.save('systems',dict(code='LATER',name_tr='Later record',is_active=True))
    assert all(r.code!='LATER' for r in context_service.systems())
    seen=[]
    fake=SimpleNamespace(_system_context_service=context_service,_system_context=ctx,
        _translate=TR.__getitem__,_transfer_pump_page=SimpleNamespace(set_project_context=seen.append))
    MainWindow.refresh_library_context_choices(fake)
    assert any(r.code=='LATER' for r in context_service.systems())
    assert fake._system_context is ctx and seen[-1] is ctx


def test_single_modeless_window_is_reused_before_calling_service_factory(monkeypatch) -> None:
    shown=[]
    window=SimpleNamespace(_library_window=SimpleNamespace(winfo_exists=lambda:True,show_category=shown.append),
                           _library_service_factory=lambda:pytest.fail('unnecessary duplicate service'))
    MainWindow._open_engineering_library(window,'sources')
    assert shown==['sources']


def test_useful_natural_order_and_temperature_order_are_deterministic(library) -> None:
    service,rows=library
    for code in ('USER10','USER2','USER1'):
        service.save('systems',dict(code=code,name_tr=code,is_active=True))
    ordered=[r.code for r in service.list_records('systems') if r.code.startswith('USER')]
    assert ordered==['USER1','USER2','USER10']
    for temperature in (100,-20,50):
        service.save('material_properties',dict(material_id=rows['materials'].id,property_name='roughness',
            value=.01,unit='mm',reference_temperature_c=temperature,source_id=None,rule_set_id=None,verification_status='USER_SUPPLIED'))
    temperatures=[r.reference_temperature_c for r in service.list_records('material_properties',rows['materials'].id) if r.property_name=='roughness']
    assert temperatures==[-20,50,100]


def test_browsing_keeps_library_schema_and_existing_rows_identical(library,library_database) -> None:
    service,rows=library
    def schema():
        with library_database.connection() as connection:
            return tuple(tuple(row) for row in connection.execute('SELECT type,name,sql FROM sqlite_master ORDER BY type,name'))
    before=schema()
    for _ in range(2):
        for category,row in rows.items(): service.details(category,row)
    assert schema()==before
    assert service.get_record('pipe_sizes',rows['pipe_sizes'].id)==rows['pipe_sizes']
    assert service.get_record('sources',rows['sources'].id)==rows['sources']


def test_reference_picker_retains_duplicate_source_labels_and_distinct_pipe_geometry(library,monkeypatch) -> None:
    service,rows=library
    second=service._repos['sources'].create(SourceRecord(reference=rows['sources'].reference))
    window,_=editor_stub(library,'fluid_properties',monkeypatch)
    choices=window._edit_choices['source_id']
    assert rows['sources'].id in choices.values() and second.id in choices.values()
    pipe=rows['pipe_sizes']
    other=replace(pipe,wall_thickness_mm=6,inside_diameter_mm=98)
    assert record_label(pipe)!=record_label(other)


def test_successful_save_followed_by_refresh_failure_is_not_reported_as_failed_write(library,monkeypatch) -> None:
    service,rows=library;c=LibraryController(service)
    c.browse('systems');c.select(rows['systems'].id);c.begin(create=False);c.draft['name_tr']='Committed value'
    def unavailable(*args,**kwargs): raise LibraryError('library2.error.storage')
    monkeypatch.setattr(service,'list_records',unavailable)
    assert c.save() and c.mode is EditMode.BROWSE
    assert c.error_key=='library2.saved_refresh_required'
    assert service.get_record('systems',rows['systems'].id).name_tr=='Committed value'
