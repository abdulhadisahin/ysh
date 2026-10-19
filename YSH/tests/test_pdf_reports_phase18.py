"""Phase 18 verifies real searchable reports from all five frozen calculation variants."""
from dataclasses import replace
from io import BytesIO
from pathlib import Path
import json
import sys
from uuid import UUID

import pytest
from pypdf import PdfReader

from engineering.module_registry import ModuleCode
from engineering.pipe_design.transfer import PipeInputState
from engineering.pipe_design.v2_calculator import PipeDesignV2Calculator
from engineering.snapshots.builders import build_snapshot, build_pipe_v2_snapshot
from engineering.snapshots.models import CalculationSnapshot
from engineering.system_context import ContextReference, SystemContext
from engineering.transfer_pump.v2_models import TransferPumpDesignInput, TransferPumpEmpiricalInput
from reporting.models import adapt_snapshot, format_number
from reporting.renderer import render_pdf
from reporting.export import default_filename, export_pdf
from services.discharge_head_loss_service import DischargeHeadLossService
from services.suction_npsh_service import SuctionNPSHService
from .test_pipe_design_v2 import request, candidate
from .test_engineering_library_phase13 import library
from .test_discharge_v2_phase8 import inputs
from .test_suction_v2_phase9 import suction_input, enpy_input
from .test_transfer_pump_v2_phase10 import service


def representative_snapshots() -> tuple[CalculationSnapshot, ...]:
    """Use synthetic engineering fixtures and named frozen Turkish context."""
    context = SystemContext(system=ContextReference(id=UUID(int=1), code='TEST', name_tr='Örnek Çalışma ŞĞİıçöü'),
                            fluid=ContextReference(id=UUID(int=2), code='TEST', name_tr='Deneme akışkanı'))
    used = request(bend_allowance_enabled=False)
    pipe = PipeDesignV2Calculator().calculate(used, [candidate(od=110, wall=4, inside=101)])
    linked = PipeInputState().link_to(pipe)
    transfer = service()
    return (build_pipe_v2_snapshot(pipe, used, context=context),) + tuple(
        build_snapshot(module, stage, result, context=context)
        for module, stage, result in (
            (ModuleCode.TRANSFER_PUMP, 'design', transfer.calculate_v2(TransferPumpDesignInput(
                transfer_volume_m3=120.123456789, target_transfer_time_h=3, selected_pump_capacity_m3_h=45))),
            (ModuleCode.TRANSFER_PUMP, 'empirical', transfer.calculate_v2(TransferPumpEmpiricalInput(source_capacity=250))),
            (ModuleCode.DISCHARGE, 'hydraulics', DischargeHeadLossService(object()).calculate_v2(inputs(linked))),
            (ModuleCode.SUCTION_NPSH, 'enpy', SuctionNPSHService(object()).calculate_v2(suction_input(linked), enpy_input()))))


@pytest.fixture(scope='module')
def snapshots():
    return representative_snapshots()


@pytest.mark.parametrize('index', range(5))
def test_pdf_structure_text_metadata_and_fidelity(snapshots, index):
    snapshot = snapshots[index]
    before = snapshot.to_json()
    report = adapt_snapshot(snapshot)
    data = render_pdf(report)
    assert data.startswith(b'%PDF-')
    reader = PdfReader(BytesIO(data))
    text = '\n'.join(page.extract_text() for page in reader.pages)
    assert report.module.upper() in text
    assert report.snapshot_id in text
    from i18n.translator import Translator
    first_title = Translator('tr').translate(report.formulas[0].title_key)
    for page in reader.pages:
        page_text = page.extract_text()
        if '4. Hesap Adımları' in page_text:
            assert first_title in page_text
    assert 'Örnek Çalışma ŞĞİıçöü' in text and 'None' not in text
    assert reader.metadata.title.startswith('D243')
    assert reader.metadata.author == 'D243'
    assert reader.metadata.creator.startswith('D243')
    assert 'Kaynaklar ve Doğrulama' in text and 'Sonuçlar' in text
    assert 'C:\\' not in text and '.venv' not in str(reader.metadata)
    assert all(abs(float(p.mediabox.width)-595.2756) < .01 for p in reader.pages)
    assert [r.value for r in report.results] == [s.result_value for s in report.formulas]
    assert snapshot.to_json() == before
    assert json.loads(report.to_json())['results'][0]['value'] == report.results[0].value
    for result in report.results:
        assert format_number(result.value) in text
    if index == 0:
        assert 'Bükme yok' in text and snapshot.evidence['facts']['selection']['status'] in text
    if index == 2:
        assert 'AMPİRİK / REFERANS GEMİ TAHMİNİ' in text
    if index in (3, 4):
        assert 'Bağlı' in text and 'Kaynak boru revizyonu' in text


def test_frozen_copy_and_library_project_mutation_isolation(snapshots, monkeypatch):
    snapshot = snapshots[0]
    report = adapt_snapshot(snapshot)
    expected = render_pdf(report)
    detached = snapshot.evidence
    detached['context']['system']['name_tr'] = 'Changed live project'
    detached['facts'].clear()
    def forbidden(*args, **kwargs):
        pytest.fail('PDF generation called a live calculator or repository')
    from repositories.material_repository import MaterialRepository
    monkeypatch.setattr(MaterialRepository, 'get_all', forbidden, raising=False)
    monkeypatch.setattr(PipeDesignV2Calculator, 'calculate', forbidden)
    assert adapt_snapshot(CalculationSnapshot.from_payload(snapshot.to_payload())) == report
    assert render_pdf(adapt_snapshot(snapshot)) == expected


def test_exclusive_file_creation_invalid_path_and_no_overwrite(tmp_path, snapshots):
    report = adapt_snapshot(snapshots[1])
    first = export_pdf(report, tmp_path/'test.pdf')
    before = first.read_bytes()
    second = export_pdf(report, first)
    assert second.name == 'test_1.pdf' and first.read_bytes() == before
    with pytest.raises(OSError):
        export_pdf(report, tmp_path/'missing'/'test.pdf')
    assert not list(tmp_path.glob('*.tmp'))
    assert not any(c in default_filename(report) for c in '<>:"/\\|?*')


def test_native_cancel_no_snapshot_and_write_failure(monkeypatch, snapshots):
    from ui.dialogs import pdf_report
    calls=[]
    monkeypatch.setattr(pdf_report.messagebox, 'showinfo', lambda *a, **k: calls.append('info'))
    monkeypatch.setattr(pdf_report.messagebox, 'showerror', lambda *a, **k: calls.append('error'))
    monkeypatch.setattr(pdf_report.filedialog, 'asksaveasfilename', lambda **k: '')
    pdf_report.save_snapshot_pdf(None, snapshots[0])
    assert calls == []
    pdf_report.save_snapshot_pdf(None, None)
    assert calls == ['info']
    monkeypatch.setattr(pdf_report.filedialog, 'asksaveasfilename', lambda **k: 'invalid/path/report.pdf')
    pdf_report.save_snapshot_pdf(None, snapshots[0])
    assert calls[-1] == 'error'


def test_headless_subprocess_does_not_import_tk(tmp_path, snapshots):
    import subprocess
    payload = tmp_path/'snapshot.json'; payload.write_text(snapshots[1].to_json(), encoding='utf-8')
    code = """import sys,json
from engineering.snapshots.models import CalculationSnapshot
from reporting.models import adapt_snapshot
from reporting.renderer import render_pdf
from pathlib import Path
snapshot=CalculationSnapshot.from_payload(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')))
assert render_pdf(adapt_snapshot(snapshot)).startswith(b'%PDF-')
assert 'tkinter' not in sys.modules
"""
    import os
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).parents[1]))
    subprocess.run([sys.executable, '-c', code, str(payload)], check=True, env=env, capture_output=True)


def test_multi_page_tables_repeat_headers_without_empty_pages(snapshots):
    report=adapt_snapshot(snapshots[1])
    long=replace(report, inputs=report.inputs*30)
    text=[p.extract_text() for p in PdfReader(BytesIO(render_pdf(long))).pages]
    assert len(text) >= 5 and all(len(p)>50 for p in text)
    assert sum('Parametre' in p for p in text) > 2


def test_formula_quarantine_and_fallback_contract(snapshots, monkeypatch):
    import reporting.renderer as renderer
    seen=[]
    original=renderer.formula_asset_path
    monkeypatch.setattr(renderer, 'formula_asset_path', lambda key: (seen.append(key), original(key))[1])
    render_pdf(adapt_snapshot(snapshots[0]));render_pdf(adapt_snapshot(snapshots[3]))
    assert 'base_wall_thickness' not in seen and 'local_loss' not in seen
    monkeypatch.setattr(renderer, 'formula_asset_path', lambda key: None)
    assert render_pdf(adapt_snapshot(snapshots[0])).startswith(b'%PDF-')


def test_persisted_pdf_survives_actual_library_and_project_changes(project_database, library):
    """Live SQLite source/material/project edits cannot replace frozen report evidence."""
    from services.snapshot_history_service import SnapshotHistoryService
    from repositories.calculation_repository import CalculationRepository
    from repositories.project_repository import ProjectRepository
    from services.project_service import ProjectService
    from engineering.provenance import EngineeringValue, OverridePolicy
    from engineering.pipe_design.v2_models import PipeProvenance
    lib, rows = library
    projects = ProjectService(ProjectRepository(project_database))
    project = projects.create_project('Original project')
    src = rows['sources'].reference
    velocity = EngineeringValue(used_value=2, recommended_value=1.5, unit='m/s', source=src,
        symbol='V', override_policy=OverridePolicy.SUGGESTED, override_reason='Frozen override reason')
    used = request(provenance=PipeProvenance(design_velocity=velocity))
    result = PipeDesignV2Calculator().calculate(used, [candidate(dimension_source=src)])
    context = SystemContext(system=ContextReference(id=UUID(int=1), code='TEST', name_tr='Frozen system'))
    snapshot = build_pipe_v2_snapshot(result, used, context=context, project_id=project.id)
    history = SnapshotHistoryService(CalculationRepository(project_database)); history.append(snapshot)
    expected = render_pdf(adapt_snapshot(snapshot))
    values = lib.form_values('sources', rows['sources'])
    values.update(document='Changed source', revision='NEW', source_organization='Changed organization')
    lib.save('sources', values, rows['sources'].id)
    values = lib.form_values('materials', rows['materials']); values['roughness_mm'] = 999
    lib.save('materials', values, rows['materials'].id)
    project.name = 'Changed live project'; projects.update_project(project)
    historical = history.list(project.id)[0]
    assert render_pdf(adapt_snapshot(historical)) == expected
    text = ''.join(p.extract_text() for p in PdfReader(BytesIO(expected)).pages)
    assert 'Frozen override reason' in text and '1,50' in text and '2,00' in text
    assert 'USER_SUPPLIED' in text and 'Changed source' not in text
    assert 'Frozen system' in text and 'Changed live project' not in text


def test_long_provenance_splits_and_local_paths_are_redacted(snapshots):
    from reporting.models import ReportSource
    report = adapt_snapshot(snapshots[1])
    long = replace(report, sources=(ReportSource((('Notlar', 'Uzun kaynak açıklaması ' * 1000),
                                                  ('Dosya', r'C:\PrivateUser\secret.db'))),))
    data = render_pdf(long)
    text = '\n'.join(p.extract_text() for p in PdfReader(BytesIO(data)).pages)
    assert 'Uzun kaynak açıklaması' in text
    assert 'PrivateUser' not in text and 'secret.db' not in text


def test_readonly_collision_preserves_original(tmp_path, snapshots):
    import stat
    target = tmp_path/'readonly.pdf'; target.write_bytes(b'preserve')
    target.chmod(stat.S_IREAD)
    try:
        output = export_pdf(adapt_snapshot(snapshots[1]), target)
        assert output.name == 'readonly_1.pdf' and target.read_bytes() == b'preserve'
    finally:
        target.chmod(stat.S_IREAD | stat.S_IWRITE)
