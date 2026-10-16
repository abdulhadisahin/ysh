"""Service layer for transfer-pump regression calculations."""
from __future__ import annotations
from core.pump_reference import PumpReference
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engineering.transfer_pump.v2_models import TransferPumpDesignInput, TransferPumpDesignResult, TransferPumpEmpiricalInput, TransferPumpEmpiricalResult
from engineering.transfer_pump.calculator import TransferPumpCalculator
from engineering.transfer_pump.models import TransferPumpInput,TransferPumpResult
from engineering.transfer_pump.capacity_basis import FuelCapacityResolution, resolve_fuel_capacity
from engineering.validation import ValidationIssue
class TransferPumpService:
    """Runs pure estimates using saved or temporary reference records."""
    def __init__(self,reference_service:object,calculator:TransferPumpCalculator|None=None)->None:
        """Configure a reference service without UI or SQL dependencies."""
        self._references=reference_service;self._calculator=calculator or TransferPumpCalculator()
    def calculate(self,new_ship_fuel_capacity_m3:float,references:list[PumpReference]|None=None)->TransferPumpResult:
        """Calculate from temporary references or saved service records."""
        records=references if references is not None else self._references.get_all_references()
        return self._calculator.calculate(TransferPumpInput(new_ship_fuel_capacity_m3,records))
    def calculate_from_capacity_input(self, mode: str, source_value: float, references: list[PumpReference] | None = None) -> tuple[FuelCapacityResolution, TransferPumpResult]:
        """Resolve D243 source units, then use the unchanged m³ regression path."""
        resolution = resolve_fuel_capacity(mode, source_value)
        return resolution, self.calculate(resolution.volume_m3, references)
    def get_regression_model(self)->TransferPumpResult:
        """Return the current model without requiring a new-ship estimate input."""
        records=self._references.get_all_references()
        if len(records)<2:return TransferPumpResult(errors=[ValidationIssue("insufficient_reference_ships")])
        return self.calculate(min(item.fuel_capacity_m3 for item in records),records)

    def calculate_v2(
        self, value: TransferPumpDesignInput | TransferPumpEmpiricalInput,
        *, references: list[PumpReference] | None = None,
    ) -> TransferPumpDesignResult | TransferPumpEmpiricalResult:
        """Keep real design and unchanged empirical estimation as distinct paths."""
        from engineering.transfer_pump.v2_models import (
            TransferPumpDesignInput, TransferPumpEmpiricalInput,
            TransferPumpEmpiricalResult, ReferenceVesselSample,
        )
        from engineering.provenance import (
            EngineeringValue, OverridePolicy, SourceReference, SourceType, VerificationStatus,
        )
        if isinstance(value, TransferPumpDesignInput):
            from engineering.transfer_pump.v2_calculator import calculate_design
            return calculate_design(value)
        if not isinstance(value, TransferPumpEmpiricalInput):
            raise TypeError("A typed transfer-pump calculation mode is required")
        records = references if references is not None else self._references.get_all_references()
        resolution, result = self.calculate_from_capacity_input(
            value.capacity_input_mode, value.source_capacity, list(records))
        samples = tuple(ReferenceVesselSample(
            reference_id=row.id, ship_name=row.ship_name,
            fuel_capacity_m3=row.fuel_capacity_m3, pump_capacity_m3_h=row.pump_capacity_m3h,
            description=row.description,
            source=SourceReference(source_type=SourceType.REFERENCE_VESSEL_DATA,
                notes=row.source or None, verification_status=VerificationStatus.UNVERIFIED),
        ) for row in records)
        calculated = None
        if result.is_successful and result.predicted_pump_capacity_m3h is not None:
            capacity = result.predicted_pump_capacity_m3h
            calculated = EngineeringValue(used_value=capacity, unit="m³/h",
                source=SourceReference(source_type=SourceType.CALCULATED,
                    formula="Qpump = m × Vfuel + b"),
                override_policy=OverridePolicy.LOCKED, recommended_value=capacity)
        return TransferPumpEmpiricalResult(input=value, resolution=resolution,
            estimate=result, references=samples, calculated_capacity=calculated)
