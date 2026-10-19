"""Audited FormulaStep bindings and PNG → MathText → text safety."""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from engineering.formula.common import step, variable
from engineering.formula.models import FormulaStep
from engineering.snapshots.serialization import decode, primitive
from ui.assets import FORMULA_ASSET_FILENAMES, formula_asset_path
from ui.formula_asset_policy import STEP_ASSET_KEYS, QUARANTINED_ASSETS, step_asset_names
from ui.widgets.formula_view import FormulaReferencePanel, FormulaSection


@pytest.mark.parametrize('key', tuple(FORMULA_ASSET_FILENAMES))
def test_formula_inventory_real_double_extension_and_frozen_path(tmp_path, key):
    path = formula_asset_path(key)
    assert path.name == FORMULA_ASSET_FILENAMES[key]
    assert path.name.endswith('.png.png')
    with Image.open(path) as image:
        assert image.format == 'PNG' and image.size == (1448, 1086)
    frozen = tmp_path / 'resources/formulas' / path.name
    frozen.parent.mkdir(parents=True)
    frozen.write_bytes(path.read_bytes())
    assert formula_asset_path(key, tmp_path) == frozen


@pytest.mark.parametrize('identity,text,expected', [
    ('pipe.D', 'D = √((4 × Qm³/s) / (π × V))', 'pipe_diameter'),
    ('pipe.stress', 'σallow = Rp0.2 / B', 'allowable_stress'),
    ('pipe.b', 'b = 0.4 × (da / R) × s0', 'bend_allowance'),
    ('pipe.wall', 's = s0 + c + b', 'required_wall_thickness'),
    ('discharge.hf', 'hf = 6.4 × 10⁶ × f × L × Q² / Di⁵', 'pipe_friction_loss'),
    ('suction.hf', 'hf = 6.4 × 10⁶ × f × L × Q² / Di⁵', 'pipe_friction_loss'),
    ('suction.ENPYm', 'ENPYm = PE/(ρg) − Pb/(ρg) − HEgeo − he', 'available_enpy'),
])
def test_current_and_frozen_steps_use_same_verified_display_mapping(identity, text, expected):
    current = step(identity, 'x', 1.123456789, 'm', text, (), 0)
    frozen = decode(FormulaStep, primitive(current))
    assert frozen == current
    assert step_asset_names(current) == step_asset_names(frozen) == (expected,)


@pytest.mark.parametrize('identity,text', [
    ('pipe.b', 'formula2.no_bend'), ('pipe.b', 'formula2.precomputed'),
    ('pipe.stress', 'formula2.configured_stress'), ('transfer.Q', 'Q = V/t'),
    ('pipe.s0', 's0'), ('discharge.hL', 'hL'), ('suction.hL', 'hL'),
])
def test_no_bend_configured_rules_and_bad_artwork_never_get_misleading_png(identity, text):
    assert step_asset_names(step(identity, 'x', 0, '', text, (), 0)) == ()


def test_configured_wall_is_not_replaced_by_simple_sum_picture():
    current = step('pipe.wall', 's', 3, 'mm', 'formula2.required_wall', (), 0)
    assert step_asset_names(current) == ('required_wall_thickness',)
    assert step_asset_names(replace(current, variables=(variable('minimum', 3, 'mm'),))) == ()
    assert set(QUARANTINED_ASSETS) == {'base_wall_thickness', 'local_loss'}
    assert set(STEP_ASSET_KEYS.values()) == set(FORMULA_ASSET_FILENAMES)


@pytest.mark.parametrize('png,mathtext,expected', [(True, True, ['png']),
    (False, True, ['png', 'mathtext']), (False, False, ['png', 'mathtext', 'text'])])
def test_actual_renderer_prioritizes_png_then_mathtext_then_native_text(monkeypatch, png, mathtext, expected):
    import ui.widgets.formula_view as module
    calls = []
    class Label:
        def __init__(self, *args, **kwargs): calls.append('text')
        def grid(self, **kwargs): pass
    monkeypatch.setattr(module.ttk, 'Label', Label)
    panel = SimpleNamespace(
        _render_formula_assets=lambda *a: calls.append('png') or png,
        _render_mathtext_equations=lambda *a: calls.append('mathtext') or mathtext,
    )
    FormulaReferencePanel._render_section_content(panel, object(),
        FormulaSection('FORMULA', 'frozen stored expression', asset_names=('pipe_diameter',)), 'FormulaEquation')
    assert calls == expected


def test_missing_and_quarantined_png_reach_existing_fallback(monkeypatch):
    import ui.widgets.formula_view as module
    attempts = []
    monkeypatch.setattr(module.AssetImageLoader, 'load', lambda *a, **kw: attempts.append(a) or None)
    panel = SimpleNamespace(_formula_asset_images=[])
    for key in ('pipe_diameter', 'base_wall_thickness', 'local_loss'):
        assert not FormulaReferencePanel._render_formula_assets(panel, object(),
            FormulaSection('FORMULA', 'stored', asset_names=(key,)), 'FormulaEquation')
    assert len(attempts) == 1


def test_spec_keeps_formula_directory_in_resources_manifest():
    source = (Path(__file__).parents[2] / 'build/ysh.spec').read_text(encoding='utf-8')
    assert '(str(application_root / "resources"), "resources")' in source
