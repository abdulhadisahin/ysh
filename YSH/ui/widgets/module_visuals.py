"""Opt-in presentation of existing calculation widgets; no state or callbacks change."""
from tkinter import ttk
from ui.theme.module_visuals import MODULES
from ui.widgets.cards import InformationCard, ResultCard, ResultMetric, SectionHeader
from ui.widgets.formula_view import FormulaReferencePanel
from ui.widgets.engineering_warning_panel import EngineeringWarningPanel


def apply_module_visuals(page: ttk.Widget, module: str) -> None:
    """Style an existing page once, leaving formula windows and severity widgets intact.

    Walk only this explicitly opted-in page. Existing bindings, variables, read-only
    states, grid geometry and custom components are preserved. No global style is
    changed here and no recurring traversal/polling is installed.
    """
    prefix = MODULES[module][0]

    def visit(widget: ttk.Widget, result: bool = False) -> None:
        if isinstance(widget, (FormulaReferencePanel, EngineeringWarningPanel, ResultMetric)):
            return
        if isinstance(widget, ResultCard):
            result = True
            widget.configure(style=prefix+'ResultCard.TLabelframe')
        elif isinstance(widget, InformationCard):
            result = False
            widget.configure(style=prefix+'InputCard.TLabelframe')
        elif isinstance(widget, SectionHeader):
            widget.configure(style=prefix+'Workspace.TFrame')
            widget._title.configure(style=prefix+'PageTitle.TLabel')
            widget._description.configure(style=prefix+'PageDescription.TLabel')
            return
        elif type(widget) is ttk.Entry:
            widget.configure(style=prefix+'.TEntry')
        elif type(widget) is ttk.Combobox:
            widget.configure(style=prefix+'.TCombobox')
        elif type(widget) is ttk.Label and not widget.cget('style'):
            widget.configure(style=prefix+('Result' if result else 'Input')+'.TLabel')
        elif isinstance(widget, ttk.Frame) and not widget.cget('style'):
            widget.configure(style=prefix+('Result' if result else 'Input')+'.TFrame')
        # Source selection is a semantic card, not an automatic update mechanism.
        elif widget is getattr(page, '_pipe_source_panel', None):
            widget.configure(style=prefix+'InputCard.TLabelframe')
        for child in widget.winfo_children():
            visit(child, result)

    page.configure(style=prefix+('Page.TLabelframe' if isinstance(page, ttk.LabelFrame) else 'Workspace.TFrame'))
    for child in page.winfo_children():
        visit(child)
    source = getattr(page, '_pipe_source_panel', None)
    if source is not None:
        for child in source.winfo_children():
            if type(child) is ttk.Label and child.cget('textvariable') == str(source._status):
                child.configure(style=prefix+'Info.TLabel')
