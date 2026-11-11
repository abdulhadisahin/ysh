"""Shared transmission and compact Fire source controls; no engineering edits."""
import pytest
from tkinter import ttk

from ui.theme.spacing import SOURCE_FIELD_WIDTH, PANEL_TRANSMISSION_FACTOR
from ui.widgets.workspace_backdrop import input_surface, OUTSIDE_INPUT_OPACITY_FACTOR
from .test_fire_phase5cd_navigation import application, shell
from .test_ui_consistency_phase7 import review_language, descendants, assert_horizontal_bounds


@pytest.mark.parametrize('size',[(1100,700),(1440,900)])
@pytest.mark.parametrize('language',['tr','en'])
def test_compact_fire_sources_and_actions(shell,size,language):
    w=shell;root=w._root;old=w._localization.language
    try:
        review_language(w,language);root.deiconify();root.geometry(f'{size[0]}x{size[1]}')
        w._show_family('fire',dirty=False);root.update()
        for kind in ('foam','hw'):
            page=w._fire_workspace;viewport=page.host._page_keys[kind]
            page.host.select(viewport);root.update();view=page.views[kind]
            library=view.library_panel
            if not library.details.expanded:library.details.toggle()
            root.update()
            for box in library.boxes.values():
                assert box.winfo_viewable()
                assert int(box.cget('width'))==SOURCE_FIELD_WIDTH
                assert box.winfo_width()==box.winfo_reqwidth()
            if kind=='hw':
                boxes=(view.service_box,view.mode_box,view.source_box)
                assert len({box.winfo_rootx() for box in boxes})==1
                assert len({box.winfo_width() for box in boxes})==1
                for box in boxes:
                    assert int(box.cget('width'))==SOURCE_FIELD_WIDTH
                    assert box.winfo_width()==box.winfo_reqwidth()
                    assert box.winfo_rootx()+box.winfo_width()<viewport.canvas.winfo_rootx()+viewport.canvas.winfo_width()-80
                buttons=[button for button,_ in view.link_buttons]
                assert len({button.winfo_rooty() for button in buttons})==1
                assert len({button.winfo_height() for button in buttons})==1
                assert all(button.winfo_width()==button.winfo_reqwidth() for button in buttons)
                assert all(button.cget('command') for button in buttons)
            assert_horizontal_bounds(descendants(view),viewport.canvas)
        padding=ttk.Style(root).lookup('Compact.Fire.Secondary.TButton','padding')
        assert tuple(map(int,root.tk.splitlist(padding)))==(8,4)
    finally:w._localization.set_language(old)


def test_shared_panel_transmission_increases_without_touching_labels(shell):
    w=shell;root=w._root;root.deiconify();root.geometry('1440x900')
    assert PANEL_TRANSMISSION_FACTOR==pytest.approx(1.2)
    for family in ('fuel','fire'):
        w._show_family(family,dirty=False);root.update()
        host=w._page_host if family=='fuel' else w._fire_workspace.host
        viewport=host._active_host();backdrop=viewport._workspace_backdrop
        backdrop.paint();root.update();assert backdrop.surfaces
        for widget,surface in backdrop.surfaces.items():
            x,y,width,height,rgb,opacity,_=surface.signature
            base=str(widget.cget('style')).split('.',2)[2]
            color=backdrop.style.lookup(base,'background')
            from ui.theme import colors
            previous=.30 if color.lower() in (colors.WORKSPACE_SURFACE.lower(),'#f1f7fa') else .94 if max(rgb)-min(rgb)>12 else .80
            expected=1-(1-previous)*1.2
            if not input_surface(widget):expected*=OUTSIDE_INPUT_OPACITY_FACTOR
            assert opacity==pytest.approx(expected)
            assert widget.winfo_class()!='TLabel'
        assert root.attributes('-alpha')==1.0
