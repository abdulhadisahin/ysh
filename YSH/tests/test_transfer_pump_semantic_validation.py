"""Semantic validation contracts for Fuel Transfer Pump calculations."""

from __future__ import annotations

import pytest

from core.pump_reference import PumpReference
from engineering.transfer_pump.calculator import TransferPumpCalculator
from engineering.transfer_pump.models import TransferPumpInput
from engineering.validation import ValidationError, ValidationIssue
from i18n.translator import Translator
from i18n.validation import render_validation_issue
from services.transfer_pump_service import TransferPumpService
from ui.pages.transfer_pump_page import TransferPumpPage


class _StringVar:
    """Minimal no-display replacement for a Tk string variable."""

    def __init__(self, value: str = "") -> None:
        """Initialize the controlled value."""
        self.value = value

    def get(self) -> str:
        """Return the stored value."""
        return self.value

    def set(self, value: str) -> None:
        """Store a new value."""
        self.value = value


class _References:
    """Provide deterministic saved references to the transfer service."""

    def __init__(self, records: list[PumpReference]) -> None:
        """Store records for the one required service operation."""
        self._records = records

    def get_all_references(self) -> list[PumpReference]:
        """Return the configured reference records."""
        return self._records


def test_empty_new_ship_capacity_uses_a_semantic_required_issue() -> None:
    """The page parser emits a stable field-specific issue for empty input."""
    with pytest.raises(ValidationError) as caught:
        from engineering.input_parsing import parse_engineering_float

        parse_engineering_float(
            "", field_name="New ship fuel capacity", field_key="field.fuel_capacity"
        )

    assert caught.value.issue == ValidationIssue("required", "field.fuel_capacity")
    assert render_validation_issue(caught.value.issue, Translator("en")) == "Fuel Capacity is required."
    assert render_validation_issue(caught.value.issue, Translator("tr")) == "Yakıt Kapasitesi gereklidir."


def test_invalid_and_non_positive_capacity_use_semantic_field_issues() -> None:
    """Fuel-capacity failures retain distinct machine-readable error codes."""
    calculator = TransferPumpCalculator()
    records = [PumpReference("A", 100, 20), PumpReference("B", 200, 30)]

    invalid = calculator.calculate(TransferPumpInput(float("nan"), records))
    non_positive = calculator.calculate(TransferPumpInput(0.0, records))

    assert invalid.errors == [ValidationIssue("valid_number", "field.fuel_capacity")]
    assert non_positive.errors == [ValidationIssue("greater_than_zero", "field.fuel_capacity")]
    assert render_validation_issue(invalid.errors[0], Translator("tr")) == (
        "Yakıt Kapasitesi geçerli bir sayı olmalıdır."
    )


def test_insufficient_references_are_a_semantic_service_precondition() -> None:
    """The service does not return a completed English model-precondition string."""
    service = TransferPumpService(_References([PumpReference("A", 100, 20)]))

    result = service.get_regression_model()

    assert result.errors == [ValidationIssue("insufficient_reference_ships")]
    assert render_validation_issue(result.errors[0], Translator("en")) == (
        "At least two reference ships are required to calculate a regression model."
    )
    assert render_validation_issue(result.errors[0], Translator("tr")) == (
        "Regresyon modelini hesaplamak için en az iki referans gemi gereklidir."
    )


def test_visible_transfer_status_rerenders_when_the_language_changes() -> None:
    """Semantic page status changes language without invoking a calculation service."""
    translator = Translator("en")
    page = TransferPumpPage.__new__(TransferPumpPage)
    page._translate = translator.translate
    page._message = _StringVar()
    page._status_messages = [ValidationIssue("insufficient_reference_ships")]

    page._render_status()
    assert page._message.value == "At least two reference ships are required to calculate a regression model."

    translator.set_language("tr")
    page._render_status()
    assert page._message.value == "Regresyon modelini hesaplamak için en az iki referans gemi gereklidir."

    translator.set_language("en")
    page._render_status()
    assert page._message.value == "At least two reference ships are required to calculate a regression model."


def test_unexpected_transfer_page_failure_hides_raw_exception_text() -> None:
    """The GUI displays a localized generic message instead of technical detail."""
    class _BrokenService:
        """Raise a technical failure from the service boundary."""

        def calculate(self, capacity: float) -> object:
            """Raise the controlled internal error."""
            del capacity
            raise RuntimeError("internal database endpoint detail")

    page = TransferPumpPage.__new__(TransferPumpPage)
    page._translate = Translator("en").translate
    page._capacity = _StringVar("250")
    page._message = _StringVar()
    page._service = _BrokenService()
    page._status_messages = []

    page._calculate()

    assert page._message.value == "An unexpected error occurred. See the application log for details."
    assert "internal database endpoint detail" not in page._message.value
