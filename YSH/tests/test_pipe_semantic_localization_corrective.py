"""Semantic widget ownership and explicit localization contracts without pixel assumptions."""
from __future__ import annotations

import ast
from pathlib import Path
import re
from types import SimpleNamespace

import pytest

from i18n.messages_tr import MESSAGES as TR
from i18n.messages_en import MESSAGES as EN
from i18n.translator import Translator
from ui.pages.pipe_design_page import PipeDesignPage
from .test_pipe_design_page import _FakeStringVar

ROOT = Path(__file__).parents[1]
PIPE = ROOT / 'ui/pages/pipe_design_page.py'


def assigned_parent(attribute: str) -> str:
    """Read widget ownership rather than brittle grid coordinates."""
    for node in ast.walk(ast.parse(PIPE.read_text(encoding='utf-8'))):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            if any(isinstance(t, ast.Attribute) and t.attr == attribute for t in node.targets):
                return ast.unparse(node.value.args[0])
    raise AssertionError(attribute)


def test_material_rp_and_source_share_strength_group() -> None:
    """Material, strength and provenance belong to one semantic input group."""
    assert assigned_parent('_source_box') == assigned_parent('_material_box') == 'strength_group'
    tree = ast.parse(PIPE.read_text(encoding='utf-8'))
    labels = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == 'labels' for t in n.targets))
    ownership = {row.elts[1].value: ast.unparse(row.elts[0]) for row in labels.elts}
    assert ownership['rp'] == 'strength_group'
    assert ownership['da'] == ownership['pc'] == 'pipe_group'
    assert ownership['sf'] == ownership['wf'] == 'design_group'
    assert ownership['c'] == 'corrosion_group' and ownership['r'] == 'bend_group'


def test_ab_corrosion_bend_and_results_have_distinct_semantic_owners() -> None:
    """Source notes stay with safety; default c stays beside the editable c input."""
    assert assigned_parent('_table_89_button') == assigned_parent('_ab_source_status') == 'design_group'
    assert assigned_parent('_circuit_default_label') == 'corrosion_group'
    assert assigned_parent('_corrosion_source_note') == 'corrosion_group'
    assert assigned_parent('_bend_mode_box') == assigned_parent('_bend_result_label') == 'bend_group'
    assert assigned_parent('_wall_result_card') == 'wall_form'
    assert 'doğrulaması gerekli' in TR['pipe.ab_source_required']
    assert 'doğrulanmış TL kuralı olarak sunulmaz' in TR['pipe.ab_source_required']
    assert 'b = 0' in TR['pipe.no_bend_note']


@pytest.mark.parametrize('label', ['Manual', 'Manuel', 'manual'])
def test_manual_mode_recognizes_both_locales_without_changing_values(label: str) -> None:
    """Persisted translated source labels remain direct manual input after a language switch."""
    value = _FakeStringVar(); value.set(label)
    for language in ('tr', 'en'):
        page = SimpleNamespace(_source=value, _translate=Translator(language).translate)
        assert not PipeDesignPage._using_library_source(page)


def test_turkish_resource_denylist_allows_symbols_codes_and_proper_names() -> None:
    """Reject known accidental English UI labels, never engineering notation or document names."""
    phrases = ('Material Library', 'Manual', 'Library', 'Source', 'Reference', 'Verified',
               'Unverified', 'User', 'Factory', 'Read Only', 'Read-only', 'Edit', 'Delete',
               'Search', 'Filter', 'Result', 'Formula', 'History', 'Project', 'Save', 'Open',
               'Cancel', 'Close', 'Warning', 'Error', 'Status', 'Default', 'Used', 'Recommended')
    forbidden = {p.casefold() for p in phrases}
    assert not {key: value for key, value in TR.items() if value.strip().casefold() in forbidden}
    assert not {key: value for key, value in TR.items() if re.search(r'\bmaterial library\b', value, re.I)}
    assert TR['message.material_source'] == TR['source.state.library'] == 'Kütüphane'
    assert TR['library.materials'] == 'Malzeme Kütüphanesi'
    assert TR['library2.read_only'] == 'Salt okunur'
    assert 'Fabrika' in TR['library2.ownership.factory']


def test_production_widget_literals_do_not_reintroduce_english_labels() -> None:
    """Check visible constructors only; legacy state identifiers and Python names are exempt."""
    forbidden = {'material library', 'manual', 'open', 'save', 'cancel', 'close', 'error', 'warning'}
    for path in (ROOT / 'ui').rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if isinstance(node, ast.keyword) and node.arg in ('text', 'title', 'values'):
                values = node.value.elts if isinstance(node.value, (ast.Tuple, ast.List)) else (node.value,)
                for value in values:
                    if isinstance(value, ast.Constant) and isinstance(value.value, str):
                        assert value.value.casefold() not in forbidden, (path, node.lineno, value.value)


def test_new_localization_keys_resolve_in_both_languages_and_keep_parameters() -> None:
    """Shared message catalogues preserve English support and formatting placeholders."""
    assert TR.keys() == EN.keys()
    for key in TR:
        if key.startswith('pipe.group.') or key in ('pipe.ab_source_required', 'pipe.corrosion_source_note',
                                                  'pipe.no_bend_note', 'pipe.wall_calculated'):
            for language in ('tr', 'en'):
                assert Translator(language).translate(key, value='1,95') != key
    assert Translator('tr').translate('pipe.wall_calculated', value='1,95') == 'Et kalınlığı: 1,95 mm'


def test_regrouped_wall_summary_copies_results_without_calculating() -> None:
    """The added readonly c result uses the accepted result rather than live edited inputs."""
    values = {name: _FakeStringVar() for name in ('_wall_value', '_wall_summary', '_wall_supporting',
             '_wall_allowable', '_wall_base', '_wall_bend', '_wall_corrosion')}
    result = dict(final_wall_thickness_mm=1.95, allowable_stress_mpa=108.3333333333,
                  base_wall_thickness_mm=.947368421, bend_allowance_mm=0, corrosion_allowance_mm=1)
    page = SimpleNamespace(**values, _wall_result=result, _t=Translator('tr').translate)
    before = dict(result)
    PipeDesignPage._update_wall_summary(page)
    assert result == before and values['_wall_bend'].get() == '0,00 mm'
    assert values['_wall_corrosion'].get() == '1,00 mm'
    assert values['_wall_value'].get() == '1,95'

def test_page_translation_helper_forwards_format_arguments() -> None:
    """Calculation completion messages must resolve their numeric argument before display."""
    page = SimpleNamespace(_translate=Translator('tr').translate)
    assert PipeDesignPage._t(page, 'pipe.wall_calculated', value='1,95') == 'Et kalınlığı: 1,95 mm'

def test_localizing_saved_library_label_does_not_refresh_frozen_rp() -> None:
    """Turkish saved workspaces retain their existing strength while the label is normalized."""
    from uuid import UUID
    from .test_ui_polish_phase15 import _automatic_page, _Value
    page = _automatic_page()
    page._bend = _Value(False)
    page._source, page._material, page._message = _Value(), _Value(), _Value()
    page._fields['rp'] = _Value('195')
    identity = UUID(int=1)
    page._material_ids = {'Saved material': identity}
    page._t = Translator('tr').translate
    for name in ('_select_pipe_standard', '_select_circuit', '_select_line_role',
                 '_set_source_mode', '_update_diameter_summary', '_update_wall_summary',
                 '_refresh_diameter_warning_message', '_evaluate_velocity_warning', '_refresh_formula_panel'):
        setattr(page, name, lambda *a, **kw: True)
    page._warning_codes_from_result = lambda: []
    page._load_selected_material = lambda: pytest.fail('Label localization refreshed a saved engineering value')
    page.load_state({'source_mode': 'Malzeme Kütüphanesi', 'material_id': str(identity),
                     'fields': {'rp': '195'}, 'bend_enabled': False})
    assert page._fields['rp'].get() == '195'
    assert page._source.get() == TR['source.state.library']


def test_micro_correction_hides_only_redundant_corrosion_row() -> None:
    """Main UI omits used c while its internal value and default remain available."""
    tree = ast.parse(PIPE.read_text(encoding='utf-8'))
    build = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '_build')
    visible = ast.unparse(build)
    assert 'result.used_corrosion_allowance' not in visible
    assert '_circuit_used_c' not in visible
    assert 'result.default_corrosion_allowance' in visible
    assert 'pipe.corrosion_source_note' in visible
    c = _FakeStringVar(); c.set('1,25')
    default = _FakeStringVar(); used = _FakeStringVar()
    result = {'corrosion_allowance_mm': 1.25, 'final_wall_thickness_mm': 2.1974250852323705}
    page = SimpleNamespace(_selected_circuit_code=lambda: 'TEST', _circuit_defaults={'TEST': 2},
                           _fields={'c': c}, _circuit_default_c=default, _circuit_used_c=used,
                           _wall_result=result)
    before = dict(result)
    PipeDesignPage._update_circuit_summary(page)
    assert c.get() == '1,25' and used.get() == '1,25 mm' and default.get() == '2,00 mm'
    assert page._wall_result == before


def test_micro_correction_safety_title_preserves_source_verification() -> None:
    """Renaming the action/dialog never upgrades the existing unverified source."""
    tr = Translator('tr').translate
    for key in ('pipe.source_notes', 'pipe.source_notes_title'):
        assert tr(key) == 'Emniyet katsayısı tablosu'
        assert 'A/B' not in tr(key)
        assert EN[key] == 'Safety factor table'
    assert 'kaynak doğrulaması gerekli' in tr('pipe.ab_source_required')
    assert 'Doğrulanmış üretim kuralı değildir' in tr('pipe.source_notes_warning')
    source = PIPE.read_text(encoding='utf-8')
    assert 'text=self._translate("pipe.source_notes")' in source
    assert 'text=self._translate("pipe.ab_source_required")' in source
    dialog = (ROOT / 'ui/dialogs/turk_loydu_table_8_9_dialog.py').read_text(encoding='utf-8')
    assert 'dialog.title(tr("pipe.source_notes_title"))' in dialog
    assert 'text=tr("pipe.source_notes_warning")' in dialog
