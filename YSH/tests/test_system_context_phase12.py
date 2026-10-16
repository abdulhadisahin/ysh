"""Project context is identity/workflow metadata, never an engineering override."""
from dataclasses import replace
import json
from types import SimpleNamespace
from uuid import UUID, uuid4
from pathlib import Path

import pytest

from engineering.system_context import ContextReference, SystemContext
from engineering.module_registry import MODULES, ModuleCode, module_availability
from engineering.pipe_design.transfer import PipeInputState, revise_selection
from engineering.transfer_pump.v2_models import PumpIntegrationContext, TransferPumpMode
from engineering.validation import ValidationError
from repositories.system_repository import SystemRepository
from repositories.circuit_repository import CircuitRepository
from repositories.fluid_repository import FluidRepository
from repositories.v2_models import System, Circuit, Fluid
from services.system_context_service import DEFAULT_SYSTEMS, SystemContextService, reference
from services.system_context_integration import contextualize_selection, pump_context
from services.discharge_head_loss_service import DischargeHeadLossService
from services.suction_npsh_service import SuctionNPSHService
from ui.main_window import MainWindow
from ui.widgets.system_context_panel import SystemContextPanel
from ui.widgets.scrollable_page_host import ScrollablePageHost
from i18n.translator import Translator
from i18n.messages_tr import MESSAGES as TR
from i18n.messages_en import MESSAGES as EN
from .test_discharge_v2_phase8 import source, inputs, Var
from .test_suction_v2_phase9 import suction_input, enpy_input
from .test_transfer_pump_v2_phase10 import transfer_page
from .test_project_persistence_workflow import _service as persistence


def context(code: str = 'FUEL', **values: object) -> SystemContext:
    """Use explicit application identities without inventing fluid properties."""
    system = next(r for r in DEFAULT_SYSTEMS if r.code == code)
    return SystemContext(system=reference(system), **values)


@pytest.fixture
def catalogs(library_database):
    """Use real Phase 4 repositories against isolated test databases."""
    systems=SystemRepository(library_database)
    circuits=CircuitRepository(library_database)
    fluids=FluidRepository(library_database)
    a=systems.create(System(code='FUEL',name_tr='Kullanıcı yakıtı',name_en='User fuel'))
    b=systems.create(System(code='CUSTOM',name_tr='Kullanıcı sistemi'))
    ca=circuits.create(Circuit(system_id=a.id,code='A',name_tr='Gerçek devre A'))
    cb=circuits.create(Circuit(system_id=b.id,code='B',name_tr='Gerçek devre B'))
    fluid=fluids.create(Fluid(code='USER_FLUID',name_tr='Kullanıcı akışkanı'))
    return SystemContextService(systems,circuits,fluids), systems,circuits,fluids,a,b,ca,cb,fluid


def test_application_defaults_are_stable_without_database_writes(library_database) -> None:
    def counts():
        with library_database.connection() as connection:
            return tuple(connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
                         for table in ('systems','circuits','fluids','fluid_properties','rule_sets'))
    before=counts()
    service=SystemContextService(SystemRepository(library_database),CircuitRepository(library_database),FluidRepository(library_database))
    expected=service.systems()
    for _ in range(3):
        service.reload()
        assert service.systems()==expected
        assert all(service.circuits(row.id)==() for row in expected)
        assert service.fluids()==()
    assert {s.code for s in expected}=={'FUEL','FRESH_WATER','OIL'}
    assert {s.name_tr for s in expected}=={'Yakıt','Tatlı Su','Yağ'}
    assert counts()==before


def test_user_records_and_inactive_codes_take_precedence(catalogs) -> None:
    service,systems,_,_,a,*_=catalogs
    assert next(r for r in service.systems() if r.code=='FUEL')==a
    systems.update(replace(a,is_active=False,name_tr='User edit'))
    service.reload()
    assert all(r.code!='FUEL' for r in service.systems())
    assert systems.get(a.id).name_tr=='User edit'
    assert len(systems.get_all())==2


def test_module_scope_uses_current_master_code_without_rewriting_history(catalogs) -> None:
    service,systems,_,_,a,*_=catalogs
    saved=SystemContext(system=reference(a))
    assert next(v for v in service.availability(saved) if v.definition.code is ModuleCode.TRANSFER_PUMP).enabled
    systems.update(replace(a,code='OTHER',name_tr='Updated user system'))
    service.reload()
    assert not next(v for v in service.availability(saved) if v.definition.code is ModuleCode.TRANSFER_PUMP).enabled
    assert saved.system.code=='FUEL' and saved.system.name_tr==a.name_tr


@pytest.mark.parametrize('code',['FUEL','FRESH_WATER','OIL',None,'CUSTOM'])
def test_module_scope_and_legacy_access(code) -> None:
    ctx=SystemContext() if code is None else (
        SystemContext(system=ContextReference(id=uuid4(),code='CUSTOM',name_tr='Custom')) if code=='CUSTOM' else context(code))
    availability=module_availability(ctx)
    assert [a.definition for a in availability]==list(MODULES)
    for item in availability:
        expected=code in (None,'FUEL') if item.definition.code is ModuleCode.TRANSFER_PUMP else True
        assert item.enabled is expected
        assert bool(item.reason_key) is not expected if item.definition.code is ModuleCode.TRANSFER_PUMP else item.reason_key is None


def test_registry_uniqueness_order_and_localization() -> None:
    assert len({m.code for m in MODULES})==len(MODULES)==4
    assert [m.display_order for m in MODULES]==sorted(m.display_order for m in MODULES)
    for messages in (TR,EN):
        for module in MODULES: assert messages[module.name_key]
        for key in (k for k in TR if k.startswith('context.')): assert messages[key]
        assert 'TL' not in messages['context.module.fuel_only']


@pytest.mark.parametrize('parts',[(),('system',),('system','circuit'),('system','fluid'),('system','circuit','fluid')])
def test_json_and_real_project_context_roundtrip(tmp_path,parts) -> None:
    refs={name:ContextReference(id=uuid4(),code=name.upper(),name_tr=f'Test {name}') for name in parts}
    ctx=SystemContext(**refs,material_id=uuid4(),pipe_standard_id=uuid4(),rule_set_id=uuid4(),revision=7)
    payload=json.loads(json.dumps({'system_context':ctx.to_payload()}))
    assert SystemContext.from_workspace(payload)==ctx
    service=persistence(tmp_path)
    project=service.create_project('Context')
    service.save({'schema_version':1,**payload})
    restored=service.open(project.id)[1]
    assert SystemContext.from_workspace(restored)==ctx


def test_project_isolation_partial_saves_legacy_and_explicit_clear(tmp_path) -> None:
    service=persistence(tmp_path)
    a=service.create_project('A')
    service.save({'system_context':context().to_payload()})
    b=service.create_project('B')
    service.save({'schema_version':1})
    assert SystemContext.from_workspace(service.open(b.id)[1])==SystemContext()
    assert SystemContext.from_workspace(service.open(a.id)[1])==context()
    service.save({'pipe_design':{'fields':{'q':'123'}}})
    assert SystemContext.from_workspace(service.open(a.id)[1])==context()
    service.save({'system_context':SystemContext().to_payload()})
    assert SystemContext.from_workspace(service.open(a.id)[1])==SystemContext()
    assert SystemContext.from_workspace(service.open(b.id)[1])==SystemContext()


@pytest.mark.parametrize('bad',[None,[],{}, {'version':2},{'version':True},{'version':1,'system':{'id':'bad'}},
    {'version':1,'revision':0},{'version':1,'is_active':'yes'}])
def test_bad_context_payload_is_rejected_before_ui_mutation(bad) -> None:
    with pytest.raises(ValidationError): SystemContext.from_workspace({'system_context':bad})


@pytest.mark.parametrize('field',['system','circuit','fluid'])
def test_missing_master_data_preserves_historical_ids(catalogs,field) -> None:
    service,_,_,_,a,_,ca,_,fluid=catalogs
    saved=SystemContext(system=reference(a),circuit=reference(ca),fluid=reference(fluid))
    missing=replace(getattr(saved,field),id=uuid4())
    saved=replace(saved,**{field:missing})
    before=saved.to_payload()
    assert any(i.field==field and i.reason_key=='context.source_missing' for i in service.issues(saved))
    assert saved.to_payload()==before
    assert SystemContext.from_workspace({'system_context':before})==saved


def test_inactive_and_wrong_system_circuit_are_distinguished(catalogs) -> None:
    service,systems,circuits,fluids,a,b,ca,cb,fluid=catalogs
    saved=SystemContext(system=reference(a),circuit=reference(cb),fluid=reference(fluid))
    assert any(i.reason_key=='context.invalid_circuit' for i in service.issues(saved))
    systems.update(replace(a,is_active=False));fluids.update(replace(fluid,is_active=False))
    circuits.update(replace(cb,is_active=False));service.reload()
    issues=service.issues(saved)
    assert {i.field for i in issues}=={'system','circuit','fluid'}
    assert saved.circuit_id==cb.id


def test_selection_validates_relationships_and_clears_only_old_circuit(catalogs) -> None:
    service,_,_,_,a,b,ca,cb,fluid=catalogs
    selected=service.select(SystemContext(),system_id=a.id,circuit_id=ca.id,fluid_id=fluid.id)
    assert selected.system_id==a.id and selected.circuit_id==ca.id and selected.fluid_id==fluid.id
    assert service.circuits(a.id)==(ca,)
    changed=service.select(selected,system_id=b.id,circuit_id=ca.id,fluid_id=fluid.id)
    assert changed.circuit is None and changed.fluid_id==fluid.id and changed.revision==selected.revision+1
    with pytest.raises(ValueError): service.select(changed,system_id=b.id,circuit_id=ca.id,fluid_id=fluid.id)
    clear=service.select(selected,system_id=None,circuit_id=ca.id,fluid_id=None)
    assert clear.system is clear.circuit is clear.fluid is None
    assert service.select(clear,system_id=None,circuit_id=None,fluid_id=None) is clear


def test_catalog_reads_are_cached_until_explicit_reload(catalogs,monkeypatch) -> None:
    service,systems,circuits,fluids,a,_,ca,_,fluid=catalogs
    saved=SystemContext(system=reference(a),circuit=reference(ca),fluid=reference(fluid))
    service.circuits(a.id);service.issues(saved)
    for repo,name in ((systems,'get_all'),(fluids,'get_all'),(circuits,'get_by_system'),(circuits,'get')):
        monkeypatch.setattr(repo,name,lambda *a,**k:pytest.fail('repeated redraw query'))
    for _ in range(5):
        service.systems();service.fluids();service.circuits(a.id)
        assert service.issues(saved)==()


def test_pipe_context_revision_and_applied_downstream_snapshots() -> None:
    ctx=context(fluid=ContextReference(id=uuid4(),code='FLUID',name_tr='Fluid'))
    first=contextualize_selection(source(),ctx)
    assert (first.system_id,first.circuit_id,first.fluid_id)==(ctx.system_id,None,ctx.fluid_id)
    assert contextualize_selection(source(),ctx,first).revision==first.revision
    state=PipeInputState().link_to(first)
    values=state.used_values
    next_context=context('OIL')
    second=contextualize_selection(source(),next_context,first)
    assert second.revision==first.revision+1 and second.selection_id==first.selection_id
    observed=state.observe(second)
    assert observed.used_values==values
    assert observed.used_values.system_id==ctx.system_id and observed.used_values.fluid_id==ctx.fluid_id
    assert first.flow_rate_m3_h==second.flow_rate_m3_h
    assert first.actual_internal_diameter_mm==second.actual_internal_diameter_mm
    discharge=DischargeHeadLossService(object()).calculate_v2(inputs(state))
    suction=SuctionNPSHService(object()).calculate_v2(suction_input(state),enpy_input())
    assert discharge.input.pipe_input.used_values==values
    assert suction.hydraulic.input.pipe_input.used_values==values


def test_transfer_future_calculations_receive_context_without_erasing_prior_results() -> None:
    page=transfer_page()
    page._design_panel.calculate()
    old=page._design_panel._last_result
    numeric={key:var.get() for key,var in page._design_panel._fields.items()}
    page.set_project_context(context())
    assert page._design_panel._last_result is old
    assert {key:var.get() for key,var in page._design_panel._fields.items()}==numeric
    page._design_panel.calculate()
    new=page._design_panel._last_result
    assert new.input.context.system_id==context().system_id
    assert new.required_flow_m3_h==old.required_flow_m3_h and new.transfer_time_h==old.transfer_time_h
    page._calculation_mode=TransferPumpMode.EMPIRICAL
    page._calculate()
    assert page._empirical_v2_result.input.context.system_id==context().system_id
    assert page._empirical_v2_result.estimate.predicted_pump_capacity_m3h==35


def test_pump_identity_does_not_inject_head_npsh_or_properties() -> None:
    existing=PumpIntegrationContext(required_head_m=123,available_npsh_m=9,required_npsh_m=7,npsh_margin_m=2)
    result=pump_context(existing,context('OIL'))
    assert (result.required_head_m,result.available_npsh_m,result.required_npsh_m,result.npsh_margin_m)==(123,9,7,2)
    assert not hasattr(result,'density_kg_m3')


def test_context_apply_changes_navigation_only_and_preserves_page_values() -> None:
    statuses={};notices=[];loaded=[];received=[]
    values={'ρ':850,'ν':2e-6,'Pb':3000,'roughness':.015,'c':1}
    window=SimpleNamespace(_system_context_service=SystemContextService(),_translate=Translator('tr').translate,
        _page_host=SimpleNamespace(set_page_enabled=lambda key,enabled:statuses.update({key:enabled})),
        _context_panel=SimpleNamespace(load=loaded.append,set_module_notice=notices.append),
        _transfer_pump_page=SimpleNamespace(set_project_context=received.append),inputs=values.copy())
    MainWindow._apply_system_context(window,context('FRESH_WATER'))
    assert window.inputs==values
    assert statuses['transfer_pump'] is False and statuses['pipe_design'] is True
    assert TR['context.module.fuel_only'] in notices[-1]
    MainWindow._apply_system_context(window,SystemContext())
    assert all(statuses.values()) and received[-1]==SystemContext()


def test_disabled_selected_tab_moves_without_destroying_it() -> None:
    states={'pipe':'normal','transfer':'normal'};selected=['transfer']
    def tab(key,option=None,**kwargs):
        if kwargs: states[key]=kwargs['state']
        return states[key]
    def select(key=None):
        if key is not None: selected[0]=key
        return selected[0]
    host=SimpleNamespace(_page_keys={'transfer_pump':'transfer'},select=select,tab=tab,tabs=lambda:('pipe','transfer'))
    ScrollablePageHost.set_page_enabled(host,'transfer_pump',False)
    assert selected[0]=='pipe' and states['transfer']=='disabled'
    ScrollablePageHost.set_page_enabled(host,'transfer_pump',True)
    assert states['transfer']=='normal' and selected[0]=='pipe'


def test_no_ui_sql_property_lookup_or_formula_edits() -> None:
    root=Path(__file__).parents[1]
    for relative in ('ui/widgets/system_context_panel.py','services/system_context_service.py','services/system_context_integration.py'):
        text=(root/relative).read_text(encoding='utf-8')
        assert 'import sqlite3' not in text and 'FluidPropertyRepository' not in text
    assert SystemContext.from_workspace({'schema_version':1})==SystemContext()


def panel_stub(service: SystemContextService) -> SystemContextPanel:
    """Run the actual selector callbacks with small display-independent controls."""
    panel=SystemContextPanel.__new__(SystemContextPanel)
    panel._service=service;panel._translate=Translator('tr').translate
    panel._context=SystemContext();panel._module_notice=''
    panel._events=[];panel._changed=panel._events.append
    panel._values={key:Var('') for key in ('system','circuit','fluid')}
    class Control:
        def __init__(self): self.options={}
        def configure(self,**kwargs): self.options.update(kwargs)
    panel._labels={key:Control() for key in panel._values}
    panel._selectors={key:Control() for key in panel._values}
    panel._status=Control();panel._choices={};panel.configure=lambda **kwargs:None
    panel.refresh_texts()
    return panel


def test_context_selector_real_callbacks_filter_clear_and_localize(catalogs) -> None:
    service,_,_,_,a,b,ca,cb,fluid=catalogs
    panel=panel_stub(service)
    def choose(field,identifier):
        panel._values[field].set(next(label for label,value in panel._choices[field].items() if value==identifier))
        panel._select()
    choose('system',a.id)
    assert panel._context.system_id==a.id and panel._context.circuit is None
    assert set(panel._choices['circuit'].values())=={None,ca.id}
    choose('circuit',ca.id);choose('fluid',fluid.id)
    choose('system',b.id)
    assert panel._context.circuit is None and panel._context.fluid_id==fluid.id
    assert set(panel._choices['circuit'].values())=={None,cb.id}
    choose('system',None);choose('fluid',None)
    assert panel._context.system is panel._context.circuit is panel._context.fluid is None
    assert TR['context.legacy'] in panel._status.options['text']
    assert panel._events
    panel._translate=Translator('en').translate
    panel.refresh_texts()
    assert panel._labels['system'].options['text']=='System'
    assert any('User fuel' in label for label in panel._choices['system'])


def test_selector_load_preserves_missing_ids_and_never_emits_edit(catalogs) -> None:
    service,_,_,_,a,_,ca,_,fluid=catalogs
    panel=panel_stub(service)
    saved=SystemContext(system=reference(a),circuit=replace(reference(ca),id=uuid4()),
                        fluid=replace(reference(fluid),id=uuid4()))
    panel.load(saved)
    assert panel._context==saved and panel._events==[]
    assert saved.circuit_id in panel._choices['circuit'].values()
    assert saved.fluid_id in panel._choices['fluid'].values()
    assert TR['context.source_missing'] in panel._status.options['text']


def test_published_pipe_receives_context_without_new_engineering_call(monkeypatch) -> None:
    import services.discharge_source_adapter as adapter
    from services.pipe_source_discovery import PipeSourceDiscovery
    calls=[]
    monkeypatch.setattr(adapter,'prepare_discharge_source',lambda *a,**k:calls.append((a,k)) or source())
    window=SimpleNamespace(_pipe_sources=PipeSourceDiscovery(),_pipe_design_service=object(),
                           _system_context=context('OIL'),_mark_workspace_dirty=lambda:None)
    identifier=MainWindow._publish_pipe_selection(window,{},True,None)
    published=window._pipe_sources.state.selections[0]
    assert identifier==published.selection_id and published.system_id==context('OIL').system_id
    assert len(calls)==1 and published.flow_rate_m3_h==source().flow_rate_m3_h


def test_window_context_export_load_clear_and_legacy_project_isolation() -> None:
    from services.pipe_source_discovery import PipeSourceDiscovery
    values=[]
    page=SimpleNamespace(load_state=lambda value:values.append(value),export_state=lambda:{'raw':'850'},clear_state=lambda:None)
    window=SimpleNamespace(_pages={'suction_npsh':page},_pipe_sources=PipeSourceDiscovery(),
        _system_context=context(),_system_context_service=SystemContextService(),_translate=Translator().translate)
    first={'schema_version':1,'system_context':context('OIL').to_payload(),'suction_npsh':{'raw':'123'}}
    MainWindow._load_all_page_states(window,first)
    assert window._system_context==context('OIL') and values[-1]=={'raw':'123'}
    assert SystemContext.from_workspace(MainWindow._export_all_page_states(window))==context('OIL')
    MainWindow._load_all_page_states(window,{'schema_version':1})
    assert window._system_context==SystemContext()
    MainWindow._load_all_page_states(window,first)
    MainWindow._clear_all_pages(window)
    assert window._system_context==SystemContext()
    count=len(values)
    with pytest.raises(ValidationError):
        MainWindow._load_all_page_states(window,{'schema_version':1,'system_context':{'version':99}})
    assert len(values)==count
