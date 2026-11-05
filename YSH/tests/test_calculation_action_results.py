"""Native action hierarchy and result presentation across the six calculators."""
from tkinter import ttk, font
import pytest

from ui.widgets.calculation_presentation import PRIMARY_HEIGHT, SECONDARY_HEIGHT
from ui.widgets.rounded_button import NEUTRAL_BUTTON_PALETTE
from .test_fire_phase5cd_navigation import application, shell
from .test_fire_phase5_live_ui import fill_view
from .test_ui_consistency_phase7 import review_language, descendants, assert_horizontal_bounds


@pytest.mark.parametrize('size',[(1100,700),(1440,900)])
@pytest.mark.parametrize('language',['tr','en'])
def test_six_calculators_action_hierarchy_and_empty_results(shell,size,language):
    w=shell;root=w._root;old=w._localization.language
    try:
        review_language(w,language);root.deiconify();root.geometry(f'{size[0]}x{size[1]}');root.update()
        tested=set()
        for family in ('fuel','fire'):
            w._show_family(family,dirty=False);root.update()
            host=w._page_host if family=='fuel' else w._fire_workspace.host
            for key,viewport in host._page_keys.items():
                host.select(viewport);root.update()
                page=w._pages[key] if family=='fuel' else w._fire_workspace.views[key]
                widgets=list(descendants(page));primary=[];secondary=[]
                for widget in widgets:
                    role=getattr(widget,'calculation_action_role',None)
                    if role is None:continue
                    assert widget.cget('command')
                    assert str(widget.cget('style')).startswith('Calculation.')
                    if role=='primary':
                        primary.append(widget)
                        assert widget._minimum_height==PRIMARY_HEIGHT
                        assert (widget._icon_size,widget._horizontal_padding,widget._vertical_padding)==(32,12,6)
                        if widget.winfo_ismapped():assert widget.winfo_height()==PRIMARY_HEIGHT
                    else:
                        secondary.append(widget)
                        assert widget._minimum_height==SECONDARY_HEIGHT
                        assert widget._palette==NEUTRAL_BUTTON_PALETTE
                        if widget.winfo_ismapped():assert widget.winfo_height()==SECONDARY_HEIGHT
                assert primary and secondary,key
                tested.add(key)
                assert_horizontal_bounds(widgets,viewport.canvas)
                if family=='fire':
                    assert page.empty_result.winfo_ismapped() and page.empty_result.cget('text')
                    assert not page.result_labels[0].winfo_ismapped()
                    assert not page.result_card.result_surface_opaque
                    assert page.status.grid_info()['row']>page.result_card.grid_info()['row']
                    assert page.source_summary.grid_info()['row']>page.status.grid_info()['row']
                    assert page.secondary_actions.grid_info()['row']>page.source_summary.grid_info()['row']
                elif key=='pipe_design':
                    assert page._pipe_result_empty_state.winfo_ismapped()
                    assert not page._diameter_result_card.result_surface_opaque
                    assert page._wall_empty_result.cget('text')
                elif key=='transfer_pump':
                    assert page._design_panel._empty_result.cget('text')
        assert len(tested)==6
    finally:w._localization.set_language(old)


@pytest.mark.parametrize('size',[(1100,700),(1440,900)])
def test_foam_primary_result_caption_warning_and_actions_are_separate(shell,size):
    w=shell;root=w._root;root.deiconify();root.geometry(f'{size[0]}x{size[1]}')
    w._show_family('fire',dirty=False);page=w._fire_workspace;view=page.views['foam']
    page.host.select(page.host._page_keys['foam']);root.update()
    fill_view(view,('210','5','30','3'));view.calculate();root.update()
    backdrop=page.host._active_host()._workspace_backdrop;backdrop.paint();root.update()
    assert page.model.results['foam'].domain_result.foam_concentrate_volume_l==945
    assert view.result_card.result_surface_opaque
    assert view.result_title.cget('text') and view.primary_caption.cget('text')
    assert '\n' not in view.result_labels[0].cget('text')
    style=ttk.Style(root)
    primary=font.Font(root,font=style.lookup(view.result_labels[0].cget('style'),'font'))
    support=font.Font(root,font=style.lookup(view.result_labels[1].cget('style'),'font'))
    assert primary.actual('size')>support.actual('size')
    assert view.source_summary.cget('text')==view.tr('result.source_manual')
    assert view.pdf_button.master is view.secondary_actions
    assert view.pdf_button.instate(['!disabled'])
    assert view.status not in list(descendants(view.result_labels[0]))
    for widget in (view.result_card,*descendants(view.result_card)):
        assert widget not in backdrop.surfaces and widget not in backdrop.tints
    assert_horizontal_bounds(descendants(view),page.host._active_host().canvas)


@pytest.mark.parametrize('size',[(1100,700),(1440,900)])
def test_pipe_calculated_primary_metric_and_warning_separation(shell,size):
    w=shell;root=w._root;root.deiconify();root.geometry(f'{size[0]}x{size[1]}')
    w._show_family('fuel',dirty=False);page=w._pages['pipe_design']
    viewport=w._page_host._page_keys['pipe_design'];w._page_host.select(viewport);root.update()
    page._fields['q'].set('20');page._fields['v'].set('2');page._calculate_diameter();root.update()
    assert page._diameter_result and page._diameter_value.get()!='—'
    assert page._diameter_result_card.result_surface_opaque
    backdrop=viewport._workspace_backdrop;backdrop.paint();root.update()
    for widget in (page._diameter_result_card,*descendants(page._diameter_result_card)):
        assert widget not in backdrop.surfaces and widget not in backdrop.tints
    style=ttk.Style(root)
    primary=font.Font(root,font=style.lookup(page._diameter_metric_value.cget('style'),'font'))
    support=font.Font(root,font=style.lookup(page._diameter_standard_value.cget('style'),'font'))
    assert primary.actual('size')>support.actual('size')
    assert page._warning_panel not in list(descendants(page._diameter_result_card))
    assert_horizontal_bounds(descendants(page),viewport.canvas)
