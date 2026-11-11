"""One secondary tools row; eligibility remains owned by the existing pages."""
import pytest

from i18n.translator import Translator
from ui.main_window import MainWindow
from .test_fire_phase5cd_navigation import application, shell
from .test_fire_phase5_live_ui import fill_view
from .test_ui_consistency_phase7 import review_language, descendants, assert_horizontal_bounds


@pytest.mark.parametrize('language',['tr','en'])
def test_all_six_tools_group_and_history_without_current_result(shell,language):
    w=shell;root=w._root;old=w._localization.language;opened=False
    try:
        review_language(w,language);root.deiconify();root.geometry('1100x700');root.update()
        tr=Translator(language).translate;tested=set()
        for family in ('fuel','fire'):
            w._show_family(family,dirty=False);root.update()
            host=w._page_host if family=='fuel' else w._fire_workspace.host
            for key,viewport in host._page_keys.items():
                host.select(viewport);root.update()
                page=w._pages[key] if family=='fuel' else w._fire_workspace.views[key]
                panel=page._formula_panel if family=='fuel' else page.formula
                panel.refresh_post_tools();root.update()
                buttons=(panel._toggle,panel._history_button,panel._pdf_button)
                for column,button in enumerate(buttons):
                    assert button.master is panel
                    assert int(button.grid_info()['row'])==0 and int(button.grid_info()['column'])==column
                    assert button.winfo_height()==36
                    assert button.calculation_action_role=='secondary'
                assert panel._toggle.instate(['disabled'])
                assert panel._pdf_button.instate(['disabled'])
                assert panel._history_button.instate(['!disabled'])
                assert panel._toggle.cget('text').strip()==tr('common.show_formula')
                assert panel._history_button._logical_text==tr('post.history')
                assert panel._pdf_button._logical_text==tr('action.pdf_current_result')
                for left,right in zip(buttons,buttons[1:]):
                    assert 0<=right.winfo_rootx()-left.winfo_rootx()-left.winfo_width()<=10
                pdfs=[widget for widget in descendants(page)
                      if getattr(widget,'_logical_text',None)==tr('action.pdf_current_result')]
                assert pdfs==[panel._pdf_button]
                primaries=[widget for widget in descendants(page)
                           if getattr(widget,'calculation_action_role',None)=='primary']
                assert primaries and all(button._minimum_height==48 for button in primaries)
                assert_horizontal_bounds(descendants(panel),viewport.canvas)
                if not opened:
                    panel._history_button.invoke();root.update()
                    assert w._history_window.winfo_exists()
                    w._history_window._close();root.update();opened=True
                tested.add(key)
        assert len(tested)==6
    finally:w._localization.set_language(old)


def test_fuel_current_formula_pdf_and_stale_guard_keep_history_available(shell):
    w=shell;root=w._root;page=w._pages['transfer_pump'];design=page._design_panel
    page._show_calculation_mode();root.deiconify()
    panel=page._formula_panel
    exports=[];history=[];pdf_available=panel._post_pdf_available
    panel.configure_post_tools(on_history=lambda:history.append(True),on_pdf=lambda:exports.append(page._pdf_snapshot),
                               pdf_available=pdf_available,history_available=lambda:True)
    pdf=panel._pdf_button
    panel.configure_post_tools(on_history=lambda:history.append(True),on_pdf=lambda:exports.append(page._pdf_snapshot),
                               pdf_available=pdf_available,history_available=lambda:True)
    assert panel._pdf_button is pdf  # repeated service/UI binding never duplicates tools
    design._fields['volume'].set('120');design._fields['target_time'].set('3');design.calculate();root.update()
    snapshot=page._pdf_snapshot;before=snapshot.to_json()
    assert MainWindow._pdf_is_current(page)
    assert panel._toggle.instate(['!disabled']) and pdf.instate(['!disabled'])
    panel._toggle.invoke();root.update();assert panel._dialog.winfo_exists()
    panel._close_dialog()
    pdf.invoke();assert exports==[snapshot]
    design._fields['target_time'].set('4');root.update()
    assert panel._toggle.instate(['disabled']) and pdf.instate(['disabled'])
    assert panel._history_button.instate(['!disabled'])
    panel._history_button.invoke();assert history==[True]
    pdf.configure(state='normal');pdf.invoke()  # handler rechecks currentness, not just widget state
    assert exports==[snapshot] and snapshot.to_json()==before
    panel.refresh_post_tools()


def test_late_history_service_refreshes_existing_fire_tools_without_result(shell):
    w=shell;root=w._root;service=w._snapshot_history
    try:
        w._snapshot_history=None
        w._show_family('fire',dirty=False);view=w._fire_workspace.views['foam']
        view.formula.refresh_post_tools()
        assert view.formula._history_button.instate(['disabled'])
        assert view.formula._toggle.instate(['disabled'])
        w.set_snapshot_history_service(service);root.update()
        assert view.formula._history_button.instate(['!disabled'])
        assert view.formula._toggle.instate(['disabled'])
        assert view.formula._pdf_button.instate(['disabled'])
    finally:
        if w._snapshot_history is not service:w.set_snapshot_history_service(service)


@pytest.mark.parametrize('kind',['foam','hw'])
def test_fire_valid_then_stale_tools_use_existing_result_eligibility(shell,kind):
    from engineering.fire.hazen_williams_workflow import HWService
    w=shell;root=w._root;w._show_family('fire',dirty=False)
    workspace=w._fire_workspace;workspace.host.select(workspace.host._page_keys[kind]);view=workspace.views[kind]
    if kind=='hw':workspace.model.service=HWService.WATER
    fill_view(view,('210','5','30','3') if kind=='foam' else ('2000','105','150','120'))
    view.calculate();root.update();panel=view.formula
    snapshot=workspace.model.snapshots[kind];before=snapshot.to_json()
    assert panel._toggle.instate(['!disabled']) and panel._pdf_button.instate(['!disabled'])
    assert panel._history_button.instate(['!disabled'])
    panel._toggle.invoke();root.update();assert panel._dialog.winfo_exists()
    panel._close_dialog()
    view.variables['application_duration_min' if kind=='foam' else 'hazen_williams_c'].set('140')
    root.update()
    assert panel._toggle.instate(['disabled']) and panel._pdf_button.instate(['disabled'])
    assert panel._history_button.instate(['!disabled'])
    assert snapshot.to_json()==before
