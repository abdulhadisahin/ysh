"""Reusable modern engineering surfaces for the YSH presentation layer."""

from __future__ import annotations

import tkinter as tk
from typing import Literal
from tkinter import ttk


class SurfaceCard(ttk.Frame):
    """Provide a frame-based card with a separate semantic title surface.

    Unlike a ``LabelFrame``, this component keeps its title and content in a
    predictable grid hierarchy.  It is intended for shell, sidebar, and dialog
    compositions where a bordered form-group appearance is undesirable.
    """

    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        style: str = "SurfaceCard.TFrame",
        title_style: str = "SurfaceCardTitle.TLabel",
        content_style: str = "SurfaceCardContent.TFrame",
        accent_style: str | None = None,
        padding: int | tuple[int, int] = 12,
        **kwargs: object,
    ) -> None:
        """Create a card with a compact title and an inner content frame."""
        super().__init__(parent, style=style, padding=padding, **kwargs)
        content_column = 1 if accent_style is not None else 0
        self.columnconfigure(content_column, weight=1)
        if accent_style is not None:
            ttk.Frame(self, style=accent_style, width=4).grid(
                row=0, column=0, rowspan=2, sticky="ns", padx=(0, 10)
            )
        self._title = ttk.Label(self, text=title, style=title_style)
        self._title.grid(row=0, column=content_column, sticky="w", pady=(0, 8))
        self.content = ttk.Frame(self, style=content_style)
        self.content.grid(row=1, column=content_column, sticky="nsew")
        self.content.columnconfigure(0, weight=1)

    def set_title(self, title: str) -> None:
        """Refresh the displayed title without rebuilding the card content."""
        self._title.configure(text=title)


class InformationCard(ttk.LabelFrame):
    """Provide a subtle reusable surface for compact non-editable information."""

    style_name = "InformationCard.TLabelframe"

    def __init__(self, parent: tk.Misc, title: str, **kwargs: object) -> None:
        """Create a padded semantic information card with a section heading."""
        super().__init__(parent, text=title, style=self.style_name, padding=12, **kwargs)


class InputCard(InformationCard):
    """Reserve a semantic surface type for future input-page migrations."""

    style_name = "InputCard.TLabelframe"


class CalculationCard(InformationCard):
    """Reserve a semantic surface type for future calculation-page migrations."""

    style_name = "CalculationCard.TLabelframe"


class ResultCard(InformationCard):
    """Reserve a semantic surface type for future result-page migrations."""

    style_name = "ResultCard.TLabelframe"


class FormulaCard(InformationCard):
    """Reserve a semantic surface type for future formula-page migrations."""

    style_name = "FormulaCard.TLabelframe"


class WarningCard(InformationCard):
    """Provide a reusable warning surface without changing alert behavior."""

    style_name = "WarningCard.TLabelframe"


class ErrorCard(InformationCard):
    """Provide a reusable error surface without changing alert behavior."""

    style_name = "ErrorCard.TLabelframe"


class CriticalCard(InformationCard):
    """Provide a reusable critical-engineering alert surface."""

    style_name = "CriticalCard.TLabelframe"


class SectionHeader(ttk.Frame):
    """Render a compact page title and optional engineering description."""

    def __init__(self, parent: tk.Misc, title: str, description: str) -> None:
        """Create a title hierarchy without consuming excessive page height."""
        super().__init__(parent, style="PageHeader.TFrame")
        self._title = ttk.Label(self, text=title, style="PageTitle.TLabel")
        self._title.grid(row=0, column=0, sticky="w")
        self._description = ttk.Label(self, text=description, style="PageDescription.TLabel")
        self._description.grid(
            row=1, column=0, sticky="w", pady=(2, 0)
        )

    def set_content(self, title: str, description: str) -> None:
        """Update translated heading content without recreating the page layout."""
        self._title.configure(text=title)
        self._description.configure(text=description)


class ResultMetric(ttk.Frame):
    """Display one emphasized engineering output backed by page-owned variables."""

    def __init__(
        self,
        parent: tk.Misc,
        label: str,
        value: tk.StringVar,
        unit: str = "",
        state: Literal["normal", "warning", "error", "critical"] = "normal",
        normal_style_prefix: str = "ResultMetric",
    ) -> None:
        """Create a semantic result metric with a restrained accent rule."""
        self._unit = unit
        self._value_variable = value
        self._state = state
        self._normal_style_prefix = normal_style_prefix
        super().__init__(parent, style=f"{normal_style_prefix}.TFrame", padding=(10, 7))
        self._accent = ttk.Frame(
            self,
            style=f"{normal_style_prefix}Accent.TFrame",
            width=4,
        )
        self._accent.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(0, 8))
        self._label = ttk.Label(
            self,
            text=label,
            style=f"{normal_style_prefix}Label.TLabel",
        )
        self._label.grid(row=0, column=1, sticky="w")
        self._value = ttk.Label(
            self,
            textvariable=value,
            style=f"{normal_style_prefix}Value.TLabel",
        )
        self._value.grid(row=1, column=1, sticky="w", pady=(2, 0))
        self._unit_label = ttk.Label(
            self,
            text=unit,
            style=f"{normal_style_prefix}Label.TLabel",
        )
        self._unit_label.grid(row=1, column=2, sticky="sw", padx=(4, 0))
        self._value_variable.trace_add("write", self._refresh_value_style)
        self.set_state(state)

    def set_label(self, label: str) -> None:
        """Update the localized metric label without changing its value source."""
        self._label.configure(text=label)

    def set_state(self, state: Literal["normal", "warning", "error", "critical"]) -> None:
        """Apply a severity presentation state without changing the value."""
        self._state = state
        self._refresh_value_style()

    def _refresh_value_style(self, *_args: object) -> None:
        """Keep unavailable placeholders quiet without weakening semantic severity."""
        style_prefix = {
            "normal": self._normal_style_prefix,
            "warning": "WarningResultMetric",
            "error": "ErrorResultMetric",
            "critical": "CriticalResultMetric",
        }[self._state]
        if self._state == "normal" and not self._value_variable.get().strip(" —"):
            style_prefix = "UnavailableResultMetric"
        self.configure(style=f"{style_prefix}.TFrame")
        self._accent.configure(style=f"{style_prefix}Accent.TFrame")
        self._label.configure(style=f"{style_prefix}Label.TLabel")
        self._value.configure(style=f"{style_prefix}Value.TLabel")
        self._unit_label.configure(style=f"{style_prefix}Label.TLabel")
