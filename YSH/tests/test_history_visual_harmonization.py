"""Frozen-history presentation contracts without live reconstruction or pixel assertions."""
from dataclasses import replace
from types import SimpleNamespace
from pathlib import Path
from uuid import uuid4

import pytest

from engineering.module_registry import ModuleCode
from engineering.snapshots.builders import build_snapshot
from engineering.snapshots.models import CalculationSnapshot
from engineering.snapshots.serialization import canonical
from engineering.formula.models import FormulaStep
from engineering.transfer_pump.v2_models import TransferPumpDesignInput, TransferPumpEmpiricalInput
from engineering.pipe_design.models import PipeDesignCalculationResult, WallThicknessInput
from engineering.pipe_design.calculator import PipeDesignCalculator
from services.suction_npsh_service import SuctionNPSHService
from ui.dialogs.calculation_history import CalculationHistoryWindow, history_summary
from ui.history_presentation import (primary_result, context_names, frozen_pipe, recorded_checks,
    recorded_warnings, recorded_state, scalar, timestamp)
from ui.theme.history_visuals import configure_history_visuals
from ui.theme.pipe_pilot import MODULE_ACCENTS
from i18n.translator import Translator
from i18n.messages_tr import MESSAGES as TR
from i18n.messages_en import MESSAGES as EN
from .test_pipe_visual_pilot import Style
from .test_calculation_snapshots_phase14 import discharge_snapshot, context
from .test_suction_v2_phase9 import suction_input, enpy_input
from .test_transfer_pump_v2_phase10 import service
from .test_discharge_v2_phase8 import source
from engineering.pipe_design.transfer import PipeInputState

ROOT=Path(__file__).parents[1]


def snapshots():
    value=WallThicknessInput(110,16,195,1.8,.85,1)
    wall=PipeDesignCalculationResult(wall_thickness=PipeDesignCalculator().calculate_wall_thickness(value),trace={'wall_input':value.to_dict()})
    transfer=service()
    return (
        build_snapshot(ModuleCode.PIPE_DESIGN,'wall',wall,context=context()),
        build_snapshot(ModuleCode.TRANSFER_PUMP,'design',transfer.calculate_v2(TransferPumpDesignInput(transfer_volume_m3=120,target_transfer_time_h=3)),context=context()),
        build_snapshot(ModuleCode.TRANSFER_PUMP,'empirical',transfer.calculate_v2(TransferPumpEmpiricalInput(source_capacity=250)),context=context()),
        discharge_snapshot(state=PipeInputState().link_to(source()))[0],
        build_snapshot(ModuleCode.SUCTION_NPSH,'enpy',SuctionNPSHService(object()).calculate_v2(suction_input(),enpy_input()),context=context()),
    )


class Widget:
    def __init__(self,parent=None,**kwargs):
        self.parent=parent;self.children=[];self.options=kwargs
        if isinstance(parent,Widget):parent.children.append(self)
    def grid(self,**kwargs):self.grid_options=kwargs
    def columnconfigure(self,*args,**kwargs):pass
    def configure(self,**kwargs):self.options.update(kwargs)
    def winfo_children(self):return tuple(self.children)
    def destroy(self):
        if isinstance(self.parent,Widget):self.parent.children.remove(self)


def selected_window(monkeypatch,snapshot):
    import ui.dialogs.calculation_history as view
    import ui.dialogs.pdf_report as pdf
    for name in ('Label','LabelFrame','Frame','Button'):monkeypatch.setattr(view.ttk,name,Widget)
    class Disclosure(Widget):
        def __init__(self,parent,*args,**kwargs):super().__init__(parent,**kwargs);self.body=Widget(self)
    class Formula(Widget):
        def __init__(self,parent,*args,**kwargs):super().__init__(parent,**kwargs)
    monkeypatch.setattr(view,'DetailDisclosure',Disclosure);monkeypatch.setattr(view,'FormulaReferencePanel',Formula)
    calls=[];monkeypatch.setattr(pdf,'save_snapshot_pdf',lambda parent,value:calls.append(value))
    window=CalculationHistoryWindow.__new__(CalculationHistoryWindow)
    window._body=Widget();window._actions=Widget();window._translate=Translator('tr').translate
    window._rows={str(snapshot.snapshot_id):snapshot};window._selected_id=str(snapshot.snapshot_id)
    window._raw=lambda data,row:calls.append(('raw',data))
    window._render_selected()
    return window,calls


@pytest.mark.parametrize('index',range(5))
def test_each_module_renders_frozen_summary_formula_and_pdf_without_calculation(monkeypatch,index):
    snapshot=snapshots()[index];before=snapshot.to_json()
    import services.engineering_library_service as library
    from services.discharge_head_loss_service import DischargeHeadLossService
    def forbidden(*args,**kwargs):raise AssertionError('Historical rendering cannot resolve or calculate')
    monkeypatch.setattr(library.EngineeringLibraryService,'details',forbidden)
    monkeypatch.setattr(DischargeHeadLossService,'calculate_v2',forbidden)
    monkeypatch.setattr(PipeDesignCalculator,'calculate_wall_thickness',forbidden)
    monkeypatch.setattr(SuctionNPSHService,'calculate_v2',forbidden)
    window,calls=selected_window(monkeypatch,snapshot)
    assert window._formula_panel.options['historical'] is True
    assert window._formula_panel.options['separate_window'] is True
    assert window._formula_panel.options['module_key']==snapshot.module_code.value
    assert window._formula_panel.options['step_provider']()==snapshot.formula_steps
    window._pdf_button.options['command']()
    assert calls[-1] is snapshot and snapshot.to_json()==before
    assert primary_result(snapshot.module_code,snapshot.evidence)!='—'


def test_frozen_context_pipe_revision_and_state_are_not_current_values():
    snapshot=snapshots()[3];before=snapshot.to_json()
    names=context_names(snapshot.evidence)
    assert names[0]==snapshot.context.system.name_tr
    pipe=dict(frozen_pipe(snapshot.evidence))
    assert pipe['mode']=='LINKED' and pipe['revision']==1
    assert snapshot.to_json()==before


def minimal():
    step=FormulaStep(step_id='old',title_key='formula2.result',formula_text='x',result_value=0,result_unit='',result_symbol='x',display_order=0)
    from dataclasses import asdict
    return CalculationSnapshot(module_code=ModuleCode.PIPE_DESIGN,stage='old',model_version='OLDER_TEST',
        evidence_json=canonical({'facts':{'old':True},'steps':[asdict(step)],'context':{},'summary':[]}))


def test_minimal_snapshot_keeps_placeholders_and_does_not_invent_status(monkeypatch):
    snapshot=minimal();window,calls=selected_window(monkeypatch,snapshot)
    assert history_summary(snapshot)==primary_result(snapshot.module_code,snapshot.evidence)=='—'
    assert context_names(snapshot.evidence)==('—','—','—')
    assert recorded_checks(snapshot.evidence)==() and recorded_warnings(snapshot.evidence)==()
    assert recorded_state(snapshot.evidence,Translator('tr').translate)=='—'
    assert window._formula_panel.options['step_provider']()==snapshot.formula_steps


@pytest.mark.parametrize('value,result',[(None,'—'),({},'—'),([],'—'),('', '—'),(0,'0,00'),(False,'False')])
def test_optional_display_values_are_safe(value,result):
    assert scalar(value)==result


def test_warnings_and_status_are_taken_from_recorded_payload(monkeypatch):
    evidence={'steps':[{'check':{'status':'WARNING'}}],'findings':[{'severity':'CRITICAL_WARNING','code':'recorded'}],
              'facts':{'outputs':{'warnings':[{'code':'old_warning'}]},'calculation':{'warnings':['Frozen old warning']}}}
    assert recorded_state(evidence,Translator('tr').translate)==TR['formula2.check.WARNING']
    assert len(recorded_warnings(evidence))==3
    assert recorded_warnings(evidence)[-1]['recorded_text']=='Frozen old warning'
    assert recorded_warnings({})==()
    snapshot=minimal();data=snapshot.evidence;data['facts']=evidence['facts']
    snapshot=replace(snapshot,evidence_json=canonical(data))
    window,calls=selected_window(monkeypatch,snapshot)
    def labels(widget):
        return [child.options.get('text') for child in widget.children]+[text for child in widget.children for text in labels(child)]
    assert 'Frozen old warning' in labels(window._body)


def test_history_scoped_styles_module_identity_and_localization():
    style=Style();configure_history_visuals(style)
    assert all(name.startswith('History') for name in style.configurations|style.maps)
    assert len(MODULE_ACCENTS)==4
    assert style.configurations['History.Treeview']['rowheight']==32
    assert 'selected' in str(style.maps['History.Treeview'])
    denylist=('Calculation History','Read Only','Snapshot','Search','Filter','Warning','Result')
    for key in (key for key in TR if key.startswith('history.visual.')):
        assert EN[key] and not any(word in TR[key] for word in denylist)
    source=(ROOT/'ui/dialogs/calculation_history.py').read_text(encoding='utf-8')
    assert 'History.Primary.TButton' in source and 'History.Secondary.TButton' in source
    assert 'watermark' not in source.lower()
    assert not any(word in source for word in ('calculate_v2','delete_snapshot','update_snapshot','EngineeringLibraryService'))


def test_timestamp_preserves_existing_local_conversion_and_explicit_offset():
    snapshot=minimal();text=timestamp(snapshot.created_at)
    assert text==snapshot.created_at.astimezone().strftime('%d.%m.%Y · %H:%M:%S %z')


def list_window(records):
    class Variable:
        def __init__(self,value=''):self.value=value
        def get(self):return self.value
        def set(self,value):self.value=value
    class Tree:
        def __init__(self):self.items={}
        def get_children(self):return tuple(self.items)
        def delete(self,key):self.items.pop(key)
        def insert(self,*args,**kwargs):self.items[kwargs['iid']]=kwargs
        def selection_set(self,key):self.selected=key
    class Empty(Widget):
        def place(self,**kwargs):self.visible=True
        def place_forget(self):self.visible=False
    owner=SimpleNamespace(_rows={str(s.snapshot_id):s for s in records},_legacy={},_display={},
        _selected_id=None,_tree=Tree(),_empty=Empty(),_count=Variable(),_search=Variable(),
        _module=Variable('all'),_module_choices={'all':None,'pipe':'pipe_design','discharge':'discharge_head_loss'},
        _translate=Translator('tr').translate,_render_selected=lambda:None)
    owner._row=lambda key,snapshot:CalculationHistoryWindow._row(owner,key,snapshot)
    return owner


def test_list_search_module_filter_and_empty_states_use_loaded_records_only():
    records=snapshots();owner=list_window(records)
    CalculationHistoryWindow._render_list(owner)
    assert len(owner._tree.items)==5 and owner._count.get()=='5 kayıt'
    owner._module.set('pipe');CalculationHistoryWindow._render_list(owner)
    assert len(owner._tree.items)==1
    owner._search.set('no matching frozen row');CalculationHistoryWindow._render_list(owner)
    assert not owner._tree.items and owner._empty.visible
    assert owner._empty.options['text']==TR['history.visual.no_results']
    owner=list_window(());CalculationHistoryWindow._render_list(owner)
    assert owner._empty.options['text']==TR['history.visual.empty']


def test_legacy_timestamp_keeps_stored_offset_without_invented_context():
    snapshot=minimal();owner=list_window(())
    owner._legacy={'old':SimpleNamespace(created_at=snapshot.created_at,calculation_type='pipe_design')}
    CalculationHistoryWindow._render_list(owner)
    values=owner._tree.items['legacy:old']['values']
    assert values[0]==snapshot.created_at.strftime('%d.%m.%Y · %H:%M:%S %z')
    assert values[2:5]==('—','—','—')


@pytest.mark.parametrize('count',[100,500,1000])
def test_large_lists_never_decode_formula_panels_and_reuse_row_cache(monkeypatch,count):
    base=minimal();records=tuple(replace(base,snapshot_id=uuid4()) for _ in range(count))
    original=CalculationSnapshot.evidence.fget;reads=[]
    def evidence(snapshot):reads.append(snapshot.snapshot_id);return original(snapshot)
    def forbidden(snapshot):raise AssertionError('A list must not decode Formula View steps')
    monkeypatch.setattr(CalculationSnapshot,'evidence',property(evidence))
    monkeypatch.setattr(CalculationSnapshot,'formula_steps',property(forbidden))
    owner=list_window(records);CalculationHistoryWindow._render_list(owner)
    assert len(owner._tree.items)==count and len(reads)==count
    CalculationHistoryWindow._render_list(owner)
    assert len(reads)==count
