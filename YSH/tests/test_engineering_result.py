"""Tests for reusable engineering result and message types."""

from __future__ import annotations

from engineering.result import EngineeringMessage, EngineeringResult


def test_successful_result_has_no_errors() -> None:
    """A result without error messages is successful."""
    result = EngineeringResult(value=12.5, unit="m")

    assert result.is_successful
    assert not result.has_warnings
    assert not result.has_errors


def test_result_reports_warnings_and_errors() -> None:
    """Warning and error messages are reflected in result state properties."""
    result = EngineeringResult(value=12.5, unit="m")
    result.add_info("SOURCE", "Input accepted")
    result.add_warning("CHECK", "Review input")
    result.add_error("INVALID", "Calculation cannot continue")

    assert len(result.messages) == 3
    assert result.has_warnings
    assert result.has_errors
    assert not result.is_successful


def test_result_serialization_preserves_messages_and_metadata() -> None:
    """Result serialization round-trips all traceability information."""
    result = EngineeringResult(
        value=12.3456789,
        unit="kPa",
        messages=[EngineeringMessage("INFO", "SOURCE", "Input accepted")],
        metadata={"project_id": "project-1", "input_count": 3},
    )
    result.add_warning("CHECK", "Review result")

    restored_result = EngineeringResult.from_dict(result.to_dict())

    assert restored_result.to_dict() == result.to_dict()


def test_result_serialization_preserves_an_empty_unit_string() -> None:
    """An empty unit remains valid when a result has no dimensional value."""
    result = EngineeringResult(value=None, unit="")

    restored_result = EngineeringResult.from_dict(result.to_dict())

    assert restored_result.to_dict() == result.to_dict()
