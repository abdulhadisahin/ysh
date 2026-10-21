"""Explicit Fire boundaries; existing pressure conversion remains authoritative."""
from engineering.units import convert_pressure
from engineering.fire.validation import finite, fraction

PERCENT_PER_FRACTION = 100.0
LITRES_PER_CUBIC_METRE = 1000.0
MINUTES_PER_HOUR = 60.0


def _scaled(value: float, factor: float, field: str) -> float:
    return finite(finite(value, field) * factor, field)


def percent_to_fraction(value: float) -> float:
    return fraction(finite(value, "percent") / PERCENT_PER_FRACTION,
                    "percent", endpoints=True)


def fraction_to_percent(value: float) -> float:
    return fraction(value, "fraction", endpoints=True) * PERCENT_PER_FRACTION


def lpm_to_m3h(value: float) -> float:
    return _scaled(value, MINUTES_PER_HOUR / LITRES_PER_CUBIC_METRE, "flow_lpm")


def m3h_to_lpm(value: float) -> float:
    return _scaled(value, LITRES_PER_CUBIC_METRE / MINUTES_PER_HOUR, "flow_m3h")


def litres_to_m3(value: float) -> float:
    return _scaled(value, 1 / LITRES_PER_CUBIC_METRE, "volume_l")


def m3_to_litres(value: float) -> float:
    return _scaled(value, LITRES_PER_CUBIC_METRE, "volume_m3")


def bar_to_pa(value: float) -> float:
    return finite(convert_pressure(finite(value, "pressure_bar"), "bar", "Pa"), "pressure_pa")


def pa_to_bar(value: float) -> float:
    return finite(convert_pressure(finite(value, "pressure_pa"), "Pa", "bar"), "pressure_bar")
