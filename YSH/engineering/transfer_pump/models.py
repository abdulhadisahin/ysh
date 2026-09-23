"""Models for linear fuel transfer pump estimates."""
from __future__ import annotations
from dataclasses import dataclass,field,asdict
from core.pump_reference import PumpReference
from engineering.validation import ValidationIssue
@dataclass(slots=True)
class TransferPumpInput:
    """New ship capacity and reference records."""
    new_ship_fuel_capacity_m3:float; reference_records:list[PumpReference]
@dataclass(slots=True)
class LinearRegressionModel:
    """Ordinary least-squares linear regression data."""
    slope:float;intercept:float;r_squared:float;reference_count:int;minimum_reference_capacity_m3:float;maximum_reference_capacity_m3:float
@dataclass(slots=True)
class TransferPumpResult:
    """Predicted capacity, emptying time, semantic messages, and trace data."""
    predicted_pump_capacity_m3h:float|None=None;estimated_emptying_time_hours:float|None=None;estimated_emptying_time_minutes:float|None=None;regression_model:LinearRegressionModel|None=None;errors:list[ValidationIssue]=field(default_factory=list);warnings:list[ValidationIssue]=field(default_factory=list);metadata:dict[str,object]=field(default_factory=dict)
    @property
    def is_successful(self)->bool: """Return whether the result contains no semantic errors.""";return not self.errors
