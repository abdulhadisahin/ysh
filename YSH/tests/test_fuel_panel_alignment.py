"""The three Fuel pages share Pipe's surface compositor, not opaque card fills."""
import pytest

from ui.widgets.cards import InformationCard, ResultCard
from .test_fire_phase5cd_navigation import application, shell
from .test_ui_consistency_phase7 import descendants, assert_horizontal_bounds


@pytest.mark.parametrize('size',[(1100,700),(1440,900)])
def test_fuel_panels_match_pipe_and_calculated_results_stay_opaque(shell,size):
    w=shell;root=w._root;root.deiconify();root.geometry(f'{size[0]}x{size[1]}')
    w._show_family('fuel',dirty=False);host=w._page_host
    host.select(host._page_keys['pipe_design']);root.update()
    reference=host._active_host()._workspace_backdrop;reference.paint();root.update()
    pipe_opacities={surface.signature[5] for surface in reference.surfaces.values()
                    if surface.signature[4]==(255,255,255)}
    assert pipe_opacities
    for key in ('transfer_pump','discharge_head_loss','suction_npsh'):
        viewport=host._page_keys[key];host.select(viewport);root.update()
        page=w._pages[key];backdrop=viewport._workspace_backdrop
        def inside_result(item):
            parent=item.master
            while parent is not page:
                if isinstance(parent,ResultCard):return True
                parent=parent.master
            return False
        cards=[item for item in descendants(page) if isinstance(item,InformationCard)
               and not isinstance(item,ResultCard) and not inside_result(item) and item.winfo_viewable()]
        assert cards,key
        for card in cards:
            assert card.composite_panel
            canvas=viewport.canvas
            top=canvas.canvasy(0)+card.winfo_rooty()-canvas.winfo_rooty()
            canvas.yview_moveto(top/max(1,viewport.content.winfo_height()))
            root.update();backdrop.paint();root.update()
            assert card in backdrop.surfaces,(key,str(card))
            assert card not in backdrop.tints
            assert backdrop.surfaces[card].signature[5] in pipe_opacities
        if key=='transfer_pump':
            panel=page._design_panel
            for name,value in {'volume':'100','target_time':'2','pump_capacity':'60'}.items():panel._fields[name].set(value)
            panel.calculate();assert hasattr(panel,'_last_result'),panel._error.get()
        elif key=='discharge_head_loss':
            page._source.set(page._translate('message.manual_source'));page._select_source_mode()
            for name,value in {'d':'100','q':'20','nu':'1','l':'100','k':'.1','h':'5'}.items():page._fields[name].set(value)
            page._calculate();assert hasattr(page,'_last_result'),page._message.get()
        else:
            page._roughness_source.set(page._translate('message.manual_source'));page._select_roughness_source()
            for name,value in {'diameter':'100','flow':'20','viscosity':'1','length':'100','roughness':'.1',
                               'pressure':'1','vapour':'.02','density':'1000','height':'1','required':'2'}.items():page._fields[name].set(value)
            page._calculate_suction_loss();assert hasattr(page,'_last_loss'),page._message.get()
            page._calculate_enpy();assert hasattr(page,'_last_enpy'),page._message.get()
        root.update();backdrop.paint();root.update()
        for card in [item for item in descendants(page) if isinstance(item,ResultCard)]:
            for widget in (card,*descendants(card)):
                assert widget not in backdrop.surfaces and widget not in backdrop.tints
                if 'style' in widget.keys():assert not str(widget.cget('style')).startswith(('Glass.','Frost.'))
        assert_horizontal_bounds(descendants(page),viewport.canvas)
        assert viewport.canvas.find_all().index(backdrop.item)<viewport.canvas.find_all().index(viewport._window)
