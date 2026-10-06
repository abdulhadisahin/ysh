"""Stable engineering context identities used by warning rules and UI state."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FluidSystem:
    code: str
    turkish_label: str


@dataclass(frozen=True, slots=True)
class LineRole:
    code: str
    turkish_label: str


FLUID_SYSTEMS: tuple[FluidSystem, ...] = (
    FluidSystem("DIESEL_FUEL", "Dizel Yakıt"),
    FluidSystem("LUBE_OIL", "Yağlama Yağı"),
    FluidSystem("SEA_WATER", "Deniz Suyu"),
)
LINE_ROLES: tuple[LineRole, ...] = (
    LineRole("SUCTION", "Emiş"),
    LineRole("DELIVERY", "Basma"),
)

FLUID_SYSTEM_BY_CODE = {item.code: item for item in FLUID_SYSTEMS}
LINE_ROLE_BY_CODE = {item.code: item for item in LINE_ROLES}

# Circuit data remains authoritative in the circuit library; this mapping only
# decides whether an enabled Phase 8 warning rule has a matching fluid context.
CIRCUIT_TO_WARNING_FLUID: dict[str, str] = {
    "FUEL": "DIESEL_FUEL",
    "SEA_WATER": "SEA_WATER",
}


def fluid_label(code: str | None) -> str:
    return FLUID_SYSTEM_BY_CODE.get(code or "", FluidSystem("", "")).turkish_label


def line_role_label(code: str | None) -> str:
    return LINE_ROLE_BY_CODE.get(code or "", LineRole("", "")).turkish_label


def warning_fluid_for_circuit(circuit_code: str | None) -> str | None:
    return CIRCUIT_TO_WARNING_FLUID.get(circuit_code or "")
