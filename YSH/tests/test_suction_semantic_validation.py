"""Semantic validation contracts for staged Suction Loss and ENPY work."""

from __future__ import annotations

import pytest

from engineering.input_parsing import parse_engineering_float
from engineering.validation import ValidationError, ValidationIssue
from i18n.translator import Translator
from i18n.validation import render_validation_issue
from services.suction_npsh_service import SuctionNPSHService
from ui.pages.suction_npsh_page import SuctionNPSHPage


class _StringVar:
    """Minimal no-display Tk string-variable replacement."""

    def __init__(self, value: str = "") -> None:
        """Store the controlled value."""
        self.value = value

    def set(self, value: str) -> None:
        """Store a rendered status string."""
        self.value = value


class _Materials:
    """Empty material dependency for manual roughness tests."""


def test_suction_hydraulic_required_and_invalid_viscosity_are_semantic() -> None:
    """Hydraulic parser errors retain stable keys before service execution."""
    with pytest.raises(ValidationError) as diameter:
        parse_engineering_float("", field_name="Diameter", field_key="field.pipe_inside_diameter")
    with pytest.raises(ValidationError) as viscosity:
        parse_engineering_float("invalid", field_name="Viscosity", field_key="field.kinematic_viscosity")

    assert render_validation_issue(diameter.value.issue, Translator("en")) == "Pipe Inside Diameter is required."
    assert render_validation_issue(viscosity.value.issue, Translator("tr")) == "Kinematik Viskozite geçerli bir sayı olmalıdır."


def test_suction_service_uses_semantic_roughness_validation() -> None:
    """Manual roughness absence never returns a completed English service error."""
    service = SuctionNPSHService(_Materials())

    with pytest.raises(ValidationError) as caught:
        service.calculate_suction_loss(100.0, 20.0, 2.0, "cSt", 20.0, None, [])

    assert caught.value.issue == ValidationIssue("required", "field.roughness")


def test_enpy_density_and_optional_required_input_remain_semantic() -> None:
    """Density is positive while optional NPSH Required remains optional."""
    service = SuctionNPSHService(_Materials())
    result = service.calculate_enpy(1.0, 1.2, "bar", 0.03, "bar", 850.0, 2.0, None)
    assert result.npsh_margin_m is None

    with pytest.raises(ValidationError) as caught:
        service.calculate_enpy(1.0, 1.2, "bar", 0.03, "bar", 0.0, 2.0)
    assert caught.value.issue == ValidationIssue("greater_than_zero", "field.fluid_density")

    with pytest.raises(ValidationError) as invalid_required:
        service.calculate_enpy(1.0, 1.2, "bar", 0.03, "bar", 850.0, 2.0, float("nan"))
    assert invalid_required.value.issue == ValidationIssue("valid_number", "field.npsh_required")


def test_suction_stage_status_rerenders_without_calculation() -> None:
    """The ENPY dependency status live-refreshes through the active translator."""
    translator = Translator("en")
    page = SuctionNPSHPage.__new__(SuctionNPSHPage)
    page._translate = translator.translate
    page._message = _StringVar()
    page._loss_status_messages = []
    page._enpy_status_messages = [ValidationIssue("suction_loss_required_for_enpy")]

    page._render_status()
    assert page._message.value == "Calculate Suction Loss before calculating ENPY."

    translator.set_language("tr")
    page._render_status()
    assert page._message.value == "ENPY hesabından önce Emme Hattı Yük Kaybını hesaplayın."

    translator.set_language("en")
    page._render_status()
    assert page._message.value == "Calculate Suction Loss before calculating ENPY."
