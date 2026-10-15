"""Contracts for standalone engineering provenance; examples are synthetic."""
from dataclasses import FrozenInstanceError, asdict, fields, replace
from datetime import date, datetime
from pathlib import Path
import ast

import pytest

from engineering.provenance import (
    EngineeringValue, OverridePolicy, SourceReference, SourceType, VerificationStatus,
)
from i18n.terminology import TERMS_TR
from i18n.translator import Translator


def suggestion(**changes):
    values = dict(
        used_value=1.0, recommended_value=1.0, unit="-",
        source=SourceReference(source_type=SourceType.TL_RULE),
        override_policy=OverridePolicy.SUGGESTED, symbol="v",
        terminology_key="engineering.v", selection_reason="Synthetic example",
    )
    return EngineeringValue(**(values | changes))


def test_source_categories_are_complete_and_distinct():
    assert {s.name for s in SourceType} == {
        "USER_INPUT", "PROJECT_CRITERION", "D243_CRITERION", "TL_RULE",
        "MATERIAL_STANDARD", "PIPE_STANDARD", "FLUID_LIBRARY",
        "ENGINEERING_REFERENCE", "MANUFACTURER_DATA", "CALCULATED",
        "REFERENCE_VESSEL_DATA",
    }
    assert len({s.value for s in SourceType}) == 11


def test_verification_states_are_complete():
    assert {s.name for s in VerificationStatus} == {
        "VERIFIED", "PARTIALLY_VERIFIED", "USER_SUPPLIED", "UNVERIFIED", "DEPRECATED",
    }


def test_calculated_value_can_be_locked():
    value = EngineeringValue(
        used_value=12000, recommended_value=12000, unit="-", symbol="Re",
        source=SourceReference(source_type=SourceType.CALCULATED),
        override_policy=OverridePolicy.LOCKED,
    )
    assert value.value == value.used_value == 12000
    assert not value.is_overridden and not value.override_allowed
    assert value.source.verification_status is None


def test_user_input_edit_is_not_a_recommendation_override():
    value = EngineeringValue(
        used_value=16, unit="bar", source=SourceReference(source_type=SourceType.USER_INPUT),
        override_policy=OverridePolicy.USER_INPUT,
    )
    edited = value.with_used_value(20)
    assert edited.used_value == 20 and value.used_value == 16
    assert edited.recommended_value is None
    assert not edited.is_overridden and not edited.override_allowed


def test_tl_reference_can_represent_all_known_metadata_without_inference():
    reference = SourceReference(
        source_type=SourceType.TL_RULE, source_organization="Synthetic organization",
        document="Example document", part="8", section="2", article="3.1",
        table="8.9", formula="1", revision="Example revision",
        effective_date=date(2025, 1, 1), verification_date=date(2025, 2, 1),
        verification_status=VerificationStatus.PARTIALLY_VERIFIED, notes="Test fixture only",
    )
    data = asdict(reference)
    assert data["source_type"] is SourceType.TL_RULE
    assert all(value is not None for value in data.values())
    assert reference.effective_date == date(2025, 1, 1)
    assert reference.verification_date == date(2025, 2, 1)
    assert reference.verification_status is VerificationStatus.PARTIALLY_VERIFIED


def test_unknown_source_fields_stay_unset_even_when_a_document_exists():
    reference = SourceReference(source_type=SourceType.ENGINEERING_REFERENCE)
    assert all(getattr(reference, f.name) is None for f in fields(reference) if f.name != "source_type")
    assert replace(reference, document="Example").verification_status is None


def test_override_preserves_recommendation_source_and_reason():
    original = suggestion()
    changed = original.with_used_value(0.9, override_reason="Certificate correction")
    assert changed.recommended_value == original.recommended_value == 1.0
    assert changed.used_value == changed.value == 0.9
    assert changed.source is original.source
    assert changed.selection_reason == original.selection_reason
    assert changed.is_overridden and changed.override_allowed
    assert changed.override_reason == "Certificate correction"
    assert not original.is_overridden
    restored = changed.with_used_value(1.0)
    assert not restored.is_overridden and restored.override_reason is None


@pytest.mark.parametrize("reason", [None, "", "   "])
def test_override_requires_an_explicit_reason(reason):
    with pytest.raises(ValueError):
        suggestion(used_value=0.9, override_reason=reason)


def test_locked_override_is_rejected_by_constructor_helper_and_replace():
    locked = suggestion(override_policy=OverridePolicy.LOCKED)
    with pytest.raises(ValueError):
        locked.with_used_value(0.9, override_reason="Attempt")
    with pytest.raises(ValueError):
        replace(locked, used_value=0.9, override_reason="Attempt")
    with pytest.raises(ValueError):
        suggestion(override_policy=OverridePolicy.LOCKED, used_value=0.9, override_reason="Attempt")


@pytest.mark.parametrize("policy", [OverridePolicy.LOCKED, OverridePolicy.SUGGESTED])
def test_recommendation_is_required_for_rule_based_policies(policy):
    with pytest.raises(ValueError):
        suggestion(override_policy=policy, recommended_value=None)


def test_user_input_does_not_allow_ambiguous_recommendation():
    with pytest.raises(ValueError):
        suggestion(override_policy=OverridePolicy.USER_INPUT)


def test_override_reason_cannot_describe_a_nonexistent_override():
    with pytest.raises(ValueError):
        suggestion(override_reason="Not actually changed")


@pytest.mark.parametrize("unit", ["mm", "m", "bar", "MPa", "m³/h", "m/s", "kg/m³", "-"])
def test_units_are_preserved_without_conversion(unit):
    assert suggestion(unit=unit).unit == unit


@pytest.mark.parametrize("symbol", tuple(TERMS_TR))
def test_symbols_and_terminology_references_are_opaque_and_preserved(symbol):
    value = suggestion(symbol=symbol, terminology_key=f"engineering.{symbol}")
    assert value.symbol == symbol
    assert Translator("tr").translate(value.terminology_key) == TERMS_TR[symbol]
    assert Translator("en").translate(value.terminology_key) != value.terminology_key


def test_objects_and_nested_source_are_immutable():
    value = suggestion()
    with pytest.raises(FrozenInstanceError):
        value.used_value = 0.9
    with pytest.raises(FrozenInstanceError):
        value.source.document = "Changed"
    assert "value" not in {f.name for f in fields(value)}
    assert "is_overridden" not in {f.name for f in fields(value)}


@pytest.mark.parametrize("field", ["effective_date", "verification_date"])
@pytest.mark.parametrize("invalid", ["2025-01-01", datetime(2025, 1, 1), 20250101])
def test_dates_require_explicit_date_objects(field, invalid):
    with pytest.raises(TypeError):
        SourceReference(source_type=SourceType.TL_RULE, **{field: invalid})


@pytest.mark.parametrize("field", ["used_value", "recommended_value"])
@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), float("-inf"), True, "1.0"])
def test_non_numeric_or_non_finite_values_are_rejected(field, invalid):
    with pytest.raises((TypeError, ValueError)):
        suggestion(**{field: invalid})


def test_controlled_enums_reject_arbitrary_strings():
    with pytest.raises(TypeError):
        SourceReference(source_type="TL_RULE")
    with pytest.raises(TypeError):
        SourceReference(source_type=SourceType.TL_RULE, verification_status="VERIFIED")
    with pytest.raises(TypeError):
        suggestion(override_policy="SUGGESTED")


def test_domain_module_has_no_ui_storage_translation_or_new_flow_definition():
    path = Path(__file__).resolve().parents[1] / "engineering/provenance.py"
    source = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(source)
    imports = {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    imports |= {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert imports <= {"__future__", "dataclasses", "datetime", "enum", "math"}
    assert "qallow" not in source.lower()
    assert "Kaynak faktörü" not in source


def test_existing_engineering_results_match_phase2_baseline():
    """Exact snapshot captured before introducing the disconnected model."""
    from engineering.pipe_design.calculator import PipeDesignCalculator
    from engineering.pipe_design.models import PipeDiameterInput,WallThicknessInput
    from engineering.head_loss.calculator import DischargeHeadLossCalculator
    from engineering.head_loss.models import DischargeHeadLossInput
    from engineering.suction_npsh.calculator import SuctionNPSHCalculator
    from engineering.suction_npsh.models import SuctionNPSHInput
    from engineering.transfer_pump.calculator import TransferPumpCalculator
    from engineering.transfer_pump.models import TransferPumpInput
    from core.local_loss_item import LocalLossItem
    from core.pump_reference import PumpReference
    p=PipeDesignCalculator()
    w=p.calculate_wall_thickness(WallThicknessInput(100,16,195,1.8,.85,1,True,300))
    d=DischargeHeadLossCalculator().calculate(DischargeHeadLossInput(100,20,2e-6,20,.015,7,[LocalLossItem('X',1,3)]))
    s=SuctionNPSHCalculator().calculate(SuctionNPSHInput(100,20,2e-6,20,.015,[LocalLossItem('X',1,3)],120000,3000,850,2))
    t=TransferPumpCalculator().calculate(TransferPumpInput(250,[PumpReference('A',100,20),PumpReference('B',200,30),PumpReference('C',300,40)]))
    values=dict(velocity=d.flow_velocity_m_s,reynolds=d.reynolds_number,friction=d.friction_factor,diameter=p.calculate_diameter(PipeDiameterInput(100,2)).diameter_mm,stress=w.allowable_stress_mpa,base=w.base_wall_thickness_mm,bend=w.bend_allowance_mm,wall=w.final_wall_thickness_mm,discharge_pipe=d.pipe_friction_loss_m,discharge_local=d.local_loss_m,suction=s.suction_line_loss_m,enpy=s.enpym_available_m,slope=t.regression_model.slope,intercept=t.regression_model.intercept,r_squared=t.regression_model.r_squared,time=t.estimated_emptying_time_hours)
    assert values == {
        "base": 0.8612955320294277,
        "bend": 0.11483940427059035,
        "diameter": 132.9807601338109,
        "discharge_local": 0.0768,
        "discharge_pipe": 0.1179633563757915,
        "enpy": 11.841330398732161,
        "friction": 0.023039718042146776,
        "intercept": 10.0,
        "r_squared": 1.0,
        "reynolds": 35367.7651315323,
        "slope": 0.1,
        "stress": 108.33333333333333,
        "suction": 0.1947633563757915,
        "time": 7.142857142857143,
        "velocity": 0.7073553026306459,
        "wall": 1.976134936300018
    }
