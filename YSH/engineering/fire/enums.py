"""Stable Fire identities, independent of visible modules and snapshot schemas."""
from enum import StrEnum
from types import MappingProxyType


class FireCalculationType(StrEnum):
    FIRE_FOAM_SYSTEM = "fire_foam_system"
    FIRE_HAZEN_WILLIAMS = "fire_hazen_williams"
    FIRE_NOZZLE = "fire_nozzle"


class FireSourceStatus(StrEnum):
    SOURCE_VERIFIED = "SOURCE_VERIFIED"
    SOURCE_VERIFIED_CONTEXT_DEPENDENT = "SOURCE_VERIFIED_CONTEXT_DEPENDENT"
    WORKBOOK_REFERENCE_ONLY = "WORKBOOK_REFERENCE_ONLY"
    USER_PROJECT_ASSUMPTION = "USER_PROJECT_ASSUMPTION"
    DERIVED_FROM_VERIFIED_RULE = "DERIVED_FROM_VERIFIED_RULE"
    SOURCE_REQUIRED = "SOURCE_REQUIRED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    SOURCE_IDENTIFIED_BUT_NOT_ACCESSIBLE = "SOURCE_IDENTIFIED_BUT_NOT_ACCESSIBLE"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class FoamMixtureBasis(StrEnum):
    CONCENTRATE_VOLUME_PER_SOLUTION_VOLUME = "CONCENTRATE_VOLUME_PER_SOLUTION_VOLUME"


class HWApplicability(StrEnum):
    WATER_ONLY = "WATER_ONLY"
    SEAWATER_SOURCE_REQUIRED = "SEAWATER_SOURCE_REQUIRED"
    OTHER_FLUID_SOURCE_REQUIRED = "OTHER_FLUID_SOURCE_REQUIRED"
    NOT_CONFIGURED = "NOT_CONFIGURED"


class FireRuleId(StrEnum):
    SOLUTION_FLOW = "FIRE.FOAM.SOLUTION_FLOW"
    CONCENTRATE_FLOW = "FIRE.FOAM.CONCENTRATE_FLOW"
    WATER_FLOW = "FIRE.FOAM.WATER_FLOW"
    CONCENTRATE_VOLUME = "FIRE.FOAM.CONCENTRATE_VOLUME"
    HW_EQUATION = "FIRE.HW.EQUATION"
    NOZZLE_RELATION = "FIRE.NOZZLE.K_FACTOR_RELATION"


# No regulatory values or UI text. Keys are the canonical domain field names.
SYMBOLS = MappingProxyType({
    "protected_area_m2": "A", "application_density_lpm_m2": "q",
    "application_duration_min": "t", "foam_fraction": "Cfoam",
    "solution_flow_lpm": "Qsolution", "foam_concentrate_flow_lpm": "Qfoam",
    "water_flow_lpm": "Qwater", "foam_concentrate_volume_l": "Vfoam",
    "hazen_williams_c": "CHW", "inside_diameter_mm": "Di",
    "pipe_length_m": "L", "pressure_loss_per_m_bar": "rHW",
    "total_pressure_loss_bar": "ΔpHW", "nozzle_k": "Knozzle",
})
