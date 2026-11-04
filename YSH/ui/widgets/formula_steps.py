"""Generic Formula View 2.0 layout and localization, without engineering math."""
from dataclasses import dataclass, fields
from collections.abc import Callable
from tkinter import ttk

from engineering.formula.common import reason_for
from engineering.formula.models import FormulaStep
from engineering.provenance import SourceReference
from ui.formula_asset_policy import step_asset_names, STEP_ASSET_KEYS, QUARANTINED_ASSETS
from ui.widgets.detail_disclosure import DetailDisclosure


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
        if value is None or value == "":
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
    library_links = []
    if step.selection_reason:
        reasons.append(tr(f"formula2.reason.{step.selection_reason.value}"))
    for variable in step.variables:
        if variable.reason or variable.source:
            reason = variable.reason or reason_for(variable.source)
            reasons.append(f"{variable.symbol}: {tr(f'formula2.reason.{reason.value}')}")
    for value in step.used_values:
        reasons.append(f"{value.symbol or ''}: {tr(f'formula2.reason.{reason_for(value.source).value}')}")
        if value.selection_reason:
            # Generated Library identities belong in diagnostics, not normal prose.
            from uuid import UUID
            parts=value.selection_reason.split(' · ')
            try:
                identity=UUID(parts[0].removeprefix('Fire Library ')) if len(parts)>=4 and parts[0].startswith('Fire Library ') else None
            except ValueError:
                identity=None
            if identity is None:
                reasons.append(value.selection_reason)
            else:
                reasons.append(' · '.join((tr('fire.library.mode.linked'),parts[1],parts[2],
                    tr('fire.library.service.'+parts[3]),*parts[4:])))
                library_links.append((value.symbol or '',str(identity),parts[1]))
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
            tr("formula2.source.source_type"), tr("formula2.source.source_organization"), tr("formula2.source.document"),
            tr("formula2.source.verification_status")))
        sections.append(StepSection("source", summary, rows=rows, details=len(rows) > 3))
    links = tuple((v.symbol, str(v.source_selection_id), str(v.source_revision)) for v in step.variables if v.source_selection_id)+tuple(library_links)
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


def verification_style(section: StepSection, translate: Callable[[str], str]) -> str:
    """Color only the recorded verification label; source presence is never proof."""
    status_label = translate('formula2.source.verification_status')
    value = next((value for label, value in section.rows if label == status_label), '')
    for status, role in (('VERIFIED','Verified'), ('PARTIALLY_VERIFIED','Warning'),
                         ('USER_SUPPLIED','Info'), ('UNVERIFIED','Warning'), ('DEPRECATED','Error')):
        if value == translate('formula2.verification_status.'+status):
            return 'FV'+role+'.TLabel'
    return 'FVMuted.TLabel'


def source_summary(section: StepSection, translate: Callable[[str], str]) -> str:
    """Keep verification visible even when document metadata is very long."""
    values = dict(section.rows)
    return ' · '.join(values[key] for key in (
        translate('formula2.source.verification_status'), translate('formula2.source.source_type'))
        if key in values) or section.text


def render_step(panel: object, step: FormulaStep, row: int) -> None:
    """Present one selected, precomputed step; asset resolution and evidence stay intact."""
    from ui.theme.spacing import XS, SM, MD
    tr = panel._translate
    prefix = getattr(panel, '_visual_prefix', 'FVNeutral')
    card = ttk.LabelFrame(panel._content, text=tr(step.title_key), padding=MD,
                          style=prefix+'Stage.TLabelframe')
    card.grid(row=row, column=0, sticky='ew', pady=(0, MD))
    card.columnconfigure(0, weight=1)
    panel._step_card = card
    panel._step_regions = {}
    panel._disclosures = []
    ttk.Frame(card, style=prefix+'Accent.TFrame').grid(row=0,column=0,sticky='ew',pady=(0,SM))
    header = ttk.Frame(card, style='FVBody.TFrame')
    header.grid(row=1,column=0,sticky='ew');header.columnconfigure(0,weight=1)
    ttk.Label(header, text=tr(f'formula2.classification.{step.classification.value}'),
              style='FVMetadata.TLabel', wraplength=640).grid(row=0,column=0,sticky='w')
    from ui.widgets.formula_view import FormulaSection
    for index, section in enumerate(step_sections(step, tr), 2):
        if section.details or section.key == 'source':
            summary = source_summary(section,tr) if section.key=='source' else section.text
            region = DetailDisclosure(card, tr(f'formula2.{section.key}'), summary,
                style='FVBody.TFrame', body_style='FVBody.TFrame',
                summary_style=verification_style(section,tr) if section.key=='source' else 'FVMetadata.TLabel')
            panel._disclosures.append(region)
            body = region.body
        else:
            region = ttk.Frame(card, style='FVBody.TFrame')
            ttk.Label(region, text=tr(f'formula2.{section.key}'),
                      style=prefix+'Heading.TLabel').grid(row=0,column=0,sticky='w')
            body = ttk.Frame(region, style='FVBody.TFrame')
            body.grid(row=1,column=0,sticky='ew',pady=(XS,0))
        panel._step_regions.setdefault(section.key, []).append(region)
        region.grid(row=index,column=0,sticky='ew',pady=(SM,0))
        region.columnconfigure(0,weight=1);body.columnconfigure(0,weight=1)
        if section.key == 'formula':
            panel._render_section_content(body,
                FormulaSection('FORMULA',section.text,asset_names=step_asset_names(step)), 'FormulaEquation')
            if STEP_ASSET_KEYS.get(step.step_id) in QUARANTINED_ASSETS:
                ttk.Label(body,text=tr('formula2.asset_unverified'),wraplength=620,
                          style='FVMetadata.TLabel').grid(row=3,column=0,columnspan=5,sticky='w',pady=(XS,0))
        elif section.rows:
            # Small native tables wrap inside the narrowest accepted window.
            columns = len(section.rows[0])
            widths = (72,220,110,80) if columns==4 else (90,140,70,160,130) if columns==5 else (180,440)
            for r,cells in enumerate(section.rows):
                for c,value in enumerate(cells):
                    body.columnconfigure(c,weight=1 if c==1 else 0)
                    style='FVTableHeader.TLabel' if r==0 and section.key in ('variables','used_values') else 'FVText.TLabel'
                    if section.key=='source': style='FVMetadata.TLabel'
                    if section.key=='used_values' and r>0 and step.used_values[r-1].is_overridden:
                        style='FVOverride.TLabel'
                    ttk.Label(body,text=value,wraplength=widths[min(c,len(widths)-1)],justify='left',
                              style=style).grid(row=r,column=c,sticky='nw',padx=(0,SM),pady=2)
        else:
            style = prefix+'Result.TLabel' if section.key=='result' else (
                'FVInfo.TLabel' if section.key=='reason' else 'FVSubstitution.TLabel' if section.key=='substitution' else 'FVText.TLabel')
            if section.key=='check' and step.check:
                role={'PASS':'Verified','WARNING':'Warning','FAIL':'Error'}.get(step.check.status.value,'Muted')
                style='FV'+role+'.TLabel'
            ttk.Label(body,text=section.text,wraplength=640,justify='left',style=style).grid(sticky='ew')
