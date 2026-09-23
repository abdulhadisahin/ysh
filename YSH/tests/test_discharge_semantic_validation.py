"""Semantic validation contracts for Discharge Head Loss calculations."""

from __future__ import annotations

import pytest

from core.local_loss_item import LocalLossItem
from engineering.head_loss.calculator import DischargeHeadLossCalculator
from engineering.head_loss.models import DischargeHeadLossInput
from engineering.input_parsing import parse_engineering_float
from engineering.validation import ValidationError, ValidationIssue
from i18n.translator import Translator
from i18n.validation import render_validation_issue
from services.discharge_head_loss_service import DischargeHeadLossService
from ui.pages.discharge_head_loss_page import DischargeHeadLossPage


class _StringVar:
    """Provide the minimal no-display string-variable contract."""

    def __init__(self, value: str = "") -> None:
        """Create an empty test variable."""
        self.value = value

    def get(self) -> str:
        """Return the configured value."""
        return self.value

    def set(self, value: str) -> None:
        """Record rendered display text."""
        self.value = value


class _Material:
    """Represent a selected material with an optional roughness value."""

    def __init__(self, roughness_mm: float | None) -> None:
        """Store the requested roughness state."""
        self.roughness_mm = roughness_mm


class _Materials:
    """Provide one material to the discharge service."""

    def __init__(self, roughness_mm: float | None) -> None:
        """Set the material roughness returned to the service."""
        self._material = _Material(roughness_mm)

    def get_material(self, identifier: object) -> _Material:
        """Return the configured material without persistence work."""
        del identifier
        return self._material


def _input(**overrides: float) -> DischargeHeadLossInput:
    """Return a valid baseline input with deterministic optional overrides."""
    values: dict[str, object] = {
        "inside_diameter_mm": 254.0,
        "flow_rate_m3h": 532.0,
        "kinematic_viscosity_m2s": 2.92e-6,
        "pipe_length_m": 343.0,
        "roughness_mm": 0.015,
        "geodetic_head_m": 17.0,
        "local_loss_items": [LocalLossItem("Valve", 1, 1.0)],
    }
    values.update(overrides)
    return DischargeHeadLossInput(**values)  # type: ignore[arg-type]


def test_diameter_required_and_flow_invalid_render_in_both_languages() -> None:
    """Parser issues retain field identity independently of visible language."""
    with pytest.raises(ValidationError) as diameter:
        parse_engineering_float("", field_name="Diameter", field_key="field.pipe_inside_diameter")
    with pytest.raises(ValidationError) as flow:
        parse_engineering_float("not-a-number", field_name="Flow", field_key="field.flow_rate")

    assert diameter.value.issue == ValidationIssue("required", "field.pipe_inside_diameter")
    assert render_validation_issue(diameter.value.issue, Translator("en")) == "Pipe Inside Diameter is required."
    assert render_validation_issue(diameter.value.issue, Translator("tr")) == "Boru İç Çapı gereklidir."
    assert flow.value.issue == ValidationIssue("valid_number", "field.flow_rate")
    assert render_validation_issue(flow.value.issue, Translator("tr")) == "Debi geçerli bir sayı olmalıdır."


@pytest.mark.parametrize(
    ("value", "code"),
    [(float("nan"), "valid_number"), (0.0, "greater_than_zero"), (-1.0, "greater_than_zero")],
)
def test_viscosity_validation_is_semantic(value: float, code: str) -> None:
    """The calculator validates converted internal viscosity before formulas run."""
    with pytest.raises(ValidationError) as caught:
        DischargeHeadLossCalculator().calculate(_input(kinematic_viscosity_m2s=value))

    assert caught.value.issue == ValidationIssue(code, "field.kinematic_viscosity")
    assert render_validation_issue(caught.value.issue, Translator("en")) == (
        "Kinematic Viscosity must be a valid number."
        if code == "valid_number"
        else "Kinematic Viscosity must be greater than zero."
    )


def test_pipe_length_and_manual_roughness_validation_remain_field_specific() -> None:
    """Non-negative length and roughness checks retain their approved semantics."""
    calculator = DischargeHeadLossCalculator()
    with pytest.raises(ValidationError) as length:
        calculator.calculate(_input(pipe_length_m=-1.0))
    with pytest.raises(ValidationError) as roughness:
        calculator.calculate(_input(roughness_mm=-0.01))

    assert length.value.issue == ValidationIssue("zero_or_greater", "field.pipe_length")
    assert roughness.value.issue == ValidationIssue("zero_or_greater", "field.roughness")


def test_material_roughness_missing_is_a_semantic_service_error() -> None:
    """The material service boundary does not emit a completed English error."""
    service = DischargeHeadLossService(_Materials(None))

    with pytest.raises(ValidationError) as caught:
        service.calculate(254, 532, 2.92e-6, 343, None, 17, [], object())

    assert caught.value.issue == ValidationIssue("material_roughness_missing")
    assert render_validation_issue(caught.value.issue, Translator("tr")) == (
        "Seçili malzemede pürüzlülük değeri yok."
    )


def test_discharge_status_rerenders_after_a_language_switch_without_calculation() -> None:
    """Stored semantic status changes language without a service call or data reset."""
    translator = Translator("en")
    page = DischargeHeadLossPage.__new__(DischargeHeadLossPage)
    page._translate = translator.translate
    page._message = _StringVar()
    page._status_messages = [ValidationIssue("material_roughness_missing")]

    page._render_status()
    assert page._message.value == "The selected material has no roughness value."

    translator.set_language("tr")
    page._render_status()
    assert page._message.value == "Seçili malzemede pürüzlülük değeri yok."

    translator.set_language("en")
    page._render_status()
    assert page._message.value == "The selected material has no roughness value."


def test_unexpected_discharge_failure_never_displays_raw_exception_text() -> None:
    """Unexpected service failures are logged and rendered through a generic key."""
    class _BrokenService:
        """Raise one controlled internal exception."""

        def calculate(self, *args: object) -> object:
            """Simulate an unexpected lower-layer failure."""
            del args
            raise RuntimeError("technical solver stack detail")

    page = DischargeHeadLossPage.__new__(DischargeHeadLossPage)
    page._translate = Translator("en").translate
    page._message = _StringVar()
    page._status_messages = []
    page._service = _BrokenService()
    page._source_mode = "manual"
    page._viscosity_unit = _StringVar("cSt")
    page._fields = {
        key: _StringVar(value)
        for key, value in {
            "d": "254", "q": "532", "nu": "2.92", "l": "343",
            "k": "0.015", "h": "17",
        }.items()
    }
    page._items = {}

    page._calculate()

    assert page._message.value == "An unexpected error occurred. See the application log for details."
    assert "technical solver stack detail" not in page._message.value
