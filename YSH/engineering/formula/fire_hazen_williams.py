"""Two explanations of precomputed HW results; source equation is not input evidence."""
from dataclasses import replace
from engineering.fire.models import HazenWilliamsResult
from engineering.formula.common import reason_for
from engineering.formula.models import FormulaStep, FormulaVariable, SelectionReason
from engineering.provenance import SourceReference, SourceType


def hazen_williams_steps(result: HazenWilliamsResult) -> tuple[FormulaStep, ...]:
    evidence = {p.field_name: p.engineering_value for p in result.input.provenance}
    specs = (("flow_lpm", "Q", "flow"), ("hazen_williams_c", "CHW", "c"),
             ("inside_diameter_mm", "Di", "diameter"), ("pipe_length_m", "L", "length"))
    variables = {}
    used = {}
    for name, symbol, key in specs:
        item = evidence[name]
        linked = result.input.pipe_input
        snap = linked.snapshot if linked else None
        variables[name] = FormulaVariable(symbol=symbol, terminology_key="fire.hw."+key,
            value=item.used_value, unit=item.unit, source=item.source,
            reason=SelectionReason.LINKED_PIPE_SELECTION if snap and name in (
                "flow_lpm", "inside_diameter_mm") else reason_for(item.source),
            source_selection_id=snap.source_selection_id if snap and name in (
                "flow_lpm", "inside_diameter_mm") else None,
            source_revision=snap.source_revision if snap and name in (
                "flow_lpm", "inside_diameter_mm") else None)
        used[name] = replace(item, symbol=symbol, terminology_key="fire.hw."+key)
    q, c, d, length = (variables[n] for n, _, _ in specs)
    r = FormulaVariable(symbol="rHW", terminology_key="fire.hw.unit_loss",
        value=result.pressure_loss_per_m_bar, unit="bar/m", reason=SelectionReason.CALCULATED)
    total = FormulaVariable(symbol="ΔpHW", terminology_key="fire.hw.total_loss",
        value=result.total_pressure_loss_bar, unit="bar", reason=SelectionReason.CALCULATED)
    source = SourceReference(source_type=SourceType.MANUFACTURER_DATA,
        source_organization="Johnson Controls / SKUM", document="ZF Inductor",
        revision="FDS-2017084-04 ©2024", section="p.2 Calculations",
        formula="FIRE.HW.EQUATION",
        notes="Phase 0 S03 practical units; limited water straight-pipe scope; not a C-value source or compliance approval.")
    rows = (
        ("unit_loss", "rHW = 605000 × Q^1.85 / (CHW^1.85 × Di^4.87)", (q,c,d,r), r,
         ("flow_lpm","hazen_williams_c","inside_diameter_mm"),
         f"rHW = 605000 × {q.value!r}^1.85 / ({c.value!r}^1.85 × {d.value!r}^4.87) = {r.value!r} bar/m"),
        ("total_loss", "ΔpHW = rHW × L", (r,length,total), total, ("pipe_length_m",),
         f"ΔpHW = {r.value!r} bar/m × {length.value!r} m = {total.value!r} bar"),
    )
    return tuple(FormulaStep(step_id="fire.hw."+key, title_key="fire.hw."+key,
        formula_text=equation, variables=vs, used_values=tuple(used[n] for n in names),
        result_value=out.value, result_unit=out.unit, result_symbol=out.symbol,
        display_order=order, sources=(source,), substitution=substitution,
        selection_reason=SelectionReason.CALCULATED)
        for order,(key,equation,vs,out,names,substitution) in enumerate(rows))
