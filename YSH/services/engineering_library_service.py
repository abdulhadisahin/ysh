"""Read-first library use cases; no seed, calculator, project or hard-delete API."""
from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import date, datetime, timezone
from enum import Enum
import math
import re
from functools import wraps
from uuid import UUID
from collections.abc import Callable
from sqlite3 import DatabaseError, IntegrityError

from database.library_database import LibraryDatabase
from engineering.provenance import SourceReference, SourceType, VerificationStatus
from engineering.input_parsing import parse_engineering_float
from engineering.validation import ValidationError
from repositories.system_repository import SystemRepository
from repositories.circuit_repository import CircuitRepository
from repositories.fluid_repository import FluidRepository
from repositories.fluid_property_repository import FluidPropertyRepository
from repositories.material_property_repository import MaterialPropertyRepository
from repositories.material_repository import MaterialRepository, MaterialRepositoryConflictError
from repositories.pipe_size_repository import PipeSizeRepository
from repositories.pipe_metadata_repository import PipeStandardMetadataRepository, PipeSizeMetadataRepository
from repositories.engineering_constant_repository import EngineeringConstantRepository, EngineeringConstantRepositoryConflictError
from repositories.engineering_constant_metadata_repository import EngineeringConstantMetadataRepository
from repositories.corrosion_allowance_circuit_repository import CorrosionAllowanceCircuitRepository
from repositories.corrosion_source_repository import CorrosionSourceRepository
from repositories.pump_reference_repository import PumpReferenceRepository
from repositories.source_repository import SourceRepository
from repositories.rule_set_repository import RuleSetRepository
from repositories.v2_errors import RepositoryError, RepositoryConflictError, RepositoryForeignKeyError
from services.library_catalog import CATEGORY_BY_CODE, PROPERTY_CODES
from engineering.fire.library import FireEngineeringDataRecord, FIRE_CATEGORIES
from engineering.fire.enums import FireSourceStatus
from repositories.fire_library_repository import FireLibraryRepository, FIRE_RECORD_PREFIX
from services.system_context_service import DEFAULT_SYSTEMS


class LibraryError(ValueError):
    """A localized stable UI error code, without a database traceback."""
    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(key)


@dataclass(frozen=True, slots=True)
class LibraryDetails:
    """Compose one selected record only, including optional linked provenance."""
    values: tuple[tuple[str, object], ...]
    sources: tuple[SourceReference, ...]
    ownership: str
    editable: bool


def readable_errors(method: Callable[..., object]) -> Callable[..., object]:
    """Translate read failures at the service boundary, never in Tk/SQL code."""
    @wraps(method)
    def wrapped(*args: object, **kwargs: object) -> object:
        try:
            return method(*args, **kwargs)
        except LibraryError:
            raise
        except (RepositoryError, DatabaseError, KeyError, ValueError, TypeError) as error:
            raise LibraryError("library2.error.storage") from error
    return wrapped


class EngineeringLibraryService:
    """Reuse existing repositories; construct lazily when Libraries is opened."""

    def __init__(self, database: LibraryDatabase) -> None:
        """Instantiate adapters without loading any dataset or initializing storage."""
        self._repos = {code: cls(database) for code, cls in (
            ("systems",SystemRepository),("circuits",CircuitRepository),("fluids",FluidRepository),
            ("fluid_properties",FluidPropertyRepository),("materials",MaterialRepository),
            ("material_properties",MaterialPropertyRepository),("pipe_standards",PipeSizeRepository),
            ("pipe_sizes",PipeSizeRepository),("pipe_standard_metadata",PipeStandardMetadataRepository),
            ("pipe_size_metadata",PipeSizeMetadataRepository),("constants",EngineeringConstantRepository),
            ("constant_metadata",EngineeringConstantMetadataRepository),("corrosion",CorrosionAllowanceCircuitRepository),
            ("corrosion_sources",CorrosionSourceRepository),("pump_references",PumpReferenceRepository),
            ("sources",SourceRepository),("rule_sets",RuleSetRepository))}
        self.fire_records = FireLibraryRepository(database)
        self._source_cache: dict[UUID, SourceReference | None] = {}
        self._application_ids: set[UUID] = set()

    @readable_errors
    def list_records(self, category: str, parent_id: UUID | None = None) -> tuple:
        """Read only the requested dataset; relationships are selected explicitly."""
        if category in FIRE_CATEGORIES:
            return tuple(r for r in self.fire_records.get_all() if r.parameter_type==FIRE_CATEGORIES[category])
        repo = self._repos[category]
        if category == "systems":
            stored = repo.get_all()
            codes = {r.code.upper() for r in stored}
            identities = {r.id for r in stored}
            defaults = tuple(r for r in DEFAULT_SYSTEMS if r.code not in codes and r.id not in identities)
            self._application_ids = {row.id for row in defaults}
            rows = (*stored, *defaults)
        elif category in ("circuits", "fluid_properties", "material_properties"):
            if parent_id is None:
                return ()
            method = {"circuits":"get_by_system","fluid_properties":"get_by_fluid","material_properties":"get_by_material"}[category]
            rows = getattr(repo, method)(parent_id)
        elif category == "pipe_standards":
            rows = repo.list_standards()
        elif category == "pipe_sizes":
            rows = repo.list_for_standard(parent_id) if parent_id else repo.get_all()
        elif category in ("pipe_standard_metadata", "pipe_size_metadata", "constant_metadata", "corrosion_sources"):
            row = repo.get(parent_id) if parent_id else None
            rows = (row,) if row else ()
        elif category == "corrosion":
            rows = repo.list()
        else:
            rows = repo.get_all()
        if category == 'constants':
            rows=tuple(row for row in rows if not row.key.startswith(FIRE_RECORD_PREFIX))
        return tuple(sorted(rows, key=self._sort_key))

    @staticmethod
    def _sort_key(row: object) -> tuple:
        label = next((str(getattr(row, key)) for key in ("code","designation","key","ship_name","nominal_diameter","property_name")
                      if hasattr(row,key)), "")
        if hasattr(row,"reference"):
            label = ' '.join(value or '' for value in (row.reference.source_organization,row.reference.document,row.reference.revision))
        natural = tuple((1,int(part)) if part.isdigit() else (0,part)
                        for part in re.split(r'(\d+)',label.casefold()))
        return (natural, getattr(row,"reference_temperature_c",None) is None,
                getattr(row,"reference_temperature_c",None) or 0, str(getattr(row,"revision","") or ""),
                str(getattr(row,"id",getattr(row,"pipe_size_id",""))))

    @readable_errors
    def get_record(self, category: str, identity: UUID) -> object | None:
        """Read persisted truth before an edit; application defaults never become DB rows."""
        if category in FIRE_CATEGORIES:
            record=self.fire_records.get(identity)
            return record if record and record.parameter_type==FIRE_CATEGORIES[category] else None
        repo = self._repos[category]
        method = "get_standard" if category == "pipe_standards" else "get_by_id" if category == "pump_references" else "get"
        record=getattr(repo, method)(identity)
        if category=='constants' and record and record.key.startswith(FIRE_RECORD_PREFIX):return None
        return record

    def ownership(self, category: str, record: object) -> str:
        """Ambiguous reference ownership is conservative, not assumed to be user data."""
        if category in FIRE_CATEGORIES:
            return 'user'
        if category == "systems" and getattr(record,"id",None) in self._application_ids:
            return "application"
        if getattr(record,"is_factory",False) or getattr(record,"is_system",False):
            return "factory"
        if CATEGORY_BY_CODE[category].model is None:
            return "reference"
        status = getattr(getattr(record,"reference",record),"verification_status",None)
        if category in ("sources","rule_sets","fluid_properties","material_properties") and status is None:
            return "reference"
        if status in (VerificationStatus.VERIFIED,VerificationStatus.PARTIALLY_VERIFIED,VerificationStatus.DEPRECATED):
            return "reference"
        return "user"

    def can_edit(self, category: str, record: object) -> bool:
        """Protect core reference truth and metadata attached to protected constants."""
        if self.ownership(category, record) != "user":
            return False
        if category == "constant_metadata":
            parent = self.get_record("constants",record.constant_id)
            return parent is not None and not parent.is_system
        return True

    @readable_errors
    def details(self, category: str, record: object) -> LibraryDetails:
        """Compose raw fields and one cached source lookup per selected linkage."""
        data = tuple((f.name,getattr(record,f.name)) for f in fields(record)
                     if getattr(record,f.name) is not None and f.name!='reference'
                     and not (category in FIRE_CATEGORIES and f.name in ('source','system_family')))
        sources = []
        if category == "sources":
            sources.append(record.reference)
        if category in FIRE_CATEGORIES and record.source:
            sources.append(record.source)
        if category == "pump_references":
            sources.append(SourceReference(source_type=SourceType.REFERENCE_VESSEL_DATA,
                                           notes=record.source or None))
        source_id = getattr(record,"source_id",None)
        if source_id is not None and category not in FIRE_CATEGORIES:
            if source_id not in self._source_cache:
                row = self._repos["sources"].get(source_id)
                self._source_cache[source_id] = row.reference if row else None
            if self._source_cache[source_id] is not None:
                sources.append(self._source_cache[source_id])
        linked = {"pipe_standards":"pipe_standard_metadata","pipe_sizes":"pipe_size_metadata",
                  "constants":"constant_metadata","corrosion":"corrosion_sources"}.get(category)
        if linked:
            extra = self._repos[linked].get(record.id)
            if extra is not None:
                detail = self.details(linked,extra)
                data += tuple((key,value) for key,value in detail.values if key not in dict(data))
                sources.extend(detail.sources)
        return LibraryDetails(data,tuple(dict.fromkeys(sources)),self.ownership(category,record),self.can_edit(category,record))

    def refresh(self) -> None:
        """Invalidate display-only provenance caches on an explicit refresh action."""
        self._source_cache.clear()

    @readable_errors
    def fire_recommendations(self,parameter,context,service):
        return tuple(record for record in self.fire_records.get_all()
                     if record.parameter_type==parameter and record.recommendable
                     and record.applicable(context,service))

    @readable_errors
    def fire_records_for_context(self,context,service):
        return tuple(sorted((record for record in self.fire_records.get_all()
            if record.recommendable and record.applicable(context,service)),
            key=lambda record:(record.parameter_type.value,record.context,str(record.id))))

    @readable_errors
    def get_fire_record(self,identity):
        return self.fire_records.get(identity)

    def form_values(self, category: str, record: object) -> dict[str, object]:
        """Return unrounded edit values; SourceRecord's nested metadata is flattened."""
        target = record.reference if category == "sources" else record
        return {field.name:getattr(target,field.name) for field in CATEGORY_BY_CODE[category].fields}

    def save(self, category: str, values: dict[str, object], identity: UUID | None = None) -> object:
        """Validate the full edit, then perform exactly one atomic repository write."""
        definition = CATEGORY_BY_CODE[category]
        if definition.model is None:
            raise LibraryError("library2.error.protected")
        current = self.get_record(category,identity) if identity is not None else None
        if identity is not None and current is None:
            raise LibraryError("library2.error.missing")
        if current is not None and not self.can_edit(category,current):
            raise LibraryError("library2.error.protected")
        try:
            parsed = self._parse(category,values)
            if identity is not None and definition.key_field in parsed and parsed[definition.key_field] != identity:
                raise LibraryError("library2.error.validation")
            self._validate_references(category,parsed)
            if category in FIRE_CATEGORIES:
                source=self._repos['sources'].get(parsed['source_id']) if parsed.get('source_id') else None
                item=FireEngineeringDataRecord(**parsed,parameter_type=FIRE_CATEGORIES[category],
                    source=source.reference if source else None,**({'id':current.id} if current else {}))
                return self.fire_records.save(item)
            if category == "sources":
                reference = SourceReference(**parsed)
                item = replace(current, reference=reference) if current else definition.model(reference=reference)
            else:
                item = replace(current, **parsed) if current else definition.model(**parsed)
            if category == "constant_metadata" and not self.can_edit(category,item):
                raise LibraryError("library2.error.protected")
            if hasattr(item,"modified_at"):
                item = replace(item,modified_at=datetime.now(timezone.utc))
            repo = self._repos[category]
            if category == "pump_references" and repo.ship_name_exists(item.ship_name,identity):
                raise LibraryError("library2.error.duplicate")
            saved = repo.update(item) if current else repo.create(item)
            self._source_cache.clear()
            return saved
        except (RepositoryConflictError,MaterialRepositoryConflictError,EngineeringConstantRepositoryConflictError,IntegrityError) as error:
            raise LibraryError("library2.error.duplicate") from error
        except RepositoryForeignKeyError as error:
            raise LibraryError("library2.error.reference") from error
        except (ValueError,TypeError,ValidationError) as error:
            if isinstance(error,LibraryError):
                raise
            raise LibraryError("library2.error.validation") from error
        except (RepositoryError,KeyError,DatabaseError) as error:
            raise LibraryError("library2.error.storage") from error

    def _parse(self, category: str, values: dict[str, object]) -> dict[str, object]:
        allowed = {field.name for field in CATEGORY_BY_CODE[category].fields}
        if set(values) - allowed:
            raise LibraryError("library2.error.validation")
        result = {}
        for field in CATEGORY_BY_CODE[category].fields:
            value = values.get(field.name,True if field.kind == "bool" else "")
            if value is None or isinstance(value,str) and not value.strip():
                if field.optional:
                    result[field.name] = None if field.kind != "text" or category in ("systems","circuits","fluids","sources","rule_sets","constant_metadata") else ""
                    continue
                raise ValueError("Required field")
            if field.kind == "float":
                value = parse_engineering_float(str(value),field_name=field.name) if not isinstance(value,bool) else None
                if value is None or not math.isfinite(value): raise ValueError("Invalid number")
            elif field.kind == "uuid": value = value if isinstance(value,UUID) else UUID(str(value))
            elif field.kind == "date": value = value if type(value) is date else date.fromisoformat(str(value))
            elif field.kind == "verification": value = VerificationStatus(value)
            elif field.kind == "source_type": value = SourceType(value)
            elif field.kind == "fire_status": value = FireSourceStatus(value)
            elif field.kind == "bool":
                if type(value) is not bool: raise ValueError("Invalid active state")
            else: value = str(value).strip()
            result[field.name] = value
        if category in PROPERTY_CODES:
            if result['property_name'] not in PROPERTY_CODES[category]: raise ValueError("Unknown property")
            if result['value'] < 0 or result['value'] == 0 and result['property_name'] != 'vapor_pressure': raise ValueError("Invalid property")
        for name in ('yield_strength_mpa','fuel_capacity_m3','pump_capacity_m3h'):
            if result.get(name) is not None and result[name] <= 0: raise ValueError("Positive value required")
        if result.get('roughness_mm',0) < 0: raise ValueError("Negative roughness")
        if category == 'constants':
            key, value = result['key'], result['value']
            if key.upper().startswith(FIRE_RECORD_PREFIX):raise ValueError('Reserved Fire namespace')
            if key in ('safety_factor','design_pressure_bar','weld_factor') and value <= 0:
                raise ValueError("Positive constant required")
            if key == 'corrosion_allowance_mm' and value < 0:
                raise ValueError("Negative corrosion allowance")
            if key == 'display_decimal_places' and (not value.is_integer() or not 0 <= value <= 12):
                raise ValueError("Invalid display precision")
        return result

    def _validate_references(self, category: str, values: dict[str, object]) -> None:
        for field in CATEGORY_BY_CODE[category].fields:
            if field.target and values.get(field.name) is not None:
                parent = self.get_record(field.target,values[field.name])
                if parent is None or not getattr(parent,"is_active",True):
                    raise LibraryError("library2.error.reference")
        if category == 'constant_metadata' and values.get('circuit_id'):
            circuit = self.get_record('circuits',values['circuit_id'])
            if circuit.system_id != values.get('system_id'):
                raise LibraryError("library2.error.reference")
