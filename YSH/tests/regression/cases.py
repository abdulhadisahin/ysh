"""Deterministic calculation scenarios for golden-value regression tests.

Every scenario uses explicit inputs (no random ids, clocks or user data) so the
normalised result is identical on every machine until a calculation really changes.
"""
from __future__ import annotations

import dataclasses
import enum
import uuid
from typing import Any, Callable

from core.local_loss_item import LocalLossItem
from core.pump_reference import PumpReference
from engineering.pipe_design.models import PipeDiameterInput, WallThicknessInput
from engineering.transfer_pump.v2_models import TransferPumpDesignInput, TransferPumpEmpiricalInput
from services.discharge_head_loss_service import DischargeHeadLossService
from engineering.formula.pipe import legacy_pipe_steps
from services.pipe_design_service import PipeDesignService
from services.suction_npsh_service import SuctionNPSHService
from services.transfer_pump_service import TransferPumpService
from types import SimpleNamespace

DROP_KEYS = {"id", "reference_id", "created_at", "updated_at"}


def normalise(value: Any) -> Any:
    """Turn results into plain JSON-compatible data; ids and timestamps are dropped."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: normalise(getattr(value, f.name)) for f in dataclasses.fields(value) if f.name not in DROP_KEYS}
    if isinstance(value, enum.Enum):
        return value.name
    if isinstance(value, uuid.UUID):
        return "<uuid>"
    if isinstance(value, dict):
        return {str(k): normalise(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0])) if str(k) not in DROP_KEYS}
    if isinstance(value, (list, tuple)):
        return [normalise(v) for v in value]
    if isinstance(value, float):
        return value
    if isinstance(value, (int, str, bool)) or value is None:
        return value
    if hasattr(value, "to_dict"):
        return normalise(value.to_dict())
    return repr(value)


LOSSES = [LocalLossItem("Dirsek 90°", 4, 0.9), LocalLossItem("Küresel vana", 2, 0.2), LocalLossItem("Süzgeç", 1, 1.5)]


def _references() -> list[PumpReference]:
    rows = (("A", 100, 20), ("B", 200, 30), ("C", 300, 40), ("D", 450, 52))
    return [PumpReference(n, v, c, source="regression", id=uuid.UUID(int=i)) for i, (n, v, c) in enumerate(rows, 1)]


def scenarios(material_service, pipe_size_service, engineering_constant_service) -> dict[str, Callable[[], Any]]:
    pipe = PipeDesignService(material_service, pipe_size_service, engineering_constant_service)
    discharge = DischargeHeadLossService(material_service)
    suction = SuctionNPSHService(material_service)
    transfer = TransferPumpService(SimpleNamespace(get_all_references=_references))

    def wall(da, pc, rp, sf, wf, c, bend=False, radius=None):
        return lambda: pipe.calculate(wall=WallThicknessInput(da, pc, rp, sf, wf, c, bend, radius)).wall_thickness

    cases: dict[str, Callable[[], Any]] = {
        "pipe_diameter_q34_v2": lambda: pipe.calculate(diameter=PipeDiameterInput(34, 2.0), standard_code="EN 10220").diameter,
        "pipe_diameter_q120_v1_5": lambda: pipe.calculate(diameter=PipeDiameterInput(120, 1.5), standard_code="EN 10220").diameter,
        "pipe_diameter_q5_v0_8": lambda: pipe.calculate(diameter=PipeDiameterInput(5, 0.8), standard_code="EN 10220").diameter,
        "pipe_wall_straight": wall(88.9, 16, 195, 1.8, 0.85, 1.0),
        "pipe_wall_high_pressure": wall(168.3, 40, 235, 1.5, 1.0, 1.5),
        "pipe_wall_bend_3d": wall(88.9, 16, 195, 1.8, 0.85, 1.0, True, 266.7),
        "pipe_wall_bend_manual": wall(60.3, 10, 240, 1.6, 0.9, 0.5, True, 300.0),
        "pipe_formula_steps_diameter": lambda: legacy_pipe_steps(pipe.calculate(diameter=PipeDiameterInput(34, 2.0), standard_code="EN 10220")),
        "pipe_formula_steps_wall": lambda: legacy_pipe_steps(pipe.calculate(wall=WallThicknessInput(88.9, 16, 195, 1.8, 0.85, 1.0, True, 266.7))),
        "discharge_basic": lambda: discharge.calculate(80.0, 45.0, 3.0e-6, 120.0, 0.045, 18.0, LOSSES),
        "discharge_low_flow_laminar": lambda: discharge.calculate(50.0, 1.0, 5.0e-6, 30.0, 0.045, 5.0, []),
        "discharge_high_flow": lambda: discharge.calculate(150.0, 220.0, 2.5e-6, 400.0, 0.1, 35.0, LOSSES),
        "suction_loss": lambda: suction.calculate_suction_loss(100.0, 60.0, 3.0, "cSt", 25.0, 0.045, LOSSES),
        "suction_enpy": lambda: suction.calculate_enpy(1.2, 1.2, "bar", 0.03, "bar", 850.0, 2.0, 4.0),
        "suction_full": lambda: suction.calculate(100.0, 60.0, 3.0, "cSt", 25.0, 0.045, LOSSES, 1.2, "bar", 0.03, "bar", 850.0, 2.0, 4.0),
        "transfer_design": lambda: transfer.calculate_v2(TransferPumpDesignInput(transfer_volume_m3=120.1, target_transfer_time_h=3, selected_pump_capacity_m3_h=45)),
        "transfer_design_no_pump": lambda: transfer.calculate_v2(TransferPumpDesignInput(transfer_volume_m3=300, target_transfer_time_h=4)),
        "transfer_empirical_volume": lambda: transfer.calculate_v2(TransferPumpEmpiricalInput(source_capacity=250)),
        "transfer_empirical_second": lambda: transfer.calculate_v2(TransferPumpEmpiricalInput(source_capacity=420)),
        "transfer_regression_model": lambda: transfer.get_regression_model(),
    }
    return cases


def run_all(material_service, pipe_size_service, engineering_constant_service) -> dict[str, Any]:
    out = {}
    for name, call in scenarios(material_service, pipe_size_service, engineering_constant_service).items():
        out[name] = normalise(call())
    return out
