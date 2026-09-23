"""Display-independent contracts for the V3-D result-card hierarchy."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(path: str) -> str:
    """Read one presentation-layer source file."""
    return (ROOT / path).read_text(encoding="utf-8")


def test_shared_result_metrics_use_a_neutral_surface_and_semantic_accent() -> None:
    """Shared result output uses one restrained card language across modules."""
    cards = _source("ui/widgets/cards.py")
    styles = _source("ui/theme/styles.py")

    assert 'style=f"{normal_style_prefix}Accent.TFrame"' in cards
    assert 'style=f"{style_prefix}Accent.TFrame"' in cards
    assert 'style.configure(f"{name}Accent.TFrame", background=accent, width=4)' in styles
    assert 'foreground=colors.NAVY_TEXT, font=value_font' in styles
    assert '"UnavailableResultMetric", colors.RESULT_SURFACE, colors.DIVIDER' in styles


def test_result_hierarchy_preserves_primary_secondary_and_technical_levels() -> None:
    """Primary values, secondary values, and supporting details stay distinct."""
    styles = _source("ui/theme/styles.py")
    typography = _source("ui/theme/typography.py")

    assert "RESULT_SECONDARY =" in typography
    assert "RESULT_TECHNICAL =" in typography
    assert "typography.RESULT_SECONDARY" in styles
    assert "typography.RESULT_TECHNICAL" in styles
    assert "typography.DOMINANT_RESULT" in styles


def test_module_accents_and_existing_result_workflows_remain_intact() -> None:
    """Presentation changes retain module identities and authoritative outputs."""
    styles = _source("ui/theme/styles.py")
    pipe = _source("ui/pages/pipe_design_page.py")
    transfer = _source("ui/pages/transfer_pump_page.py")
    discharge = _source("ui/pages/discharge_head_loss_page.py")
    suction = _source("ui/pages/suction_npsh_page.py")

    for style_name in (
        "TransferResultMetric",
        "DischargeResultMetric",
        "SuctionResultMetric",
        "PipeResultAccent.TFrame",
    ):
        assert style_name in styles
    assert pipe.count('accent_style="PipeResultAccent.TFrame"') == 2
    assert "action.use_recommended_pipe" in pipe
    assert "result.predicted_pump_capacity" in transfer
    assert "result.pump_discharge_head" in discharge
    assert "result.available_npsh" in suction
