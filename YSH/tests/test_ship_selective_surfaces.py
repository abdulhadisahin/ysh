"""Selective backgrounds preserve occupied inputs and decorative header geometry."""
import pytest
from ui.widgets.workspace_backdrop import input_surface, input_bounds, OUTSIDE_INPUT_OPACITY_FACTOR
from .test_fire_phase5cd_navigation import application, shell
from .test_ui_consistency_phase7 import descendants, assert_horizontal_bounds

@pytest.mark.parametrize('size',[(1100,700),(1440,900)])
def test_ship_and_selective_surfaces(shell,size):
    w=shell;root=w._root;root.deiconify();root.minsize(1100,700);root.geometry(f'{size[0]}x{size[1]}');root.update()
    w._place_header_ship();root.update()
    ship=w._header_ship_label;header=w._shell_header
    assert ship.winfo_viewable(), [(c._ribbon_group.winfo_x(),c._ribbon_group.winfo_y(),c._ribbon_group.winfo_width(),c._ribbon_group.winfo_height(),header.winfo_width(),header.winfo_height()) for c in (w._ribbon_project,w._ribbon_library,w._ribbon_help)]
    assert w._header_ship_source_image.width()>ship.winfo_width()
    assert ship.winfo_x()>=0 and ship.winfo_y()>=0
    assert ship.winfo_x()+ship.winfo_width()<=header.winfo_width()
    assert ship.winfo_y()+ship.winfo_height()<=header.winfo_height()
    def overlaps(a,b):
        return (a.winfo_rootx()<b.winfo_rootx()+b.winfo_width() and b.winfo_rootx()<a.winfo_rootx()+a.winfo_width()
                and a.winfo_rooty()<b.winfo_rooty()+b.winfo_height() and b.winfo_rooty()<a.winfo_rooty()+a.winfo_height())
    groups=[commands._ribbon_group for commands in (w._ribbon_project,w._ribbon_library,w._ribbon_help)]
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
            surfaces=[(item,s) for item,s in backdrop.surfaces.items() if s.signature and s.signature[4]==(255,255,255)]
            solid=[s.signature[5] for item,s in surfaces if input_surface(item)]
            outside=[s.signature[5] for item,s in surfaces if not input_surface(item)]
            assert solid and outside
            assert max(outside)<max(solid)
            assert max(solid)==pytest.approx(.76)
            assert OUTSIDE_INPUT_OPACITY_FACTOR<1
            assert_horizontal_bounds(descendants(viewport.content),viewport.canvas)
