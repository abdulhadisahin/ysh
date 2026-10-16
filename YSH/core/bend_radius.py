"""D243 bend-radius product convention for pipe wall-thickness input."""

from __future__ import annotations

from dataclasses import dataclass
import math
from enum import StrEnum


class BendState(StrEnum):
    """Explicit engineering state; no radius/coefficient serves as an OFF flag."""
    NO_BEND = "NO_BEND"
    BEND_APPLIES = "BEND_APPLIES"


@dataclass(frozen=True, slots=True)
class BendRadiusMode:
    """Stable bend-radius mode metadata, independent of its visible label."""

    code: str
    label: str
    multiplier: float | None

    @property
    def is_manual(self) -> bool:
        return self.code == "MANUAL"

    @property
    def applies(self) -> bool:
        """Separate the explicit no-bend state from every radius choice."""
        return self.code != "NO_BEND"


BEND_RADIUS_MODES: tuple[BendRadiusMode, ...] = (
    BendRadiusMode("NO_BEND", "Bükme yok", None),
    BendRadiusMode("D1_5", "1.5D", 1.5),
    BendRadiusMode("D2", "2D", 2.0),
    BendRadiusMode("D3", "3D", 3.0),
    BendRadiusMode("D5", "5D", 5.0),
    BendRadiusMode("D10", "10D", 10.0),
    BendRadiusMode("MANUAL", "Manuel", None),
)
DEFAULT_BEND_RADIUS_MODE = "D3"

_BY_CODE = {mode.code: mode for mode in BEND_RADIUS_MODES}


def bend_radius_mode(code: str | None) -> BendRadiusMode:
    """Return a supported mode, defaulting legacy state to the D243 3D mode."""
    return _BY_CODE.get(code or DEFAULT_BEND_RADIUS_MODE, _BY_CODE[DEFAULT_BEND_RADIUS_MODE])


def automatic_bend_radius_mm(mode_code: str, outside_diameter_mm: float) -> float:
    """Return R = multiplier × da for an automatic D243 bend mode.

    ``D`` is explicitly the authoritative pipe outside diameter ``da``.  This
    product convention does not claim to be a Turkish Lloyd requirement.
    """
    mode = bend_radius_mode(mode_code)
    if not mode.applies:
        raise ValueError("No bend has no radius.")
    if mode.is_manual:
        raise ValueError("Manual bend radius has no automatic multiplier.")
    if isinstance(outside_diameter_mm, bool) or not isinstance(outside_diameter_mm, (int, float)):
        raise ValueError("Outside diameter must be a finite positive number.")
    if not math.isfinite(outside_diameter_mm) or outside_diameter_mm <= 0:
        raise ValueError("Outside diameter must be a finite positive number.")
    assert mode.multiplier is not None
    return mode.multiplier * float(outside_diameter_mm)


def bend_mode_from_state(mode_code: str | None, enabled: bool, *, radius_present: bool = False) -> str:
    """Map legacy boolean state without reinterpreting active bends as straight pipe."""
    if not enabled:
        return "NO_BEND"
    if mode_code is None and radius_present:
        return "MANUAL"
    return bend_radius_mode(mode_code).code
