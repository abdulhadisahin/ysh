"""Adapters for active legacy and configured V2 pipe results."""
from engineering.formula.common import step, used, variable
from engineering.formula.models import CheckStatus, FormulaCheck, FormulaStep, SelectionReason
from engineering.pipe_design.models import PipeDesignCalculationResult
from engineering.pipe_design.rules import StressMode
from engineering.pipe_design.v2_models import PipeDesignV2Input, PipeSelection
from engineering.provenance import SourceReference, SourceType


def legacy_pipe_steps(result: PipeDesignCalculationResult) -> tuple[FormulaStep, ...]:
    """Read the service-captured inputs, including resolved library strength."""
    steps = []
    diameter = result.diameter
    if diameter is not None:
        raw = result.trace.get("diameter_input", {})
        variables = tuple(variable(symbol, raw[key], unit) for symbol, key, unit in (
            ("Q", "flow_rate_m3h", "m³/h"), ("V", "design_velocity_mps", "m/s")) if key in raw)
        steps.append(step("pipe.D", "D", diameter.diameter_mm, "mm",
                          "D = √((4 × Qm³/s) / (π × V))", variables, 0,
                          used_values=(used("V", raw["design_velocity_mps"], "m/s"),)
                          if "design_velocity_mps" in raw else ()))
        if diameter.recommended_inside_diameter_mm is not None:
            source = SourceReference(source_type=SourceType.PIPE_STANDARD,
                                     document=result.trace.get("pipe_standard_code"))
            steps.append(step("pipe.Di", "Di", diameter.recommended_inside_diameter_mm, "mm",
                              "formula2.standard_selection", (), 7,
                              selection_reason=SelectionReason.PIPE_STANDARD, sources=(source,)))
    wall = result.wall_thickness
    if wall is not None:
        raw = result.trace.get("wall_input", {})
        def values(*items: tuple[str, str, str]) -> tuple:
            return tuple(variable(symbol, raw[key], unit) for symbol, key, unit in items
                         if key in raw and raw[key] is not None)
        stress = variable("σallow", wall.allowable_stress_mpa, "MPa")
        base = variable("s0", wall.base_wall_thickness_mm, "mm")
        steps.extend((
            step("pipe.stress", "σallow", wall.allowable_stress_mpa, "MPa", "σallow = Rp0.2 / B",
                 values(("Rp0.2", "yield_strength_mpa", "MPa"), ("B", "safety_factor", "")), 1),
            step("pipe.s0", "s0", wall.base_wall_thickness_mm, "mm",
                 "s0 = (da × pc) / ((20 × σallow × v) + pc)",
                 values(("da", "outside_diameter_mm", "mm"), ("pc", "design_pressure_bar", "bar"),
                        ("v", "weld_factor", "")) + (stress,), 2),
            step("pipe.b", "b", wall.bend_allowance_mm, "mm",
                 ("b = 0.4 × (da / R) × s0" if raw["bend_allowance_enabled"] else "formula2.no_bend")
                 if "bend_allowance_enabled" in raw else "formula2.precomputed",
                 values(("da", "outside_diameter_mm", "mm"), ("R", "bend_radius_mm", "mm")) + (base,)
                 if raw.get("bend_allowance_enabled") else (), 3),
            step("pipe.c", "c", wall.corrosion_allowance_mm, "mm", "c",
                 (), 4, used_values=(used("c", wall.corrosion_allowance_mm, "mm"),)
                 if raw else ()),
            step("pipe.wall", "s", wall.final_wall_thickness_mm, "mm", "s = s0 + c + b",
                 (base, variable("c", wall.corrosion_allowance_mm, "mm"),
                  variable("b", wall.bend_allowance_mm, "mm")), 6),
        ))
    return tuple(steps)


def pipe_steps(result: PipeSelection, inp: PipeDesignV2Input) -> tuple[FormulaStep, ...]:
    """Explain configured results without evaluating any rule or selecting a pipe."""
    from dataclasses import replace
    from engineering.pipe_design.models import WallThicknessResult
    legacy = PipeDesignCalculationResult(trace={"diameter_input": {
        "flow_rate_m3h": result.flow_rate_m3_h, "design_velocity_mps": result.design_velocity_m_s}})
    if result.wall is not None and result.allowable_stress is not None and result.allowable_stress.value is not None:
        from dataclasses import asdict
        wall = result.wall
        legacy.wall_thickness = WallThicknessResult(result.allowable_stress.value, wall.base_wall_mm,
            wall.bend_allowance_mm, wall.corrosion_allowance_mm, wall.final_required_wall_mm)
        legacy.trace["wall_input"] = {**asdict(inp), "outside_diameter_mm": result.candidate.outside_diameter_mm}
    steps = list(legacy_pipe_steps(legacy))
    steps.insert(0, step("pipe.D", "D", result.theoretical_internal_diameter_mm, "mm",
        "D = √((4 × Qm³/s) / (π × V))",
        (variable("Q", result.flow_rate_m3_h, "m³/h"), variable("V", result.design_velocity_m_s, "m/s")), 0,
        used_values=tuple(v for v in (result.provenance.design_velocity,) if v is not None)))
    provenance = result.provenance
    by_id = {"pipe.stress": provenance.allowable_stress, "pipe.c": provenance.corrosion_allowance,
             "pipe.s0": provenance.source_factor}
    for index, current in enumerate(steps):
        selected = by_id.get(current.step_id)
        if selected is not None:
            steps[index] = replace(current, used_values=(selected,), sources=(selected.source,))
        if current.step_id == "pipe.stress" and inp.stress_rule.mode is not StressMode.LEGACY_RP02:
            steps[index] = replace(steps[index], formula_text="formula2.configured_stress", variables=())
        if current.step_id == "pipe.wall":
            variables = current.variables
            if result.wall.manufacturing_allowance_mm is not None:
                variables += (variable("tolerance", result.wall.manufacturing_allowance_mm, "mm",
                                       key="formula2.tolerance"),)
            if result.wall.minimum_required_wall_mm is not None:
                variables += (variable("minimum", result.wall.minimum_required_wall_mm, "mm", key="formula2.minimum"),)
            steps[index] = replace(current, formula_text="formula2.required_wall", variables=variables)
    for name, rule, configured in (("tolerance", result.manufacturing_tolerance, provenance.manufacturing_tolerance),
                                   ("minimum", result.minimum_wall, provenance.minimum_wall)):
        if rule is not None and rule.value is not None:
            steps.append(replace(step(f"pipe.{name}", name, rule.value, "mm", "formula2.configured_rule", (), 5,
                                used_values=(configured,) if configured else (),
                                sources=(rule.source,) if rule.source else ()), title_key=f"formula2.{name}"))
    steps.extend(selection_geometry_steps(result))
    return tuple(steps)


def selection_geometry_steps(result: PipeSelection) -> tuple[FormulaStep, ...]:
    """Read already selected geometry and velocity; do not resolve a source link."""
    steps = []
    if result.selected_pipe is not None:
        source = result.selected_pipe.dimension_source
        steps.append(step("pipe.Di", "Di", result.actual_internal_diameter_mm, "mm",
                          "formula2.standard_selection", (), 7, selection_reason=SelectionReason.PIPE_STANDARD,
                          sources=(source,) if source else ()))
        steps.append(step("pipe.selected_wall", "s", result.selected_wall_thickness_mm, "mm",
                          "formula2.standard_selection", (), 8,
                          selection_reason=SelectionReason.PIPE_STANDARD,
                          sources=(source,) if source else ()))
    if result.actual_velocity_m_s is not None:
        steps.append(step("pipe.actual_velocity", "V", result.actual_velocity_m_s, "m/s", "V = 4Q / (πDi²)",
            (variable("Q", result.flow_rate_m3_h, "m³/h"), variable("Di", result.actual_internal_diameter_mm, "mm")), 8,
            check=FormulaCheck(status=CheckStatus.PASS if result.velocity_within_design else CheckStatus.WARNING,
                               actual_value=result.actual_velocity_m_s, reference_value=result.design_velocity_m_s,
                               operator="<=", reason_key="formula2.velocity_check")))
    return tuple(steps)
