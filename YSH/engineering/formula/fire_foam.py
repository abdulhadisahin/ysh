"""Explain precomputed Foam results; no arithmetic engine or presentation imports."""
from dataclasses import replace

from engineering.fire.models import FoamSystemResult
from engineering.formula.common import reason_for
from engineering.formula.models import FormulaStep, FormulaVariable, SelectionReason
from engineering.provenance import SourceReference, SourceType


def foam_steps(result: FoamSystemResult) -> tuple[FormulaStep, ...]:
    """Formula source is derived algebra; q/t/c sources remain input evidence."""
    evidence = {item.field_name: item.engineering_value for item in result.input.provenance}

    def input_variable(name, symbol, key):
        value = evidence[name]
        return FormulaVariable(symbol=symbol, terminology_key=key,
            value=value.used_value, unit=value.unit, source=value.source,
            reason=reason_for(value.source))

    def calculated(symbol, value, key, unit="L/min"):
        return FormulaVariable(symbol=symbol, terminology_key=key, value=value,
                               unit=unit, reason=SelectionReason.CALCULATED)

    area = input_variable("protected_area_m2", "A", "fire.foam.area")
    density = input_variable("application_density_lpm_m2", "q", "fire.foam.density")
    duration = input_variable("application_duration_min", "t", "fire.foam.duration")
    ratio = input_variable("foam_fraction", "Cfoam", "fire.foam.fraction")
    solution = calculated("Qsolution", result.solution_flow_lpm, "fire.foam.solution_flow")
    concentrate = calculated("Qfoam", result.foam_concentrate_flow_lpm, "fire.foam.concentrate_flow")
    water = calculated("Qwater", result.water_flow_lpm, "fire.foam.water_flow")
    volume = calculated("Vfoam", result.foam_concentrate_volume_l, "fire.foam.concentrate_volume", "L")
    specs = (
        ("solution_flow", "Qsolution = A × q", (area, density, solution), solution,
         ("protected_area_m2", "application_density_lpm_m2"),
         f"Qsolution = {area.value!r} × {density.value!r} = {solution.value!r} L/min"),
        ("concentrate_flow", "Qfoam = Cfoam × Qsolution", (ratio, solution, concentrate), concentrate,
         ("foam_fraction",),
         f"Qfoam = {ratio.value!r} × {solution.value!r} = {concentrate.value!r} L/min"),
        ("water_flow", "Qwater = (1 - Cfoam) × Qsolution", (ratio, solution, water), water,
         ("foam_fraction",),
         f"Qwater = (1 - {ratio.value!r}) × {solution.value!r} = {water.value!r} L/min"),
        ("concentrate_volume", "Vfoam = Qfoam × t", (concentrate, duration, volume), volume,
         ("application_duration_min",),
         f"Vfoam = {concentrate.value!r} × {duration.value!r} = {volume.value!r} L"),
    )
    steps = []
    for order, (name, equation, variables, output, used_names, substitution) in enumerate(specs):
        formula_source = SourceReference(source_type=SourceType.CALCULATED,
            document="D243 Fire Phase 0 — Source Decisions", revision="2026-10-21",
            section="4 — Nominal volumetric mixing contract",
            formula=result.rule_ids[order].value,
            notes="Derived relation under explicit mixture basis; not a source for input defaults or compliance.")
        used = tuple(replace(evidence[n], symbol={"protected_area_m2":"A",
            "application_density_lpm_m2":"q", "application_duration_min":"t", "foam_fraction":"Cfoam"}[n],
            terminology_key={"protected_area_m2":"fire.foam.area", "application_density_lpm_m2":"fire.foam.density",
                             "application_duration_min":"fire.foam.duration", "foam_fraction":"fire.foam.fraction"}[n])
            for n in used_names)
        steps.append(FormulaStep(step_id="fire.foam."+name, title_key="fire.foam."+name,
            formula_text=equation, variables=variables, used_values=used,
            result_value=output.value, result_unit=output.unit, result_symbol=output.symbol,
            display_order=order, selection_reason=SelectionReason.CALCULATED,
            sources=(formula_source,), substitution=substitution))
    return tuple(steps)
