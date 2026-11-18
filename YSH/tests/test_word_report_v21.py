"""Focused editable Word report coverage for D243 V2.1."""
from io import BytesIO
from zipfile import ZipFile

from docx import Document

from reporting.models import adapt_snapshot
from reporting.word_renderer import render_word
from reporting.transfer_graph import frozen_transfer_graph
from reporting.word_export import default_word_filename,export_word
from reporting.word_presentation import ReportLanguage,basis_explanations
from i18n.translator import Translator
from .test_pdf_reports_phase18 import representative_snapshots
from .test_fire_phase4_snapshot_history_pdf import foam, hw
from .test_fire_phase3_hazen_williams_workflow import parameter as hw_parameter
from engineering.snapshots.fire import build_fire_snapshot
from engineering.fire.enums import FireSourceStatus


def _document(snapshot, language='tr'):
    report=adapt_snapshot(snapshot,language)
    data=render_word(report)
    with ZipFile(BytesIO(data)) as package:
        assert package.testzip() is None
        assert 'word/document.xml' in package.namelist()
    return report,Document(BytesIO(data)),data


def _all_text(document):
    parts=[p.text for p in document.paragraphs]
    for table in document.tables:
        parts.extend(cell.text for row in table.rows for cell in row.cells)
    return '\n'.join(parts)


def test_word_outputs_are_valid_editable_for_all_fuel_report_modes():
    snapshots=representative_snapshots()
    assert len(snapshots)==5
    for snapshot in snapshots:
        _report,document,_data=_document(snapshot)
        assert document.paragraphs
    _pipe_report,pipe_document,_=_document(snapshots[0])
    pipe_text=_all_text(pipe_document)
    assert 'Örnek Çalışma' in pipe_text and 'Deneme akışkanı' in pipe_text
    assert str(snapshots[0].snapshot_id) not in pipe_text
    empirical=next(s for s in snapshots if s.module_code.value=='transfer_pump' and s.stage=='empirical')
    report,document,data=_document(empirical)
    text=_all_text(document)
    assert 'Kapasite Girişi' in text and '250,00' in text
    assert report.transfer_graph and 'Referans Gemiler' in text
    assert 'Regresyon Denklemi' in text and 'Belirlilik Katsayısı' in text
    assert 'SOURCE_REQUIRED' not in text and 'Vfuel' not in text and 'Qpump' not in text
    with ZipFile(BytesIO(data)) as package:
        assert any(name.startswith('word/media/') for name in package.namelist())


def test_fire_word_outputs_and_turkish_statuses_are_localized():
    source_required=hw(hazen_williams_c=hw_parameter('hazen_williams_c',120,status=FireSourceStatus.SOURCE_REQUIRED))
    for snapshot in (build_fire_snapshot(foam()),build_fire_snapshot(source_required)):
        report,document,_data=_document(snapshot)
        assert report.module_code.startswith('fire_') and document.tables
        text=_all_text(document)
        assert 'SOURCE_REQUIRED' not in text and 'DERIVED_MIDPOINT' not in text
        if snapshot.module_code.value=='fire_hazen_williams':assert 'Kaynak Gerekli' in text
    _report,english,_data=_document(build_fire_snapshot(source_required),'en')
    english_text=_all_text(english)
    assert 'Source Required' in english_text and 'SOURCE_REQUIRED' not in english_text


def test_transfer_graph_reads_only_frozen_snapshot_facts():
    empirical=next(s for s in representative_snapshots() if s.module_code.value=='transfer_pump' and s.stage=='empirical')
    graph=frozen_transfer_graph(empirical)
    assert graph and graph.references
    assert graph.slope==empirical.evidence['facts']['calculation']['estimate']['regression_model']['slope']
    legacy=empirical.evidence
    legacy['facts']['calculation']['references']=[]
    from dataclasses import replace
    from engineering.snapshots.serialization import canonical
    old=replace(empirical,evidence_json=canonical(legacy))
    assert frozen_transfer_graph(old) is None


def test_word_english_strings_and_symbol_labels():
    snapshot=representative_snapshots()[2]
    _report,document,_data=_document(snapshot,'en')
    text=_all_text(document)
    assert 'Engineering Calculation Report' in text
    assert 'Source Required' not in text or 'SOURCE_REQUIRED' not in text
    assert 'Vfuel' not in text and 'Qpump' not in text


def test_localization_basis_explanation_old_report_and_collision_safe_export(tmp_path,monkeypatch):
    snapshot=representative_snapshots()[2]
    report,document,_data=_document(snapshot)
    assert 'Yakıt Kapasitesi' in _all_text(document)
    assert default_word_filename(report).endswith('.docx')
    target=tmp_path/default_word_filename(report)
    first=export_word(report,target);second=export_word(report,target)
    assert first.exists() and second.name!=first.name
    assert ZipFile(first).testzip() is None

    basis={'fluid':'NATO F-76','values':[{'reference':{'name':'NATO F-76','property_name':'density',
        'unit':'kg/m³','source_min':800,'source_max':876,'reference_temperature_c':15,
        'default_value':838,'default_method':'DERIVED_MIDPOINT','source_nominal':None},
        'used_value':850,'status':'OVERRIDE'}]}
    explanations=basis_explanations(basis,'tr')
    assert any('800,00–876,00' in row and '15,00' in row for row in explanations)
    assert any('orta değeri' in row and '838,00' in row for row in explanations)
    assert any('850,00' in row and 'manuel' in row.lower() for row in explanations)

    from dataclasses import replace
    old=replace(report,engineering_basis_json=None,transfer_graph=None)
    monkeypatch.setattr('reporting.models.adapt_snapshot',lambda *a,**k:(_ for _ in ()).throw(AssertionError('renderer called adapter')))
    assert render_word(old).startswith(b'PK')


def test_report_status_codes_are_localized_before_word_display():
    ui=ReportLanguage('tr')
    codes=('SOURCE_REQUIRED','DERIVED_MIDPOINT','LINKED_STALE','RECOMMENDED_RANGE','HARD_LIMIT','D243_CRITERION','PROJECT_LINKED','LIMITED_APPLICABILITY')
    cleaned=ui.text(' · '.join(codes))
    assert not any(code in cleaned for code in codes)


def test_primary_word_dialog_uses_docx_and_frozen_snapshot(monkeypatch,tmp_path):
    from ui.dialogs import word_report
    snapshot=representative_snapshots()[0];chosen=tmp_path/'Rapor.docx';messages=[]
    monkeypatch.setattr(word_report.filedialog,'asksaveasfilename',lambda **kwargs:(
        (assert_docx(kwargs['defaultextension'],kwargs['filetypes']),str(chosen))[1]))
    monkeypatch.setattr(word_report.messagebox,'showinfo',lambda *a,**k:messages.append(a))
    word_report.save_snapshot_word(None,snapshot,translate=Translator('tr').translate)
    assert chosen.exists() and ZipFile(chosen).testzip() is None
    assert messages and messages[0][0]=='Word Raporu Oluştur'


def assert_docx(extension,filetypes):
    assert extension=='.docx' and filetypes[0][1]=='*.docx'
