"""Serializable inputs and outputs for the pipe-design calculation module."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

def _now() -> datetime:
    return datetime.now(timezone.utc)
@dataclass(slots=True)
class PipeDiameterInput:
    """Input values for required internal pipe diameter."""
    flow_rate_m3h: float
    design_velocity_mps: float
    def to_dict(self) -> dict[str, object]: """Serialize this input."""; return asdict(self)
    @classmethod
    def from_dict(cls,data:dict[str,object])->"PipeDiameterInput": """Deserialize this input."""; return cls(float(data["flow_rate_m3h"]),float(data["design_velocity_mps"]))
@dataclass(slots=True)
class PipeDiameterResult:
    """Result values for diameter and DN selection.

    Warning entries are stable engineering warning codes, rather than rendered
    user-interface text.  Presentation code resolves them through its active
    translation catalogue.
    """
    diameter_m: float
    diameter_mm: float
    minimum_matching_dn: str | None = None
    recommended_dn: str | None = None
    recommended_inside_diameter_mm: float | None = None
    recommended_outside_diameter_mm: float | None = None
    recommended_wall_thickness_mm: float | None = None
    warnings: list[str] = field(default_factory=list)
    def to_dict(self)->dict[str,object]: """Serialize this result.""";return asdict(self)
    @classmethod
    def from_dict(cls,data:dict[str,object])->"PipeDiameterResult": """Deserialize this result.""";return cls(float(data["diameter_m"]),float(data["diameter_mm"]),data.get("minimum_matching_dn") if isinstance(data.get("minimum_matching_dn"),str) else None,data.get("recommended_dn") if isinstance(data.get("recommended_dn"),str) else None,float(data["recommended_inside_diameter_mm"]) if data.get("recommended_inside_diameter_mm") is not None else None,float(data["recommended_outside_diameter_mm"]) if data.get("recommended_outside_diameter_mm") is not None else None,float(data["recommended_wall_thickness_mm"]) if data.get("recommended_wall_thickness_mm") is not None else None,list(data.get("warnings",[])))
@dataclass(slots=True)
class WallThicknessInput:
    """Input values for the approved minimum wall-thickness formula."""
    outside_diameter_mm: float
    design_pressure_bar: float
    yield_strength_mpa: float | None
    safety_factor: float
    weld_factor: float
    corrosion_allowance_mm: float
    bend_allowance_enabled: bool = False
    bend_radius_mm: float | None = None
    def to_dict(self)->dict[str,object]: """Serialize this input.""";return asdict(self)
    @classmethod
    def from_dict(cls,data:dict[str,object])->"WallThicknessInput": """Deserialize this input.""";return cls(float(data["outside_diameter_mm"]),float(data["design_pressure_bar"]),None if data.get("yield_strength_mpa") is None else float(data["yield_strength_mpa"]),float(data["safety_factor"]),float(data["weld_factor"]),float(data["corrosion_allowance_mm"]),bool(data.get("bend_allowance_enabled",False)),None if data.get("bend_radius_mm") is None else float(data["bend_radius_mm"]))
@dataclass(slots=True)
class WallThicknessResult:
    """Full-precision outputs of the wall-thickness calculation."""
    allowable_stress_mpa: float
    base_wall_thickness_mm: float
    bend_allowance_mm: float
    corrosion_allowance_mm: float
    final_wall_thickness_mm: float
    selected_standard_wall_thickness_mm: float | None = None
    def to_dict(self)->dict[str,object]: """Serialize this result.""";return asdict(self)
    @classmethod
    def from_dict(cls,data:dict[str,object])->"WallThicknessResult": """Deserialize this result.""";return cls(**{key:float(value) for key,value in data.items()})
@dataclass(slots=True)
class PipeDesignCalculationResult:
    """Combined pipe-design result with trace metadata and messages."""
    diameter: PipeDiameterResult | None = None
    wall_thickness: WallThicknessResult | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    trace: dict[str, Any] = field(default_factory=dict)
    calculated_at: datetime = field(default_factory=_now)
    @property
    def is_successful(self)->bool: """Return whether the calculation has no errors.""";return not self.errors
    def to_dict(self)->dict[str,object]: """Serialize the combined result.""";return {"diameter":None if self.diameter is None else self.diameter.to_dict(),"wall_thickness":None if self.wall_thickness is None else self.wall_thickness.to_dict(),"warnings":self.warnings,"errors":self.errors,"trace":self.trace,"calculated_at":self.calculated_at.isoformat()}
    @classmethod
    def from_dict(cls,data:dict[str,object])->"PipeDesignCalculationResult": """Deserialize a combined result.""";return cls(PipeDiameterResult.from_dict(data["diameter"]) if isinstance(data.get("diameter"),dict) else None,WallThicknessResult.from_dict(data["wall_thickness"]) if isinstance(data.get("wall_thickness"),dict) else None,list(data.get("warnings",[])),list(data.get("errors",[])),dict(data.get("trace",{})),datetime.fromisoformat(str(data["calculated_at"])))
