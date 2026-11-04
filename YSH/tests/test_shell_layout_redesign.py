"""New user-approved shell/underlay contract, independent of screenshot capture."""
import pytest
from PIL import Image

from ui.widgets.workspace_backdrop import compose_backdrop, composite_surface, light_surface
from ui.theme import colors
from .test_fire_phase5cd_navigation import application, shell
from .test_ui_consistency_phase7 import descendants, assert_horizontal_bounds, review_language


@pytest.mark.parametrize('size',[(1100,700),(1280,800),(1440,900),(1700,1000)])
@pytest.mark.parametrize('language',['tr','en'])
def test_shell_geometry_and_composited_pages(shell,size,language):
    w=shell;root=w._root;old=w._localization.language
    try:
        review_language(w,language);root.deiconify();root.geometry(f'{size[0]}x{size[1]}');root.update()
        assert not w._context_panel.winfo_ismapped()
        assert w._workspace_row==0 and w._page_host.grid_info()['row']==0
        assert w._sidebar.grid_info()['rowspan']==3
        buttons=(w._sidebar_new,w._sidebar_open,w._sidebar_save,w._sidebar_delete,w._sidebar_refresh)
        widths={button.winfo_width() for button in buttons}
        assert max(widths)-min(widths)<=1
        assert len({button.winfo_height() for button in buttons})==1
        for index,button in enumerate(buttons):
            assert int(button.grid_info()['row'])==index//2
            assert int(button.grid_info()['column'])==index%2
        assert buttons[0].winfo_x()==buttons[2].winfo_x()==buttons[4].winfo_x()
        assert buttons[1].winfo_x()==buttons[3].winfo_x()
        assert max(w._sidebar_logo_image.width(),w._sidebar_logo_image.height())==176
        assert str(w._sidebar_logo.cget('anchor'))=='center'
        assert abs(w._sidebar_logo.winfo_rootx()+w._sidebar_logo.winfo_width()/2-
                   (w._sidebar.winfo_rootx()+w._sidebar.winfo_width()/2))<=2
        assert max(w._projects_tree.winfo_height(),w._project_empty_state.winfo_height())>=100
        for family in ('fuel','fire'):
            w._show_family(family,dirty=False);root.update()
            host=w._page_host if family=='fuel' else w._fire_workspace.host
            for key,viewport in host._page_keys.items():
                host.select(viewport);root.update()
                backdrop=viewport._workspace_backdrop;backdrop.paint();root.update()
                assert backdrop.emblem is not None and backdrop.surfaces
                assert viewport.canvas.find_withtag('workspace_backdrop')
                assert viewport.canvas.find_all().index(backdrop.item)<viewport.canvas.find_all().index(viewport._window)
                page=w._pages[key] if family=='fuel' else w._fire_workspace.views[key]
                assert_horizontal_bounds(descendants(page),viewport.canvas)
                from .test_shell_layering_corrective import elements
                from tkinter import ttk
                for widget in descendants(page):
                    if widget.winfo_class() in ('TLabel','TLabelframe'):
                        assert not any(name.startswith('GlassSurface') for name in elements(ttk.Style(root).layout(widget.cget('style') or widget.winfo_class())))
                assert backdrop.size==(viewport.canvas.winfo_width(),viewport.canvas.winfo_height())
                for widget,entry in backdrop.surfaces.items():
                    assert backdrop.style.lookup(widget.cget('style'),'foreground')==backdrop.style.lookup(str(widget.cget('style')).split('.',2)[2],'foreground')
                viewport.canvas.yview_moveto(1);root.update();backdrop.paint()
                assert viewport.canvas.yview()[1]>=.99
                assert tuple(map(float,viewport.canvas.cget('scrollregion').split()))==pytest.approx(viewport.canvas.bbox(viewport._window))
                viewport.canvas.yview_moveto(0)
    finally:w._localization.set_language(old)


def test_context_state_preserved_and_optional_editor_available(shell):
    w=shell;before=w._system_context.to_dict() if hasattr(w._system_context,'to_dict') else w._system_context
    w._root.deiconify();w._open_system_context();w._root.update()
    try:
        assert w._context_editor.winfo_ismapped()
        assert not w._context_panel.winfo_ismapped()
        assert w._context_editor._context==w._system_context
        assert (w._system_context.to_dict() if hasattr(w._system_context,'to_dict') else w._system_context)==before
    finally:
        w.unregister_localizable(w._context_editor);w._context_dialog.destroy();w._context_editor=None


def test_compositing_is_backdrop_relative_and_preserves_source_pixels():
    emblem=Image.new('RGBA',(50,50),(20,40,60,255));before=emblem.tobytes()
    image=compose_backdrop((900,650),emblem)
    assert image.size==(900,650) and image.getextrema()[0][0]<image.getextrema()[0][1]
    patch=composite_surface(image,(150,100,200,180),(255,255,255),.86)
    assert patch.size==(200,180) and patch.getextrema()[0][0]>=220
    assert emblem.tobytes()==before
    assert light_surface((255,255,255)) and not light_surface((16,43,70))


def test_backdrop_does_not_replace_controls_text_or_semantic_status(shell):
    w=shell;root=w._root;root.deiconify();w._show_family('fire',dirty=False);root.update()
    view=w._fire_workspace.views['foam'];viewport=w._fire_workspace.host._active_host()
    entries={name:(entry,entry.cget('textvariable')) for name,entry in view.entries.items()}
    view.variables['foam_fraction'].set('0,03');root.update()
    backdrop=viewport._workspace_backdrop;backdrop.paint();root.update()
    assert view.concentration_warning.cget('style')=='Fire.Status.TLabel'
    assert backdrop.style.lookup('Fire.Status.TLabel','background')==colors.WARNING_SURFACE
    for name,(entry,variable) in entries.items():
        assert entry is view.entries[name] and entry.cget('textvariable')==variable
        assert entry.cget('style')=='Fire.TEntry'
    assert view.variables['foam_fraction'].get()=='0,03'
    assert root.attributes('-alpha')==1.0
