"""Real shell navigation, project JSON round trips and single Foam guidance."""
import json
from uuid import uuid4

import pytest

from engineering.system_context import ContextReference, SystemContext
from i18n.translator import Translator
from ui.workspace_navigation import WorkspaceNavigation
from .test_fire_phase5_live_ui import live, fill_view


@pytest.mark.parametrize('text,count', [('',0),('3',0),('3,00',0),('1',0),('0,5',1),('0,03',1)])
def test_only_one_contextual_foam_message(live, text, count):
    root,page,_,_=live
    view=page.views['foam']
    view.variables['foam_fraction'].set(text)
    root.update_idletasks()
    assert len(view.clarifications)==count
    assert bool(view.concentration_warning.grid_info())==bool(count)
    assert bool(view.concentration_help.grid_info())==(not bool(count))
    assert '%3' not in view.scope['text']
    if count:
        assert view.concentration_warning['text']=='Bu alan yüzde bekler. %3 için 3 giriniz.'
    else:
        assert view.concentration_help['text']=='Köpük konsantrasyonunu yüzde olarak giriniz.'


@pytest.mark.parametrize('corrected',['3',''])
def test_correction_removes_warning_and_restores_helper(live,corrected):
    _,page,_,_=live
    view=page.views['foam']
    view.variables['foam_fraction'].set('0,03')
    view.variables['foam_fraction'].set(corrected)
    assert not view.clarifications and not view.concentration_warning.grid_info()
    assert view.concentration_help.grid_info()


def test_exact_english_guidance(live):
    _,page,_,_=live
    view=page.views['foam'];view.tr=Translator('en').translate;view.refresh_texts()
    assert view.concentration_help['text']=='Enter foam concentration as percent.'
    view.variables['foam_fraction'].set('0.03')
    assert view.concentration_warning['text']=='This field expects percent. Enter 3 for 3%.'
    assert not view.concentration_help.grid_info()


@pytest.fixture(scope='module')
def application(tmp_path_factory):
    """Compose the production shell with databases isolated from user projects."""
    import tkinter as tk
    import ui
    import ui.main_window as canonical_shell
    from YSH.app import YSHApplication
    # Package composition also imports YSH.ui.main_window; retain the legacy
    # package attribute used by existing test monkeypatches and sys.modules.
    ui.main_window=canonical_shell
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv('LOCALAPPDATA',str(tmp_path_factory.mktemp('phase5cd')))
        patch.setattr(tk.Tk,'mainloop',lambda self:None)
        app=YSHApplication();app.run()
        root=app._root;root.withdraw();root.update()
        yield app
        root.destroy();app.shutdown()


@pytest.fixture
def shell(application):
    w=application._main_window
    w._active_project=None;w._project_persistence_service.close()
    w._clear_all_pages();w._root.update()
    yield w
    w._active_project=None;w._root.withdraw()


def select(host,key,root):
    host.select(host._page_keys[key]);root.update()


def test_single_sidebar_selector_and_contextual_visibility(shell):
    w=shell;root=w._root;root.deiconify();root.update()
    assert w._family=='fuel' and w._page_host.winfo_ismapped()
    assert tuple(w._page_host._page_keys)==('pipe_design','transfer_pump','discharge_head_loss','suction_npsh')
    assert not hasattr(w,'_family_bar') and not hasattr(w,'_existing_family_button')
    assert w._family_selector.master is w._family_frame
    assert str(w._family_selector['state'])=='readonly'
    w._family_selector.current(1);w._select_family();root.update()
    assert w._family=='fire' and not w._page_host.winfo_ismapped()
    assert w._fire_workspace.winfo_ismapped()
    assert tuple(w._fire_workspace.host._page_keys)==('foam','hw')
    w._family_selector.current(0);w._select_family();root.update()
    assert w._page_host.winfo_ismapped() and not w._fire_workspace.winfo_ismapped()


def test_roundtrip_preserves_live_fields_results_and_module_memory(shell):
    w=shell;root=w._root;pipe=w._pipe_design_page
    pipe._select_pipe_standard(None)
    pipe._fields['q'].set('25');pipe._fields['v'].set('2')
    pipe._calculate_diameter()
    assert pipe._diameter_result
    fuel_before={key:page.export_state() for key,page in w._pages.items()}
    select(w._page_host,'suction_npsh',root)
    w._show_family('fire');root.update()
    page=w._fire_workspace;view=page.views['foam']
    fill_view(view,('210','5','30','3'));view.calculate()
    result=page.model.results['foam'];snapshot=page.model.snapshots['foam']
    assert result.domain_result.foam_concentrate_volume_l==945
    fire_before=page.export_state()
    select(page.host,'hw',root)
    ids=tuple(id(p) for p in w._pages.values()),id(page)
    for _ in range(3):
        w._show_family('fuel');root.update()
        assert w._page_host.select()==str(w._page_host._page_keys['suction_npsh'])
        assert {key:p.export_state() for key,p in w._pages.items()}==fuel_before
        w._show_family('fire');root.update()
        assert page.host.select()==str(page.host._page_keys['hw'])
        assert page.model.results['foam'] is result
        assert page.model.snapshots['foam'] is snapshot
        assert page.export_state()['fields']==fire_before['fields']
    assert ids==(tuple(id(p) for p in w._pages.values()),id(w._fire_workspace))
    assert len(page.views.created)==2


def test_saved_project_restores_family_and_both_module_ids(shell):
    w=shell;root=w._root;service=w._project_persistence_service
    project=service.create_project('Navigation '+str(uuid4()));w._active_project=project
    select(w._page_host,'suction_npsh',root)
    w._show_family('fire');root.update()
    select(w._fire_workspace.host,'hw',root)
    w._fire_workspace.views['hw'].variables['inside_diameter_mm'].set('105')
    state=w._export_all_page_states();service.save(state)
    encoded=json.dumps(state)
    assert 'active_system_family' in encoded and 'Yakıt Sistemi' not in encoded
    w._clear_all_pages();root.update()
    _,restored=service.open(project.id);w._load_all_page_states(restored);root.update()
    assert w._family=='fire'
    assert w._fire_workspace.host.select()==str(w._fire_workspace.host._page_keys['hw'])
    assert w._fire_workspace.views['hw'].variables['inside_diameter_mm'].get()=='105'
    assert not service.is_dirty
    w._show_family('fuel');root.update()
    assert w._page_host.select()==str(w._page_host._page_keys['suction_npsh'])


def test_legacy_workspace_and_new_project_default_to_fuel(shell):
    w=shell;w._show_family('fire');w._root.update()
    state=w._export_all_page_states();state.pop('navigation')
    w._load_all_page_states(state);w._root.update()
    assert w._family=='fuel'
    assert w._navigation.last_active_module_by_family=={'fuel':'pipe_design','fire':'foam'}
    w._show_family('fire');w._clear_all_pages();w._root.update()
    assert w._family=='fuel'


def test_family_change_keeps_engineering_context_and_reports_conflict(shell):
    w=shell
    system=ContextReference(id=uuid4(),code='FUEL',name_tr='Yakıt')
    context=SystemContext(system=system,circuit=ContextReference(id=uuid4(),code='C',name_tr='Devre'),
                          fluid=ContextReference(id=uuid4(),code='FUEL',name_tr='Yakıt'))
    w._apply_system_context(context)
    w._show_family('fire');w._root.update()
    assert w._system_context is context
    assert w._family_notice.grid_info() and w._family_notice['text']==w._translate('navigation.incompatible')
    w._show_family('fuel')
    assert w._system_context is context and not w._family_notice.grid_info()


@pytest.mark.parametrize('language,labels',[('tr',('Yakıt Sistemi','Yangın Söndürme')),('en',('Fuel System','Fire Fighting'))])
@pytest.mark.parametrize('size',[(1100,700),(1440,900)])
def test_real_shell_localization_and_geometry(shell,language,labels,size):
    w=shell;root=w._root
    old=w._translate;w._translate=Translator(language).translate
    try:
        w._refresh_family_selector();w._context_panel._translate=w._translate;w._context_panel.refresh_texts()
        root.deiconify();root.geometry(f'{size[0]}x{size[1]}');root.update()
        assert tuple(w._family_selector['values'])==labels
        assert w._family_label['text']==('Sistem' if language=='tr' else 'System')
        assert w._context_panel._labels['system']['text']==w._translate('context.profile')
        selector=w._family_selector
        import tkinter.font as font
        assert max(font.nametofont('TkTextFont').measure(label) for label in labels)+28<=selector.winfo_width()
        assert selector.winfo_rootx()+selector.winfo_width()<=w._project_footer.winfo_rootx()+w._project_footer.winfo_width()
        assert w._project_tree_container.master.grid_bbox(0,3)[3]>=120
        for family in ('fuel','fire'):
            w._show_family(family);root.update()
            assert w._context_panel.winfo_rootx()+w._context_panel.winfo_width()<=root.winfo_rootx()+root.winfo_width()
            for combo in w._context_panel._selectors.values():
                assert combo.winfo_rootx()+combo.winfo_width()<=root.winfo_rootx()+root.winfo_width()
    finally:
        w._translate=old;w._context_panel._translate=old;w._context_panel.refresh_texts();w._refresh_family_selector()


@pytest.mark.parametrize('payload',[{}, {'navigation':None}, {'navigation':{'version':2}},
    {'navigation':{'version':1,'active_system_family':'Yangın Söndürme','last_active_module_by_family':{'fuel':'bad'}}}])
def test_unknown_or_legacy_navigation_has_safe_defaults(payload):
    state=WorkspaceNavigation.from_workspace(payload)
    assert state.to_payload()==WorkspaceNavigation().to_payload()


def test_partial_project_save_preserves_navigation(shell):
    service=shell._project_persistence_service
    project=service.create_project('Partial '+str(uuid4()))
    state=WorkspaceNavigation();state.active_system_family='fire'
    service.save({'schema_version':1,'navigation':state.to_payload()})
    service.save({'schema_version':1,'pipe_design':{}})
    assert service.open(project.id)[1]['navigation']==state.to_payload()


def test_system_selector_stays_visible_when_project_footer_scrolls(shell):
    w=shell;root=w._root;root.deiconify();root.geometry('1100x700');root.update()
    selector=w._family_selector
    before=selector.winfo_rooty()
    w._project_footer.canvas.yview_moveto(1.0);root.update()
    assert selector.winfo_viewable() and selector.winfo_rooty()==before
    assert selector.winfo_rooty()+selector.winfo_height()<=root.winfo_rooty()+root.winfo_height()
    w._family_selector.current(1);w._select_family();root.update()
    assert w._family=='fire' and w._fire_workspace.winfo_ismapped()
    w._project_footer.canvas.yview_moveto(0.0)


def test_user_requested_gold_header_and_navy_sidebar_keep_icon_sizes(shell):
    from tkinter import ttk
    from ui.theme import colors
    from ui.widgets.rounded_button import HEADER_COMMAND_PALETTE
    style=ttk.Style(shell._root)
    assert style.lookup('Header.TFrame','background')==colors.GOLD
    assert style.lookup('HeaderTitle.TLabel','foreground')==colors.NAVY
    assert style.lookup('SidebarPanel.TFrame','background')==colors.NAVY
    assert style.lookup('SidebarTitle.TLabel','foreground')==colors.GOLD
    assert style.lookup('SidebarSearchLabel.TLabel','foreground')==colors.WHITE
    assert HEADER_COMMAND_PALETTE.normal==(colors.GOLD,colors.GOLD)
    assert style.lookup('SidebarAction.TButton','foreground')==colors.WHITE
    assert style.lookup('SidebarAction.TButton','foreground',('active',))==colors.NAVY
