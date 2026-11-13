"""Corrective lifecycle tests; visual acceptance is not inferred from these tests."""
import pytest
from services.fire_workspace import FireWorkspace
from .test_fire_phase5_live_ui import live, fill_view


def test_only_initial_subview_is_constructed_and_refresh_is_passive(live):
    root,page,saved,tr=live
    assert set(page.views.created)=={'foam'}
    initial=page.views['foam']
    page.observe();page.refresh_texts();page.export_state()
    root.update_idletasks()
    assert set(page.views.created)=={'foam'}
    assert page.views['foam'] is initial


def test_selection_creates_hw_once_and_caches_both_views(live):
    root,page,saved,tr=live
    page.host.select(page.host._page_keys['hw']);root.update()
    assert set(page.views.created)=={'foam','hw'}
    first=page.views['hw']
    for _ in range(3):
        page.host.select(page.host._page_keys['foam']);root.update()
        page.host.select(page.host._page_keys['hw']);root.update()
    assert page.views['hw'] is first


def test_state_for_uncreated_view_is_preserved_and_language_changes_apply_later(live):
    from i18n.translator import Translator
    root,page,saved,tr=live
    page.model.fields['hw']['hazen_williams_c']='120'
    state=page.export_state()
    assert set(page.views.created)=={'foam'}
    page.load_state(state)
    assert set(page.views.created)=={'foam'}
    page.tr=Translator('en').translate
    for view in page.views.created.values():view.tr=page.tr
    page.refresh_texts()
    hw=page.views['hw']
    assert hw.variables['hazen_williams_c'].get()=='120'
    assert hw.calculate_button._logical_text=='Calculate'
    assert hw.calculate_button['text'].strip()=='Calculate'


def test_saved_hw_subview_can_be_first_without_creating_foam(live):
    import tkinter as tk
    from ui.pages.fire_workspace_page import FireWorkspacePage
    root,page,saved,tr=live
    state=FireWorkspace().export_state();state['active']='hw'
    other=FireWorkspacePage(root,tr.translate,sources=page.sources,context=page.context_provider,
        project=lambda:None,on_snapshot=saved.append,on_dirty=lambda:None,state=state)
    assert set(other.views.created)=={'hw'}
    root.update_idletasks()
    assert set(other.views.created)=={'hw'}
    other.destroy()


def test_valid_result_stale_actions_stay_identical_after_lazy_switch(live):
    root,page,saved,tr=live
    foam=page.views['foam'];fill_view(foam,('210','5','30','3'));foam.calculate()
    snapshot=saved[-1]
    page.host.select(page.host._page_keys['hw']);root.update()
    page.host.select(page.host._page_keys['foam']);root.update()
    assert foam.steps()==snapshot.formula_steps
    foam.variables['foam_fraction'].set('6')
    assert not foam.steps() and str(foam.pdf_button['state'])=='disabled'
    assert snapshot.formula_steps[-1].result_value==945
