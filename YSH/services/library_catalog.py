"""Explicit engineering library categories and editable field allowlists."""
from dataclasses import dataclass

from engineering.fire.library import FireEngineeringDataRecord, FIRE_CATEGORIES
from core.material import Material
from core.engineering_constant import EngineeringConstant
from core.pump_reference import PumpReference
from repositories.v2_models import (
    System, Circuit, Fluid, FluidProperty, MaterialProperty, SourceRecord, RuleSet,
    EngineeringConstantMetadata,
)


@dataclass(frozen=True, slots=True)
class LibraryField:
    """One explicitly editable field, independent of database column discovery."""
    name: str
    kind: str = "text"
    optional: bool = False
    target: str | None = None


@dataclass(frozen=True, slots=True)
class LibraryCategory:
    """A meaningful dataset inside one of eight engineering groups."""
    code: str
    group: str
    model: type | None
    fields: tuple[LibraryField, ...] = ()
    parent: str | None = None
    parent_field: str | None = None
    key_field: str = "id"


def field(name: str, kind: str = "text", optional: bool = False,
          target: str | None = None) -> LibraryField:
    """Declare a controlled field without exposing repository internals to the UI."""
    return LibraryField(name, kind, optional, target)


IDENTITY = (field("code"), field("name_tr"), field("name_en", optional=True), field("is_active", "bool"))
PROPERTIES = (field("property_name", "property"), field("value", "float"), field("unit"),
              field("reference_temperature_c", "float", True), field("source_id", "uuid", True, "sources"),
              field("verification_status", "verification", True))
SOURCE_FIELDS = tuple(field(name, kind, optional) for name, kind, optional in (
    ("source_type", "source_type", False), ("source_organization", "text", True),
    ("document", "text", True), ("part", "text", True), ("section", "text", True),
    ("article", "text", True), ("table", "text", True), ("formula", "text", True),
    ("revision", "text", True), ("effective_date", "date", True),
    ("verification_date", "date", True), ("verification_status", "verification", True),
    ("notes", "text", True)))

CATEGORIES = (
    LibraryCategory("systems", "systems", System, IDENTITY),
    LibraryCategory("circuits", "systems", Circuit, (field("system_id", "uuid", target="systems"),) + IDENTITY, "systems", "system_id"),
    LibraryCategory("fluids", "fluids", Fluid, IDENTITY),
    LibraryCategory("fluid_properties", "fluids", FluidProperty,
                    (field("fluid_id", "uuid", target="fluids"),) + PROPERTIES, "fluids", "fluid_id"),
    LibraryCategory("materials", "materials", Material, tuple(field(n,k,o) for n,k,o in (
        ("name","text",False),("designation","text",False),("standard","text",True),
        ("yield_strength_mpa","float",True),("roughness_mm","float",False),
        ("description","text",True),("source","text",True)))),
    LibraryCategory("material_properties", "materials", MaterialProperty,
                    (field("material_id", "uuid", target="materials"),) + PROPERTIES +
                    (field("rule_set_id", "uuid", True, "rule_sets"),), "materials", "material_id"),
    LibraryCategory("pipe_standards", "pipes", None),
    LibraryCategory("pipe_sizes", "pipes", None, parent="pipe_standards", parent_field="standard_id"),
    LibraryCategory("pipe_standard_metadata", "pipes", None, parent="pipe_standards", key_field="standard_id"),
    LibraryCategory("pipe_size_metadata", "pipes", None, parent="pipe_sizes", key_field="pipe_size_id"),
    LibraryCategory("constants", "constants", EngineeringConstant, tuple(field(n,k,o) for n,k,o in (
        ("key","text",False),("display_name","text",False),("value","float",False),
        ("unit","text",True),("description","text",True),("source","text",True)))),
    LibraryCategory("constant_metadata", "constants", EngineeringConstantMetadata,
        (field("constant_id","uuid",target="constants"),field("source_id","uuid",True,"sources"),
         field("rule_set_id","uuid",True,"rule_sets"),field("system_id","uuid",True,"systems"),
         field("circuit_id","uuid",True,"circuits"),field("selection_reason",optional=True)),
        "constants", key_field="constant_id"),
    LibraryCategory("corrosion", "corrosion", None),
    LibraryCategory("corrosion_sources", "corrosion", None, parent="corrosion", key_field="corrosion_circuit_id"),
    LibraryCategory("pump_references", "pumps", PumpReference, tuple(field(n,k,o) for n,k,o in (
        ("ship_name","text",False),("fuel_capacity_m3","float",False),("pump_capacity_m3h","float",False),
        ("description","text",True),("source","text",True)))),
    LibraryCategory("sources", "sources", SourceRecord, SOURCE_FIELDS),
    LibraryCategory("rule_sets", "sources", RuleSet,
        (field("code"),field("name"),field("organization",optional=True),field("revision",optional=True),
         field("effective_date","date",True),field("verification_status","verification",True),
         field("source_id","uuid",True,"sources"),field("is_active","bool"))),
)
CATEGORIES += tuple(LibraryCategory(code, "fire", FireEngineeringDataRecord,
    (field("value","float"),field("unit"),field("context",optional=True),field("service","fire_service"),
     field("applicability",optional=True),field("source_id","uuid",True,"sources"),
     field("source_status","fire_status"),field("notes",optional=True),field("is_active","bool")))
    for code in FIRE_CATEGORIES)
CATEGORY_BY_CODE = {category.code: category for category in CATEGORIES}
PROPERTY_CODES = {
    "fluid_properties": ("density", "kinematic_viscosity", "vapor_pressure"),
    "material_properties": ("Rm", "ReH", "Rp0.2", "allowable_stress", "roughness"),
}
