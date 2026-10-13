"""Reusable, result-preserving presentation for engineering findings."""

from __future__ import annotations

from collections.abc import Callable, Iterable
import tkinter as tk
from tkinter import ttk

from core.engineering_context import fluid_label, line_role_label
from engineering.warning_rules import EngineeringFinding, SOURCE_REGISTRY, WarningSeverity
from ui.formatting import format_user_number
from ui.widgets.engineering_components import StatusBadge


_SEVERITY_ORDER = {
    WarningSeverity.ERROR: 0,
    WarningSeverity.CRITICAL_WARNING: 1,
    WarningSeverity.ENGINEERING_WARNING: 2,
}


def normalized_findings(findings: Iterable[EngineeringFinding]) -> tuple[EngineeringFinding, ...]:
    """Deduplicate stable finding codes and keep presentation deterministic."""
    unique: dict[str, EngineeringFinding] = {}
    for finding in findings:
        unique.setdefault(finding.code, finding)
    return tuple(sorted(unique.values(), key=lambda item: (_SEVERITY_ORDER[item.severity], item.code)))


class EngineeringWarningPanel(ttk.Frame):
    """Show source-backed guidance without turning valid results into errors."""

    def __init__(self, parent: tk.Misc, translate: Callable[[str], str]) -> None:
        super().__init__(parent, style="EngineeringWarningPanel.TFrame", padding=(10, 8))
        self.columnconfigure(0, weight=1)
        self._translate = translate
        self._findings: tuple[EngineeringFinding, ...] = ()

    @property
    def findings(self) -> tuple[EngineeringFinding, ...]:
        return self._findings

    def set_findings(self, findings: Iterable[EngineeringFinding]) -> None:
        self._findings = normalized_findings(findings)
        for child in self.winfo_children():
            child.destroy()
        if not self._findings:
            self.grid_remove()
            return
        for row, finding in enumerate(self._findings):
            self._render_finding(row, finding)
        self.grid()

    def refresh_texts(self) -> None:
        self.set_findings(self._findings)

    def _render_finding(self, row: int, finding: EngineeringFinding) -> None:
        critical = finding.severity is WarningSeverity.CRITICAL_WARNING
        error = finding.severity is WarningSeverity.ERROR
        title_key = "warning.title.critical" if critical else "warning.title.engineering"
        title_style = "EngineeringCriticalWarningTitle.TLabel" if critical else "EngineeringWarningTitle.TLabel"
        body_style = "EngineeringCriticalWarning.TLabel" if critical else "EngineeringWarning.TLabel"
        icon_state = "error" if error else "critical" if critical else "warning"
        StatusBadge(
            self,
            text=self._translate(title_key),
            state=icon_state,
            # A 34 px canvas renders a roughly 30 px status silhouette once
            # the status-only transparent safety border is applied.
            icon_size=34,
            style=title_style,
        ).grid(
            row=row * 2, column=0, sticky="w", pady=((0 if row == 0 else 10), 0)
        )
        ttk.Label(self, text=self._message(finding), style=body_style, wraplength=860).grid(
            # Reserve a stable 40 px leading lane so the explanation aligns
            # below the heading rather than beneath the status symbol.
            row=row * 2 + 1, column=0, sticky="ew", padx=(40, 0), pady=(4, 0)
        )

    def _message(self, finding: EngineeringFinding) -> str:
        if finding.code.startswith("velocity."):
            actual = finding.actual_value
            relation = "warning.relation.below" if finding.lower_bound is not None and actual is not None and actual < finding.lower_bound else "warning.relation.above"
            details = [
                self._translate("warning.velocity.message", fluid=fluid_label(finding.context.get("system")), role=line_role_label(finding.context.get("line_role")), relation=self._translate(relation)),
                f"{self._translate('warning.calculated')}: {format_user_number(actual)} {finding.unit}",
                f"{self._translate('warning.reference_range')}: {format_user_number(finding.lower_bound)}–{format_user_number(finding.upper_bound)} {finding.unit}",
            ]
        elif finding.code == "npsh.available_not_above_required":
            details = [
                self._translate("warning.npsh.message"),
                f"{self._translate('warning.available_enpy')}: {format_user_number(finding.actual_value)} {finding.unit}",
                f"{self._translate('warning.required_npsh')}: {format_user_number(finding.lower_bound)} {finding.unit}",
            ]
        else:
            details = [self._translate(finding.message_key)]
        if finding.source_id:
            source = SOURCE_REGISTRY.get(finding.source_id)
            if source:
                details.append(f"{self._translate('warning.source')}: {source.title}")
        return "\n".join(details)
