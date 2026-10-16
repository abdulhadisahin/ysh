"""V2 pipe selection contracts; all configured rule numbers are synthetic fixtures."""
from dataclasses import replace
from itertools import permutations
import math
from uuid import UUID, uuid4

import pytest

from core.pipe_size import PipeSize
from engineering.pipe_design.calculator import PipeDesignCalculator
from engineering.pipe_design.models import PipeDiameterInput, WallThicknessInput
from engineering.pipe_design.rules import (
    AllowableStressRule, DesignStatus, ManufacturingToleranceRule, MinimumWallRule,
    StrengthLimit, StressMode, StressPoint, fuel_velocity_criterion,
)
from engineering.pipe_design.selection import select_pipe_candidate, select_standard_wall, actual_velocity
from engineering.pipe_design.v2_calculator import PipeDesignV2Calculator
from engineering.pipe_design.v2_models import PipeCandidate, PipeDesignV2Input, PipeProvenance
from engineering.provenance import EngineeringValue, OverridePolicy, SourceReference, SourceType, VerificationStatus
from engineering.validation import ValidationError

STANDARD = UUID(int=1)
OTHER = UUID(int=2)
SYNTHETIC = SourceReference(
    source_type=SourceType.ENGINEERING_REFERENCE,
    document="TEST ONLY - synthetic configured rule, not a production standard",
    verification_status=VerificationStatus.VERIFIED,
)


def candidate(wall=3.0, *, od=100.0, inside=None, identifier=1, standard=STANDARD, dn="DN-test", **kwargs):
    return PipeCandidate(id=UUID(int=identifier), standard_id=standard,
                         outside_diameter_mm=od, wall_thickness_mm=wall,
                         inside_diameter_mm=inside, nominal_diameter=dn, **kwargs)


def request(**changes):
    values = dict(flow_rate_m3_h=20, design_velocity_m_s=2, standard_id=STANDARD,
                  design_pressure_bar=16, weld_factor=.85, corrosion_allowance_mm=1,
                  yield_strength_mpa=195, safety_factor=1.8)
    return PipeDesignV2Input(**(values | changes))


def configured(**changes):
    values = dict(
        tolerance_rule=ManufacturingToleranceRule(10, lambda base, a: a / (100 - a) * base, SYNTHETIC),
        minimum_wall_rule=MinimumWallRule(1.5, SYNTHETIC),
    )
    return request(**(values | changes))


def test_theoretical_d_is_unchanged_and_distinct_from_selected_actual_di():
    value = request()
    result = PipeDesignV2Calculator().calculate(value, [candidate()])
    expected = PipeDesignCalculator().calculate_diameter(PipeDiameterInput(20, 2))
    assert result.theoretical_internal_diameter_mm == expected.diameter_mm
    assert result.actual_internal_diameter_mm == 94
    assert result.actual_internal_diameter_mm != result.theoretical_internal_diameter_mm
    assert result.design_velocity_m_s == 2
    assert result.actual_velocity_m_s == 4 * (20 / 3600) / (math.pi * .094**2)
    assert result.actual_velocity_m_s != result.design_velocity_m_s
    assert result.velocity_within_design is True


def test_smallest_adequate_id_exact_match_undersized_and_empty_selection():
    small = candidate(inside=70, identifier=1)
    exact = candidate(inside=80, identifier=2)
    large = candidate(inside=90, identifier=3)
    assert select_pipe_candidate(80, [large, small, exact], STANDARD) == exact
    assert select_pipe_candidate(81, [small, exact, large], STANDARD) == large
    assert select_pipe_candidate(91, [small, exact, large], STANDARD) is None
    assert select_pipe_candidate(80, [], STANDARD) is None
    result = PipeDesignV2Calculator().calculate(request(), [])
    assert result.status is DesignStatus.NO_PIPE_CANDIDATE
    assert result.actual_internal_diameter_mm is None and result.actual_velocity_m_s is None


def test_stable_tie_breaker_is_independent_of_iteration_order():
    choices = [candidate(identifier=i) for i in (9, 3, 7)]
    for order in permutations(choices):
        assert select_pipe_candidate(90, order, STANDARD).id == UUID(int=3)


def test_no_cross_standard_fallback_and_no_invented_asme_data():
    choice = candidate(standard=OTHER, standard_code="OTHER")
    assert select_pipe_candidate(80, [choice], STANDARD) is None
    assert select_pipe_candidate(80, [candidate(standard_code="EN")], STANDARD, standard_code="ASME") is None
    result = PipeDesignV2Calculator().calculate(request(standard_code="ASME"), [candidate(standard_code="EN")])
    assert result.status is DesignStatus.NO_PIPE_CANDIDATE
    assert result.nps is None and result.schedule is None


def test_stored_id_has_precedence_and_missing_id_is_derived():
    stored = candidate(inside=93.9)
    derived = candidate()
    assert stored.actual_internal_diameter_mm == 93.9
    assert derived.actual_internal_diameter_mm == 100 - 2 * 3
    assert actual_velocity(20, stored.actual_internal_diameter_mm) != actual_velocity(20, derived.actual_internal_diameter_mm)


@pytest.mark.parametrize("change", [{"wall": 0}, {"wall": 50}, {"inside": 0}, {"inside": 101}, {"od": float("nan")}])
def test_invalid_candidate_dimensions_are_validation_failures(change):
    with pytest.raises(ValidationError):
        candidate(**change)


def test_standard_wall_is_smallest_adequate_exact_match_with_stable_ties():
    first = candidate(2, identifier=1)
    choices = [first, candidate(4, identifier=4), candidate(3, identifier=3), candidate(3, identifier=2)]
    assert select_standard_wall(3, first, choices).id == UUID(int=2)
    assert select_standard_wall(3.01, first, choices).wall_thickness_mm == 4
    assert select_standard_wall(4.01, first, choices) is None
    for order in permutations(choices):
        assert select_standard_wall(3, first, order).id == UUID(int=2)


def test_final_wall_does_not_cross_nominal_size_od_or_standard():
    first = candidate(2)
    wrong = [candidate(5, standard=OTHER), candidate(5, dn="other"), candidate(5, od=120)]
    assert select_standard_wall(3, first, wrong) is None
    narrowed = candidate(8, identifier=2)
    assert select_standard_wall(8, first, [narrowed], required_internal_diameter_mm=90) is None


def test_legacy_wall_components_and_corrosion_are_unchanged_when_rules_missing():
    value = request(bend_allowance_enabled=True, bend_radius_mm=300, corrosion_allowance_mm=2.2)
    result = PipeDesignV2Calculator().calculate(value, [candidate(wall=5)])
    legacy = PipeDesignCalculator().calculate_wall_thickness(WallThicknessInput(100, 16, 195, 1.8, .85, 2.2, True, 300))
    assert result.allowable_stress.value == legacy.allowable_stress_mpa
    assert result.wall.base_wall_mm == legacy.base_wall_thickness_mm
    assert result.wall.bend_allowance_mm == legacy.bend_allowance_mm
    assert result.wall.corrosion_allowance_mm == legacy.corrosion_allowance_mm
    assert result.calculated_required_wall_mm == result.final_required_wall_mm == legacy.final_wall_thickness_mm
    assert result.wall.manufacturing_allowance_mm is None
    assert result.minimum_required_wall_mm is None
    assert result.manufacturing_tolerance.status is DesignStatus.RULE_NOT_CONFIGURED
    assert result.minimum_wall.status is DesignStatus.RULE_NOT_CONFIGURED
    assert result.status is DesignStatus.RULE_NOT_CONFIGURED
    assert result.selected_pipe is not None  # Provisional numerical result remains available.
    assert result.allowable_stress.source.verification_status is VerificationStatus.UNVERIFIED
    assert result.provenance.source_factor.symbol == "v"


def test_configured_synthetic_tolerance_and_minimum_rule_select_final_wall():
    value = configured(minimum_wall_rule=MinimumWallRule(3.2, SYNTHETIC))
    choices = [candidate(2, identifier=1), candidate(4, identifier=2)]
    result = PipeDesignV2Calculator().calculate(value, choices)
    assert result.status is DesignStatus.SUCCESS
    assert result.wall.manufacturing_allowance_mm == 10 / 90 * result.wall.base_wall_mm
    assert result.calculated_required_wall_mm == result.wall.base_wall_mm + 1 + result.wall.bend_allowance_mm + result.wall.manufacturing_allowance_mm
    assert result.minimum_required_wall_mm == 3.2
    assert result.final_required_wall_mm == max(result.calculated_required_wall_mm, 3.2)
    assert result.selected_wall_thickness_mm == 4
    assert result.actual_internal_diameter_mm == 92
    assert result.actual_velocity_m_s == actual_velocity(20, 92)


def test_no_wall_match_does_not_round_or_expose_nonexistent_final_geometry():
    result = PipeDesignV2Calculator().calculate(configured(minimum_wall_rule=MinimumWallRule(9.01, SYNTHETIC)), [candidate(9)])
    assert result.status is DesignStatus.NO_STANDARD_WALL_MATCH
    assert result.final_required_wall_mm == 9.01
    assert result.selected_wall_thickness_mm is None
    assert result.actual_internal_diameter_mm is None and result.actual_velocity_m_s is None


@pytest.mark.parametrize("status", [None, VerificationStatus.UNVERIFIED, VerificationStatus.PARTIALLY_VERIFIED, VerificationStatus.DEPRECATED])
def test_unverified_rules_never_execute_tolerance_formula(status):
    source = replace(SYNTHETIC, verification_status=status)
    def forbidden(base, percent):
        raise AssertionError("Unverified formula must not run")
    tolerance = ManufacturingToleranceRule(10, forbidden, source).evaluate(1)
    minimum = MinimumWallRule(3, source).evaluate()
    assert tolerance.value is None and tolerance.status is DesignStatus.SOURCE_REQUIRED
    assert minimum.value is None and minimum.status is DesignStatus.SOURCE_REQUIRED


def test_absent_document_is_not_sufficient_even_with_verified_marker():
    source = replace(SYNTHETIC, document=None)
    assert MinimumWallRule(3, source).evaluate().status is DesignStatus.SOURCE_REQUIRED


@pytest.mark.parametrize("percent", [-1, 100, 101, float("nan")])
def test_invalid_tolerance_percent_is_rejected(percent):
    with pytest.raises(ValidationError):
        ManufacturingToleranceRule(percent, lambda base, a: base, SYNTHETIC).evaluate(1)


def test_missing_tolerance_formula_is_not_zero_or_an_assumed_formula():
    result = ManufacturingToleranceRule(10, None, SYNTHETIC).evaluate(1)
    assert result.value is None and result.status is DesignStatus.RULE_NOT_CONFIGURED
    assert MinimumWallRule().evaluate().value is None


def test_legacy_stress_is_exact_rp02_over_factor():
    rule = AllowableStressRule()
    assert rule.evaluate(yield_strength_mpa=195, safety_factor=1.8).value == 195 / 1.8


def test_only_configured_strength_terms_participate_and_minimum_wins():
    limits = (StrengthLimit("synthetic Rm", 450, 3), StrengthLimit("synthetic Rp", 200, 2))
    rule = AllowableStressRule(StressMode.FACTOR_BASED_STEEL_RULE, SYNTHETIC, limits=limits)
    assert rule.evaluate().value == 100
    assert replace(rule, limits=(limits[0],)).evaluate().value == 150
    assert replace(rule, limits=()).evaluate().status is DesignStatus.RULE_NOT_CONFIGURED
    assert replace(rule, source=None).evaluate().status is DesignStatus.SOURCE_REQUIRED


def test_direct_table_exact_temperature_lookup_and_no_silent_steel_fallback():
    rule = AllowableStressRule(StressMode.DIRECT_TABLE_RULE, SYNTHETIC,
                              table=(StressPoint(40, 90), StressPoint(80, 70)))
    assert rule.evaluate(design_temperature_c=80).value == 70
    assert rule.evaluate(design_temperature_c=60).status is DesignStatus.RULE_NOT_CONFIGURED
    assert rule.evaluate().value is None
    assert replace(rule, table=()).evaluate(yield_strength_mpa=195, safety_factor=1.8).value is None
    assert replace(rule, source=None).evaluate(design_temperature_c=40).status is DesignStatus.SOURCE_REQUIRED
    result = PipeDesignV2Calculator().calculate(request(stress_rule=replace(rule, table=())), [candidate()])
    assert result.status is DesignStatus.RULE_NOT_CONFIGURED
    assert result.wall is None and result.actual_velocity_m_s is None


def test_direct_table_and_user_stress_use_shared_base_wall_equation():
    for rule in (
        AllowableStressRule(StressMode.DIRECT_TABLE_RULE, SYNTHETIC, table=(StressPoint(80, 70),)),
        AllowableStressRule(StressMode.USER_PROVIDED_RULE, user_value_mpa=70),
    ):
        result = PipeDesignV2Calculator().calculate(request(stress_rule=rule, design_temperature_c=80), [candidate(5)])
        assert result.allowable_stress.value == 70
        assert result.wall.base_wall_mm == 100 * 16 / ((20 * 70 * .85) + 16)
        assert result.design_temperature_c == 80
    assert PipeDesignV2Calculator().calculate(request(), [candidate()]).design_temperature_c is None


def test_duplicate_table_temperatures_and_invalid_strengths_fail_validation():
    rule = AllowableStressRule(StressMode.DIRECT_TABLE_RULE, SYNTHETIC,
                              table=(StressPoint(40, 90), StressPoint(40, 80)))
    with pytest.raises(ValidationError):
        rule.evaluate(design_temperature_c=40)
    with pytest.raises(ValidationError):
        StrengthLimit("bad", 200, 0)


def test_phase2_overrides_and_independent_source_classes_are_preserved():
    corrosion = EngineeringValue(
        used_value=2.2, recommended_value=1, unit="mm", symbol="c",
        source=SourceReference(source_type=SourceType.TL_RULE, verification_status=VerificationStatus.UNVERIFIED),
        override_policy=OverridePolicy.SUGGESTED, override_reason="Synthetic user correction",
    )
    velocity = fuel_velocity_criterion()
    assert velocity.used_value == 7 and velocity.source.source_type is SourceType.D243_CRITERION
    assert velocity.source.source_type is not SourceType.TL_RULE
    material_source = SourceReference(source_type=SourceType.MATERIAL_STANDARD)
    dimension_source = SourceReference(source_type=SourceType.PIPE_STANDARD)
    provenance = PipeProvenance(corrosion_allowance=corrosion, material_standard=material_source, design_velocity=velocity)
    result = PipeDesignV2Calculator().calculate(request(design_velocity_m_s=7, corrosion_allowance_mm=2.2, provenance=provenance), [candidate(5, dimension_source=dimension_source)])
    assert result.provenance.corrosion_allowance is corrosion
    assert corrosion.recommended_value == 1 and corrosion.is_overridden
    assert result.provenance.material_standard is material_source
    assert result.selected_pipe.dimension_source.source_type is SourceType.PIPE_STANDARD
    assert result.provenance.source_factor.source.source_type is SourceType.USER_INPUT
    assert SourceReference(source_type=SourceType.CALCULATED).source_type is SourceType.CALCULATED


def test_provenance_mismatch_cannot_silently_change_used_value():
    supplied = EngineeringValue(used_value=1, unit="mm", source=SourceReference(source_type=SourceType.USER_INPUT), override_policy=OverridePolicy.USER_INPUT)
    with pytest.raises(ValidationError):
        PipeDesignV2Calculator().calculate(request(corrosion_allowance_mm=2, provenance=PipeProvenance(corrosion_allowance=supplied)), [candidate()])

def test_final_wall_that_narrows_id_below_theoretical_requirement_is_not_selected():
    q = math.pi * .09**2 / 4 * 2 * 3600
    result = PipeDesignV2Calculator().calculate(
        configured(flow_rate_m3_h=q, minimum_wall_rule=MinimumWallRule(8, SYNTHETIC)),
        [candidate(2, identifier=1), candidate(8, identifier=2)],
    )
    assert result.candidate.wall_thickness_mm == 2
    assert result.status is DesignStatus.NO_STANDARD_WALL_MATCH
    assert result.actual_velocity_m_s is None


@pytest.mark.parametrize("source_type", [
    SourceType.D243_CRITERION, SourceType.TL_RULE, SourceType.PIPE_STANDARD,
    SourceType.MATERIAL_STANDARD, SourceType.USER_INPUT, SourceType.CALCULATED,
])
def test_provenance_classification_is_preserved_without_relabelling(source_type):
    source = SourceReference(source_type=source_type, verification_status=VerificationStatus.UNVERIFIED)
    factor = EngineeringValue(used_value=.85, recommended_value=.85, unit="-", symbol="v",
                              source=source, override_policy=OverridePolicy.LOCKED)
    result = PipeDesignV2Calculator().calculate(request(provenance=PipeProvenance(source_factor=factor)), [candidate()])
    assert result.provenance.source_factor is factor
    assert factor.source.source_type is source_type
    assert factor.source.verification_status is VerificationStatus.UNVERIFIED


def test_user_stress_without_a_value_is_not_configured():
    result = AllowableStressRule(StressMode.USER_PROVIDED_RULE).evaluate()
    assert result.value is None and result.status is DesignStatus.RULE_NOT_CONFIGURED


def test_invalid_formula_result_is_not_accepted_as_an_allowance():
    with pytest.raises(ValidationError):
        ManufacturingToleranceRule(10, lambda base, a: -1, SYNTHETIC).evaluate(1)


def test_source_required_state_remains_visible_with_provisional_geometry():
    unverified = replace(SYNTHETIC, verification_status=VerificationStatus.UNVERIFIED)
    result = PipeDesignV2Calculator().calculate(request(minimum_wall_rule=MinimumWallRule(3, unverified)), [candidate()])
    assert result.status is DesignStatus.SOURCE_REQUIRED
    assert result.minimum_required_wall_mm is None
    assert result.selected_pipe is not None


def test_invalid_v2_user_inputs_are_validation_failures():
    for changes in ({"flow_rate_m3_h": 0}, {"weld_factor": 0}, {"corrosion_allowance_mm": -1},
                    {"design_temperature_c": float("nan")}, {"bend_allowance_enabled": True}):
        with pytest.raises(ValidationError):
            PipeDesignV2Calculator().calculate(request(**changes), [candidate()])


def test_v2_service_reads_real_standard_rows_and_phase4_metadata_without_mutation(
    material_service, pipe_size_service, engineering_constant_service, library_database,
):
    from repositories.pipe_metadata_repository import PipeSizeMetadataRepository
    from repositories.source_repository import SourceRepository
    from repositories.v2_models import PipeSizeMetadata, SourceRecord
    from services.pipe_design_service import PipeDesignService

    standard = pipe_size_service.create_standard(code="SYNTHETIC_TEST", display_name="Synthetic dimensional fixture")
    pipe = pipe_size_service.create_pipe_size(
        standard_id=standard.id, nominal_diameter="DN-test", outside_diameter_mm=100,
        wall_thickness_mm=3, inside_diameter_mm=94,
    )
    source = SourceRepository(library_database).create(SourceRecord(reference=replace(SYNTHETIC, source_type=SourceType.PIPE_STANDARD)))
    metadata = PipeSizeMetadataRepository(library_database).create(PipeSizeMetadata(
        pipe_size_id=pipe.id, nps="synthetic NPS", schedule="synthetic schedule",
        manufacturing_tolerance=12.5, tolerance_unit="%", source_id=source.id,
    ))
    service = PipeDesignService(material_service, pipe_size_service, engineering_constant_service)
    with library_database.connection() as c:
        before = list(c.iterdump())
    result = service.calculate_v2(request(standard_id=standard.id), pipe_metadata={pipe.id: metadata},
                                  source_references={source.id: source.reference})
    assert result.selected_pipe.id == pipe.id
    assert result.selected_standard_id == standard.id
    assert result.selected_standard_code == standard.code
    assert result.nps == "synthetic NPS" and result.schedule == "synthetic schedule"
    assert result.actual_internal_diameter_mm == 94
    assert result.selected_pipe.dimension_source == source.reference
    assert result.manufacturing_tolerance.status is DesignStatus.RULE_NOT_CONFIGURED
    assert result.wall.manufacturing_allowance_mm is None  # Stored percent alone is not an approved formula.
    with library_database.connection() as c:
        assert list(c.iterdump()) == before


def test_v2_service_empty_standard_never_invents_geometry_or_nominal_metadata(
    material_service, pipe_size_service, engineering_constant_service,
):
    from services.pipe_design_service import PipeDesignService
    standard = pipe_size_service.create_standard(code="EMPTY_TEST", display_name="Empty test")
    result = PipeDesignService(material_service, pipe_size_service, engineering_constant_service).calculate_v2(request(standard_id=standard.id))
    assert result.status is DesignStatus.NO_PIPE_CANDIDATE
    assert result.nps is None and result.schedule is None and result.selected_pipe is None


def test_v2_service_direct_mode_never_uses_material_rp02_as_cuni_table_fallback(
    material_service, pipe_size_service, engineering_constant_service,
):
    from services.pipe_design_service import PipeDesignService
    material = material_service.create_material(name="Synthetic CuNi fixture", designation="TEST_CUNI", yield_strength_mpa=200, standard="Synthetic material fixture")
    standard = pipe_size_service.get_standard_by_code(pipe_size_service.DEFAULT_STANDARD_CODE)
    service = PipeDesignService(material_service, pipe_size_service, engineering_constant_service)
    value = request(standard_id=standard.id, material_id=material.id,
                    stress_rule=AllowableStressRule(StressMode.DIRECT_TABLE_RULE), design_temperature_c=80)
    result = service.calculate_v2(value)
    assert result.allowable_stress.value is None
    assert result.status is DesignStatus.RULE_NOT_CONFIGURED
    assert result.provenance.material_standard.source_type is SourceType.MATERIAL_STANDARD
    assert result.provenance.material_standard.verification_status is VerificationStatus.UNVERIFIED


def test_v2_service_legacy_material_lookup_is_explicit_and_numerically_compatible(
    material_service, pipe_size_service, engineering_constant_service,
):
    from services.pipe_design_service import PipeDesignService
    material = material_service.create_material(name="Synthetic steel", designation="TEST_STEEL", yield_strength_mpa=200)
    standard = pipe_size_service.get_standard_by_code(pipe_size_service.DEFAULT_STANDARD_CODE)
    result = PipeDesignService(material_service, pipe_size_service, engineering_constant_service).calculate_v2(
        request(standard_id=standard.id, material_id=material.id, yield_strength_mpa=None),
    )
    assert result.allowable_stress.value == 200 / 1.8


def test_v2_core_has_no_ui_repository_sqlite_or_localization_dependency():
    import ast
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "engineering/pipe_design"
    for name in ("rules", "selection", "v2_models", "v2_calculator"):
        source = (root / f"{name}.py").read_text(encoding="utf-8-sig")
        tree = ast.parse(source)
        imports = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        imports |= {a.name for node in ast.walk(tree) if isinstance(node, ast.Import) for a in node.names}
        assert not any(i.startswith(("sqlite3", "database", "repositories", "ui", "tkinter", "i18n", "matplotlib", "PIL")) for i in imports)
        assert "qallow" not in source.lower()

def test_weld_factor_provenance_rejects_obsolete_symbol():
    supplied = EngineeringValue(used_value=.85, unit="-", symbol="w", source=SourceReference(source_type=SourceType.USER_INPUT), override_policy=OverridePolicy.USER_INPUT)
    with pytest.raises(ValidationError):
        PipeDesignV2Calculator().calculate(request(provenance=PipeProvenance(source_factor=supplied)), [candidate()])


def test_calculated_wall_dominates_a_smaller_configured_minimum():
    result = PipeDesignV2Calculator().calculate(configured(minimum_wall_rule=MinimumWallRule(.1, SYNTHETIC)), [candidate(3)])
    assert result.final_required_wall_mm == result.calculated_required_wall_mm
    assert result.final_required_wall_mm > result.minimum_required_wall_mm


def test_standard_wall_does_not_cross_conflicting_standard_codes():
    original = candidate(2, standard_code="EN")
    conflicting = candidate(4, identifier=2, standard_code="OTHER")
    assert select_standard_wall(3, original, [conflicting]) is None


def test_v2_service_does_not_select_rows_from_an_inactive_standard(
    material_service, pipe_size_service, engineering_constant_service, library_database,
):
    from services.pipe_design_service import PipeDesignService
    standard = pipe_size_service.create_standard(code="INACTIVE_TEST", display_name="Synthetic inactive standard")
    pipe_size_service.create_pipe_size(standard_id=standard.id, nominal_diameter="DN-test", outside_diameter_mm=100, wall_thickness_mm=3, inside_diameter_mm=94)
    with library_database.connection() as c:
        c.execute("UPDATE pipe_standards SET is_active=0 WHERE id=?", (str(standard.id),))
    result = PipeDesignService(material_service, pipe_size_service, engineering_constant_service).calculate_v2(request(standard_id=standard.id))
    assert result.status is DesignStatus.NO_PIPE_CANDIDATE
