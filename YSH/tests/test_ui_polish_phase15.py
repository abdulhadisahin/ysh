"""Non-pixel UI contracts and real bend/result/history integration."""
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw

from core.bend_radius import BendState, automatic_bend_radius_mm, bend_mode_from_state
from engineering.pipe_design.models import WallThicknessInput
from engineering.snapshots.builders import build_snapshot
from engineering.module_registry import ModuleCode
from engineering.system_context import SystemContext
from i18n.translator import Translator
from services.pipe_design_service import PipeDesignService
from ui.pages.pipe_design_page import PipeDesignPage
from ui.widgets.asset_loader import AssetImageLoader
from ui.widgets.rounded_button import RoundedImageButton
from ui.widgets.workspace_watermark import CanvasBackgroundWatermark, watermark_size
from ui.assets import action_icon_path
from .test_bend_radius_phase6 import _automatic_page, _Value


@pytest.mark.parametrize('enabled,code,expected', [
    (False, 'D3', 'NO_BEND'), (False, 'MANUAL', 'NO_BEND'),
    (True, None, 'D3'), (True, 'MANUAL', 'MANUAL'),
    (True, 'D5', 'D5'), (False, 'NO_BEND', 'NO_BEND')])
def test_legacy_bend_state_mapping(enabled, code, expected) -> None:
    assert bend_mode_from_state(code, enabled) == expected


def test_no_bend_is_not_a_numeric_radius_flag() -> None:
    with pytest.raises(ValueError, match='No bend'):
        automatic_bend_radius_mm('NO_BEND', 100)
    value = WallThicknessInput(100, 16, 195, 1.8, .85, 1)
    assert value.bend_state is BendState.NO_BEND and value.bend_radius_mm is None
    value.bend_allowance_enabled = True
    value.bend_radius_mm = 1
    assert value.bend_state is BendState.BEND_APPLIES
    assert WallThicknessInput.from_dict(value.to_dict()).to_dict() == value.to_dict()


def test_mode_transitions_preserve_manual_radius_without_calculation() -> None:
    page = _automatic_page()
    page._bend = _Value(False)
    page._bend_radius_entry = SimpleNamespace(configure=lambda **kw: None)
    page._select_bend_mode('MANUAL')
    page._fields['r'].set('300,25')
    page._on_bend_radius_change()
    page._select_bend_mode('NO_BEND')
    assert page._bend.get() is False and page._fields['r'].get() == ''
    page._select_bend_mode('D3')
    assert page._bend.get() is True and page._fields['r'].get() == '266,70'
    page._select_bend_mode('MANUAL')
    assert page._fields['r'].get() == '300,25'


@pytest.mark.parametrize('first,second', [('D3', 'NO_BEND'), ('NO_BEND', 'D3')])
def test_real_page_bend_calculation_formula_and_snapshot_freeze(
        material_service, pipe_size_service, engineering_constant_service, first, second) -> None:
    page = _automatic_page()
    page._service = PipeDesignService(material_service, pipe_size_service, engineering_constant_service)
    page._fields.update({key: _Value(value) for key, value in
                        dict(da='100', pc='16', rp='195', sf='1.8', wf='.85', c='1').items()})
    page._number = lambda key: float(page._fields[key].get().replace(',', '.'))
    page._bend = _Value(False)
    page._using_library_source = lambda: False
    page._notify_pipe_selection = lambda: None
    page._update_wall_summary = lambda: None
    page._refresh_formula_panel = lambda: None
    page._message = _Value()
    page._snapshot_listener = None
    page._formula_selection = None
    snapshots, results = [], []
    for mode in (first, second):
        page._select_bend_mode(mode)
        page._calculate_wall()
        result = page._wall_formula_result
        results.append(result)
        snapshots.append(build_snapshot(ModuleCode.PIPE_DESIGN, 'wall', result, context=SystemContext()))
        assert result.trace['bend_state'] == ('NO_BEND' if mode == 'NO_BEND' else 'BEND_APPLIES')
        raw = result.trace['wall_input']
        wall = result.wall_thickness
        step = next(s for s in snapshots[-1].formula_steps if s.step_id == 'pipe.b')
        if mode == 'NO_BEND':
            assert raw['bend_radius_mm'] is None and wall.bend_allowance_mm == 0
            assert step.formula_text == 'formula2.no_bend' and not step.variables
            assert 'Bükme yok' in Translator('tr').translate(step.formula_text)
        else:
            assert wall.bend_allowance_mm == .4 * (100 / 300) * wall.base_wall_thickness_mm
            assert step.formula_text == 'b = 0.4 × (da / R) × s0'
    frozen = snapshots[0].to_json()
    page._select_bend_mode(first)
    assert snapshots[0].to_json() == frozen
    assert snapshots[0].evidence['facts']['calculation']['trace']['wall_input'] == results[0].trace['wall_input']
    assert results[0].wall_thickness.base_wall_thickness_mm == results[1].wall_thickness.base_wall_thickness_mm
    assert results[0].wall_thickness.allowable_stress_mpa == results[1].wall_thickness.allowable_stress_mpa


@pytest.mark.parametrize('source,viewport', [((1254, 1254), (220, 600)),
    ((600, 300), (220, 110)), ((300, 600), (100, 80)), ((600, 300), (2000, 1500))])
def test_watermark_geometry_is_bounded_and_proportionate(source, viewport) -> None:
    width, height = watermark_size(source, viewport)
    assert 0 < width <= viewport[0] and 0 < height <= viewport[1]
    assert max(width, height) <= 480
    assert abs(width / height - source[0] / source[1]) < .04
    assert (width, height) == watermark_size(source, viewport)


def test_watermark_missing_geometry_is_safe() -> None:
    assert watermark_size((100, 100), (1, 1)) == (0, 0)


class CanvasDouble:
    """Record canvas operations without claiming rendered visual verification."""
    width, height = 220, 500
    def __init__(self, *args, **kwargs): self.settings = kwargs
    def create_image(self, *args, **kwargs): return 1
    def tag_lower(self, item): pass
    def bind(self, *args, **kwargs): pass
    def after_idle(self, callback): return 'pending'
    def winfo_width(self): return self.width
    def winfo_height(self): return self.height
    def coords(self, *args): self.position = args
    def itemconfigure(self, *args, **kwargs): self.item = kwargs
    def grid(self, **kwargs): self.cell = kwargs


def test_watermark_resize_cache_is_lazy_bounded_and_reuses_quantized_size(tmp_path, monkeypatch) -> None:
    import ui.widgets.workspace_watermark as module
    path = tmp_path / 'logo.png'
    Image.new('RGBA', (100, 100), (0, 20, 40, 255)).save(path)
    renders = []
    monkeypatch.setattr(module.ImageTk, 'PhotoImage', lambda image, **kw: renders.append(image.copy()) or renders[-1])
    canvas = CanvasDouble()
    renderer = CanvasBackgroundWatermark(canvas, path)
    assert not renders
    renderer._refresh()
    assert renders[-1].getchannel('A').getextrema() == (36, 36)
    canvas.width += 1
    renderer._refresh()
    assert len(renders) == 1
    for width in range(240, 500, 24):
        canvas.width = width
        renderer._refresh()
    assert len(renderer._cache) <= renderer.CACHE_LIMIT
    assert canvas.item['state'] == 'normal'


def test_watermark_shares_existing_surfaces_without_an_extra_grid_cell(tmp_path, monkeypatch) -> None:
    import ui.widgets.scrollable_frame as module
    path = tmp_path / 'logo.png'; path.touch()
    selected = []
    class Decoration:
        @staticmethod
        def is_available(): return True
        def __init__(self, parent, source, callback, placement):
            selected.append((parent, placement))
    monkeypatch.setattr(module, 'WorkspaceWatermark', Decoration)
    frame = module.ScrollableFrame.__new__(module.ScrollableFrame)
    frame._background_watermark = []
    surface = object()
    frame.set_background_watermark(path, (surface,))
    assert selected == [(surface, (1.0, 1.0))]
    frame.set_background_watermark(path, (surface,))
    assert len(selected) == 1
    assert '_decoration' not in frame.__dict__


def test_real_action_art_has_more_visible_area_without_changing_aspect_or_mapping() -> None:
    path = action_icon_path('new')
    with Image.open(path) as source:
        rgba = source.convert('RGBA')
    fitted = AssetImageLoader._full_asset_safe(rgba)
    original_bounds = rgba.getchannel('A').point(lambda a: 255 if a >= 8 else 0).getbbox()
    fitted_bounds = fitted.getchannel('A').point(lambda a: 255 if a >= 8 else 0).getbbox()
    original_art = max(original_bounds[2]-original_bounds[0], original_bounds[3]-original_bounds[1])
    fitted_art = max(fitted_bounds[2]-fitted_bounds[0], fitted_bounds[3]-fitted_bounds[1])
    assert original_art == fitted_art
    assert 64 <= fitted_art * 72 / max(fitted.size) <= 72
    assert fitted_art * 36 / max(fitted.size) >= 32
    assert len({action_icon_path(key) for key in ('new', 'open', 'save', 'save_as')}) == 4


def test_alpha_fit_keeps_antialiased_edges_and_aspect_ratio() -> None:
    rgba = Image.new('RGBA', (100, 90))
    ImageDraw.Draw(rgba).rectangle((20, 25, 80, 65), fill=(50, 50, 50, 255))
    ImageDraw.Draw(rgba).rectangle((19, 24, 81, 66), outline=(50, 50, 50, 7))
    fitted = AssetImageLoader._full_asset_safe(rgba)
    assert fitted.getchannel('A').getbbox()[0] > 0
    assert fitted.getchannel('A').getextrema()[1] == 255
    assert fitted.getchannel('A').histogram()[7] > 0


def test_branding_and_no_separate_bend_checkbox_contract() -> None:
    for language in ('tr', 'en'):
        tr = Translator(language)
        assert tr.translate('app.title') == 'D243'
        assert 'YSH' not in tr.translate('message.about_ysh')
        assert tr.translate('pipe.bend_mode.NO_BEND') in ('Bükme yok', 'No bend')
    source = (Path(__file__).parents[1] / 'ui/pages/pipe_design_page.py').read_text(encoding='utf-8')
    assert '_bend_check' not in source
    assert 'bend_mode_from_state(' in source
    assert 'command=self._open_table_8_9' in source


def test_asset_cache_reuses_same_request_and_is_bounded(tmp_path, monkeypatch) -> None:
    import ui.widgets.asset_loader as module
    path = tmp_path / 'icon.png'
    Image.new('RGBA', (100, 80), (10, 30, 60, 255)).save(path)
    monkeypatch.setattr(module.ImageTk, 'PhotoImage', lambda image, **kw: image.copy())
    monkeypatch.setattr(AssetImageLoader, '_cache', {})
    monkeypatch.setattr(AssetImageLoader, 'CACHE_LIMIT', 2)
    master = SimpleNamespace(tk=object())
    first = AssetImageLoader.load(master, path, 24)
    assert first is AssetImageLoader.load(master, path, 24)
    assert first.rendered.size == (24, 19)
    AssetImageLoader.load(master, path, 32)
    AssetImageLoader.load(master, path, 36)
    assert len(AssetImageLoader._cache) == 2
    assert first.rendered.size == (24, 19)  # Existing widget references stay valid.


def test_button_surface_grows_with_icon_height(monkeypatch) -> None:
    import ui.widgets.rounded_button as module
    font = SimpleNamespace(measure=lambda text: len(text) * 7, metrics=lambda key: 16)
    monkeypatch.setattr(module.tkfont, 'Font', lambda **kw: font)
    monkeypatch.setattr(module.ttk, 'Style', lambda master: SimpleNamespace(lookup=lambda *a: 'TkDefaultFont'))
    button = SimpleNamespace(_icon_only=False, _stable_texts=(), _minimum_height=48,
        _icon_image=SimpleNamespace(rendered=SimpleNamespace(height=lambda: 52)),
        _horizontal_padding=18, _vertical_padding=7, cget=lambda key: 'Hesapla',
        _surface_dimensions_from_content=RoundedImageButton._surface_dimensions_from_content)
    width, height = RoundedImageButton._content_surface_dimensions(button)
    assert width >= len('Hesapla') * 7 + 36
    assert height == 64


@pytest.mark.parametrize('state,mode,radius', [
    ({'bend_enabled': True, 'fields': {'r': '333.25'}}, 'MANUAL', '333.25'),
    ({'bend_enabled': False, 'bend_mode': 'MANUAL', 'fields': {'r': '333.25'}}, 'NO_BEND', ''),
    ({'bend_enabled': True, 'bend_mode': 'D3', 'fields': {'da': '88.90'}}, 'D3', '266,70')])
def test_real_page_legacy_load_and_new_state_round_trip(state, mode, radius) -> None:
    def page_double():
        page = _automatic_page()
        page._bend = _Value(False)
        page._source, page._material, page._message = _Value(), _Value(), _Value()
        page._material_ids = {}
        page._t = Translator('tr').translate
        for name in ('_select_pipe_standard', '_select_circuit', '_select_line_role',
                     '_set_source_mode', '_update_diameter_summary', '_update_wall_summary',
                     '_refresh_diameter_warning_message', '_evaluate_velocity_warning', '_refresh_formula_panel'):
            setattr(page, name, lambda *a, **kw: True)
        page._warning_codes_from_result = lambda: []
        page._selected_pipe_standard_code = lambda: None
        page._selected_circuit_code = lambda: None
        page._selected_line_role_code = lambda: None
        return page
    first = page_double()
    first.load_state(state)
    assert first._selected_bend_mode_code() == mode
    assert first._fields['r'].get() == radius
    saved = first.export_state()
    second = page_double()
    second.load_state(saved)
    assert second.export_state() == saved
    if state.get('bend_mode') == 'MANUAL':
        second._select_bend_mode('MANUAL')
        assert second._fields['r'].get() == '333.25'
