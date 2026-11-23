"""Selective backgrounds preserve occupied inputs and decorative header geometry."""
import pytest
from ui.widgets.workspace_backdrop import input_surface, input_bounds, OUTSIDE_INPUT_OPACITY_FACTOR
from .test_fire_phase5cd_navigation import application, shell
from .test_ui_consistency_phase7 import descendants, assert_horizontal_bounds
from ._tk_geometry import settle_geometry

@pytest.mark.parametrize('size',[(1100,700),(1440,900)])
def test_ship_and_selective_surfaces(shell,size):
    w=shell;root=w._root;root.deiconify();root.minsize(1100,700);root.geometry(f'{size[0]}x{size[1]}');root.update()
    w._place_header_ship();root.update()
    ship=w._header_ship_label;header=w._shell_header
    assert ship.winfo_viewable(), [(c._ribbon_group.winfo_x(),c._ribbon_group.winfo_y(),c._ribbon_group.winfo_width(),c._ribbon_group.winfo_height(),header.winfo_width(),header.winfo_height()) for c in (w._ribbon_project,w._ribbon_library)]
    assert w._header_ship_source_image.width()>ship.winfo_width()
    assert ship.winfo_x()>=0 and ship.winfo_y()>=0
    assert ship.winfo_x()+ship.winfo_width()<=header.winfo_width()
    assert ship.winfo_y()+ship.winfo_height()<=header.winfo_height()
    def overlaps(a,b):
        return (a.winfo_rootx()<b.winfo_rootx()+b.winfo_width() and b.winfo_rootx()<a.winfo_rootx()+a.winfo_width()
                and a.winfo_rooty()<b.winfo_rooty()+b.winfo_height() and b.winfo_rooty()<a.winfo_rooty()+a.winfo_height())
    groups=[commands._ribbon_group for commands in (w._ribbon_project,w._ribbon_library)]
    assert all(not overlaps(ship,group) for group in groups), [(i.winfo_rootx(),i.winfo_rooty(),i.winfo_width(),i.winfo_height()) for i in (ship,*groups)]
    geometry=[(g.winfo_x(),g.winfo_y(),g.winfo_width(),g.winfo_height()) for g in groups]
    ship.place_forget();root.update()
    assert geometry==[(g.winfo_x(),g.winfo_y(),g.winfo_width(),g.winfo_height()) for g in groups]
    w._place_header_ship();root.update()
    for family in ('fuel','fire'):
        w._show_family(family,dirty=False);root.update()
        host=w._page_host if family=='fuel' else w._fire_workspace.host
        for viewport in host._page_keys.values():
            host.select(viewport);root.update()
            backdrop=viewport._workspace_backdrop;backdrop.paint();root.update()
            inputs=[item for item in descendants(viewport.content) if getattr(item,'workspace_surface_role',None)=='input']
            assert inputs
            assert all(input_surface(item) and input_bounds(item) for item in inputs if item.winfo_viewable())
            assert backdrop.image is not None
            # A mapped input may be below the viewport at 1100x700. Paint each
            # occupied card in view before inspecting its composed background.
            for card in inputs:
                if not card.winfo_viewable():
                    continue
                canvas=viewport.canvas
                top=canvas.canvasy(0)+card.winfo_rooty()-canvas.winfo_rooty()
                canvas.yview_moveto(top/max(1,viewport.content.winfo_height()))
                settle_geometry(root,viewport,card)
                backdrop.paint();root.update_idletasks()
                assert card in backdrop.surfaces, (family,str(card))
                surface=backdrop.surfaces[card]
                assert surface.signature[4]==(255,255,255)
                assert surface.signature[5]==pytest.approx(.76)
                assert surface.input_bounds==input_bounds(card)
                assert surface.input_bounds
                # The unoccupied part of this same input card uses the lower
                # outside opacity; labels/controls retain their native painters.
                from ui.widgets.workspace_backdrop import composite_surface
                x,y,width,height,rgb,opacity,_=surface.signature
                expected=composite_surface(backdrop.image,(x,y,width,height),rgb,
                                           opacity*OUTSIDE_INPUT_OPACITY_FACTOR)
                for left,top,bw,bh in surface.input_bounds:
                    expected.paste(composite_surface(backdrop.image,(x+left,y+top,bw,bh),rgb,opacity),(left,top))
                from io import BytesIO
                from PIL import Image
                # Pillow's reverse PhotoImage bridge is unsafe with Tk 9;
                # read the native photo through Tk's public PNG serializer.
                data=surface.photo.tk.call(str(surface.photo),'data','-format','png')
                with Image.open(BytesIO(data)) as actual:
                    assert actual.convert('RGB').tobytes()==expected.tobytes()
            viewport.canvas.yview_moveto(0);root.update()
            assert OUTSIDE_INPUT_OPACITY_FACTOR<1
            assert_horizontal_bounds(descendants(viewport.content),viewport.canvas)
