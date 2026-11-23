"""Approved Library PNGs and compact shell retain existing command safeguards."""
import hashlib
from uuid import uuid4
from tkinter import ttk

import pytest
from PIL import Image

from ui.assets import action_icon_path,action_icon_fit_mode
from ui.widgets.asset_loader import AssetImageLoader
from .test_fire_phase5cd_navigation import application,shell
from ._tk_geometry import settle_geometry

APPROVED={
    'library_materials':('boru_malzemeleri.png','6E5221D52F933BBFE41936BC5DC57BEE94678E38A9AB71EBAC03452703987534'),
    'library_fluids':('akiskanlar.png','AEBC7D35E8EA63EB94A0F8ED61B15D4D1D7A161FF6AFBDA7F72E706B7D040379'),
    'library_engineering_constants':('muhendislik_sabitleri.png','AA98E90F076056E8F754087499FDC3D7DF8325D6D1F66E9038E8D8D257B52AC6'),
    'library_standards':('standartlar.png','2AA279F81192C2E2879F8BFE7DBC6AA6F5F7FEE8B48F0D5E27B3B9D904DDB391'),
}


def assert_compact_sidebar(window):
    for name in ('_family_selector','_family_frame','_sidebar_actions','_project_footer',
                 '_sidebar_new','_sidebar_open','_sidebar_save','_sidebar_delete','_sidebar_refresh'):
        assert not hasattr(window,name),name
    assert window._sidebar_logo.winfo_viewable()
    assert window._project_search_entry.winfo_viewable()
    visible=window._project_tree_container if window._projects_tree.get_children() else window._project_empty_state
    assert visible.winfo_viewable()
    sidebar=window._sidebar
    assert sidebar.grid_size()[1]==4
    gap=sidebar.winfo_rooty()+sidebar.winfo_height()-visible.winfo_rooty()-visible.winfo_height()
    assert 0<=gap<=20


@pytest.mark.parametrize('size',[(1100,700),(1440,900)])
@pytest.mark.parametrize('language',['tr','en'])
def test_sidebar_reflows_and_two_toolbar_groups_fit(shell,size,language):
    w=shell;root=w._root;old=w._localization.language
    try:
        w._localization.set_language(language);root.deiconify();root.geometry(f'{size[0]}x{size[1]}')
        settle_geometry(root,w._sidebar,w._toolbar_delete)
        assert_compact_sidebar(w)
        assert not hasattr(w,'_ribbon_help') and not hasattr(w,'_toolbar_about')
        assert len(w._ribbon_project.winfo_children())==5
        assert len(w._ribbon_library.winfo_children())==4
        for commands in (w._ribbon_project,w._ribbon_library):
            group=commands._ribbon_group
            assert group.winfo_rootx()>=w._sidebar.winfo_rootx()+w._sidebar.winfo_width()
            assert group.winfo_rootx()+group.winfo_width()<=w._shell_header.winfo_rootx()+w._shell_header.winfo_width()
            for button in commands.winfo_children():
                assert button._square_size==86 and button._icon_size==79
                assert button._icon_only and ttk.Button.cget(button,'text')==''
                assert button.winfo_viewable() and button.cget('command')
        for button in (w._toolbar_materials,w._toolbar_fluids,w._toolbar_constants,w._toolbar_standards):
            path=action_icon_path(button._icon_name)
            name,digest=APPROVED[button._icon_name]
            assert path.name==name and hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest
            assert action_icon_fit_mode(button._icon_name)=='canvas'
            with Image.open(path) as source:
                rendered=button._icon_image.rendered
                assert rendered.width()/rendered.height()==pytest.approx(source.width/source.height,rel=.02)
        assert w._help_menu.entrycget(0,'command')
        assert w._help_menu.entrycget(0,'label')==w._translate('menu.help.about')
    finally:w._localization.set_language(old)


def test_approved_assets_are_not_edited_and_canvas_fit_keeps_full_image(shell):
    for key,(name,digest) in APPROVED.items():
        path=action_icon_path(key)
        assert path.name==name
        assert hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest
        loaded=AssetImageLoader.load(shell._root,path,79,fit_mode=action_icon_fit_mode(key))
        with Image.open(path) as source:
            ratio=min(79/source.width,79/source.height,1)
            assert (loaded.rendered.width(),loaded.rendered.height())==(
                max(1,round(source.width*ratio)),max(1,round(source.height*ratio)))


@pytest.mark.parametrize('control,category',[
    ('_toolbar_materials','materials'),('_toolbar_fluids','fluids'),
    ('_toolbar_constants','constants'),('_toolbar_standards','pipe_standards')])
def test_library_buttons_use_existing_category_commands(shell,monkeypatch,control,category):
    seen=[]
    monkeypatch.setattr(shell,'_open_engineering_library',seen.append)
    getattr(shell,control).invoke()
    assert seen==[category]


def test_delete_button_preserves_no_selection_confirmation_and_dirty_guards(shell,monkeypatch):
    import ui.main_window as view
    w=shell;service=w._project_persistence_service
    infos=[];confirm=[]
    monkeypatch.setattr(view.messagebox,'showinfo',lambda *a,**k:infos.append(a))
    monkeypatch.setattr(view.messagebox,'askyesno',lambda *a,**k:confirm.append(a) or False)
    selection=w._projects_tree.selection()
    if selection:w._projects_tree.selection_remove(*selection)
    w._toolbar_delete.invoke()
    assert len(infos)==1 and not confirm
    assert w._create_project('Delete guard '+str(uuid4()),'','','fuel')
    project=w._active_project
    service.mark_dirty()
    monkeypatch.setattr(view.messagebox,'askyesnocancel',lambda *a,**k:None)
    w._toolbar_delete.invoke()
    assert service.get_project(project.id)==project and not confirm
    monkeypatch.setattr(view.messagebox,'askyesnocancel',lambda *a,**k:False)
    w._toolbar_delete.invoke()
    assert service.get_project(project.id)==project and len(confirm)==1
    monkeypatch.setattr(view.messagebox,'askyesno',lambda *a,**k:True)
    w._toolbar_delete.invoke()
    assert w._active_project is None
    assert project.id not in {p.id for p in service.get_all_projects()}


@pytest.mark.parametrize('family',['fuel','fire'])
def test_create_save_open_and_family_lock_need_no_sidebar_selector(shell,family):
    w=shell
    assert w._create_project('Compact family '+str(uuid4()),'Description','Legacy notes',family)
    project=w._active_project
    assert w._save_project()
    w._close_project();w._activate_project(project)
    assert w._family==family and w._locked_project_family()==family
    assert project.name in w._project_family_indicator['text']
    w._show_family('fire' if family=='fuel' else 'fuel')
    assert w._family==family
    assert not hasattr(w,'_family_selector')
