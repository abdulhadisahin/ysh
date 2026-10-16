"""Deterministic selection from supplied real pipe rows; no standards catalog."""
from __future__ import annotations

from collections.abc import Sequence
import math
from uuid import UUID

from engineering.pipe_design.v2_models import PipeCandidate
from engineering.pipe_design.validation import _positive, _non_negative


def select_pipe_candidate(
    required_internal_diameter_mm: float, candidates: Sequence[PipeCandidate],
    standard_id: UUID, *, standard_code: str | None = None,
) -> PipeCandidate | None:
    """Smallest adequate actual ID, then OD, wall, labels, and stable row UUID."""
    _positive(required_internal_diameter_mm, "result.calculated_diameter")
    eligible = [p for p in candidates if p.standard_id == standard_id
                and (standard_code is None or p.standard_code is not None and p.standard_code.casefold() == standard_code.casefold())
                and p.actual_internal_diameter_mm >= required_internal_diameter_mm]
    return min(eligible, key=lambda p: (
        p.actual_internal_diameter_mm, p.outside_diameter_mm, p.wall_thickness_mm,
        p.nominal_diameter or "", p.nps or "", p.schedule or "", str(p.id),
    )) if eligible else None


def select_standard_wall(
    required_wall_mm: float, candidate: PipeCandidate, candidates: Sequence[PipeCandidate],
    *, required_internal_diameter_mm: float | None = None,
) -> PipeCandidate | None:
    """Smallest adequate wall in the chosen standard/nominal-size/OD context.

    An optional ID constraint also protects final velocity after thicker-wall
    selection. No standard/nominal-size substitution or thickness rounding occurs.
    """
    _non_negative(required_wall_mm, "result.required_wall_thickness")
    if required_internal_diameter_mm is not None:
        _positive(required_internal_diameter_mm, "result.calculated_diameter")
    eligible = [p for p in candidates if p.standard_id == candidate.standard_id
                and (p.standard_code or "").casefold() == (candidate.standard_code or "").casefold()
                and p.nominal_diameter == candidate.nominal_diameter and p.nps == candidate.nps
                and p.outside_diameter_mm == candidate.outside_diameter_mm
                and p.wall_thickness_mm >= required_wall_mm
                and (required_internal_diameter_mm is None or p.actual_internal_diameter_mm >= required_internal_diameter_mm)]
    return min(eligible, key=lambda p: (p.wall_thickness_mm, p.actual_internal_diameter_mm,
                                      p.schedule or "", str(p.id))) if eligible else None


def actual_velocity(flow_rate_m3_h: float, inside_diameter_mm: float) -> float:
    """Calculate Vreal using the final actual ID, with m³/h and mm inputs."""
    _positive(flow_rate_m3_h, "field.flow_rate")
    _positive(inside_diameter_mm, "field.pipe_inside_diameter")
    return (4 * (flow_rate_m3_h / 3600)) / (math.pi * (inside_diameter_mm / 1000) ** 2)
