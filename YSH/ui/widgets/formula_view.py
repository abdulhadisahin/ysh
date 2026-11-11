"""On-demand engineering explanations with a retained inline history view."""

from __future__ import annotations

import base64
import io
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from tkinter import ttk
from typing import Literal

from ui.assets import formula_asset_path, status_icon_fit_mode, status_icon_path
from ui.widgets.engineering_components import EmptyState
from ui.theme import typography
from ui.theme.spacing import MD, SM
from ui.widgets.asset_loader import AssetImageLoader, LoadedImage
from ui.formula_asset_policy import QUARANTINED_ASSETS
from ui.widgets.formula_image import FormulaImage


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


from reporting.equations import MATHTEXT_LINES as _MATHTEXT_LINES

_LONG_EQUATION_CHARACTER_THRESHOLD = 90
_FORMULA_MARKER_RENDER_SIZE = 32
_FORMULA_MARKER_LANE_SIZE = 36


@dataclass(frozen=True, slots=True)
class FormulaSection:
    """One page-owned item in a structured engineering formula stage."""

    heading: str
    text: str
    stage: str = "ENGINEERING REFERENCE"
    role: FormulaSectionRole = "formula"
    asset_names: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FormulaBlock:
    """A logical engineering stage containing semantic formula sections."""

    title: str
    sections: tuple[FormulaSection, ...]


def active_step_id(steps: tuple, previous: str | None) -> str | None:
    """Keep display selection only while its frozen step is still present."""
    ids = tuple(step.step_id for step in steps)
    return previous if previous in ids else (ids[0] if ids else None)


class FormulaReferencePanel(ttk.Frame):
    """Present FormulaStep explanations on demand without recalculating."""

    def __init__(
        self,
        parent: tk.Misc,
        section_provider: Callable[[], list[FormulaSection]],
        translate: Callable[[str], str] | None = None,
        toggle_button_factory: FormulaToggleFactory | None = None,
        content_available: Callable[[], bool] | None = None,
        step_provider: Callable[[], tuple] | None = None,
        *,
        separate_window: bool = False,
        module_key: str | None = None,
        historical: bool = False,
    ) -> None:
        """Create a collapsed panel backed by a page-owned section provider."""
        super().__init__(parent)
        self.columnconfigure(0, weight=1)
        self._section_provider = section_provider
        self._translate = translate or (lambda key: key)
        self._content_available = content_available
        self._step_provider = step_provider
        self._module_key = module_key
        self._historical = historical
        self._active_step_id = None
        self._steps = ()
        self._rendered_signature = None
        from ui.theme.formula_visuals import identity
        self._visual_prefix = identity(module_key)[0]
        self._expanded = False
        self._separate_window = separate_window
        self._dialog: tk.Toplevel | None = None
        button_factory = toggle_button_factory or self._create_default_toggle
        self._toggle = button_factory(
            self,
            self._translate("common.show_formula"),
            self.toggle,
        )
        self._configure_toggle_stable_texts()
        self._toggle.grid(row=0, column=0, sticky="w")
        self._content: ttk.LabelFrame | None = None
        if not separate_window:
            self._content = self._create_content(self)
        self._formula_strips: list[tuple[ttk.Frame, tuple[ttk.Frame, ...]]] = []
        self._equation_images: list[tk.PhotoImage] = []
        self._formula_asset_images: list[LoadedImage] = []
        self._section_marker_images: list[LoadedImage] = []

    def configure_post_tools(self, *, on_history, on_pdf, pdf_available,
                             history_available=None, formula_available=None):
        """Opt current calculation pages into one row; retain existing callbacks."""
        from ui.widgets.calculation_presentation import calculation_button
        from ui.widgets.tooltip import Tooltip
        self._post_pdf_available=pdf_available
        self._post_history_available=history_available or (lambda:callable(on_history))
        self._post_formula_available=formula_available
        if not hasattr(self,'_history_button'):
            self._history_button=calculation_button(self,'',lambda:None,
                style='PostTools.TButton',icon_name='history')
            self._post_history_hint=Tooltip(self._history_button,'',wraplength=280)
            self._pdf_button=calculation_button(self,'',lambda:None,
                style='PostTools.TButton',icon_name='pdf')
        self._history_button.configure(command=lambda:on_history() if callable(on_history) and self._post_history_available() else None)
        self._pdf_button.configure(command=lambda:on_pdf() if self._post_pdf_available() else None)
        for column,button in enumerate((self._toggle,self._history_button,self._pdf_button)):
            self.columnconfigure(column,weight=0)
            button.grid(row=0,column=column,sticky='w',padx=(0,8))
        self.columnconfigure(3,weight=1)
        self.refresh_post_tools()

    def refresh_post_tools(self):
        """Presentation eligibility delegates to the page's existing predicates."""
        if not hasattr(self,'_post_pdf_available'):return
        available=(self._post_formula_available() if self._post_formula_available is not None else
                   self._content_available() if self._content_available is not None else
                   bool(self._step_provider and self._step_provider()))
        self._toggle.configure(state='normal' if available else 'disabled')
        self._history_button.configure(text=self._translate('post.history'),
            state='normal' if self._post_history_available() else 'disabled')
        self._post_history_hint.set_text(self._translate('post.history.help'))
        self._pdf_button.configure(text=self._translate('action.pdf_current_result'),
            state='normal' if self._post_pdf_available() else 'disabled')

    def _create_content(self, parent: tk.Misc) -> ttk.LabelFrame:
        content = ttk.LabelFrame(
            parent, text="" if self._step_provider else self._translate("formula.view_title" if self._separate_window else "formula.reference"),
            style="FVContainer.TLabelframe" if self._step_provider else "FormulaCard.TLabelframe", padding=MD,
        )
        content.columnconfigure(0, weight=1)
        return content

    def _close_dialog(self) -> None:
        self._expanded = False
        if self._dialog is not None:
            self._dialog.destroy()
        self._dialog = None
        self._content = None
        self._rendered_signature = None
        self._steps = ()
        self._disclosures = []
        self._step_regions = {}
        self._formula_strips.clear()
        self._equation_images.clear()
        self._formula_asset_images.clear()
        self._section_marker_images.clear()
        self._toggle.configure(text=self._translate("common.show_formula"))

    def _toggle_dialog(self) -> None:
        from ui.widgets.scrollable_frame import ScrollableFrame

        if self._expanded:
            self._close_dialog()
            return
        self._dialog = tk.Toplevel(self)
        self._dialog.title(self._translate("formula.view_title" if self._separate_window else "formula.reference"))
        self._dialog.transient(self.winfo_toplevel())
        self._dialog.geometry("1100x750")
        self._dialog.minsize(700, 450)
        self._dialog.protocol("WM_DELETE_WINDOW", self._close_dialog)
        host = ScrollableFrame(self._dialog)
        self._scroll_host = host
        host.pack(fill="both", expand=True)
        host.set_wheel_active(True)
        self._content = self._create_content(host.content)
        self._content.pack(fill="x", expand=True)
        self._expanded = True
        self.refresh()
        self._toggle.configure(text=self._translate("common.hide_formula"))

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
        """Return whether the explanatory view is currently open."""
        return self._expanded

    def toggle(self) -> None:
        """Open the requested presentation while retaining the history inline default."""
        if self._separate_window:
            self._toggle_dialog()
            return
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
        self.refresh_post_tools()
        if self._content is not None:
            self._content.configure(text="" if self._step_provider else self._translate("formula.view_title" if self._separate_window else "formula.reference"))
        if self._dialog is not None:
            self._dialog.title(self._translate("formula.view_title" if self._separate_window else "formula.reference"))
        self._toggle.configure(
            text=self._translate(
                "common.hide_formula" if self._expanded else "common.show_formula"
            )
        )
        self._configure_toggle_stable_texts()
        if self._expanded:
            self._rendered_signature = None
            self.refresh()

    def refresh(self) -> None:
        """Render current authoritative static and dynamic page sections."""
        if self._content is None:
            return
        available = self._content_available is None or self._content_available()
        provider = getattr(self, "_step_provider", None)
        steps = provider() if available and provider is not None else ()
        if steps:
            from engineering.formula.models import ordered_steps
            steps = ordered_steps(steps)
            selected_id = active_step_id(steps, self._active_step_id)
            if getattr(self, '_rendered_signature', None) == (steps, selected_id):
                return  # Preserve disclosure/focus state on unrelated page reflows.
        self._rendered_signature = None
        self._steps = ()
        self._disclosures = []
        self._step_regions = {}
        for child in self._content.winfo_children():
            child.destroy()
        self._formula_strips.clear()
        self._equation_images.clear()
        self._formula_asset_images.clear()
        self._section_marker_images.clear()
        if not available:
            EmptyState(
                self._content, "formula", "Formül referansı henüz hazır değil",
                "Önce hesaplama yapın. Formül, değişkenler ve yerine koyma adımları burada gösterilecektir.",
                image_size=190,
            ).grid(row=0, column=0, sticky="ew", pady=SM)
            return
        if steps:
            from ui.widgets.formula_steps import render_step
            self._steps = steps
            self._active_step_id = active_step_id(self._steps, self._active_step_id)
            self._render_step_header()
            selected = next(step for step in self._steps if step.step_id == self._active_step_id)
            render_step(self, selected, 1)
            self._rendered_signature = (steps, self._active_step_id)
            return
        for row, block in enumerate(self._blocks()):
            self._render_block(block, row)

    def _render_step_header(self) -> None:
        """Compact identity and selection chrome; only stored display steps are read."""
        from ui.theme.formula_visuals import identity
        prefix, _, _, _, module_label = identity(self._module_key)
        header = ttk.Frame(self._content, style=prefix+'Header.TFrame')
        header.grid(row=0, column=0, sticky='ew', pady=(0, SM))
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text='ƒx', style=prefix+'Title.TLabel').grid(row=0, column=0, rowspan=2, padx=(0, MD))
        ttk.Label(header, text=self._translate('formula.view_title'), style=prefix+'Title.TLabel').grid(row=0,column=1,sticky='w')
        ttk.Label(header, text=self._translate(module_label), style=prefix+'Module.TLabel').grid(row=1,column=1,sticky='w')
        if self._historical:
            ttk.Label(header, text=self._translate('formula.visual.historical'), style='FVMuted.TLabel').grid(row=0,column=2,sticky='e')
        nav = ttk.Frame(header, style=prefix+'Header.TFrame')
        nav.grid(row=2,column=0,columnspan=3,sticky='ew',pady=(SM,0)); nav.columnconfigure(1,weight=1)
        index = next(i for i,s in enumerate(self._steps) if s.step_id == self._active_step_id)
        self._previous = ttk.Button(nav,text=self._translate('formula.visual.previous'),command=lambda:self._select_step(index-1))
        self._previous.grid(row=0,column=0,sticky='w',padx=(0,SM))
        self._previous.configure(state='disabled' if index==0 else 'normal')
        self._step_selector = ttk.Combobox(nav,state='readonly',width=26,style=prefix+'Selector.TCombobox',
            values=tuple(f'{i+1}. {self._translate(s.title_key)}' for i,s in enumerate(self._steps)))
        self._step_selector.grid(row=0,column=1,sticky='ew'); self._step_selector.current(index)
        self._step_selector.bind('<<ComboboxSelected>>',lambda event:self._select_step(self._step_selector.current()))
        self._next = ttk.Button(nav,text=self._translate('formula.visual.next'),command=lambda:self._select_step(index+1))
        self._next.grid(row=0,column=2,sticky='e',padx=(SM,0))
        self._next.configure(state='disabled' if index==len(self._steps)-1 else 'normal')

    def _select_step(self, index: int) -> None:
        """Select by position without changing any FormulaStep or evaluating equations."""
        if not 0 <= index < len(self._steps):
            return
        self._active_step_id = self._steps[index].step_id
        self.refresh()
        host = getattr(self, '_scroll_host', None)
        if host is not None:
            host.canvas.yview_moveto(0)

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
        container = ttk.Frame(
            parent,
            style=f"{style_root}.TFrame",
            padding=(MD, SM),
        )
        container.columnconfigure(3, weight=1)
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
        marker = AssetImageLoader.load(
            container,
            status_icon_path(self._marker_state(section.role)),
            _FORMULA_MARKER_RENDER_SIZE,
            fit_mode=status_icon_fit_mode(self._marker_state(section.role)),
        )
        if marker is not None:
            self._section_marker_images.append(marker)
            ttk.Label(
                container,
                image=marker.rendered,
                style=f"{style_root}Title.TLabel",
            # The marker is a semantic silhouette, not a square thumbnail.
            # Its 32 px render canvas occupies a compact 36 px title lane.
            ).grid(
                row=0,
                column=1,
                sticky="w",
                padx=(_FORMULA_MARKER_LANE_SIZE - _FORMULA_MARKER_RENDER_SIZE, 0),
                pady=(0, 0),
            )
        ttk.Label(
            container,
            text=(self._translate(heading_key) if heading_key is not None else section.heading),
            style=f"{style_root}Title.TLabel",
            wraplength=260,
        ).grid(
            row=0,
            column=2,
            columnspan=3,
            sticky="w",
            padx=(SM, 0),
            pady=(0, 0),
        )
        self._render_section_content(container, section, style_root)
        return container

    def _render_section_content(
        self,
        container: ttk.Frame,
        section: FormulaSection,
        style_root: str,
    ) -> None:
        """Render MathText only for equations, retaining Tk text as the fallback."""
        if section.role == "formula" and self._render_formula_assets(
            container, section, style_root
        ):
            return
        if section.role == "formula" and self._render_mathtext_equations(
            container, section.text, style_root
        ):
            return
        if section.role == "variables" and self._render_variable_rows(container, section):
            return
        ttk.Label(
            container,
            text=section.text,
            style=f"{style_root}Text.TLabel",
            justify="left",
            wraplength=260,
        ).grid(
            row=1,
            column=2,
            columnspan=3,
            sticky="ew",
            padx=(SM, MD),
            pady=(SM, 0),
        )

    @staticmethod
    def _variable_rows(text: str) -> tuple[tuple[str, str, str], ...] | None:
        """Parse existing display-only ``symbol | explanation | unit`` rows."""
        rows: list[tuple[str, str, str]] = []
        for line in text.splitlines():
            parts = tuple(part.strip() for part in line.split("|", maxsplit=2))
            if len(parts) != 3:
                return None
            rows.append(parts)
        return tuple(rows) or None

    def _render_variable_rows(
        self,
        container: ttk.Frame,
        section: FormulaSection,
    ) -> bool:
        """Present the page-owned variable text in aligned native columns."""
        rows = self._variable_rows(section.text)
        if rows is None:
            return False
        for row, (symbol, description, unit) in enumerate(rows, start=1):
            pady = (SM if row == 1 else SM // 2, 0)
            ttk.Label(
                container,
                text=symbol,
                style="FormulaVariablesSymbol.TLabel",
            ).grid(row=row, column=2, sticky="w", padx=(SM, SM), pady=pady)
            ttk.Label(
                container,
                text=description,
                style="FormulaVariablesText.TLabel",
                wraplength=210,
            ).grid(row=row, column=3, sticky="w", pady=pady)
            ttk.Label(
                container,
                text=unit,
                style="FormulaVariablesUnit.TLabel",
            ).grid(row=row, column=4, sticky="e", padx=(SM, MD), pady=pady)
        return True

    def _render_formula_assets(
        self,
        container: ttk.Frame,
        section: FormulaSection,
        style_root: str,
    ) -> bool:
        """Render supplied complete equation artwork, with native text fallback."""
        if not section.asset_names or any(key in QUARANTINED_ASSETS for key in section.asset_names):
            return False
        rendered = False
        for row, asset_name in enumerate(section.asset_names, start=1):
            formula_image = FormulaImage(
                container, formula_asset_path(asset_name), style=f"{style_root}Text.TLabel",
            )
            if not formula_image.available:
                formula_image.destroy()
                continue
            formula_image.grid(
                row=row, column=2, columnspan=3, sticky="n",
                padx=(SM, MD), pady=(SM if row == 1 else SM // 2, 0),
            )
            container.columnconfigure(2, weight=1)
            rendered = True
        return rendered

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
                    column=2,
                    columnspan=3,
                    sticky="n",
                    padx=(SM, MD),
                    pady=(SM if row == 1 else SM // 2, 0),
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
                    column=2,
                    columnspan=3,
                    sticky="ew",
                    padx=(SM, MD),
                    pady=(SM if row == 1 else SM // 2, 0),
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
        requested_width += MD * (len(panels) - 1)
        largest_panel = max(panel.winfo_reqwidth() for panel in panels)

        if width >= requested_width:
            columns = len(panels)
        elif len(panels) > 1 and width >= (largest_panel * 2) + MD:
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
                padx=(0 if column == 0 else MD, 0),
                pady=(0 if row == 0 else MD, 0),
            )

    @staticmethod
    def _marker_state(role: FormulaSectionRole) -> str:
        """Map reference roles to supplied standalone glyphs, never framed buttons."""
        return {
            "formula": "information",
            "variables": "ready",
            "substitution": "working",
            "result": "success",
            "note": "information",
        }[role]
