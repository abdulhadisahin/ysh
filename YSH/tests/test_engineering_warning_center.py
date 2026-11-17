"""Warning Center projections never calculate, resolve sources or mutate workspaces."""
from types import SimpleNamespace as NS
from uuid import uuid4

import pytest

from services.engineering_warning_center import (
    EngineeringWarning as W, ModuleWarningState as M, WarningStatus as S, aggregate_warnings,
)
from ui.warning_center_state import collect_warning_summary
from i18n.translator import Translator
from .test_fire_phase5cd_navigation import application, shell
from ._tk_geometry import settle_geometry


@pytest.mark.parametrize('family,allowed,other', [('fuel','pipe_design','foam'), ('fire','foam','pipe_design')])
def test_aggregation_family_filter_and_counts(family, allowed, other):
    items = tuple(W(allowed, status, status.value) for status in S)
    summary = aggregate_warnings(family, (M(allowed, items + items, 2), M(other, (W(other,S.ERROR,'bad'),),9)))
    assert len(summary.items) == 8
    assert summary.completed_count == 2
    assert (summary.info_count, summary.warning_count, summary.source_required_count,
            summary.stale_count, summary.error_count) == (1,1,1,1,4)
    assert all(item.module_id == allowed for item in summary.items)
    assert not aggregate_warnings(None, (M(allowed, items, 1),)).items


def test_empty_aggregation():
    summary = aggregate_warnings('fuel', ())
    assert summary.items == () and summary.completed_count == 0
    assert summary.error_count == summary.warning_count == summary.source_required_count == summary.stale_count == 0


def fail(*args, **kwargs):
    raise AssertionError('Warning Center must not calculate or resolve external data')


def fire_shell():
    from services.fire_workspace import FireWorkspace
    model = FireWorkspace()
    views = NS(created={})
    workspace = NS(model=model, views=views, sources=NS(available=fail))
    window = NS(_active_project=object(), _locked_project_family=lambda:'fire',
                _translate=Translator('en').translate, _fire_workspace=workspace,
                _pages=NS(), _snapshot_history=NS(list=fail), _library_service_factory=fail)
    return window, model


def test_fire_current_sources_stale_errors_and_info_are_not_reinterpreted():
    window, model = fire_shell()
    model.calculate = fail
    model.fields['hw']['hazen_williams_c'] = '120'
    model.library_inputs.stale['hazen_williams_c'] = True
    window._fire_workspace.views.created['hw'] = NS(_center_message='fire.ui.blocked')
    model.results['foam'] = NS(warnings=(NS(category=S.INFO,field_name='a',message_key='fire.foam.source.USER_PROJECT_ASSUMPTION'),))
    before = model.export_state()
    summary = collect_warning_summary(window)
    assert summary.source_required_count == 1
    assert any(item.source == window._translate('fire.hw.c') for item in summary.items if item.severity == S.SOURCE_REQUIRED)
    assert summary.stale_count == 1
    assert summary.error_count == 1
    assert summary.info_count == 1 and summary.warning_count == 0
    assert summary.completed_count == 1
    assert any(item.severity == S.BLOCKED for item in summary.items)
    assert model.export_state() == before
    model.invalidate('foam')
    assert collect_warning_summary(window).completed_count == 0


def test_no_project_or_blank_fire_has_no_synthetic_warning():
    window, model = fire_shell()
    assert not collect_warning_summary(window).items
    window._active_project = None
    window._fire_workspace = NS(model=NS())
    assert not collect_warning_summary(window).items


def test_fuel_current_link_and_superseded_result_do_not_read_history():
    pipe = NS(mode=NS(value='LINKED'), status=NS(value='LINKED_STALE'))
    page = NS(_workflow=NS(pipe_input=pipe), _pdf_snapshot=object())
    window = NS(_active_project=object(), _locked_project_family=lambda:'fuel',
                _translate=Translator('en').translate, _pages={'discharge_head_loss':page},
                _fire_workspace=NS(model=NS()), _snapshot_history=NS(list=fail))
    summary = collect_warning_summary(window)
    assert summary.stale_count == 2
    assert {item.code for item in summary.items} == {'pipe:LINKED_STALE', 'superseded_result'}
    page._last_result = NS(warnings=())
    assert collect_warning_summary(window).stale_count == 1


@pytest.mark.parametrize('family', ['fuel', 'fire'])
@pytest.mark.parametrize('size', [(1100,700), (1440,900)])
def test_real_project_center_is_readonly_localized_and_family_isolated(shell, family, size):
    w = shell
    w._root.deiconify()
    w._root.geometry(f'{size[0]}x{size[1]}')
    assert w._create_project('Warning Center '+str(uuid4()), '', '', family)
    if family == 'fire':
        model = w._fire_workspace.model
        model.fields['hw']['hazen_williams_c'] = '120'
        model.library_inputs.stale['hazen_williams_c'] = True
    before = w._export_all_page_states()
    dirty = w._project_persistence_service.is_dirty
    w._open_warning_center()
    dialog = w._warning_center_dialog
    settle_geometry(w._root, w._project_family_indicator, w._warning_center_button)
    summary = w._refresh_warning_center()
    if family == 'fuel':
        assert summary.items == ()
        assert dialog.empty['text'] == w._translate('center.empty')
    else:
        assert summary.source_required_count == 1 and summary.stale_count == 1
        assert all(item.module_id in ('foam','hw') for item in summary.items)
    assert dialog.tree.get_children() or not summary.items
    assert w._export_all_page_states() == before
    assert w._project_persistence_service.is_dirty == dirty
    original = w._translate
    try:
        for lang in ('tr','en'):
            w._translate = Translator(lang).translate
            w._refresh_family_selector()
            assert dialog.window.title() == w._translate('center.title')
            assert 'center.' not in dialog.summary['text']
    finally:
        w._translate = original
        w._refresh_family_selector()
    button = w._warning_center_button
    assert button.winfo_rootx()+button.winfo_width() <= w._root.winfo_rootx()+w._root.winfo_width()
    other = 'fire' if family == 'fuel' else 'fuel'
    w._show_family(other)
    assert w._family == family
    dialog.window.destroy()


def test_fire_calculation_attempt_status_is_existing_ui_status(shell):
    w = shell
    assert w._create_project('Blocked '+str(uuid4()), '', '', 'fire')
    view = w._fire_workspace.views['hw']
    view.calculate()  # Existing UNKNOWN applicability blocker, no new rule.
    summary = collect_warning_summary(w)
    assert any(item.severity == S.BLOCKED and item.message_key == 'fire.ui.blocked' for item in summary.items)
    view._dirty()
    assert not any(item.severity == S.BLOCKED for item in collect_warning_summary(w).items)


def test_existing_fuel_findings_and_validation_keep_severity_and_message():
    from engineering.warning_rules import WarningSeverity
    panel = NS(findings=(NS(code='npsh.test', severity=WarningSeverity.CRITICAL_WARNING),),
               _message=lambda finding:'Existing advisory with its source')
    page = NS(_warning_panel=panel, _center_error_text='Existing validation',
              _message=NS(get=lambda:'Existing validation'))
    window = NS(_active_project=object(), _locked_project_family=lambda:'fuel',
                _translate=Translator('en').translate, _pages={'pipe_design':page})
    summary = collect_warning_summary(window)
    assert summary.warning_count == 1 and summary.error_count == 1
    assert summary.items[0].detail == 'Existing advisory with its source'
    page._message = NS(get=lambda:'Ready')
    assert collect_warning_summary(window).error_count == 0


def test_existing_transfer_capacity_status_is_warning_not_error():
    result = NS(status=NS(value='PUMP_CAPACITY_BELOW_REQUIRED'))
    page = NS(_design_panel=NS(_last_result=result))
    window = NS(_active_project=object(), _locked_project_family=lambda:'fuel',
                _translate=Translator('en').translate, _pages={'transfer_pump':page})
    summary = collect_warning_summary(window)
    assert summary.warning_count == 1 and summary.error_count == 0 and summary.completed_count == 1
    result.status.value = 'NO_SELECTED_PUMP'
    summary = collect_warning_summary(window)
    assert summary.info_count == 1 and summary.warning_count == 0


def test_actual_pipe_validation_is_visible_and_clears_after_edit(shell):
    w = shell
    assert w._create_project('Invalid Pipe '+str(uuid4()), '', '', 'fuel')
    page = w._pipe_design_page
    page._fields['q'].set('bad')
    page._calculate_diameter()
    assert any(item.code == 'pipe_validation' and item.severity == S.ERROR
               for item in collect_warning_summary(w).items)
    page._fields['q'].set('25')
    assert not any(item.code == 'pipe_validation' for item in collect_warning_summary(w).items)
