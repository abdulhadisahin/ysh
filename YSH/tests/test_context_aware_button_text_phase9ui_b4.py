"""Contracts for B4 context-aware icon/text command presentation."""

from __future__ import annotations

from pathlib import Path

from ui.widgets.rounded_button import RoundedImageButton


ROOT = Path(__file__).resolve().parents[1]


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_top_commands_remain_icon_only_at_the_larger_shared_size() -> None:
    source = _source("ui/main_window.py")
    header_factory = source.split("def _create_header_button", 1)[1].split("def _add_header_logo", 1)[0]

    assert "icon_only=True" in header_factory
    assert "tooltip_text=text" in header_factory
    assert "icon_size=72" in header_factory
    assert "square_size=86" in header_factory


def test_sidebar_actions_keep_native_text_callbacks_and_icons() -> None:
    source = _source("ui/main_window.py")
    sidebar_factory = source.split("def _create_sidebar_button", 1)[1].split("def _add_decorative_image", 1)[0]

    assert "icon_only=True" not in sidebar_factory
    assert "icon_size=36" in sidebar_factory
    assert "minimum_height=48" in sidebar_factory
    assert "horizontal_padding=18" in sidebar_factory
    for callback in ("self._open_new_project", "self._open_selected_project", "self._save_project", "self._delete_project", "self._refresh_projects"):
        assert callback in source


def test_icon_text_lane_keeps_a_ten_pixel_gap_after_the_drawn_icon() -> None:
    """Text begins after the independently rendered icon and its visible gap."""
    spaces = RoundedImageButton._icon_text_gap_spaces(
        icon_width=36,
        horizontal_padding=18,
        icon_text_gap=RoundedImageButton.ICON_TEXT_GAP,
        space_width=4,
    )
    icon_x = max(6, 18 // 2)
    text_start = 18 + (spaces * 4)

    assert RoundedImageButton.ICON_TEXT_GAP == 10
    assert text_start >= icon_x + 36 + RoundedImageButton.ICON_TEXT_GAP


def test_shared_button_uses_measured_icon_lane_for_long_native_labels() -> None:
    """Turkish calculation and Formula labels grow the native surface safely."""
    source = _source("ui/widgets/rounded_button.py")

    assert "def _icon_text_gap_spaces" in source
    assert "self._icon_image.rendered.width()" in source
    assert "tuple(self._icon_text(text) for text in self._stable_texts)" in source


def test_formula_controls_and_sections_use_icons_without_changing_math() -> None:
    transfer = _source("ui/pages/transfer_pump_page.py")
    pipe = _source("ui/pages/pipe_design_page.py")
    discharge = _source("ui/pages/discharge_head_loss_page.py")
    suction = _source("ui/pages/suction_npsh_page.py")
    formula = _source("ui/widgets/formula_view.py")

    assert 'icon_name="formula", icon_size=36' in transfer
    assert 'icon_name="formula",' in pipe
    assert 'icon_name="formula",icon_size=36' in discharge
    assert 'icon_name="formula", icon_size=36' in suction
    assert "self._section_marker_images" in formula
    assert "status_icon_path(self._marker_state(section.role))" in formula
    assert "_render_mathtext_equations" in formula
    assert "math_to_image" in formula


def test_transfer_compact_toolbar_stays_icon_only_while_calculate_keeps_text() -> None:
    transfer = _source("ui/pages/transfer_pump_page.py")

    for icon_name in ('icon_name="add", icon_only=True', 'icon_name="edit", icon_only=True', 'icon_name="delete", icon_only=True'):
        assert icon_name in transfer
    assert 'icon_name="calculate", icon_size=36' in transfer
