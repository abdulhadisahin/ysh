"""Inline expandable engineering formula-reference presentation widgets."""

from __future__ import annotations

import base64
import io
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from tkinter import ttk
from typing import Literal

from ui.theme import typography
from ui.theme.spacing import MD, SM


FormulaSectionRole = Literal[
    "formula",
    "variables",
    "substitution",
    "result",
    "note",
]
FormulaToggleFactory = Callable[[tk.Misc, str, Callable[[], None]], ttk.Button]


FORMULA_STAGE_KEYS = {
    "1. PIPE DIAMETER": "formula.stage.pipe_diameter",
    "2. ALLOWABLE STRESS": "formula.stage.allowable_stress",
    "3. BASE WALL THICKNESS": "formula.stage.base_wall_thickness",
    "4. BEND ALLOWANCE": "formula.stage.bend_allowance",
    "5. REQUIRED WALL THICKNESS": "formula.stage.required_wall_thickness",
    "PIPE SIZE RECOMMENDATION": "formula.stage.pipe_size_recommendation",
    "1. LINEAR REGRESSION MODEL": "formula.stage.regression_model",
    "2. PREDICTED PUMP CAPACITY": "formula.stage.predicted_pump_capacity",
    "3. EMPTYING TIME": "formula.stage.emptying_time",
    "1. FLOW AND FRICTION": "formula.stage.flow_and_friction",
    "2. HYDRAULIC LOSSES": "formula.stage.hydraulic_losses",
    "3. SYSTEM MANOMETRIC HEAD": "formula.stage.system_manometric_head",
    "1. SUCTION HYDRAULICS": "formula.stage.suction_hydraulics",
    "2. ENPY / NPSH AVAILABLE": "formula.stage.available_npsh",
}


_MATHTEXT_LINES = {
    "Qm³/s = Qm³/h / 3600": r"Q_{\mathrm{m^3/s}} = \frac{Q_{\mathrm{m^3/h}}}{3600}",
    "D = √((4 × Qm³/s) / (π × V))": r"D = \sqrt{\frac{4Q_{\mathrm{m^3/s}}}{\pi V}}",
    "σallow = Rp0.2 / B": r"\sigma_{\mathrm{allow}} = \frac{R_{p0.2}}{B}",
    "s0 = (da × pc) / ((20 × σallow × w) + pc)": r"s_0 = \frac{d_a p_c}{(20\sigma_{\mathrm{allow}}w)+p_c}",
    "b = 0.4 × (da / R) × s0": r"b = 0.4\left(\frac{d_a}{R}\right)s_0",
    "s = s0 + c + b": r"s = s_0 + c + b",
    "Qpump = m × Vfuel + b": r"Q_{\mathrm{pump}} = mV_{\mathrm{fuel}} + b",
    "m = Σ((Vfuel − V̄fuel)(Qpump − Q̄pump)) / Σ(Vfuel − V̄fuel)²": r"m = \frac{\sum((V_{\mathrm{fuel}}-\bar{V}_{\mathrm{fuel}})(Q_{\mathrm{pump}}-\bar{Q}_{\mathrm{pump}}))}{\sum(V_{\mathrm{fuel}}-\bar{V}_{\mathrm{fuel}})^2}",
    "b = Q̄pump − m × V̄fuel": r"b = \bar{Q}_{\mathrm{pump}} - m\bar{V}_{\mathrm{fuel}}",
    "t = Vfuel / Qpump": r"t = \frac{V_{\mathrm{fuel}}}{Q_{\mathrm{pump}}}",
    "v = 4Q / (πD²)": r"v = \frac{4Q}{\pi D^2}",
    "Re = vD / ν": r"Re = \frac{vD}{\nu}",
    "ε = k / D": r"\varepsilon = \frac{k}{D}",
    "Ktotal = Σ(quantity × K)": r"K_{\mathrm{total}} = \sum(\mathrm{quantity}\cdot K)",
    "h_local = 6400 × Ktotal × Q² / D⁴": r"h_{\mathrm{local}} = \frac{6400K_{\mathrm{total}}Q^2}{D^4}",
    "h_pipe = 6.4 × 10⁶ × f × L × Q² / D⁵": r"h_{\mathrm{pipe}} = \frac{6.4\times10^6fLQ^2}{D^5}",
    "h_total = h_pipe + h_local": r"h_{\mathrm{total}} = h_{\mathrm{pipe}} + h_{\mathrm{local}}",
    "H_system = Hgeo + h_total": r"H_{\mathrm{system}} = H_{\mathrm{geo}} + h_{\mathrm{total}}",
    "he = h_pipe + h_local": r"h_e = h_{\mathrm{pipe}} + h_{\mathrm{local}}",
    "ENPYm = PE/(ρg) − Pb/(ρg) − HEgeo − he": r"ENPY_m = \frac{P_E}{\rho g} - \frac{P_b}{\rho g} - H_{E\mathrm{geo}} - h_e",
}

_LONG_EQUATION_CHARACTER_THRESHOLD = 90


@dataclass(frozen=True, slots=True)
class FormulaSection:
    """One page-owned item in a structured engineering formula stage."""

    heading: str
    text: str
    stage: str = "ENGINEERING REFERENCE"
    role: FormulaSectionRole = "formula"


@dataclass(frozen=True, slots=True)
class FormulaBlock:
    """A logical engineering stage containing semantic formula sections."""

    title: str
    sections: tuple[FormulaSection, ...]


class FormulaReferencePanel(ttk.Frame):
    """Render always-available formula reference blocks inline on a page."""

    def __init__(
        self,
        parent: tk.Misc,
        section_provider: Callable[[], list[FormulaSection]],
        translate: Callable[[str], str] | None = None,
        toggle_button_factory: FormulaToggleFactory | None = None,
    ) -> None:
        """Create a collapsed panel backed by a page-owned section provider."""
        super().__init__(parent)
        self.columnconfigure(0, weight=1)
        self._section_provider = section_provider
        self._translate = translate or (lambda key: key)
        self._expanded = False
        button_factory = toggle_button_factory or self._create_default_toggle
        self._toggle = button_factory(
            self,
            self._translate("common.show_formula"),
            self.toggle,
        )
        self._configure_toggle_stable_texts()
        self._toggle.grid(row=0, column=0, sticky="w")
        self._content = ttk.LabelFrame(
            self,
            text=self._translate("formula.reference"),
            style="FormulaCard.TLabelframe",
            padding=MD,
        )
        self._content.columnconfigure(0, weight=1)
        self._formula_strips: list[tuple[ttk.Frame, tuple[ttk.Frame, ...]]] = []
        self._equation_images: list[tk.PhotoImage] = []

    @staticmethod
    def _create_default_toggle(
        parent: tk.Misc,
        text: str,
        command: Callable[[], None],
    ) -> ttk.Button:
        """Create the unchanged default toggle for non-Pipe formula panels."""
        return ttk.Button(
            parent,
            text=text,
            command=command,
            style="Secondary.TButton",
        )

    @property
    def expanded(self) -> bool:
        """Return whether the inline reference is currently visible."""
        return self._expanded

    def toggle(self) -> None:
        """Expand or collapse the formula reference without a separate dialog."""
        self._expanded = not self._expanded
        if self._expanded:
            self.refresh()
            self._content.grid(row=1, column=0, sticky="nsew", pady=(SM, 0))
            self._toggle.configure(text=self._translate("common.hide_formula"))
        else:
            self._content.grid_remove()
            self._toggle.configure(text=self._translate("common.show_formula"))

    def _configure_toggle_stable_texts(self) -> None:
        """Reserve stable width for the current language's Show and Hide labels."""
        set_stable_texts = getattr(self._toggle, "set_stable_texts", None)
        if callable(set_stable_texts):
            set_stable_texts(
                (
                    self._translate("common.show_formula"),
                    self._translate("common.hide_formula"),
                )
            )

    def refresh_texts(self) -> None:
        """Refresh panel chrome while retaining its expanded/collapsed state."""
        self._content.configure(text=self._translate("formula.reference"))
        self._toggle.configure(
            text=self._translate(
                "common.hide_formula" if self._expanded else "common.show_formula"
            )
        )
        self._configure_toggle_stable_texts()
        if self._expanded:
            self.refresh()

    def refresh(self) -> None:
        """Render current authoritative static and dynamic page sections."""
        for child in self._content.winfo_children():
            child.destroy()
        self._formula_strips.clear()
        self._equation_images.clear()
        for row, block in enumerate(self._blocks()):
            self._render_block(block, row)

    def _blocks(self) -> tuple[FormulaBlock, ...]:
        """Group consecutive page-owned sections into engineering stages."""
        grouped: dict[str, list[FormulaSection]] = {}
        for section in self._section_provider():
            grouped.setdefault(section.stage, []).append(section)
        return tuple(
            FormulaBlock(title, tuple(sections))
            for title, sections in grouped.items()
        )

    def _render_block(self, formula_block: FormulaBlock, row: int) -> None:
        """Render one readable stage without recalculating any engineering data."""
        block = ttk.LabelFrame(
            self._content,
            text=self._translate(
                FORMULA_STAGE_KEYS.get(formula_block.title, formula_block.title)
            ),
            style="FormulaStage.TLabelframe",
            padding=MD,
        )
        block.grid(row=row, column=0, sticky="ew", pady=(0, MD))
        block.columnconfigure(0, weight=1)
        strip = ttk.Frame(block, style="FormulaStrip.TFrame")
        strip.grid(row=0, column=0, sticky="ew")
        panels = tuple(
            self._render_section(strip, section)
            for section in formula_block.sections
        )
        self._formula_strips.append((strip, panels))
        strip.bind(
            "<Configure>",
            lambda event, current_strip=strip, current_panels=panels:
            self._reflow_strip(current_strip, current_panels, event.width),
            add="+",
        )
        self.after_idle(self._reflow_strip, strip, panels)

    def _render_section(
        self,
        parent: ttk.Frame,
        section: FormulaSection,
    ) -> ttk.Frame:
        """Render one semantic reference, substitution, result, or note surface."""
        style_root = {
            "formula": "FormulaEquation",
            "variables": "FormulaVariables",
            "substitution": "FormulaSubstitution",
            "result": "FormulaResult",
            "note": "FormulaNote",
        }[section.role]
        container = ttk.Frame(parent, style=f"{style_root}.TFrame")
        container.columnconfigure(1, weight=1)
        heading_key = {
            "FORMULA": "formula.formula",
            "VARIABLES": "formula.variables",
            "CURRENT SUBSTITUTION": "formula.current_substitution",
            "RESULT": "formula.result",
            "NOTE": "formula.note",
            "MODEL INFORMATION": "formula.model_information",
        }.get(section.heading)
        accent = ttk.Frame(
            container,
            style=f"{style_root}Accent.TFrame",
            width=4,
        )
        accent.grid(row=0, column=0, rowspan=2, sticky="ns")
        ttk.Label(
            container,
            text=(self._translate(heading_key) if heading_key is not None else section.heading),
            style=f"{style_root}Title.TLabel",
            wraplength=260,
        ).grid(row=0, column=1, sticky="w", padx=(SM, MD), pady=(SM, 0))
        self._render_section_content(container, section, style_root)
        return container

    def _render_section_content(
        self,
        container: ttk.Frame,
        section: FormulaSection,
        style_root: str,
    ) -> None:
        """Render MathText only for equations, retaining Tk text as the fallback."""
        if section.role == "formula" and self._render_mathtext_equations(
            container, section.text, style_root
        ):
            return
        ttk.Label(
            container,
            text=section.text,
            style=f"{style_root}Text.TLabel",
            justify="left",
            wraplength=260,
        ).grid(
            row=1,
            column=1,
            sticky="w",
            padx=(SM, MD),
            pady=(SM // 2, SM),
        )

    def _render_mathtext_equations(
        self,
        container: ttk.Frame,
        equation_text: str,
        style_root: str,
    ) -> bool:
        """Render known display equations at Tk DPI, falling back line-by-line safely."""
        lines = equation_text.splitlines()
        if not any(line in _MATHTEXT_LINES for line in lines):
            return False
        rendered = False
        for row, line in enumerate(lines, start=1):
            mathtext = _MATHTEXT_LINES.get(line)
            image = self._render_mathtext_image(container, mathtext) if mathtext else None
            if image is not None:
                self._equation_images.append(image)
                ttk.Label(
                    container,
                    image=image,
                    style=f"{style_root}Text.TLabel",
                ).grid(
                    row=row,
                    column=1,
                    sticky="w",
                    padx=(SM, MD),
                    pady=(SM if row == 1 else SM // 2, SM // 2),
                )
                rendered = True
            else:
                ttk.Label(
                    container,
                    text=line,
                    style=f"{style_root}Text.TLabel",
                    justify="left",
                    wraplength=260,
                ).grid(
                    row=row,
                    column=1,
                    sticky="w",
                    padx=(SM, MD),
                    pady=(SM if row == 1 else SM // 2, SM // 2),
                )
        return rendered

    @staticmethod
    def _mathtext_font_size(mathtext: str) -> int:
        """Select a readable display size without allowing long equations to clip."""
        if len(mathtext) > _LONG_EQUATION_CHARACTER_THRESHOLD:
            return max(
                typography.MATHTEXT_MINIMUM_SIZE,
                typography.MATHTEXT_LONG_EQUATION_SIZE,
            )
        return typography.MATHTEXT_EQUATION_DISPLAY_SIZE

    @classmethod
    def _render_mathtext_image(
        cls,
        parent: tk.Misc,
        mathtext: str | None,
    ) -> tk.PhotoImage | None:
        """Render a local Matplotlib MathText equation without requiring LaTeX."""
        if mathtext is None:
            return None
        try:
            from matplotlib.font_manager import FontProperties
            from matplotlib.mathtext import math_to_image

            buffer = io.BytesIO()
            dpi = max(96, round(parent.winfo_fpixels("1i")))
            math_to_image(
                f"${mathtext}$",
                buffer,
                prop=FontProperties(size=cls._mathtext_font_size(mathtext)),
                dpi=dpi,
                format="png",
                color="#102A43",
            )
            return tk.PhotoImage(
                master=parent,
                data=base64.b64encode(buffer.getvalue()).decode("ascii"),
            )
        except Exception:
            return None

    def _reflow_strip(
        self,
        strip: ttk.Frame,
        panels: tuple[ttk.Frame, ...],
        available_width: int | None = None,
    ) -> None:
        """Lay out a formula stage from its requested geometry without scrolling."""
        if not panels:
            return

        width = available_width if available_width is not None else strip.winfo_width()
        if width <= 1:
            return

        requested_width = sum(panel.winfo_reqwidth() for panel in panels)
        requested_width += SM * (len(panels) - 1)
        largest_panel = max(panel.winfo_reqwidth() for panel in panels)

        if width >= requested_width:
            columns = len(panels)
        elif len(panels) > 1 and width >= (largest_panel * 2) + SM:
            columns = 2
        else:
            columns = 1

        for column in range(len(panels)):
            strip.columnconfigure(column, weight=1 if column < columns else 0)

        for index, panel in enumerate(panels):
            row, column = divmod(index, columns)
            panel.grid(
                row=row,
                column=column,
                sticky="nsew",
                padx=(0 if column == 0 else SM, 0),
                pady=(0 if row == 0 else SM, 0),
            )
