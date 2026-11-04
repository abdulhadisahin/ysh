"""Structural bounds for the continuous sidebar, without screenshot goldens."""
from tkinter import ttk

import pytest

from ui.theme import colors
from .test_fire_phase5cd_navigation import application, shell


@pytest.mark.parametrize('language',['tr','en'])
@pytest.mark.parametrize('size',[(1100,700),(1280,800),(1440,900),(1700,1000)])
def test_continuous_sidebar_and_right_workspace_do_not_overlap(shell,language,size):
    w=shell;root=w._root
    old=w._localization.language
    try:
        w._localization.set_language(language)
        root.deiconify();root.geometry(f'{size[0]}x{size[1]}');root.update()
        sidebar=w._sidebar
        assert sidebar.master is root and sidebar.grid_info()['rowspan']==3
        assert sidebar.winfo_x()==0 and sidebar.winfo_y()==0
        assert abs(sidebar.winfo_height()-root.winfo_height())<=2
        assert sidebar.winfo_width()<root.winfo_width()/3
        assert ttk.Style(root).lookup(sidebar['style'],'background')==colors.NAVY
        logo=w._sidebar_logo
        assert 170<=max(w._sidebar_logo_image.width(),w._sidebar_logo_image.height())<=184
        assert logo.winfo_width()<=w._sidebar_brand.winfo_width()
        assert abs(logo.winfo_x()+logo.winfo_width()/2-w._sidebar_brand.winfo_width()/2)<=2
        assert logo.winfo_rooty()+logo.winfo_height()<=w._sidebar_title.winfo_rooty()
        assert sidebar.grid_bbox(0,3)[3]>=120
        assert not hasattr(w,'_header_title') and not hasattr(w,'_header_subtitle')
        right=sidebar.winfo_rootx()+sidebar.winfo_width()
        header=w._shell_header
        assert header.winfo_rootx()>=right
        assert header.winfo_height()<root.winfo_height()/2
        for commands in (w._ribbon_project,w._ribbon_library,w._ribbon_help):
            group=commands._ribbon_group
            assert group.winfo_rootx()>=right
            assert group.winfo_rootx()+group.winfo_width()<=header.winfo_rootx()+header.winfo_width()
            assert group.winfo_rooty()+group.winfo_height()<=header.winfo_rooty()+header.winfo_height()
        assert w._status_bar.winfo_rootx()>=right
        for family in ('fuel','fire'):
            w._show_family(family);root.update()
            host=w._page_host if family=='fuel' else w._fire_workspace.host
            canvas=host._active_host().canvas
            assert canvas.winfo_rootx()>=right
            assert canvas.winfo_width()>root.winfo_width()/2
            assert canvas.winfo_height()>150
            assert w._family_selector.winfo_viewable()
            assert w._family_selector.winfo_rootx()+w._family_selector.winfo_width()<=right
        footer=w._project_footer
        for button in (w._sidebar_new,w._sidebar_open,w._sidebar_save,w._sidebar_delete,w._sidebar_refresh):
            offset=button.winfo_rooty()-footer.content.winfo_rooty()
            footer.canvas.yview_moveto(offset/max(1,footer.content.winfo_height()));root.update()
            assert button.winfo_rootx()+button.winfo_width()<=right
            assert button.winfo_rooty()<footer.canvas.winfo_rooty()+footer.canvas.winfo_height()
            assert button.winfo_rooty()+button.winfo_height()>footer.canvas.winfo_rooty()
        footer.canvas.yview_moveto(0)
    finally:
        w._localization.set_language(old)


def test_large_logo_preserves_asset_aspect_and_cached_identity(shell):
    w=shell;image=w._sidebar_logo_image;source=w._sidebar_logo_source_image
    assert image.width()/image.height()==pytest.approx(source.width()/source.height(),rel=.02)
    buttons=tuple(id(button) for button in (w._toolbar_new,w._toolbar_open,w._toolbar_save,w._toolbar_about))
    for size in ('1100x700','1700x1000','1280x800'):
        w._root.geometry(size);w._root.update()
        assert w._sidebar_logo_image is image
        assert tuple(id(button) for button in (w._toolbar_new,w._toolbar_open,w._toolbar_save,w._toolbar_about))==buttons
    assert colors.SHELL_CYAN=='#27C4D4'
    assert (colors.FIRE_SELECTOR_INACTIVE,colors.FIRE_SELECTOR_ACTIVE)==('#C94454','#B51F32')
    assert colors.WARNING=='#E98600'
