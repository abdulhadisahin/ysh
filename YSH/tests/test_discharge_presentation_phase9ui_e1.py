"""Focused display contracts for the Discharge presentation-polish pass."""

from __future__ import annotations

from pathlib import Path

from i18n.messages_en import MESSAGES as MESSAGES_EN
from i18n.messages_tr import MESSAGES as MESSAGES_TR


ROOT = Path(__file__).resolve().parents[1]


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_formula_headers_use_readable_standalone_status_glyphs() -> None:
    """Formula headings use supplied glyph assets, never tiny framed action tiles."""
    source = _source("ui/widgets/formula_view.py")

    assert "status_icon_path" in source
    assert "status_icon_fit_mode" in source
    assert "status_icon_path(self._marker_state(section.role))" in source
    assert "_FORMULA_MARKER_RENDER_SIZE = 32" in source
    assert "_FORMULA_MARKER_LANE_SIZE = 36" in source
    assert '"formula": "information"' in source
    assert '"result": "success"' in source


def test_formula_cards_have_consistent_internal_and_inter_card_spacing() -> None:
    """Formula math, headings, and semantic cards retain breathable layout spacing."""
    source = _source("ui/widgets/formula_view.py")

    assert "padding=(MD, SM)" in source
    assert "requested_width += MD" in source
    assert "padx=(0 if column == 0 else MD, 0)" in source
    assert "pady=(0 if row == 0 else MD, 0)" in source


def test_warning_presentation_emphasizes_icon_and_keeps_text_compact() -> None:
    """The warning panel improves only visual hierarchy, not findings semantics."""
    source = _source("ui/widgets/engineering_warning_panel.py")

    assert "icon_size=34" in source
    assert "wraplength=860" in source
    assert "padx=(40, 0)" in source
    assert "normalized_findings" in source
    assert "SOURCE_REGISTRY" in source


def test_discharge_result_spacing_preserves_hs_primary_hierarchy() -> None:
    """Hs remains the primary metric while technical losses stay visually secondary."""
    source = _source("ui/pages/discharge_head_loss_page.py")

    assert 'normal_style_prefix="DischargeResultMetric"' in source
    assert 'normal_style_prefix="DischargeLossMetric"' in source
    assert "losses_metrics.grid(row=4,column=0,columnspan=2,sticky=\"ew\",pady=(8,0))" in source
    assert "self._supporting_metrics.grid(row=5,column=0,columnspan=2,sticky=\"ew\",pady=(8,0))" in source


def test_visible_moody_label_has_no_legacy_ysh_branding() -> None:
    """The Formula View copy is D243-neutral while the friction calculation remains unchanged."""
    key = "formula.approved_ysh_moody_result"

    assert MESSAGES_TR[key] == "Moody hesaplama sonucu"
    assert MESSAGES_EN[key] == "Moody calculation result"
    assert "YSH/Moody" not in MESSAGES_TR[key]
    assert "YSH/Moody" not in MESSAGES_EN[key]
