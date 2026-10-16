"""Service workflow for the Version 1 pipe-design module."""
from __future__ import annotations
from uuid import UUID
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING
from core.material import Material
from core.pipe_standard import PipeStandard
from engineering.pipe_design.calculator import PipeDesignCalculator
from engineering.pipe_design.models import PipeDesignCalculationResult, PipeDiameterInput, WallThicknessInput
from services.engineering_constant_service import EngineeringConstantService
from services.material_service import MaterialService
from services.pipe_size_service import PipeSizeService
from services.corrosion_allowance_circuit_service import CorrosionAllowanceCircuitService
from core.corrosion_allowance_circuit import CorrosionAllowanceCircuit
from engineering.validation import ValidationError
if TYPE_CHECKING:
    from engineering.pipe_design.v2_models import PipeDesignV2Input, PipeSelection
    from engineering.provenance import SourceReference
    from repositories.v2_models import PipeSizeMetadata


class PipeDesignService:
    """Coordinates library values with pure pipe calculations."""
    def __init__(self, materials: MaterialService, pipe_sizes: PipeSizeService, constants: EngineeringConstantService, circuits: CorrosionAllowanceCircuitService | None = None) -> None:
        """Configure dependencies without accessing SQL or Tkinter."""
        self._materials=materials;self._pipe_sizes=pipe_sizes;self._constants=constants;self._circuits=circuits;self._calculator=PipeDesignCalculator()
    def get_current_constants(self) -> dict[str, float]:
        """Return required saved constants for a new calculation page."""
        required = (
            "safety_factor",
            "design_pressure_bar",
            "weld_factor",
            "corrosion_allowance_mm",
            "display_decimal_places",
        )
        values: dict[str, float] = {}
        for key in required:
            try:
                values[key] = self._constants.get_constant(key).value
            except LookupError as error:
                raise ValueError(
                    f"Required engineering constant '{key}' is missing."
                ) from error
        return values
    def get_all_materials(self) -> Sequence[Material]:
        """Return library materials for the wall-thickness source selector."""
        return self._materials.get_all_materials()
    def get_material(self, material_id: UUID) -> Material:
        """Return a full material record for current-calculation use."""
        return self._materials.get_material(material_id)
    def get_available_pipe_standards(self) -> Sequence[PipeStandard]:
        """Return active pipe standards for the current calculation selection."""
        return self._pipe_sizes.get_available_standards()
    def get_active_corrosion_allowance_circuits(self) -> Sequence[CorrosionAllowanceCircuit]:
        """Return circuit defaults for the Pipe Design current calculation."""
        return () if self._circuits is None else self._circuits.get_active_circuits()
    def calculate(self, diameter: PipeDiameterInput|None=None, wall: WallThicknessInput|None=None, material_id: UUID|None=None, manual_input: bool=True, standard_code: str | None = None) -> PipeDesignCalculationResult:
        """Calculate provided sections while retaining errors and traceability."""
        result=PipeDesignCalculationResult(trace={"module_identifier":"pipe_design","module_version":"1","manual_input":manual_input,"constants":self.get_current_constants()})
        try:
            if material_id is not None and wall is not None:
                material=self._materials.get_material(material_id);self._materials.validate_required_properties(material,"yield_strength_mpa");wall.yield_strength_mpa=material.yield_strength_mpa;result.trace["material"]={"id":str(material.id),"designation":material.designation,"standard":material.standard,"source":material.source,"yield_strength_mpa":material.yield_strength_mpa}
            if diameter is not None:
                selected_standard = standard_code or PipeSizeService.DEFAULT_STANDARD_CODE
                sizes = self._pipe_sizes.get_pipe_sizes_for_standard(
                    selected_standard
                )
                result.trace["pipe_standard_code"] = selected_standard
                result.diameter=self._calculator.recommend_dn(self._calculator.calculate_diameter(diameter),sizes)
                if not sizes:
                    result.diameter.warnings = ["selected_standard_empty"]
                result.warnings.extend(result.diameter.warnings)
            from dataclasses import asdict
            if diameter is not None:
                result.trace["diameter_input"] = asdict(diameter)
            if wall is not None:
                result.trace["wall_input"] = asdict(wall)
                result.wall_thickness=self._calculator.calculate_wall_thickness(wall)
        except ValidationError:
            raise
        except (ValueError, LookupError):
            result.errors.append("unexpected_error")
        return result

    def calculate_v2(
        self, value: PipeDesignV2Input, *,
        pipe_metadata: Mapping[UUID, PipeSizeMetadata] | None = None,
        source_references: Mapping[UUID, SourceReference] | None = None,
        previous_selection: PipeSelection | None = None,
    ) -> PipeSelection:
        """Opt in to V2 using real rows from one explicitly selected standard.

        Optional metadata/reference maps can be prepared with Phase 4 repositories.
        No per-candidate repository reads, standard seeding or tolerance inference
        occurs. Missing material tables never fall back to steel in direct mode.
        """
        from dataclasses import replace
        from engineering.pipe_design.rules import StressMode
        from engineering.pipe_design.v2_models import PipeCandidate
        from engineering.pipe_design.v2_calculator import PipeDesignV2Calculator
        from engineering.provenance import SourceReference, SourceType, VerificationStatus

        standard = self._pipe_sizes.get_standard(value.standard_id)
        sizes = self._pipe_sizes.get_pipe_sizes_for_standard(standard.id) if standard.is_active else ()
        metadata = pipe_metadata or {}
        references = source_references or {}
        candidates = []
        for row in sizes:
            extra = metadata.get(row.id)
            source = references.get(extra.source_id) if extra and extra.source_id else None
            if source is None:
                source = SourceReference(
                    source_type=SourceType.PIPE_STANDARD, document=standard.display_name,
                    verification_status=VerificationStatus.UNVERIFIED,
                    notes="Stored library dimensions; verification is not inferred.",
                )
            candidates.append(PipeCandidate(
                id=row.id, standard_id=row.standard_id, standard_code=standard.code,
                nominal_diameter=row.nominal_diameter,
                outside_diameter_mm=row.outside_diameter_mm,
                wall_thickness_mm=row.wall_thickness_mm,
                inside_diameter_mm=row.inside_diameter_mm,
                nps=(extra.nps or None) if extra else None, schedule=(extra.schedule or None) if extra else None,
                dimension_source=source,
            ))
        if value.material_id is not None:
            material = self._materials.get_material(value.material_id)
            provenance = value.provenance
            if provenance.material_standard is None and material.standard:
                provenance = replace(provenance, material_standard=SourceReference(
                    source_type=SourceType.MATERIAL_STANDARD, document=material.standard,
                    verification_status=VerificationStatus.UNVERIFIED,
                ))
            strength = value.yield_strength_mpa
            if value.stress_rule.mode is StressMode.LEGACY_RP02 and strength is None:
                strength = material.yield_strength_mpa
            value = replace(value, yield_strength_mpa=strength, provenance=provenance)
        result = PipeDesignV2Calculator().calculate(value, tuple(candidates))
        if previous_selection is not None:
            from engineering.pipe_design.transfer import revise_selection
            result = revise_selection(previous_selection, result)
        return result
