"""Fire uses the shared composited input surface and stateful opaque results."""
import pytest
from tkinter import ttk

from engineering.fire.hazen_williams_workflow import HWService
from .test_fire_phase5cd_navigation import application, shell
from .test_fire_phase5_live_ui import fill_view
from .test_shell_layering_corrective import elements
from .test_ui_consistency_phase7 import descendants, assert_horizontal_bounds


@pytest.mark.parametrize('size',[(1100,700),(1440,900)])
@pytest.mark.parametrize('kind',['foam','hw'])
def test_fire_input_glass_and_result_state(shell,size,kind):
    w=shell;root=w._root;root.deiconify();root.geometry(f'{size[0]}x{size[1]}')
    w._show_family('fire',dirty=False);page=w._fire_workspace
    viewport=page.host._page_keys[kind];page.host.select(viewport);root.update()
    view=page.views[kind];view.clear();root.update()
    backdrop=viewport._workspace_backdrop;backdrop.paint();root.update()
    assert view.input_card in backdrop.surfaces
    assert all(entry.winfo_viewable() for entry in view.entries.values())
    assert not view.result_card.result_surface_opaque

    def reveal_empty():
        root.update()
        canvas=viewport.canvas
        top=canvas.canvasy(0)+view.result_card.winfo_rooty()-canvas.winfo_rooty()
        canvas.yview_moveto(top/max(1,viewport.content.winfo_height()))
        root.update();backdrop.paint();root.update()
        assert view.result_card in backdrop.surfaces
    reveal_empty()
    if kind=='foam':values=('210','5','30','3')
    else:
        page.model.service=HWService.WATER
        values=('2000','105','150','120')
    fill_view(view,values);view.calculate();root.update();backdrop.paint();root.update()
    assert page.model.results[kind]
    if kind=='foam':assert page.model.results[kind].domain_result.foam_concentrate_volume_l==945
    else:assert page.model.results[kind].domain_result.total_pressure_loss_bar==pytest.approx(2.3717829024660286)
    assert view.result_card.result_surface_opaque
    for widget in (view.result_card,*descendants(view.result_card)):
        assert widget not in backdrop.surfaces and widget not in backdrop.tints
    for label in (*view.labels.values(),*view.result_labels):
        assert label.winfo_viewable() and label.cget('text')
        assert not any(name.startswith('GlassSurface') for name in elements(ttk.Style(root).layout(label.cget('style'))))
    assert view.pdf_button.instate(['!disabled'])
    assert_horizontal_bounds(descendants(view),viewport.canvas)
    assert viewport.canvas.find_all().index(backdrop.item)<viewport.canvas.find_all().index(viewport._window)
    view.clear();root.update();reveal_empty()
