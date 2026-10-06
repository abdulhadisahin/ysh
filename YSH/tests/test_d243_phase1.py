"""Focused contracts for the D243 Phase 1 product foundation."""

from __future__ import annotations

from engineering.input_parsing import parse_engineering_float
from i18n.manager import LocalizationManager
from YSH.product import PRODUCT_FULL_NAME, PRODUCT_SHORT_NAME
from ui.formatting import DISPLAY_DECIMAL_PLACES, format_user_number


def test_d243_identity_is_centralized() -> None:
    """Visible product naming has one authoritative source."""
    assert PRODUCT_SHORT_NAME == "D243"
    assert PRODUCT_FULL_NAME == "D243 Boru ve Tulumba Boyutlandırma Programı"


def test_turkish_display_formatter_keeps_internal_value_unchanged() -> None:
    """Formatting is a presentation-only two-decimal conversion."""
    value = 12.347891
    assert DISPLAY_DECIMAL_PLACES == 2
    assert format_user_number(value) == "12,35"
    assert format_user_number(12) == "12,00"
    assert format_user_number(0.5) == "0,50"
    assert value == 12.347891


def test_input_parser_accepts_both_decimal_separators() -> None:
    """Turkish rendering does not restrict existing input compatibility."""
    assert parse_engineering_float("12,5", field_name="x") == 12.5
    assert parse_engineering_float("12.5", field_name="x") == 12.5


def test_localization_manager_forces_turkish_despite_saved_english(tmp_path) -> None:
    """A V1 English preference cannot re-enable visible English UI."""
    settings = tmp_path / "settings.json"
    settings.write_text('{"language": "en"}', encoding="utf-8")
    manager = LocalizationManager(settings)
    assert manager.language == "tr"
    assert manager.translate("page.pipe.tab") == "Boru Tasarımı"
