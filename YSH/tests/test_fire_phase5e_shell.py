"""Controlled shell branding checks using the production Tk composition."""
from tkinter import ttk

import pytest

from i18n.translator import Translator
from ui.theme import colors
from .test_fire_phase5cd_navigation import application, shell
from ._tk_geometry import settle_geometry


@pytest.mark.parametrize('language',['tr','en'])
@pytest.mark.parametrize('size',[(1100,700),(1280,800),(1440,900),(1700,1000)])
def test_logo_selector_actions_and_header_fit(shell,language,size):
    w=shell;root=w._root;old=w._translate
    w._translate=Translator(language).translate
    try:
        w._refresh_family_selector();root.deiconify()
        root.geometry(f'{size[0]}x{size[1]}')
        settle_geometry(root,w._toolbar_delete,w._sidebar)
        assert not hasattr(w,'_header_title') and not hasattr(w,'_header_subtitle')
        assert 'D243' in root.title()
        logo=w._sidebar_logo
        assert logo.master is w._sidebar_brand
        assert 0<w._sidebar_logo_image.width()<=176 and 0<w._sidebar_logo_image.height()<=176
        assert logo.winfo_rooty()+logo.winfo_height()<=w._sidebar_title.winfo_rooty()
        assert w._project_tree_container.master.grid_bbox(0,3)[3]>=120
        assert logo.winfo_width()<=w._sidebar_brand.winfo_width()
        # Removed logo/title cannot reserve a blank column in the command strip.
        toolbar=w._ribbon_project.master.master
        assert toolbar.grid_info()['column']==0
        assert toolbar.winfo_rootx()+toolbar.winfo_width()<=root.winfo_rootx()+root.winfo_width()
        assert toolbar.master.winfo_height()<root.winfo_height()/2
        for family in ('fuel','fire'):
            w._show_family(family);root.update()
            assert not hasattr(w,'_family_selector')
        from .test_toolbar_sidebar_cleanup import assert_compact_sidebar
        assert_compact_sidebar(w)
        for action in (w._toolbar_new,w._toolbar_open,w._toolbar_save,w._toolbar_delete):
            assert action.winfo_viewable()
    finally:
        w._translate=old;w._refresh_family_selector()


def test_creation_family_choice_remains_available_without_sidebar_popup(shell):
    import tkinter as tk
    from ui.widgets.project_family_choice import ProjectFamilyChoice
    w=shell;root=w._root;root.deiconify();root.update()
    assert not hasattr(w,'_family_selector')
    dialog=tk.Toplevel(root);choice=ProjectFamilyChoice(dialog,w._translate);choice.pack()
    try:
        assert tuple(choice.choice['values'])==(w._translate('project.family.fuel'),w._translate('project.family.fire'))
        assert choice.choice.current()==-1
        choice.choice.current(1);assert choice.selected()=='fire'
        choice.choice.current(0);assert choice.selected()=='fuel'
    finally:dialog.destroy()


def test_logo_not_reloaded_during_family_language_or_resize(shell,monkeypatch):
    from ui.widgets.asset_loader import AssetImageLoader
    logo=shell._sidebar_logo_image
    original=AssetImageLoader.load;calls=[]
    def load(*args,**kwargs):
        calls.append((args,kwargs));return original(*args,**kwargs)
    monkeypatch.setattr(AssetImageLoader,'load',load)
    for size in ('1100x700','1440x900'):
        shell._root.geometry(size)
        for family in ('fire','fuel'):
            shell._show_family(family);shell._refresh_family_selector();shell._root.update()
    assert shell._sidebar_logo_image is logo
    assert not any(len(args)>2 and args[2]==176 for args,_ in calls)


def test_shell_cyan_does_not_replace_module_or_warning_colors(shell):
    style=ttk.Style(shell._root)
    assert colors.HEADER_SURFACE==colors.SHELL_CYAN=='#27C4D4'
    assert style.lookup('SidebarTitle.TLabel','foreground')==colors.SHELL_CYAN
    assert colors.WARNING=='#E98600' and colors.WARNING_SURFACE=='#FFF6E8'
    assert colors.GOLD_DARK=='#7B5A17' and colors.PIPE==colors.GOLD
    assert colors.TRANSFER==colors.GOLD and colors.DISCHARGE==colors.NAVY
    shell._show_family('fire');shell._root.update()
    assert style.lookup('Fire.Status.TLabel','foreground')==colors.GOLD_DARK
    assert style.lookup('Fire.Status.TLabel','background')==colors.WARNING_SURFACE
