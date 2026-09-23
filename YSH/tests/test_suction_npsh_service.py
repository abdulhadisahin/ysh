"""Tests for independently staged suction-loss and ENPY services."""

from __future__ import annotations

import pytest

from engineering.validation import ValidationError, ValidationIssue
from services.suction_npsh_service import SuctionNPSHService


class _Materials:
    """Minimal material dependency for manual-roughness tests."""


def test_suction_loss_does_not_require_enpy_inputs() -> None:
    """Calculate hydraulics with an empty local-loss list and no pressures."""
    service = SuctionNPSHService(_Materials())
    result = service.calculate_suction_loss(100.0, 20.0, 2.0, "cSt", 20.0, 0.015, [])

    assert result.local_loss_coefficient_total == 0.0
    assert result.total_hydraulic_loss_m >= 0.0


def test_enpy_uses_existing_loss_and_keeps_required_optional() -> None:
    """Calculate ENPY after hydraulics without requiring an NPSH requirement."""
    service = SuctionNPSHService(_Materials())
    loss = service.calculate_suction_loss(100.0, 20.0, 2.0, "cSt", 20.0, 0.015, [])
    result = service.calculate_enpy(loss.total_hydraulic_loss_m, 1.2, "bar", 0.03, "bar", 850.0, 2.0)

    assert result.suction_line_loss_m == loss.total_hydraulic_loss_m
    assert result.npsh_margin_m is None


def test_enpy_rejects_invalid_density_without_recalculating_loss() -> None:
    """Make ENPY-stage validation independent of saved hydraulics."""
    service = SuctionNPSHService(_Materials())
    with pytest.raises(ValidationError) as caught:
        service.calculate_enpy(1.0, 1.2, "bar", 0.03, "bar", 0.0, 2.0)

    assert caught.value.issue == ValidationIssue("greater_than_zero", "field.fluid_density")
