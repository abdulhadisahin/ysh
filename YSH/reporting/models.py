"""Immutable presentation model and snapshot-only adapter for engineering reports."""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import datetime
import json
from typing import TypeAlias

from engineering.formula.models import FormulaStep, ordered_steps
from engineering.provenance import SourceReference
from engineering.snapshots.models import CalculationSnapshot
from engineering.snapshots.serialization import decode
from engineering.validation import ValidationIssue
from i18n.validation import render_validation_issue
from i18n.translator import Translator

Scalar: TypeAlias = str | float | int | bool
_TR = Translator('tr').translate
MODULES = {'pipe_design': 'Boru Tasarımı', 'transfer_pump': 'Yakıt Transfer Tulumbası',
           'discharge_head_loss': 'Tulumba Basma Yük Kaybı',
           'suction_npsh': 'Tulumba Emme Yük Kaybı ve ENPY',
           'fire_foam_system': _TR('fire.history.foam'),
           'fire_hazen_williams': _TR('fire.history.hw')}


@dataclass(frozen=True, slots=True)
class ReportField:
    """Unrounded frozen scalar and its human-readable presentation identity."""
    label: str
    symbol: str
    value: Scalar
    unit: str = ''


@dataclass(frozen=True, slots=True)
class ReportSource:
    """Available frozen provenance fields, with no inferred verification."""
    rows: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class EngineeringReport:
    """Complete deterministic renderer input, independent of current application state."""
    snapshot_id: str
    module: str
    stage: str
    created_at: datetime
    identification: tuple[ReportField, ...]
    inputs: tuple[ReportField, ...]
    selections: tuple[ReportField, ...]
    formulas: tuple[FormulaStep, ...]
    results: tuple[ReportField, ...]
    warnings: tuple[str, ...]
    sources: tuple[ReportSource, ...]
    metadata: tuple[ReportField, ...]

    def to_json(self) -> str:
        """Serialize without display rounding or mutable references."""
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=lambda value: value.isoformat() if hasattr(value, 'isoformat') else str(value), allow_nan=False)


def source_rows(source: SourceReference) -> tuple[tuple[str, str], ...]:
    """Translate source labels; keep actual stored status codes visible for audits."""
    return tuple((_TR('formula2.source.' + f.name),
                  (str(value.value) + ' · ' + _TR('formula2.' + f.name + '.' + value.value))
                  if f.name in ('source_type', 'verification_status') else str(value))
                 for f in fields(source) if (value := getattr(source, f.name)) is not None and value != '')


def adapt_snapshot(snapshot: CalculationSnapshot) -> EngineeringReport:
    """Transform frozen evidence only; this function has no service/repository dependencies."""
    steps = ordered_steps(snapshot.formula_steps)
    inputs: list[ReportField] = []
    selections: list[ReportField] = []
    warnings: list[str] = []
    sources: list[ReportSource] = []
    identification = [ReportField('Tarih / saat', '', snapshot.created_at.isoformat()),
                      ReportField('Snapshot kimliği', '', str(snapshot.snapshot_id)),
                      ReportField('Hesap türü', '', {'selection': 'Boru seçimi', 'hydraulics': 'Hidrolik', 'diameter': 'Çap', 'wall': 'Et kalınlığı'}.get(snapshot.stage, snapshot.stage.upper()))]
    if snapshot.project_id:
        identification.append(ReportField('Proje kimliği', '', str(snapshot.project_id)))
    for label, reference in zip(('Sistem', 'Devre', 'Akışkan'),
                                (snapshot.context.system, snapshot.context.circuit, snapshot.context.fluid)):
        if reference:
            identification.append(ReportField(label, '', reference.name_tr))
    for step in steps:
        for variable in step.variables + step.reference_variables:
            row = ReportField((variable.context + ' · ' if variable.context else '') + _TR(variable.terminology_key), variable.symbol, variable.value, variable.unit)
            if row not in inputs:
                inputs.append(row)
            if variable.source_selection_id:
                selections.append(ReportField('Bağlı boru seçimi', variable.symbol,
                    f'{variable.source_selection_id} · Revizyon {variable.source_revision}'))
        for value in step.used_values:
            selections.append(ReportField('Kaynak / doğrulama', value.symbol or '',
                ' · '.join(text for label, text in source_rows(value.source))))
            selections.append(ReportField(_TR(value.terminology_key) if value.terminology_key else value.symbol or 'Kullanılan değer',
                                          value.symbol or '', value.used_value, value.unit))
            if value.recommended_value is not None:
                selections.append(ReportField('Önerilen değer', value.symbol or '', value.recommended_value, value.unit))
            for label, text in (('Seçim gerekçesi', value.selection_reason), ('Override gerekçesi', value.override_reason)):
                if text:
                    selections.append(ReportField(label, value.symbol or '', text))
        if step.selection_reason:
            selections.append(ReportField('Seçim dayanağı', step.result_symbol,
                                          _TR('formula2.reason.' + step.selection_reason.value)))
        if step.check:
            warning = step.result_symbol + ': ' + _TR('formula2.check.' + step.check.status.value)
            if step.check.reason_key:
                warning += ' · ' + _TR(step.check.reason_key)
            if step.check.actual_value is not None and step.check.reference_value is not None:
                warning += f' ({format_number(step.check.actual_value)} {step.check.operator or ""} {format_number(step.check.reference_value)})'
            warnings.append(warning)
        references = list(step.sources) + [v.source for v in step.variables + step.reference_variables if v.source]
        references += [v.source for v in step.used_values]
        if step.check and step.check.source:
            references.append(step.check.source)
        for reference in references:
            source = ReportSource(source_rows(reference))
            if source not in sources:
                sources.append(source)
    # Only explicitly labelled frozen facts are exported. No generic JSON/field-name dump.
    labels = {'bend_allowance_enabled': ('Bükme durumu', ''), 'bend_radius_mm': ('Bükme yarıçapı', 'mm'),
              'nominal_diameter': ('Anma çapı', ''), 'schedule': ('Schedule', ''),
              'standard_code': ('Boru standardı', ''), 'selected_standard_code': ('Boru standardı', ''),
              'outside_diameter_mm': ('Boru dış çapı', 'mm'), 'wall_thickness_mm': ('Seçilen et kalınlığı', 'mm'),
              'mode': ('Boru girdi modu', ''), 'kept_current': ('Mevcut değerler korundu', ''),
              'source_selection_id': ('Kaynak boru seçimi UUID', ''), 'source_revision': ('Kaynak boru revizyonu', ''),
              'observed_revision': ('Gözlenen revizyon', ''), 'selection_id': ('Boru seçimi UUID', ''),
              'revision': ('Boru seçimi revizyonu', ''), 'status': ('Kayıt durumu', ''),
              'upstream_status': ('Kaynak boru uygunluk durumu', ''), 'material_id': ('Malzeme kimliği', '')}
    def visit(node: object) -> None:
        if isinstance(node, dict):
            if {'name', 'quantity', 'k_coefficient'} <= node.keys():
                selections.append(ReportField('Lokal eleman: ' + node['name'], 'K', node['k_coefficient']))
                selections.append(ReportField('Lokal eleman adedi: ' + node['name'], '', node['quantity']))
            material = node.get('used_material')
            if isinstance(material, dict):
                for key, label in (('name', 'Malzeme'), ('standard', 'Malzeme standardı'), ('source', 'Malzeme kaynağı')):
                    if material.get(key):
                        selections.append(ReportField(label, '', str(material[key])))
            if 'source_type' in node:
                try:
                    source = ReportSource(source_rows(decode(SourceReference, node)))
                    if source not in sources:
                        sources.append(source)
                except (ValueError, TypeError, KeyError):
                    pass
            if 'code' in node and 'field_key' in node and 'params' in node:
                warnings.append(render_validation_issue(ValidationIssue(**node), Translator('tr')))
            if 'message_key' in node:
                key = node['message_key']
                try:
                    text = _TR(key, **node.get('context', {}))
                except (KeyError, ValueError):
                    text = str(key)
                warnings.append(text)
            for key, value in node.items():
                if key in labels and isinstance(value, (str, int, float, bool)):
                    label, unit = labels[key]
                    if key == 'bend_allowance_enabled':
                        value = 'Bükme var' if value else 'Bükme yok'
                    elif key == 'mode':
                        if value not in ('MANUAL', 'LINKED'):
                            label = 'Hesap / kapasite modu'
                        value = {'MANUAL': 'Manuel', 'LINKED': 'Bağlı'}.get(value, value)
                    row = ReportField(label, '', value, unit)
                    if row not in selections:
                        selections.append(row)
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)
    is_fire = snapshot.module_code.value in ('fire_foam_system','fire_hazen_williams')
    if not is_fire:
        visit(snapshot.evidence['facts'])
    visit(snapshot.evidence.get('findings', []))
    for source in snapshot.evidence.get('finding_sources', []):
        sources.append(ReportSource(tuple((label, str(source[key])) for key, label in
            (('title', 'Doküman'), ('note', 'Notlar')) if source.get(key))))
    results = tuple(ReportField(_TR(step.title_key), step.result_symbol, step.result_value, step.result_unit) for step in steps)
    report = EngineeringReport(str(snapshot.snapshot_id), MODULES[snapshot.module_code.value], snapshot.stage,
        snapshot.created_at, tuple(identification), tuple(inputs), tuple(dict.fromkeys(selections)), steps, results,
        tuple(dict.fromkeys(warnings)), tuple(sources),
        (ReportField('Snapshot şeması', '', snapshot.schema_version),
         ReportField('Hesap modeli', '', snapshot.model_version),
         ReportField('Bağlam revizyonu', '', snapshot.context.revision)))
    if is_fire:
        from reporting.fire import enrich_fire_report
        return enrich_fire_report(snapshot, report)
    return report


def format_number(value: Scalar) -> str:
    """Round only visible copies, preserving small engineering quantities."""
    if isinstance(value, bool):
        return 'Evet' if value else 'Hayır'
    if isinstance(value, (int, float)):
        return (f'{value:.4g}' if 0 < abs(value) < 1 else f'{value:.2f}').replace('.', ',')
    return str(value)
