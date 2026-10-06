"""User-facing numeric formatting for the Turkish D243 interface."""

from __future__ import annotations

from engineering.precision import format_engineering_value


DISPLAY_DECIMAL_PLACES = 2


def format_user_number(value: object) -> str:
    """Format a finite engineering value for display without altering its value.

    The application keeps full precision in calculation and persistence layers.
    This presentation helper alone applies the D243 two-decimal Turkish format.
    """
    formatted = format_engineering_value(value, DISPLAY_DECIMAL_PLACES)
    integer, fraction = formatted.split(".", 1)
    grouped_integer = f"{int(integer):,}".replace(",", ".")
    return f"{grouped_integer},{fraction}"
