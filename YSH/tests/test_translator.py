"""Tests for offline localization readiness."""

from __future__ import annotations

from i18n.translator import Translator


def test_known_and_formatted_messages() -> None:
    """Resolve registered English keys and formatting placeholders."""
    translator = Translator()
    assert translator.translate("common.clear") == "Clear"
    assert translator.translate("validation.required", field_name="Flow") == "Flow is required."


def test_missing_key_and_turkish_registration_are_safe() -> None:
    """Allow a future Turkish catalogue without incomplete visible translations."""
    translator = Translator("tr")
    translator.register("tr", {"common.clear": "Temizle"})
    assert translator.translate("common.clear") == "Temizle"
    assert translator.translate("missing.key") == "missing.key"
