"""Professional report presentation consumes frozen evidence across Fuel and Fire."""
from dataclasses import replace
from io import BytesIO
from uuid import UUID
import pytest
from pypdf import PdfReader

from reporting.context import freeze_report_context
from reporting.models import adapt_snapshot, ReportWarning, ReportSource
from reporting.renderer import render_pdf
from engineering.snapshots.models import CalculationSnapshot
from engineering.formula.models import ordered_steps
from engineering.snapshots.serialization import canonical
from .test_pdf_reports_phase18 import representative_snapshots
from .test_fire_phase4_snapshot_history_pdf import foam, hw
from engineering.snapshots.fire import build_fire_snapshot


@pytest.fixture(scope='module')
def report_snapshots():
    return representative_snapshots() + (build_fire_snapshot(foam()),build_fire_snapshot(hw()))


def text_of(report):
    return '\n'.join(page.extract_text() for page in PdfReader(BytesIO(render_pdf(report))).pages)


@pytest.mark.parametrize('index',range(7))
@pytest.mark.parametrize('language',['tr','en'])
def test_shared_report_hierarchy_identity_primary_inputs_and_sources(report_snapshots,index,language):
    from i18n.translator import Translator
    tr = Translator(language).translate
    snapshot = replace(report_snapshots[index],project_id=UUID(int=2021))
    before = snapshot.to_json()
    family = 'fire' if index >= 5 else 'fuel'
    frozen = freeze_report_context(snapshot,project_name='Frozen Example Project',system_family=family)
    report = adapt_snapshot(frozen,language)
    assert report.project_name == 'Frozen Example Project' and report.system_family == family
    assert report.language == language and report.primary_result in report.results
    symbol = ('s','Qgerekli','Qpump','Hs','ENPYm','Vfoam','Δp')[index]
    if index != 6: assert report.primary_result.symbol == symbol
    else: assert report.primary_result.value == report_snapshots[index].evidence['facts']['fire']['results']['total_pressure_loss_bar']['value']
    assert report.inputs and all(row.unit or isinstance(row.value,(float,int,str)) for row in report.inputs)
    assert all(row.source for row in report.inputs)
    assert report.formulas == ordered_steps(frozen.formula_steps)
    text = text_of(report)
    assert report.project_name in text and report.module.upper() in text
    assert tr('project.family.'+family) in text
    for key in ('title','context','inputs','primary','supporting','steps','warnings','provenance','approval'):
        assert tr('report.'+key) in text
    for key in ('prepared','checked','approved','name','date','signature'):
        assert tr('report.'+key) in text
    assert 'Page 1 /' in text if language=='en' else 'Sayfa 1 /' in text
    assert snapshot.to_json() == before


def test_identity_freeze_never_changes_existing_history_or_accepts_wrong_family(report_snapshots):
    snapshot = replace(report_snapshots[1],project_id=UUID(int=12))
    before = snapshot.to_json()
    frozen = freeze_report_context(snapshot,project_name='Original',system_family='fuel')
    assert frozen.snapshot_id == snapshot.snapshot_id and frozen.formula_steps == snapshot.formula_steps
    assert freeze_report_context(frozen,project_name='Renamed').to_json() == frozen.to_json()
    assert snapshot.to_json() == before and 'report_context' not in snapshot.evidence
    assert adapt_snapshot(snapshot).project_name is None
    with pytest.raises(ValueError,match='family'):
        freeze_report_context(snapshot,system_family='fire')
    bad = frozen.evidence;bad['report_context']['system_family']='fire'
    with pytest.raises(ValueError,match='family'):
        adapt_snapshot(replace(frozen,evidence_json=canonical(bad)))


def test_frozen_warning_taxonomy_and_source_required_without_live_center(report_snapshots,monkeypatch):
    snapshot = report_snapshots[0]
    evidence = snapshot.evidence
    evidence['findings'] = [{'code':'d243.pipe.velocity_max','severity':'ENGINEERING_WARNING',
        'message_key':'pipe.warning.d243_velocity_max','upper_bound':7,'actual_value':99,
        'lower_bound':None,'context':{'criterion':'D243'},'source_id':None,'unit':'m/s'}]
    frozen = replace(snapshot,evidence_json=canonical(evidence))
    report = adapt_snapshot(frozen,'en')
    assert any(w.severity=='WARNING' and '7.00' in w.message.replace(',','.') and 'D243' in w.message for w in report.warning_items)
    from .test_fire_phase3_hazen_williams_workflow import parameter as hw_parameter
    from engineering.fire.enums import FireSourceStatus
    unresolved = hw(hazen_williams_c=hw_parameter('hazen_williams_c',120,status=FireSourceStatus.SOURCE_REQUIRED))
    fire = adapt_snapshot(build_fire_snapshot(unresolved),'en')
    assert any(w.severity=='SOURCE_REQUIRED' for w in fire.warning_items)
    from engineering.pipe_design.v2_calculator import PipeDesignV2Calculator
    from services.fire_hazen_williams_service import HazenWilliamsCalculationService
    from repositories.material_repository import MaterialRepository
    def forbidden(*args,**kwargs): raise AssertionError('Reporting must not calculate or query live data')
    monkeypatch.setattr(PipeDesignV2Calculator,'calculate',forbidden)
    monkeypatch.setattr(HazenWilliamsCalculationService,'calculate',forbidden)
    monkeypatch.setattr(MaterialRepository,'get_all',forbidden)
    expected = render_pdf(report)
    detached = frozen.evidence;detached['findings'].clear();detached['facts'].clear()
    assert render_pdf(adapt_snapshot(CalculationSnapshot.from_payload(frozen.to_payload()),'en')) == expected
    assert 'SOURCE_REQUIRED' in text_of(fire)


def test_multipage_headers_page_totals_and_blank_approval(report_snapshots):
    report = adapt_snapshot(report_snapshots[1],'en')
    long = replace(report,inputs=report.inputs*35,
        sources=(ReportSource((('Notes','Frozen long source note '*1000),)),),warning_items=())
    reader = PdfReader(BytesIO(render_pdf(long)))
    pages = [page.extract_text() for page in reader.pages]
    assert len(pages)>4 and all(len(page)>50 for page in pages)
    for index,page in enumerate(pages,1): assert f'Page {index} / {len(pages)}' in page
    assert sum('Parameter' in page for page in pages)>2
    approval_pages = [page for page in pages if 'Prepared by' in page]
    assert len(approval_pages)==1
    assert '8. Approval / Signatures' in approval_pages[0]
    assert all(label in approval_pages[0] for label in ('Checked by','Approved by','Name','Date','Signature'))
    assert 'No active engineering warnings were recorded' in '\n'.join(pages)
    assert 'Approved Engineer' not in '\n'.join(pages)


def test_ui_capture_freezes_project_identity_without_reconstructing_history(report_snapshots):
    from types import SimpleNamespace
    from ui.main_window import MainWindow
    snapshot = replace(report_snapshots[1],project_id=UUID(int=22))
    project = SimpleNamespace(id=snapshot.project_id,name='Calculation-time name')
    window = SimpleNamespace(_active_project=project,
        _project_persistence_service=SimpleNamespace(active_system_family='fuel'))
    frozen = MainWindow._freeze_report_identity(window,snapshot)
    project.name='Later name'
    assert adapt_snapshot(frozen).project_name=='Calculation-time name'
    assert frozen.formula_steps==snapshot.formula_steps


def test_info_only_report_does_not_claim_external_compliance(report_snapshots):
    report = replace(adapt_snapshot(report_snapshots[1],'en'),
        warning_items=(ReportWarning('INFO','Recorded information'),))
    text = text_of(report)
    assert 'Recorded information' in text
    assert 'No active engineering warnings were recorded for this calculation.' in text
    assert 'fully compliant' not in text.lower()


def test_fire_current_and_history_export_share_the_same_frozen_identity(report_snapshots):
    from types import SimpleNamespace as NS
    from ui.pages.fire_workspace_page import FireCalculatorPage
    snapshot = replace(report_snapshots[5],project_id=UUID(int=55))
    persisted = []
    model = NS(set_context=lambda context:None, snapshots={'foam':snapshot},
               calculate=lambda kind,project_id:object())
    workspace = NS(context_provider=lambda:snapshot.context,project_provider=lambda:snapshot.project_id,
        prepare_snapshot=lambda record:freeze_report_context(record,project_name='Frozen Fire Project',system_family='fire'),
        on_snapshot=persisted.append)
    view = NS(model=model,workspace=workspace,kind='foam',entries={},
        library_panel=NS(refresh=lambda:None),sync=lambda:None,
        after_idle=lambda action:None,_reveal_primary_result=lambda:None)
    FireCalculatorPage.calculate(view)
    assert len(persisted)==1 and model.snapshots['foam'] is persisted[0]
    assert adapt_snapshot(persisted[0]).project_name=='Frozen Fire Project'
    assert persisted[0].formula_steps==snapshot.formula_steps


@pytest.mark.parametrize('language',['tr','en'])
def test_report_export_success_uses_localized_line_break(language):
    from i18n.translator import Translator
    message = Translator(language).translate('report.export_success',path='report.pdf')
    assert '\nreport.pdf' in message
    assert '\\n' not in message
