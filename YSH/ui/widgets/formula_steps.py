"""Generic Formula View 2.0 layout and localization, without engineering math."""
from dataclasses import dataclass, fields
from collections.abc import Callable
from tkinter import ttk

from engineering.formula.common import reason_for
from engineering.formula.models import FormulaStep
from engineering.provenance import SourceReference


@dataclass(frozen=True, slots=True)
class StepSection:
    """Display-only table or text region; absent content creates no section."""
    key: str
    text: str = ""
    rows: tuple[tuple[str, ...], ...] = ()
    details: bool = False


def number(value: float) -> str:
    """Format a copy using the shared V2 precision target."""
    from ui.formatting import format_user_number
    if 0 < abs(value) < 0.005:
        return f"{value:.2e}".replace(".", ",")
    return format_user_number(value)


def source_rows(source: SourceReference, translate: Callable[[str], str]) -> tuple[tuple[str, str], ...]:
    """Omit NULL metadata; source presence never implies verification."""
    rows = []
    for field in fields(source):
        value = getattr(source, field.name)
        if value is None:
            continue
        if field.name in ("source_type", "verification_status"):
            value = translate(f"formula2.{field.name}.{value.value}")
        elif hasattr(value, "isoformat"):
            value = value.isoformat()
        rows.append((translate(f"formula2.source.{field.name}"), str(value)))
    return tuple(rows)


def step_sections(step: FormulaStep, translate: Callable[[str], str]) -> tuple[StepSection, ...]:
    """Present raw step data; symbol bindings explain substitution without evaluation."""
    tr = translate
    sections = [StepSection("formula", tr(step.formula_text) if step.formula_text.startswith("formula2.") else step.formula_text)]
    if step.variables:
        rows = [(tr("formula2.symbol"), tr("formula2.description"), tr("formula2.value"), tr("formula2.unit"))]
        rows.extend((v.symbol, tr(v.terminology_key), number(v.value), v.unit) for v in step.variables)
        sections.append(StepSection("variables", rows=tuple(rows)))
    if step.reference_variables:
        rows = tuple((v.context or "", v.symbol, tr(v.terminology_key), number(v.value), v.unit)
                     for v in step.reference_variables)
        sections.append(StepSection("reference_data", rows=rows, details=True))
    if step.used_values:
        rows = [(tr("formula2.symbol"), tr("formula2.used"), tr("formula2.unit"), tr("formula2.source_type"), tr("formula2.override"))]
        rows.extend((v.symbol or tr(v.terminology_key or "formula2.value"), number(v.used_value), v.unit,
                     tr(f"formula2.source_type.{v.source.source_type.value}"),
                     tr(f"formula2.override.{v.override_policy.value}") +
                     (f" · {tr('formula2.overridden')}" if v.is_overridden else "")) for v in step.used_values)
        sections.append(StepSection("used_values", rows=tuple(rows)))
    reasons = []
    if step.selection_reason:
        reasons.append(tr(f"formula2.reason.{step.selection_reason.value}"))
    for variable in step.variables:
        if variable.reason or variable.source:
            reason = variable.reason or reason_for(variable.source)
            reasons.append(f"{variable.symbol}: {tr(f'formula2.reason.{reason.value}')}")
    for value in step.used_values:
        reasons.append(f"{value.symbol or ''}: {tr(f'formula2.reason.{reason_for(value.source).value}')}")
        if value.selection_reason:
            reasons.append(value.selection_reason)
        if value.recommended_value is not None:
            reasons.append(f"{tr('formula2.recommended')}: {number(value.recommended_value)} {value.unit}; "
                           f"{tr('formula2.used')}: {number(value.used_value)} {value.unit}")
        if value.override_reason:
            reasons.append(f"{tr('formula2.override_reason')}: {value.override_reason}")
    if reasons:
        sections.append(StepSection("reason", "\n".join(dict.fromkeys(reasons))))
    sources = list(step.sources) + [v.source for v in step.variables if v.source] + [v.source for v in step.used_values]
    if step.check and step.check.source:
        sources.append(step.check.source)
    for source in dict.fromkeys(sources):
        rows = source_rows(source, tr)
        summary = " · ".join(value for name, value in rows if name in (
            tr("formula2.source.source_type"), tr("formula2.source.document"),
            tr("formula2.source.verification_status")))
        sections.append(StepSection("source", summary, rows=rows, details=len(rows) > 3))
    links = tuple((v.symbol, str(v.source_selection_id), str(v.source_revision)) for v in step.variables if v.source_selection_id)
    if links:
        sections.append(StepSection("technical_details", rows=links, details=True))
    if step.substitution or step.variables:
        binding = "; ".join(f"{v.symbol} = {number(v.value)} {v.unit}" for v in step.variables)
        sections.append(StepSection("substitution", step.substitution or binding))
    sections.append(StepSection("result", f"{step.result_symbol} = {number(step.result_value)} {step.result_unit}"))
    if step.check:
        check = step.check
        parts = [tr(f"formula2.check.{check.status.value}")]
        if check.actual_value is not None and check.reference_value is not None:
            parts.append(f"{number(check.actual_value)} {check.operator or ''} {number(check.reference_value)}")
        if check.reason_key:
            parts.append(tr(check.reason_key))
        sections.append(StepSection("check", "\n".join(parts)))
    return tuple(sections)


def render_step(panel: object, step: FormulaStep, row: int) -> None:
    """Render a vertical engineering card using existing equation fallbacks."""
    tr = panel._translate
    card = ttk.LabelFrame(panel._content, text=tr(step.title_key), padding=12,
                          style="FormulaStage.TLabelframe")
    card.grid(row=row, column=0, sticky="ew", pady=(0, 12))
    card.columnconfigure(0, weight=1)
    ttk.Label(card, text=tr(f"formula2.classification.{step.classification.value}")).grid(row=0, sticky="w")
    from ui.widgets.formula_view import FormulaSection
    for index, section in enumerate(step_sections(step, tr), 1):
        region = ttk.LabelFrame(card, text=tr(f"formula2.{section.key}"), padding=8)
        region.grid(row=index, column=0, sticky="ew", pady=(6, 0))
        region.columnconfigure(0, weight=1)
        body = ttk.Frame(region)
        body.grid(row=1, column=0, sticky="ew")
        if section.details:
            body.grid_remove()
            if section.text:
                ttk.Label(region, text=section.text, wraplength=720).grid(row=0, sticky="w")
            def toggle(target: ttk.Frame = body) -> None:
                (target.grid_remove if target.winfo_manager() else target.grid)()
            ttk.Button(region, text=tr("formula2.details"), command=toggle).grid(row=2, sticky="w")
        if section.key == "formula":
            panel._render_section_content(body, FormulaSection("FORMULA", section.text), "FormulaEquation")
        elif section.rows:
            for r, cells in enumerate(section.rows):
                for c, value in enumerate(cells):
                    body.columnconfigure(c, weight=1 if c == 1 else 0)
                    ttk.Label(body, text=value, wraplength=420 if c == 1 else 180,
                              justify="left").grid(row=r, column=c, sticky="nw", padx=(0, 12), pady=3)
        else:
            ttk.Label(body, text=section.text, wraplength=720, justify="left").grid(sticky="ew")
