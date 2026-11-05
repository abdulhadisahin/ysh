"""Focused visual layering acceptance without screenshot dependencies."""
from PIL import Image, ImageChops
import pytest

from ui.widgets.cards import ResultCard
from ui.widgets.workspace_backdrop import compose_backdrop
from ui.theme import colors
from .test_fire_phase5cd_navigation import application, shell
from .test_ui_consistency_phase7 import descendants, assert_horizontal_bounds


@pytest.mark.parametrize('size', [(1100,700),(1440,900)])
def test_watermark_is_centered_in_its_workspace(size):
    emblem=Image.new('RGBA',(100,50),(20,40,60,255))
    background=Image.new('RGB',size,colors.WORKSPACE_SURFACE)
    bounds=ImageChops.difference(compose_backdrop(size,emblem),background).getbbox()
    assert bounds
    assert abs((bounds[0]+bounds[2])/2-size[0]/2)<=1
    assert abs((bounds[1]+bounds[3])/2-size[1]/2)<=1


@pytest.mark.parametrize('size', [(1100,700),(1440,900)])
def test_results_opaque_and_decoration_below_native_controls(shell,size):
    w=shell;root=w._root;root.deiconify();root.geometry(f'{size[0]}x{size[1]}');root.update()
    assert root.attributes('-alpha')==1.0
    logo=w._sidebar_logo
    assert abs(logo.winfo_rootx()+logo.winfo_width()/2-
               (w._sidebar.winfo_rootx()+w._sidebar.winfo_width()/2))<=2
    for family in ('fuel','fire'):
        w._show_family(family,dirty=False);root.update()
        host=w._page_host if family=='fuel' else w._fire_workspace.host
        for key,viewport in host._page_keys.items():
            host.select(viewport);root.update()
            page=w._pages[key] if family=='fuel' else w._fire_workspace.views[key]
            backdrop=viewport._workspace_backdrop;backdrop.paint();root.update()
            order=viewport.canvas.find_all()
            assert order.index(backdrop.item)<order.index(viewport._window)
            assert not viewport.canvas.tag_bind('workspace_backdrop','<Button-1>')
            assert backdrop.surfaces
            widgets=list(descendants(page))
            results=[item for item in widgets if isinstance(item,ResultCard) or
                     (item.winfo_class()=='TFrame' and 'result' in str(item.cget('style')).lower())]
            assert results,key
            for result in results:
                for item in (result,*descendants(result)):
                    assert item not in backdrop.surfaces and item not in backdrop.tints
                    if 'style' in item.keys():
                        assert not str(item.cget('style')).startswith(('Glass.','Frost.'))
            assert_horizontal_bounds(widgets,viewport.canvas)
            assert tuple(map(float,viewport.canvas.cget('scrollregion').split()))==pytest.approx(viewport.canvas.bbox(viewport._window))
