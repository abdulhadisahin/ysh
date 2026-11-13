"""Fire historical truth uses stored primitives; all current calculators may disappear."""
from dataclasses import FrozenInstanceError, replace
from io import BytesIO
import json
from types import SimpleNamespace
from uuid import UUID

import pytest
from pypdf import PdfReader

from engineering.fire.enums import FireSourceStatus, HWApplicability
from engineering.fire.hazen_williams_workflow import HWService
from engineering.module_registry import ModuleCode, MODULES
from engineering.snapshots.fire import build_fire_snapshot
from engineering.snapshots.models import CalculationSnapshot
from engineering.snapshots.serialization import canonical
from engineering.system_context import SystemContext, ContextReference
from i18n.translator import Translator
from reporting.models import adapt_snapshot, format_number
from reporting.renderer import render_pdf
from repositories.calculation_repository import CalculationRepository
from repositories.project_repository import ProjectRepository
from services.project_service import ProjectService
from services.snapshot_history_service import SnapshotHistoryService
from ui.dialogs.calculation_history import CalculationHistoryWindow
from ui.history_presentation import (MODULE_LABELS, primary_result, frozen_pipe, recorded_warnings,
                                    context_names, fire_details)
from ui.theme.formula_visuals import identity
from ui.theme.history_visuals import configure_history_visuals
from .test_fire_phase2_foam_workflow import request as foam_request, calculate as foam_calculate, parameter
from .test_fire_phase3_hazen_williams_workflow import request as hw_request, calculate as hw_calculate, linked, selection
from .test_history_visual_harmonization import selected_window, list_window, minimal
from .test_pipe_visual_pilot import Style


def context():
    return SystemContext(system=ContextReference(id=UUID(int=77),code='FIRE_TEST',name_tr='Donmuş Yangın ŞĞİıçöü'),
        fluid=ContextReference(id=UUID(int=78),code='TEST_WATER',name_tr='Kayıtlı su'))


def foam(override=False):
    extra={}
    if override:
        extra['foam_fraction']=parameter('foam_fraction',.06,'1',recommended=.03,
            reason='Project-selected approved concentrate')
    return foam_calculate(foam_request(context=context(),case_id=UUID(int=76),revision=3,**extra))


def hw(c=120,**kwargs):
    return hw_calculate(hw_request(c=c,context=context(),**kwargs))


@pytest.mark.parametrize('kind',['foam','hw'])
def test_snapshot_roundtrip_detached_full_evidence_and_steps(kind):
    workflow=foam() if kind=='foam' else hw()
    snapshot=build_fire_snapshot(workflow)
    restored=CalculationSnapshot.from_payload(json.loads(snapshot.to_json()))
    assert restored==snapshot and restored.schema_version==1
    assert restored.model_version==workflow.workflow_version
    payload=restored.evidence['facts']['fire']
    assert payload==workflow.snapshot_payload
    assert restored.formula_steps==workflow.formula_steps
    assert restored.context==context()
    assert payload['rule_ids'] and payload['provenance'] and payload['warnings']
    detached=workflow.snapshot_payload; detached['normalized_inputs'].clear()
    copy=snapshot.evidence; copy['facts']['fire']['results'].clear()
    assert restored.evidence['facts']['fire']['results']
    with pytest.raises(FrozenInstanceError): snapshot.model_version='changed'
    if kind=='foam':
        values=payload['results']
        assert [values[n]['value'] for n in ('solution_flow_lpm','foam_concentrate_flow_lpm',
            'water_flow_lpm','foam_concentrate_volume_l')]==[1050,31.5,1018.5,945]


def test_foam_override_used_recommended_reason_and_sources_survive_pdf():
    snapshot=build_fire_snapshot(foam(True))
    restored=CalculationSnapshot.from_payload(snapshot.to_payload())
    used=restored.formula_steps[1].used_values[0]
    assert used.recommended_value==.03 and used.used_value==.06
    assert used.override_reason=='Project-selected approved concentrate'
    assert used.source.document=='Explicit test criteria'
    assert restored.formula_steps[-1].result_value==1890
    report=adapt_snapshot(restored)
    assert report.results[-1].value==1890
    text='\n'.join(p.extract_text() for p in PdfReader(BytesIO(render_pdf(report))).pages)
    assert 'Project-selected approved concentrate' in text
    assert '3,00' in text and '6,00' in text and '1890,00' in text
    assert {row.value for row in report.selections if row.symbol=='Cfoam' and row.unit=='%'}>={3,6}


@pytest.mark.parametrize('c,expected',[(120,2.3717829024660286),(140,1.7832957445009588)])
def test_hw_workbook_snapshot_values(c,expected):
    snapshot=CalculationSnapshot.from_payload(build_fire_snapshot(hw(c)).to_payload())
    assert snapshot.formula_steps[-1].result_value==pytest.approx(expected,rel=1e-13)
    assert snapshot.evidence['facts']['fire']['results']['total_pressure_loss_bar']['value']==snapshot.formula_steps[-1].result_value
    assert primary_result(snapshot.module_code,snapshot.evidence).startswith('ΔpHW = ')


def test_linked_pipe_freeze_after_newer_external_selection():
    from engineering.fire.units import m3h_to_lpm
    from engineering.pipe_design.transfer import revise_selection
    original=selection()
    revised=revise_selection(original,replace(original,flow_rate_m3_h=180,
        selected_pipe=replace(original.selected_pipe,inside_diameter_mm=110)))
    state=linked().keep_current(revised)
    snapshot=build_fire_snapshot(hw(q=m3h_to_lpm(120),pipe_input=state,inside_diameter_mm=None))
    before=snapshot.to_json()
    next_state=state.update(revised)
    assert next_state.used_values.actual_internal_diameter_mm==110
    restored=CalculationSnapshot.from_payload(snapshot.to_payload())
    pipe=restored.evidence['facts']['fire']['pipe_selection']
    assert pipe['inside_diameter_used_mm']==105 and pipe['source_revision']==3
    assert pipe['values']['pipe_id']==str(UUID(int=2))
    assert pipe['status']=='LINKED_STALE' and pipe['kept_current']
    assert dict(frozen_pipe(restored.evidence))=={'mode':'LINKED','status':'LINKED_STALE','revision':3}
    assert before==restored.to_json()
    report=adapt_snapshot(restored)
    from i18n.translator import Translator
    assert any(row.value==Translator('tr').translate('fire.value.LINKED_STALE') for row in report.selections)


def test_source_required_is_not_upgraded_historically():
    from .test_fire_phase3_hazen_williams_workflow import parameter as hw_parameter
    result=hw(hazen_williams_c=hw_parameter('hazen_williams_c',120,status=FireSourceStatus.SOURCE_REQUIRED))
    snapshot=CalculationSnapshot.from_payload(build_fire_snapshot(result).to_payload())
    assert any(w['source_status']=='SOURCE_REQUIRED' for w in recorded_warnings(snapshot.evidence))
    report=adapt_snapshot(snapshot)
    assert any('SOURCE_REQUIRED' in w for w in report.warnings)
    assert any(r.symbol=='CHW' and r.value=='SOURCE_REQUIRED' for r in report.selections)
    assert 'REGULATORY_COMPLIANT' not in report.to_json()


@pytest.mark.parametrize('kind',['foam','hw'])
def test_history_persistence_list_selection_formula_pdf_without_any_recalculation(kind,project_database,monkeypatch):
    workflow=foam() if kind=='foam' else hw()
    project=ProjectService(ProjectRepository(project_database)).create_project('Fire history test')
    snapshot=build_fire_snapshot(workflow,project_id=project.id)
    history=SnapshotHistoryService(CalculationRepository(project_database));history.append(snapshot)
    def forbidden(*args,**kwargs):pytest.fail('Historical path queried current engineering data')
    import engineering.fire.calculators as calculators
    import services.fire_foam_service as fs
    import services.fire_hazen_williams_service as hs
    import engineering.formula.fire_foam as ff
    import engineering.formula.fire_hazen_williams as fh
    from services.engineering_library_service import EngineeringLibraryService
    from services.system_context_service import SystemContextService
    from engineering.pipe_design.transfer import PipeInputState
    for module,name in ((calculators,'calculate_foam_system'),(calculators,'calculate_hazen_williams'),
                        (fs,'calculate_foam_system'),(hs,'calculate_hazen_williams'),
                        (ff,'foam_steps'),(fh,'hazen_williams_steps')):
        monkeypatch.setattr(module,name,forbidden)
    monkeypatch.setattr(fs.FoamCalculationService,'calculate',forbidden)
    monkeypatch.setattr(hs.HazenWilliamsCalculationService,'calculate',forbidden)
    monkeypatch.setattr(EngineeringLibraryService,'details',forbidden)
    for method in ('reload','systems','fluids','circuits','issues','select','availability'):
        monkeypatch.setattr(SystemContextService,method,forbidden)
    monkeypatch.setattr(PipeInputState,'update',forbidden)
    monkeypatch.setattr(PipeInputState,'observe',forbidden)
    loaded=history.list(project.id)[0]
    assert loaded==snapshot
    owner=list_window((loaded,));CalculationHistoryWindow._render_list(owner)
    assert len(owner._tree.items)==1
    window,calls=selected_window(monkeypatch,loaded)
    panel=window._formula_panel.options
    assert panel['historical'] and panel['separate_window']
    assert panel['step_provider']()==workflow.formula_steps
    window._pdf_button.options['command']()
    assert calls[-1] is loaded
    assert render_pdf(adapt_snapshot(loaded)).startswith(b'%PDF-')
    assert context_names(loaded.evidence)[0]=='Donmuş Yangın ŞĞİıçöü'
    # Detached live-like edits cannot alter historical output.
    changed=loaded.evidence;changed['context']['system']['name_tr']='Current project'
    assert loaded.context.system.name_tr=='Donmuş Yangın ŞĞİıçöü'


@pytest.mark.parametrize('kind',['foam','hw'])
def test_history_filter_color_details_and_primary(kind):
    snapshot=build_fire_snapshot(foam() if kind=='foam' else hw())
    tr=Translator('tr').translate
    assert tr(MODULE_LABELS[snapshot.module_code]).startswith('Yangın — ')
    assert primary_result(snapshot.module_code,snapshot.evidence).startswith('Vfoam' if kind=='foam' else 'ΔpHW')
    owner=list_window((snapshot,))
    owner._module_choices['fire']=snapshot.module_code.value;owner._module.set('fire')
    CalculationHistoryWindow._render_list(owner)
    assert len(owner._tree.items)==1
    owner._module.set('pipe');CalculationHistoryWindow._render_list(owner)
    assert not owner._tree.items
    assert identity(snapshot.module_code)[1:4]==('#C65D4B','#963E32','#FFF2EE')
    style=Style();configure_history_visuals(style)
    assert style.configurations['History.'+snapshot.module_code+'.Result.TLabel']['foreground']=='#963E32'
    details='\n'.join(fire_details(snapshot.evidence,tr))
    assert 'İş akışı sürümü' not in details and 'USER_PROJECT_ASSUMPTION' not in details
    assert tr('fire.ui.source.USER_PROJECT_ASSUMPTION') in details
    assert snapshot.model_version  # retained in frozen record / technical diagnostics


@pytest.mark.parametrize('kind',['foam','hw'])
def test_real_pdf_searchable_turkish_frozen_results_metadata_and_a4(kind):
    snapshot=build_fire_snapshot(foam() if kind=='foam' else hw())
    report=adapt_snapshot(snapshot);before=snapshot.to_json()
    reader=PdfReader(BytesIO(render_pdf(report)))
    text='\n'.join(p.extract_text() for p in reader.pages)
    assert 'Yangın Söndürme' in text and 'Donmuş Yangın ŞĞİıçöü' in text
    assert ('Köpük Sistemi' if kind=='foam' else 'Hazen-Williams Basınç Kaybı') in text
    assert ('Gerekli Köpük Konsantresi Hacmi' if kind=='foam' else 'Toplam Basınç Kaybı') in text
    assert str(snapshot.snapshot_id) in text and snapshot.model_version in text
    assert 'USER_PROJECT_ASSUMPTION' in text
    for row in report.results:assert format_number(row.value) in text
    assert all(abs(float(p.mediabox.width)-595.2756)<.01 for p in reader.pages)
    assert 'None' not in text and 'null' not in text and 'head loss' not in text.lower()
    assert 'WORKFLOW' not in text
    assert snapshot.to_json()==before


@pytest.mark.parametrize('kind',['foam','hw'])
def test_missing_optional_metadata_safe_and_legacy_unchanged(kind,monkeypatch):
    snapshot=build_fire_snapshot(foam() if kind=='foam' else hw())
    evidence=snapshot.evidence;fire=evidence['facts']['fire']
    for name in ('provenance','case_id','pipe_selection','context','warnings'):
        fire.pop(name,None)
    evidence['context']={}
    snapshot=replace(snapshot,evidence_json=canonical(evidence))
    window,_=selected_window(monkeypatch,snapshot)
    assert window._formula_panel.options['step_provider']()==snapshot.formula_steps
    report=adapt_snapshot(snapshot)
    assert 'None' not in report.to_json()
    assert render_pdf(report).startswith(b'%PDF-')
    old=minimal();assert CalculationSnapshot.from_payload(old.to_payload())==old
    assert adapt_snapshot(old).formulas==old.formula_steps


def test_nozzle_and_unsupported_hw_cannot_be_adapted_or_registered():
    from engineering.fire.models import NozzleRequest
    with pytest.raises(TypeError):build_fire_snapshot(NozzleRequest())
    with pytest.raises(ValueError):ModuleCode('fire_nozzle')
    result=hw()
    with pytest.raises(ValueError):build_fire_snapshot(replace(result,service=HWService.SEAWATER))
    with pytest.raises(ValueError):build_fire_snapshot(replace(result,applicability=HWApplicability.SEAWATER_SOURCE_REQUIRED))
    assert len(MODULES)==4  # historical identities never add live pages


def test_snapshot_adaptation_has_no_file_or_network_io(monkeypatch):
    result=hw()
    def forbidden(*args,**kwargs):pytest.fail('Snapshot adaptation attempted I/O')
    with monkeypatch.context() as guard:
        guard.setattr('builtins.open',forbidden);guard.setattr('io.open',forbidden)
        guard.setattr('socket.create_connection',forbidden)
        snapshot=build_fire_snapshot(result)
        assert primary_result(snapshot.module_code,snapshot.evidence)


def test_original_workflow_replacement_does_not_change_snapshot():
    result=foam();snapshot=build_fire_snapshot(result);before=snapshot.to_json()
    changed=replace(result,domain_result=replace(result.domain_result,foam_concentrate_volume_l=0))
    assert changed.domain_result.foam_concentrate_volume_l==0
    assert snapshot.to_json()==before
