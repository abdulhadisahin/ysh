"""Typed suction/ENPY composition; all arithmetic remains in Phase 5 calculators."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from engineering.head_loss.models import DischargeHeadLossResult
from engineering.head_loss.v2_models import DischargeLocalLoss
from engineering.pipe_design.transfer import PipeInputState
from engineering.suction_npsh.models import SuctionNPSHResult


@dataclass(frozen=True, slots=True, kw_only=True)
class SuctionV2Input:
    """Local suction inputs are independent of the applied pipe snapshot."""

    pipe_input: PipeInputState
    viscosity: float
    viscosity_unit: str
    pipe_length_m: float
    roughness_mm: float | None
    local_losses: tuple[DischargeLocalLoss, ...] = ()
    material_id: UUID | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.pipe_input, PipeInputState):
            raise TypeError("pipe_input must be PipeInputState")
        if not isinstance(self.local_losses, tuple) or not all(
            isinstance(item, DischargeLocalLoss) for item in self.local_losses
        ):
            raise TypeError("local_losses must be immutable typed entries")


@dataclass(frozen=True, slots=True, kw_only=True)
class ENPYV2Input:
    """Raw local pressures/units, density, signed HEgeo and external optional NPSHr."""

    suction_pressure: float
    suction_pressure_unit: str
    vapour_pressure: float
    vapour_pressure_unit: str
    density_kg_m3: float
    static_suction_height_m: float
    npsh_required_m: float | None = None


@dataclass(slots=True, kw_only=True)
class SuctionV2LossResult(DischargeHeadLossResult):
    """Full hydraulic results plus exact applied Q/Di and local input provenance."""

    input: SuctionV2Input
    flow_rate_m3_h: float
    actual_internal_diameter_mm: float


@dataclass(slots=True, kw_only=True)
class SuctionV2Result(SuctionNPSHResult):
    """ENPY outputs composed with hydraulics, preserving existing result properties."""

    hydraulic: SuctionV2LossResult
    input: ENPYV2Input

    @property
    def flow_rate_m3_h(self) -> float:
        """Return exact Q used in the hydraulic stage."""
        return self.hydraulic.flow_rate_m3_h

    @property
    def actual_internal_diameter_mm(self) -> float:
        """Return actual applied Di; theoretical D is never a substitute."""
        return self.hydraulic.actual_internal_diameter_mm

    @property
    def suction_loss_m(self) -> float:
        """Keep the existing Formula View's staged loss alias available."""
        return self.suction_line_loss_m
