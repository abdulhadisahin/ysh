"""D243 maximum velocity and summary-driven project alert regressions."""
from uuid import uuid4
import pytest

from engineering.pipe_design.rules import evaluate_fuel_velocity_criterion, fuel_velocity_criterion
from services.engineering_warning_center import EngineeringWarning, ModuleWarningState, aggregate_warnings, WarningStatus
from ui.warning_center_state import collect_warning_summary
from i18n.translator import Translator
from .test_fire_phase5cd_navigation import application, shell
from ._tk_geometry import settle_geometry


@pytest.mark.parametrize('velocity,expected', [(2,False),(7,False),(7.01,True),(99,True)])
def test_existing_d243_criterion_is_advisory(velocity, expected):
    findings = evaluate_fuel_velocity_criterion(velocity)
    assert bool(findings) == expected
    if findings:
        finding = findings[0]
        assert finding.upper_bound == fuel_velocity_criterion().used_value
        assert finding.severity.value == 'ENGINEERING_WARNING'
        assert not finding.blocks_calculation
        assert finding.source_id is None and finding.context == {'criterion':'D243'}


@pytest.mark.parametrize('velocity', ['2','7','7.01','99'])
def test_actual_pipe_warning_reaches_center_and_correction_clears_it(shell, velocity):
    w = shell
    assert w._create_project('Velocity '+str(uuid4()), '', '', 'fuel')
    page = w._pipe_design_page
    page._select_pipe_standard(None)
    page._fields['q'].set('25')
    page._fields['v'].set(velocity)
    page._calculate_diameter()
    assert page._diameter_result  # This remains a successful calculation.
    before = w._export_all_page_states()
    summary = w._refresh_warning_center()
    matches = [i for i in summary.items if i.code == 'd243.pipe.velocity_max']
    assert bool(matches) == (float(velocity) > 7)
    if matches:
        assert matches[0].severity == (WarningStatus.CRITICAL if float(velocity)==99 else WarningStatus.WARNING)
        assert matches[0].module_id == 'pipe_design'
        assert summary.warning_count + summary.error_count >= 1
        assert 'D243' in matches[0].detail and '7' in matches[0].detail
        assert 'Türk Loydu' not in matches[0].detail
        w._open_warning_center()
        rows = w._warning_center_dialog.tree.get_children()
        assert any('D243' in str(w._warning_center_dialog.tree.item(row,'values')) for row in rows)
        w._warning_center_dialog.window.destroy()
        assert not hasattr(w,'_warning_center_alert')
        assert page._warning_panel.grid_info()
        assert any(f.code=='d243.pipe.velocity_max' for f in page._warning_panel.findings)
    assert w._export_all_page_states() == before
    original = w._translate
    try:
        for lang in ('tr','en'):
            page._translate = Translator(lang).translate
            page._warning_panel._translate = page._translate
            w._translate = page._translate
            message = collect_warning_summary(w)
            if matches:
                detail = next(i.detail for i in message.items if i.code == 'd243.pipe.velocity_max')
                assert ('Akış hızı' if lang == 'tr' else 'Flow velocity') in detail
    finally:
        page._translate = original
        page._warning_panel._translate = original
        w._translate = original
    page._fields['v'].set('7')
    page._calculate_diameter()
    assert page._diameter_result
    summary = w._refresh_warning_center()
    assert not any(i.code == 'd243.pipe.velocity_max' for i in summary.items)
    assert not any(f.code == 'd243.pipe.velocity_max' for f in page._warning_panel.findings)
    assert not hasattr(w,'_warning_center_alert')


@pytest.mark.parametrize('status', [None, *WarningStatus])
def test_removed_header_indicators_do_not_change_warning_details(shell, monkeypatch, status):
    import ui.warning_center_state as projection
    w=shell
    assert w._create_project('Warning details '+str(uuid4()),'','','fuel')
    items=() if status is None else (EngineeringWarning('pipe_design',status,'test','center.review'),)
    summary=aggregate_warnings('fuel',(ModuleWarningState('pipe_design',items),))
    monkeypatch.setattr(projection,'collect_warning_summary',lambda window:summary)
    before=w._export_all_page_states()
    assert w._refresh_warning_center()==summary
    assert not hasattr(w,'_warning_center_button') and not hasattr(w,'_warning_center_alert')
    w._open_warning_center()
    assert w._warning_center_dialog.window.winfo_exists()
    assert len(w._warning_center_dialog.tree.get_children())==len(items)
    assert w._export_all_page_states()==before
    w._warning_center_dialog.window.destroy()


@pytest.mark.parametrize('size', [(1100,700),(1440,900)])
@pytest.mark.parametrize('active',[False,True])
def test_header_has_no_warning_controls_or_reserved_space(shell,size,active):
    from ui.theme.spacing import SM
    w=shell;w._root.deiconify();w._root.geometry(f'{size[0]}x{size[1]}')
    if active:
        assert w._create_project('Header layout '+str(uuid4()),'','','fuel')
        page=w._pipe_design_page
        page._fields['q'].set('25');page._fields['v'].set('99');page._calculate_diameter()
    w._refresh_family_selector();w._root.update()
    assert not hasattr(w,'_warning_center_button') and not hasattr(w,'_warning_center_alert')
    strip=w._project_status_strip
    assert strip.winfo_children()==[w._project_family_indicator]
    for column in (1,2):
        assert strip.grid_slaves(row=0,column=column)==[]
        assert strip.grid_columnconfigure(column)['minsize']==0
        assert strip.grid_columnconfigure(column)['pad']==0
    if active:
        settle_geometry(w._root,w._project_family_indicator)
        assert w._project_family_indicator.winfo_rootx()==strip.winfo_rootx()+SM
        assert w._page_host.winfo_rootx()==strip.winfo_rootx()
        assert w._active_project.name in w._project_family_indicator['text']
        assert w._translate('project.family.fuel') in w._project_family_indicator['text']
    else:
        assert not strip.grid_info()
        assert w._page_host.winfo_y()==0
