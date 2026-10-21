"""Headless Foam application orchestration; the Phase 1 domain owns every equation."""
from dataclasses import asdict
from types import MappingProxyType

from engineering.fire.calculators import calculate_foam_system
from engineering.fire.enums import FireSourceStatus
from engineering.fire.foam_workflow import (
    FoamWorkflowInput, FoamWorkflowResult, FoamWorkflowStatus, FoamSourceMessage,
    FoamSummaryValue, SourceMessageCategory, SourceReadiness,
)
from engineering.fire.models import FoamSystemInput
from engineering.fire.provenance import ParameterProvenance
from engineering.fire.units import percent_to_fraction, lpm_to_m3h, litres_to_m3
from engineering.formula.fire_foam import foam_steps
from engineering.snapshots.serialization import canonical
from engineering.validation import ValidationError, ValidationIssue

INPUT_UNITS = MappingProxyType({"protected_area_m2":"m²", "application_density_lpm_m2":"L/(min·m²)",
                               "application_duration_min":"min", "foam_fraction":"1"})


class FoamCalculationService:
    """No state or external dependencies; repeated identical inputs give identical payloads."""

    def calculate(self, request: FoamWorkflowInput) -> FoamWorkflowResult:
        if not isinstance(request, FoamWorkflowInput):
            raise TypeError("request requires FoamWorkflowInput")
        evidence = []
        for name in INPUT_UNITS:
            item = getattr(request, name)
            if item is None:
                raise ValidationError(ValidationIssue("required", name))
            if not isinstance(item, ParameterProvenance):
                raise TypeError("input fields require ParameterProvenance")
            if item.field_name != name:
                raise ValidationError(ValidationIssue("fire.provenance_field", name))
            evidence.append(item)
        if request.mixture_basis is None:
            raise ValidationError(ValidationIssue("required", "mixture_basis"))
        evidence = tuple(evidence)
        normalized = {item.field_name:item.engineering_value.used_value for item in evidence}
        domain_input = FoamSystemInput(**normalized, mixture_basis=request.mixture_basis,
                                     provenance=evidence, context=request.context)
        raw = {name:{"value":value,"unit":INPUT_UNITS[name],"representation":"normalized_input"}
               for name,value in normalized.items()}
        seen = set()
        for observation in request.raw_inputs:
            name = observation.field_name
            if name not in INPUT_UNITS or name in seen:
                raise ValidationError(ValidationIssue("fire.raw_input_field", name))
            seen.add(name)
            if name == "foam_fraction" and observation.unit == "%":
                compared = percent_to_fraction(observation.value)
            elif observation.unit == INPUT_UNITS[name]:
                compared = observation.value
            else:
                raise ValidationError(ValidationIssue("fire.raw_input_unit", name))
            if compared != normalized[name]:
                raise ValidationError(ValidationIssue("fire.raw_input_mismatch", name))
            raw[name] = {"value":observation.value,"unit":observation.unit,"representation":"original_input"}

        domain = calculate_foam_system(domain_input)
        steps = foam_steps(domain)
        messages = []
        for item in evidence:
            status = item.source_status
            if status in (FireSourceStatus.SOURCE_VERIFIED, FireSourceStatus.DERIVED_FROM_VERIFIED_RULE):
                continue
            category = {
                FireSourceStatus.SOURCE_VERIFIED_CONTEXT_DEPENDENT: SourceMessageCategory.SOURCE_CONTEXT_REQUIRED,
                FireSourceStatus.USER_PROJECT_ASSUMPTION: SourceMessageCategory.INFO,
                FireSourceStatus.WORKBOOK_REFERENCE_ONLY: SourceMessageCategory.WARNING,
            }.get(status, SourceMessageCategory.SOURCE_REQUIRED)
            messages.append(FoamSourceMessage(field_name=item.field_name, source_status=status,
                category=category, message_key="fire.foam.source."+status.value))
        messages = tuple(messages)
        readiness = (SourceReadiness.REVIEW_REQUIRED if any(
            m.category is not SourceMessageCategory.SOURCE_CONTEXT_REQUIRED for m in messages)
            else SourceReadiness.CONTEXT_REQUIRED if messages else SourceReadiness.READY)
        status = (FoamWorkflowStatus.CALCULATED_WITH_SOURCE_WARNING if messages
                  else FoamWorkflowStatus.CALCULATED)
        summary = (
            FoamSummaryValue(key="solution_flow_lpm", label_key="fire.foam.solution_flow",symbol="Qsolution",value=domain.solution_flow_lpm,unit="L/min"),
            FoamSummaryValue(key="foam_concentrate_flow_lpm",label_key="fire.foam.concentrate_flow",symbol="Qfoam",value=domain.foam_concentrate_flow_lpm,unit="L/min"),
            FoamSummaryValue(key="water_flow_lpm",label_key="fire.foam.water_flow",symbol="Qwater",value=domain.water_flow_lpm,unit="L/min"),
            FoamSummaryValue(key="foam_concentrate_volume_l",label_key="fire.foam.concentrate_volume",symbol="Vfoam",value=domain.foam_concentrate_volume_l,unit="L"),
        )
        payload = {
            "payload_version":1, "workflow_version":FoamWorkflowResult.workflow_version,
            "calculation_type":domain.calculation_type, "formula_version":domain.formula_version,
            "rule_ids":domain.rule_ids, "case_id":request.case_id, "revision":request.revision,
            "raw_inputs":raw, "normalized_inputs":normalized, "input_units":dict(INPUT_UNITS),
            "mixture_basis":domain_input.mixture_basis, "context":domain_input.context,
            "assumptions":request.assumptions, "provenance":[asdict(v) for v in evidence],
            "results":{row.key:{"value":row.value,"unit":row.unit} for row in summary},
            "converted_results":{
                "foam_concentrate_flow_m3h":{"value":lpm_to_m3h(domain.foam_concentrate_flow_lpm),"unit":"m³/h"},
                "water_flow_m3h":{"value":lpm_to_m3h(domain.water_flow_lpm),"unit":"m³/h"},
                "foam_concentrate_volume_m3":{"value":litres_to_m3(domain.foam_concentrate_volume_l),"unit":"m³"},
            },
            "formula_steps":steps, "warnings":[asdict(m) for m in messages],
            "calculation_validity":"VALID", "source_readiness":readiness, "status":status,
            "primary_result_key":"foam_concentrate_volume_l", "summary":[asdict(v) for v in summary],
        }
        return FoamWorkflowResult(domain_result=domain, formula_steps=steps, warnings=messages,
            status=status, source_readiness=readiness, input_provenance=evidence,
            summary=summary, primary_result_key="foam_concentrate_volume_l", payload_json=canonical(payload))
