"""Scoped visual-pilot contracts; engineering and other module identities remain independent."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from ui.theme import colors
from ui.theme import pipe_pilot as pilot
from ui.theme.module_visuals import MODULES
from ui.widgets.scrollable_page_host import ScrollablePageHost

ROOT = Path(__file__).parents[1]


class Style:
    """Collect ttk registration without requiring a desktop."""
    def __init__(self, *args: object) -> None:
        self.configurations = {}
        self.maps = {}

    def configure(self, name: str, **kwargs: object) -> None:
        """Record style roles and values."""
        self.configurations[name] = kwargs

    def map(self, name: str, **kwargs: object) -> None:
        """Record state appearance without introducing status logic."""
        self.maps[name] = kwargs


def test_pilot_registers_only_pipe_prefixed_styles() -> None:
    """Shared defaults, other modules, Formula View and Library styles remain untouched."""
    style = Style()
    pilot.configure_pipe_pilot(style)
    assert all(name.startswith('Pipe') for name in style.configurations | style.maps)
    assert style.configurations['PipeResultAccent.TFrame']['background'] == pilot.PIPE_ACCENT
    assert style.configurations['PipeMetricValue.TLabel']['foreground'] == pilot.PIPE_DARK
    assert style.maps['Pipe.TEntry']['bordercolor'][0] == ('focus', pilot.PIPE_ACCENT)
    assert colors.PIPE == colors.GOLD  # Existing compatibility tokens are not propagated.
    assert len(set(pilot.MODULE_ACCENTS.values())) == 4


@pytest.mark.parametrize('key', ['pipe_design', 'transfer_pump', 'discharge_head_loss', 'suction_npsh'])
def test_selected_tab_receives_accepted_module_identity(monkeypatch, key: str) -> None:
    """Changing tabs selects its identity without changing Pipe teal."""
    import ui.widgets.scrollable_page_host as module
    style = Style()
    monkeypatch.setattr(module.ttk, 'Style', lambda parent: style)
    frame = object()
    owner = SimpleNamespace(select=lambda: str(frame), _page_keys={key: frame})
    ScrollablePageHost._apply_active_tab_color(owner)
    state = style.maps['YSH.TNotebook.Tab']
    assert state['background'][0] == ('selected', pilot.PIPE_DARK if key == 'pipe_design' else MODULES[key][2])
    assert state['foreground'][0] == ('selected', colors.WHITE)


@pytest.mark.parametrize('page', ['transfer_pump_page', 'discharge_head_loss_page', 'suction_npsh_page'])
def test_other_module_pages_do_not_use_pilot_styles(page: str) -> None:
    """The prototype cannot silently spread via page-specific imports or style names."""
    source = (ROOT / f'ui/pages/{page}.py').read_text(encoding='utf-8')
    assert 'pipe_pilot' not in source and 'PipeSection.TFrame' not in source
    assert 'Pipe.TEntry' not in source and 'Pipe.TCombobox' not in source


def test_pipe_semantics_actions_units_and_source_safety_survive_visual_pilot() -> None:
    """All accepted source groups and frozen-report actions remain discoverable."""
    source = (ROOT / 'ui/pages/pipe_design_page.py').read_text(encoding='utf-8')
    for key in ('pipe.group.pipe_data', 'pipe.group.strength', 'pipe.group.safety',
                'pipe.group.corrosion', 'pipe.group.bend', 'pipe.ab_source_required'):
        assert key in source
    assert 'self._circuit_used_label' not in source
    assert 'result.default_corrosion_allowance' in source
    assert 'style="PipeUnit.TLabel"' in source
    assert 'separate_window=True' in source
    assert 'self._calculate_wall' in source and 'self._clear_user_state' in source
    assert 'watermark' not in source.lower()
    main = (ROOT / 'ui/main_window.py').read_text(encoding='utf-8')
    assert 'save_snapshot_pdf(self._root, target._pdf_snapshot)' in main
    assert 'icon_size=79' in main and 'square_size=86' in main
    assert 'icon_size=32' in main and 'minimum_height=44' in main


def test_context_compact_mode_remains_presentation_only() -> None:
    """Context uses the same selection service and identity callback with a single-row option."""
    source = (ROOT / 'ui/widgets/system_context_panel.py').read_text(encoding='utf-8')
    assert 'compact: bool = False' in source
    assert 'column=column * 2 + 1 if compact else column' in source
    assert 'self._service.select(self._context, **ids)' in source
    assert 'self._changed(context)' in source
