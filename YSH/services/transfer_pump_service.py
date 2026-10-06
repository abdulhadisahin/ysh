"""Service layer for transfer-pump regression calculations."""
from __future__ import annotations
from core.pump_reference import PumpReference
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
