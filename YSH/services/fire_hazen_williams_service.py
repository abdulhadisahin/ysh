"""Headless water-only orchestration; Phase 1 exclusively owns HW arithmetic."""
from dataclasses import asdict
from types import MappingProxyType

from engineering.fire.calculators import calculate_hazen_williams, FireCalculationBlocked
from engineering.fire.enums import FireSourceStatus, HWApplicability
from engineering.fire.foam_workflow import FoamSourceMessage, FoamSummaryValue, SourceMessageCategory, SourceReadiness
from engineering.fire.hazen_williams_workflow import (
    HazenWilliamsWorkflowInput, HazenWilliamsWorkflowResult, HWWorkflowStatus, HWService,
)
from engineering.fire.models import HazenWilliamsInput
from engineering.fire.pipe_adapter import hazen_williams_from_pipe
from engineering.fire.provenance import ParameterProvenance
from engineering.fire.units import m3h_to_lpm
from engineering.formula.fire_hazen_williams import hazen_williams_steps
from engineering.pipe_design.transfer import PipeInputMode, PipeLinkStatus
from engineering.provenance import EngineeringValue, OverridePolicy, SourceReference, SourceType
from engineering.snapshots.serialization import canonical
from engineering.validation import ValidationError, ValidationIssue

INPUT_UNITS = MappingProxyType({"flow_lpm":"L/min", "inside_diameter_mm":"mm",
                               "pipe_length_m":"m", "hazen_williams_c":"1"})


class HWApplicabilityBlocked(FireCalculationBlocked):
    workflow_status = "BLOCKED_APPLICABILITY"
    calculation_validity = "NOT_CALCULATED"

    def __init__(self, request):
        self.service = request.service
        self.applicability = request.applicability
        super().__init__(FireSourceStatus.SOURCE_REQUIRED, "FIRE-HW-UNITS-001")


class HazenWilliamsCalculationService:
    def calculate(self, request: HazenWilliamsWorkflowInput) -> HazenWilliamsWorkflowResult:
        if not isinstance(request, HazenWilliamsWorkflowInput):
            raise TypeError("request requires HazenWilliamsWorkflowInput")
        # Gate before adapter/calculator execution; no numeric result for blocked services.
        if request.service is not HWService.WATER or request.applicability is not HWApplicability.WATER_ONLY:
            raise HWApplicabilityBlocked(request)
        pipe = request.pipe_input
        mode = pipe.mode if pipe else PipeInputMode.MANUAL
        evidence = []
        for name, unit in INPUT_UNITS.items():
            item = getattr(request, name)
            if item is None and name == "inside_diameter_mm" and mode is PipeInputMode.LINKED:
                diameter = pipe.used_values.actual_internal_diameter_mm
                source = pipe.used_values.dimension_source or SourceReference(
                    source_type=SourceType.PIPE_STANDARD,
                    notes="Applied PipeSelection geometry; source verification not supplied.")
                # Captured transfer is locked, but it does not acquire verification.
                item = ParameterProvenance(field_name=name, source_status=FireSourceStatus.SOURCE_REQUIRED,
                    engineering_value=EngineeringValue(used_value=diameter, recommended_value=diameter,
                        unit=unit, source=source, override_policy=OverridePolicy.LOCKED,
                        selection_reason="LINKED_PIPE_SELECTION"))
            if item is None:
                raise ValidationError(ValidationIssue("required", name))
            if not isinstance(item, ParameterProvenance):
                raise TypeError("inputs require ParameterProvenance")
            if item.field_name != name:
                raise ValidationError(ValidationIssue("fire.provenance_field", name))
            evidence.append(item)
        evidence = tuple(evidence)
        normalized = {p.field_name:p.engineering_value.used_value for p in evidence}
        if pipe:
            domain_input = hazen_williams_from_pipe(pipe,
                pipe_length_m=normalized["pipe_length_m"], hazen_williams_c=normalized["hazen_williams_c"],
                applicability=request.applicability, provenance=evidence, context=request.context)
        else:
            domain_input = HazenWilliamsInput(**normalized, applicability=request.applicability,
                provenance=evidence, context=request.context)
        raw = {name:{"value":value,"unit":INPUT_UNITS[name],"representation":"normalized_input"}
               for name,value in normalized.items()}
        seen = set()
        for observation in request.raw_inputs:
            name = observation.field_name
            if name not in INPUT_UNITS or name in seen:
                raise ValidationError(ValidationIssue("fire.raw_input_field", name))
            seen.add(name)
            if observation.unit == INPUT_UNITS[name]:
                value = observation.value
            elif name == "flow_lpm" and observation.unit == "m³/h":
                value = m3h_to_lpm(observation.value)
            else:
                raise ValidationError(ValidationIssue("fire.raw_input_unit", name))
            if value != normalized[name]:
                raise ValidationError(ValidationIssue("fire.raw_input_mismatch", name))
            raw[name] = {"value":observation.value,"unit":observation.unit,"representation":"original_input"}
        domain = calculate_hazen_williams(domain_input)
        steps = hazen_williams_steps(domain)
        messages = []
        for item in evidence:
            source_status = item.source_status
            if source_status in (FireSourceStatus.SOURCE_VERIFIED, FireSourceStatus.DERIVED_FROM_VERIFIED_RULE):
                continue
            category = {
                FireSourceStatus.SOURCE_VERIFIED_CONTEXT_DEPENDENT:SourceMessageCategory.SOURCE_CONTEXT_REQUIRED,
                FireSourceStatus.USER_PROJECT_ASSUMPTION:SourceMessageCategory.INFO,
                FireSourceStatus.WORKBOOK_REFERENCE_ONLY:SourceMessageCategory.WARNING,
            }.get(source_status, SourceMessageCategory.SOURCE_REQUIRED)
            messages.append(FoamSourceMessage(field_name=item.field_name, source_status=source_status,
                category=category, message_key="fire.hw.source."+source_status.value))
        if mode is PipeInputMode.LINKED and pipe.status is not PipeLinkStatus.LINKED_SYNCED:
            messages.append(FoamSourceMessage(field_name="pipe_input", source_status=FireSourceStatus.SOURCE_REQUIRED,
                category=SourceMessageCategory.WARNING, message_key="fire.hw.pipe_review"))
        messages = tuple(messages)
        readiness = (SourceReadiness.REVIEW_REQUIRED if any(
            m.category is not SourceMessageCategory.SOURCE_CONTEXT_REQUIRED for m in messages)
            else SourceReadiness.CONTEXT_REQUIRED if messages else SourceReadiness.READY)
        status = HWWorkflowStatus.CALCULATED_WITH_SOURCE_WARNING if messages else HWWorkflowStatus.CALCULATED
        summary = tuple(FoamSummaryValue(key=name,label_key="fire.hw."+key,symbol=symbol,value=value,unit=unit)
            for name,key,symbol,value,unit in (
                ("total_pressure_loss_bar","total_loss","ΔpHW",domain.total_pressure_loss_bar,"bar"),
                ("pressure_loss_per_m_bar","unit_loss","rHW",domain.pressure_loss_per_m_bar,"bar/m"),
                ("flow_lpm","flow","Q",domain.input.flow_lpm,"L/min"),
                ("inside_diameter_mm","diameter","Di",domain.input.inside_diameter_mm,"mm"),
                ("pipe_length_m","length","L",domain.input.pipe_length_m,"m"),
                ("hazen_williams_c","c","CHW",domain.input.hazen_williams_c,"1")))
        pipe_capture = pipe.trace() if pipe else {"mode":mode,"status":PipeLinkStatus.MANUAL,
            "source_selection_id":None,"source_revision":None}
        # Capture applied transfer facts only, never an entire selection/project/UI.
        pipe_capture = pipe_capture | {"inside_diameter_used_mm":domain.input.inside_diameter_mm,
            "values":asdict(pipe.used_values) if pipe else None}
        payload = {
            "payload_version":1,"workflow_version":HazenWilliamsWorkflowResult.workflow_version,
            "calculation_type":domain.calculation_type,"formula_version":domain.formula_version,
            "rule_ids":domain.rule_ids,"case_id":request.case_id,"revision":request.revision,
            "input_mode":mode,"raw_inputs":raw,"normalized_inputs":normalized,"input_units":dict(INPUT_UNITS),
            "service":request.service,"applicability":request.applicability,"context":request.context,
            "assumptions":request.assumptions,"pipe_selection":pipe_capture,
            "provenance":[asdict(p) for p in evidence],"formula_steps":steps,
            "results":{r.key:{"value":r.value,"unit":r.unit} for r in summary[:2]},
            "warnings":[asdict(m) for m in messages],"calculation_validity":"VALID",
            "source_readiness":readiness,"status":status,"primary_result_key":"total_pressure_loss_bar",
            "summary":[asdict(r) for r in summary],
        }
        return HazenWilliamsWorkflowResult(domain_result=domain,formula_steps=steps,warnings=messages,
            status=status,source_readiness=readiness,applicability=request.applicability,service=request.service,
            input_provenance=evidence,pipe_mode=mode,pipe_input=pipe,summary=summary,
            primary_result_key="total_pressure_loss_bar",payload_json=canonical(payload))
