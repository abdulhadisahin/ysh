"""Scoped catalog facts, distinct from specification limits and calculator defaults."""
from dataclasses import dataclass, field
from uuid import UUID, uuid4
from engineering.catalog import numeric


@dataclass(frozen=True, kw_only=True)
class FluidCatalogProfile:
    fluid_id: UUID
    canonical_code: str
    classification: str
    operating_requirements: str
    concentration_percent: float | None = None
    concentration_basis: str = ''
    def __post_init__(self):
        numeric(self.concentration_percent)
        if self.concentration_percent is not None and not 0 <= self.concentration_percent <= 100:
            raise ValueError('Concentration must be percent by stated basis')
        if self.concentration_percent is not None and not self.concentration_basis:
            raise ValueError('Concentration basis required')


@dataclass(frozen=True, kw_only=True)
class OperatingFluidProperty:
    code: str
    fluid_id: UUID
    property_name: str
    value: float
    unit: str
    reference_temperature_c: float
    reference_salinity_g_kg: float
    reference_pressure_mpa: float
    source_key: str
    applicability: str
    verification: str = 'SOURCE_REQUIRED'
    is_active: bool = True
    id: UUID = field(default_factory=uuid4)
    def __post_init__(self):
        numeric(self.value, self.reference_temperature_c, self.reference_salinity_g_kg, self.reference_pressure_mpa)
        if self.value <= 0 or self.reference_salinity_g_kg < 0 or self.reference_pressure_mpa <= 0:
            raise ValueError('Invalid operating property condition')
        if self.property_name not in ('density', 'kinematic_viscosity'):
            raise ValueError('Unsupported operating property')


@dataclass(frozen=True, kw_only=True)
class MechanicalGrade:
    code: str
    designation: str
    material_number: str
    standard: str
    source_key: str
    applicability: str
    national_adoption_status: str = 'SOURCE_REQUIRED'
    requested_standard: str = 'TS EN 10216-1'
    is_active: bool = True
    is_factory: bool = True
    id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, kw_only=True)
class MechanicalGradeProperty:
    code: str
    grade_id: UUID
    property_name: str
    minimum_value: float
    maximum_value: float | None
    thickness_above_mm: float
    thickness_up_to_mm: float
    unit: str
    source_key: str
    applicability: str
    verification: str = 'SOURCE_REQUIRED'
    is_active: bool = True
    id: UUID = field(default_factory=uuid4)
    def __post_init__(self):
        numeric(self.minimum_value, self.maximum_value, self.thickness_above_mm, self.thickness_up_to_mm)
        if self.minimum_value <= 0 or self.thickness_above_mm < 0 or self.thickness_up_to_mm <= self.thickness_above_mm:
            raise ValueError('Invalid mechanical range')
        if self.maximum_value is not None and self.maximum_value < self.minimum_value:
            raise ValueError('Invalid strength range')
        if self.property_name not in ('Rm', 'ReH') or self.unit != 'MPa':
            raise ValueError('Mechanical property is not roughness or allowable stress')
