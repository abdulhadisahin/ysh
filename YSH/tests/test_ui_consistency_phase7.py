"""Presentation contracts across the composed Fuel/Fire application; no screenshots."""
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest

from i18n.translator import Translator
from ui.main_window import MainWindow
from ui.widgets.cards import SectionHeader, ResultMetric
from ui.widgets.scrollable_frame import ScrollableFrame
from ui.widgets.formula_steps import step_sections
from ui.history_presentation import fire_details
from ui.theme import typography, colors
from ui.theme.spacing import CARD_PADDING, CONTROL_PADDING
from .test_fire_phase5cd_navigation import application, shell
from .test_fire_phase5_live_ui import fill_view
from .test_fire_phase6_library import library, record
from .test_history_visual_harmonization import snapshots


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def review_language(window, language):
    # The accepted V1 product manager deliberately pins TR. Exercise the actual
    # EN catalogue/controls without changing that production language policy.
    window._localization._translator.set_language(language)
    window._refresh_all_localized_ui()


def assert_horizontal_bounds(widgets, canvas):
    left = canvas.winfo_rootx(); right = left+canvas.winfo_width()
    for widget in widgets:
        if widget.winfo_ismapped() and widget.winfo_class() in ('TEntry','TCombobox','TButton','TLabel'):
            assert widget.winfo_rootx() >= left-2, (str(widget), 'left')
            assert widget.winfo_rootx()+widget.winfo_width() <= right+2, (str(widget), widget.cget('text') if widget.winfo_class()=='TLabel' else '', 'right')


@pytest.mark.parametrize('language', ['tr','en'])
@pytest.mark.parametrize('size', [(1100,700),(1280,800),(1440,900),(1700,1000)])
def test_all_calculation_pages_geometry_and_scroll(shell, language, size):
    w=shell; root=w._root; previous=w._localization.language
    try:
        review_language(w,language)
        root.deiconify(); root.geometry(f'{size[0]}x{size[1]}'); root.update()
        sidebar=w._sidebar.winfo_rootx()+w._sidebar.winfo_width()
        for family in ('fuel','fire'):
            w._show_family(family,dirty=False); root.update()
            host=w._page_host if family=='fuel' else w._fire_workspace.host
            for key, viewport in host._page_keys.items():
                host.select(viewport); root.update()
                page=w._pages[key] if family=='fuel' else w._fire_workspace.views[key]
                if key in ('discharge_head_loss','suction_npsh'):
                    from .test_discharge_v2_phase8 import source
                    from engineering.pipe_design.transfer import revise_selection
                    panel=page._pipe_source_panel; workflow=panel.workflow
                    selection=replace(source(),selection_id=uuid4()); workflow.publish(selection); workflow.link(selection.selection_id)
                    workflow.publish(revise_selection(selection,replace(selection,flow_rate_m3_h=selection.flow_rate_m3_h+1)))
                    panel.render(); root.update()
                canvas=viewport.canvas
                assert canvas.winfo_rootx()>=sidebar
                assert canvas.winfo_width()>400 and canvas.winfo_height()>150
                assert_horizontal_bounds(descendants(page),canvas)
                assert host._active_host()._wheel_active
                assert all(not other._wheel_active for other in host._hosts.values() if other is not viewport)
                canvas.yview_moveto(0); root.update()
                top=canvas.yview()
                viewport.scroll_mousewheel(SimpleNamespace(delta=-120))
                root.update(); assert canvas.yview()[0]>=top[0]
                canvas.yview_moveto(1); root.update()
                assert canvas.yview()[1]>=.99
                canvas.yview_moveto(0)
        assert w._sidebar.winfo_rootx()+w._sidebar.winfo_width()==sidebar
    finally:
        w._localization.set_language(previous)


@pytest.mark.parametrize('language', ['tr','en'])
@pytest.mark.parametrize('size', [(1100,700),(1280,800),(1440,900),(1700,1000)])
def test_shared_windows_geometry_without_recalculation(shell, language, size):
    w=shell; root=w._root; previous=w._localization.language
    windows=[]
    try:
        review_language(w,language); root.deiconify(); root.geometry(f'{size[0]}x{size[1]}'); root.update()
        w._open_engineering_library('fire_foam_rate'); library_window=w._library_window; windows.append(library_window)
        library_window.geometry(f'{size[0]}x{size[1]}'); library_window._new(); root.update()
        assert library_window._navigation.exists('group:fire:foam')
        assert not {'system_family','system_type'} & library_window._edit_vars.keys()
        assert_horizontal_bounds(descendants(library_window._body),library_window._detail_scroll.canvas)
        w.unregister_localizable(library_window); library_window.destroy(); windows.remove(library_window)
        w._open_calculation_history(); history=w._history_window; windows.append(history)
        history.geometry(f'{size[0]}x{size[1]}'); root.update()
        assert history._tree.winfo_width()>200
        # A frozen record supplies formula content; live engineering providers are not used.
        snapshot=snapshots()[1]; before=snapshot.to_json()
        history._rows={str(snapshot.snapshot_id):snapshot}; history._selected_id=str(snapshot.snapshot_id)
        history._render_selected(); root.update()
        from ui.widgets.detail_disclosure import DetailDisclosure
        diagnostics=next(child for child in descendants(history._body) if isinstance(child,DetailDisclosure)
                         and child._title==w._translate('history.visual.diagnostics'))
        assert not diagnostics.expanded
        assert all(str(snapshot.snapshot_id) not in str(widget.cget('text')) for widget in descendants(history._body)
                   if widget.winfo_class()=='TLabel' and widget.winfo_ismapped())
        panel=history._formula_panel; panel.toggle(); dialog=panel._dialog; windows.append(dialog)
        dialog.geometry(f'{size[0]}x{size[1]}'); root.update()
        assert panel._scroll_host.canvas.winfo_width()>400
        assert panel._scroll_host.canvas.winfo_height()>150
        assert_horizontal_bounds(descendants(panel._content),panel._scroll_host.canvas)
        panel._scroll_host.canvas.yview_moveto(1); root.update()
        assert panel._scroll_host.canvas.yview()[1]>=.99
        assert snapshot.to_json()==before
        panel._close_dialog(); windows.remove(dialog)
    finally:
        for window in reversed(windows):
            if window.winfo_exists():
                w.unregister_localizable(window); window.destroy()
        w._localization.set_language(previous)


def test_shared_typography_control_padding_and_warning_semantics(shell):
    from tkinter import ttk
    w=shell; w._show_family('fire',dirty=False); view=w._fire_workspace.views['foam']
    style=ttk.Style(w._root)
    for prefix in ('Fire','Transfer','Discharge','Suction','Pipe'):
        actual=tuple(int(value) for value in style.lookup(prefix+'.TEntry','padding'))
        assert actual==CONTROL_PADDING
    for name in ('PipePageTitle.TLabel','TransferPageTitle.TLabel','DischargePageTitle.TLabel','SuctionPageTitle.TLabel','Fire.Title.TLabel'):
        from tkinter import font
        face=font.Font(root=w._root,font=style.lookup(name,'font'))
        assert face.actual('size')==typography.PAGE_TITLE[1]
    assert all(entry.cget('style')=='Fire.TEntry' for entry in view.entries.values())
    assert view.calculate_button.cget('style')=='Fire.Primary.TButton'
    assert all(button.cget('style')=='Fire.Secondary.TButton' for buttons in view.library_panel.buttons.values() for button in buttons.values())
    assert style.lookup('Fire.Secondary.TButton','background')==colors.WHITE
    for key,prefix in (('discharge_head_loss','Discharge'),('suction_npsh','Suction')):
        assert all(button.cget('style')==prefix+'Secondary.TButton' for button in w._pages[key]._pipe_source_panel._buttons.values())
    view.sync(); assert view.status.cget('style')=='Fire.Info.TLabel'
    view.calculate(); assert view.status.cget('style')=='Fire.Error.TLabel'
    assert style.lookup('Fire.Status.TLabel','background')==colors.WARNING_SURFACE
    assert style.lookup('Fire.Error.TLabel','background')==colors.ERROR_SURFACE
    assert style.lookup('Fire.Info.TLabel','background')==colors.INFO_SURFACE


def test_pdf_action_follows_exact_current_result_and_language(shell):
    w=shell; page=w._pages['transfer_pump']; panel=page._design_panel; root=w._root
    page._show_calculation_mode()  # accepted default design workflow
    panel._fields['volume'].set('120'); panel._fields['target_time'].set('3')
    panel.calculate(); root.update()
    snapshot=page._pdf_snapshot
    assert snapshot is not None and page._pdf_button.instate(['!disabled'])
    assert MainWindow._pdf_is_current(page)
    before=snapshot.to_json()
    panel._fields['target_time'].set('4'); root.update()
    assert page._pdf_button.instate(['disabled'])
    assert not MainWindow._pdf_is_current(page)
    assert snapshot.to_json()==before and page._pdf_snapshot is snapshot
    for language in ('tr','en'):
        review_language(w,language); root.update()
        assert page._pdf_button.cget('text')==Translator(language).translate('action.pdf_current_result')
    panel.calculate(); root.update()
    assert page._pdf_button.instate(['!disabled']) and MainWindow._pdf_is_current(page)
    panel.clear(); root.update(); assert page._pdf_button.instate(['disabled'])


@pytest.mark.parametrize('page_key', ['discharge_head_loss','suction_npsh'])
def test_pipe_link_actions_are_contextual_and_preserve_values(shell,page_key):
    from .test_discharge_v2_phase8 import source
    from engineering.pipe_design.transfer import revise_selection
    w=shell; page=w._pages[page_key]; panel=page._pipe_source_panel; workflow=panel.workflow
    workflow.manual(); panel.render()
    assert all(not button.grid_info() for button in panel._buttons.values())
    selection=replace(source(),selection_id=uuid4()); workflow.publish(selection); workflow.link(selection.selection_id); panel.render()
    assert all(not button.grid_info() for button in panel._buttons.values())
    old=workflow.pipe_input.snapshot
    updated=revise_selection(selection,replace(selection,flow_rate_m3_h=selection.flow_rate_m3_h+1))
    workflow.publish(updated); panel.render()
    assert all(button.grid_info() for button in panel._buttons.values())
    assert panel._status_label.cget('style')=='StatusWarning.TLabel'
    workflow.keep_current(); panel.render()
    assert workflow.pipe_input.snapshot is old
    workflow.update(); panel.render()
    assert all(not button.grid_info() for button in panel._buttons.values())


@pytest.mark.parametrize('language', ['tr','en'])
def test_fire_library_identity_is_diagnostic_and_history_status_localized(library,language):
    from services.fire_workspace import FireWorkspace
    from .test_fire_phase5_live_ui import foam
    service,_=library; item=record(library); draft=FireWorkspace(); foam(draft)
    draft.set_library_context('foam','TEST_ONLY'); draft.link_library('foam','application_density_lpm_m2',item)
    result=draft.calculate('foam'); snapshot=draft.snapshots['foam']; before=snapshot.to_json()
    tr=Translator(language).translate
    sections=[section for step in result.formula_steps for section in step_sections(step,tr)]
    assert all(str(item.id) not in section.text for section in sections if not section.details)
    assert any(str(item.id) in str(section.rows) for section in sections if section.key=='technical_details' and section.details)
    rows=fire_details(snapshot.evidence,tr)
    assert any(tr('fire.ui.source.'+item.source_status.value) in row for row in rows)
    assert all(item.source_status.value not in row for row in rows)
    assert snapshot.to_json()==before


def test_wrapped_metric_keeps_exact_value_unit_and_severity(shell):
    import tkinter as tk
    root=shell._root; root.deiconify()
    value=tk.StringVar(root,value='123456,789')
    metric=ResultMetric(root,'Uzun mühendislik sonucu / Long engineering result',value,'m³/h')
    metric.place(x=320,y=200,width=220,height=160)
    try:
        root.update()
        assert int(metric._label.cget('wraplength'))>0
        assert int(metric._value.cget('wraplength'))>0
        assert value.get()=='123456,789' and metric._unit_label.cget('text')=='m³/h'
        for width in (220,500):
            metric.place_configure(width=width); root.update()
            gap=metric._unit_label.winfo_rootx()-(metric._value.winfo_rootx()+metric._value.winfo_width())
            assert 0<=gap<=12  # unit stays beside the value, not at the far card edge
        metric.set_state('warning')
        assert metric._value.cget('style')=='WarningResultMetricValue.TLabel'
        assert value.get()=='123456,789'
    finally:
        metric.destroy()


def test_pdf_partial_stage_cannot_export_another_stale_stage():
    snapshot=snapshots()[0]
    page=SimpleNamespace(_pdf_snapshot=snapshot,_formula_steps=lambda:snapshot.formula_steps[:1])
    assert len(snapshot.formula_steps)>1
    assert not MainWindow._pdf_is_current(page)
    page._formula_steps=lambda:snapshot.formula_steps
    assert MainWindow._pdf_is_current(page)
    page._pdf_snapshot=SimpleNamespace(formula_steps=())
    assert not MainWindow._pdf_is_current(page)


@pytest.mark.parametrize('language',['tr','en'])
def test_pdf_action_uses_one_caption_across_fuel_fire_and_history(language):
    tr=Translator(language).translate
    assert tr('action.pdf_current_result')==tr('fire.ui.pdf')==tr('history.visual.pdf')
