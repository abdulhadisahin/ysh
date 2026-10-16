"""Typed discharge workflow inputs/results; mathematics stays in the shared core."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID
import math

from engineering.validation import ValidationError, ValidationIssue

from core.local_loss_item import LocalLossItem
from engineering.head_loss.models import DischargeHeadLossResult
from engineering.pipe_design.transfer import PipeInputState


@dataclass(frozen=True, slots=True)
class DischargeLocalLoss:
    """An immutable copy of a page-owned local-loss entry."""

    name: str
    quantity: int
    k_coefficient: float

    def __post_init__(self) -> None:
        if type(self.quantity) is not int:
            raise ValidationError(ValidationIssue("whole_number", "field.quantity"))
        if self.quantity < 0:
            raise ValidationError(ValidationIssue("zero_or_greater", "field.quantity"))
        if (isinstance(self.k_coefficient, bool)
                or not isinstance(self.k_coefficient, (int, float))
                or not math.isfinite(self.k_coefficient)):
            raise ValidationError(ValidationIssue("valid_number", "field.local_loss_k"))
        if self.k_coefficient < 0:
            raise ValidationError(ValidationIssue("zero_or_greater", "field.local_loss_k"))

    def to_item(self) -> LocalLossItem:
        """Adapt without modifying quantity or K semantics."""
        return LocalLossItem(self.name, self.quantity, self.k_coefficient)


@dataclass(frozen=True, slots=True, kw_only=True)
class DischargeV2Input:
    """Applied/manual pipe inputs are separate from discharge-local inputs."""

    pipe_input: PipeInputState
    kinematic_viscosity_m2s: float
    pipe_length_m: float
    roughness_mm: float | None
    geodetic_head_m: float
    local_losses: tuple[DischargeLocalLoss, ...] = ()
    material_id: UUID | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.pipe_input, PipeInputState):
            raise TypeError("pipe_input must be typed PipeInputState")
        if not isinstance(self.local_losses, tuple) or not all(
            isinstance(item, DischargeLocalLoss) for item in self.local_losses
        ):
            raise TypeError("local_losses must be an immutable tuple of DischargeLocalLoss")


@dataclass(slots=True, kw_only=True)
class DischargeV2Result(DischargeHeadLossResult):
    """Core results plus exact used inputs/source, compatible with Formula View."""

    input: DischargeV2Input
    flow_rate_m3_h: float
    actual_internal_diameter_mm: float
    geodetic_head_m: float
