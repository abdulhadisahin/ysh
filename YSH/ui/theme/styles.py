"""Central ttk style configuration and semantic widget-style names."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import colors, typography
from .spacing import SM


def apply_theme(root: tk.Misc) -> None:
    """Apply the YSH Phase-1 ttk visual system to a live Tk root once."""
    if not hasattr(root, "tk"):
        return
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    root.configure(background=colors.BACKGROUND)
    style.configure(".", background=colors.BACKGROUND, foreground=colors.TEXT_PRIMARY, font=typography.BODY)
    style.configure("TFrame", background=colors.BACKGROUND)
    style.configure("Main.TFrame", background=colors.BACKGROUND)
    style.configure("Header.TFrame", background=colors.NAVY)
    style.configure("Toolbar.TFrame", background=colors.NAVY)
    style.configure("HeaderBrand.TFrame", background=colors.NAVY)
    style.configure("HeaderUtility.TFrame", background=colors.NAVY)
    style.configure(
        "HeaderLogoPlate.TFrame",
        background=colors.NAVY,
        bordercolor=colors.NAVY,
        relief="flat",
        borderwidth=0,
    )
    style.configure(
        "HeaderLogoPlate.TLabel",
        background=colors.NAVY,
    )
    style.configure("Ribbon.TFrame", background=colors.NAVY)
    style.configure(
        "CommandGroup.TFrame",
        background=colors.NAVY,
        bordercolor=colors.NAVY,
        relief="flat",
        borderwidth=0,
    )
    style.configure(
        "CommandGroupCommands.TFrame",
        background=colors.NAVY,
    )
    style.configure(
        "CommandGroupTitle.TLabel",
        background=colors.NAVY,
        foreground=colors.GOLD,
        font=typography.SUBSECTION_TITLE,
    )
    style.configure("Sidebar.TFrame", background=colors.SURFACE)
    style.configure("SidebarPanel.TFrame", background=colors.SIDEBAR_SURFACE, bordercolor=colors.BORDER, relief="solid", borderwidth=1)
    style.configure("SidebarActions.TFrame", background=colors.SIDEBAR_SURFACE)
    style.configure("SidebarSearchLabel.TLabel", background=colors.SIDEBAR_SURFACE, foreground=colors.TEXT_SECONDARY, font=typography.MUTED)
    style.configure("Workspace.TFrame", background=colors.BACKGROUND)
    style.configure("TableToolbar.TFrame", background=colors.CARD_SURFACE)
    style.configure("EmptyState.TFrame", background=colors.SURFACE_ALT)
    style.configure("EmptyState.TLabel", background=colors.SURFACE_ALT, foreground=colors.TEXT_MUTED, font=typography.MUTED)
    style.configure("EmptyStateTitle.TLabel", background=colors.SURFACE_ALT, foreground=colors.NAVY, font=typography.BODY_BOLD)
    style.configure("EmptyStateHelper.TLabel", background=colors.SURFACE_ALT, foreground=colors.TEXT_SECONDARY, font=typography.MUTED)
    style.configure("Tooltip.TLabel", background=colors.DEEP_NAVY, foreground=colors.ON_ACCENT, font=typography.MUTED)
    style.configure("StatusInformation.TLabel", background=colors.INFO_SURFACE, foreground=colors.INFO, font=typography.MUTED)
    style.configure("StatusReady.TLabel", background=colors.SURFACE_ALT, foreground=colors.TEXT_SECONDARY, font=typography.MUTED)
    style.configure("StatusWarning.TLabel", background=colors.WARNING_SURFACE, foreground=colors.WARNING, font=typography.MUTED)
    style.configure("StatusCritical.TLabel", background=colors.CRITICAL_ENGINEERING_SURFACE, foreground=colors.CRITICAL_ENGINEERING, font=typography.MUTED)
    style.configure("StatusError.TLabel", background=colors.ERROR_SURFACE, foreground=colors.ERROR, font=typography.MUTED)
    style.configure("StatusSuccess.TLabel", background=colors.SUCCESS_SURFACE, foreground=colors.SUCCESS, font=typography.MUTED)
    style.configure("StatusSaved.TLabel", background=colors.SUCCESS_SURFACE, foreground=colors.SUCCESS, font=typography.MUTED)
    style.configure("StatusWorking.TLabel", background=colors.INFO_SURFACE, foreground=colors.INFO, font=typography.MUTED)
    style.configure("TLabel", background=colors.BACKGROUND, foreground=colors.TEXT_PRIMARY)
    style.configure("EngineeringWarningPanel.TFrame", background=colors.WARNING_SURFACE, bordercolor=colors.WARNING, relief="solid", borderwidth=1)
    style.configure("EngineeringWarningTitle.TLabel", background=colors.WARNING_SURFACE, foreground="#8A5A00", font=typography.BODY_BOLD)
    style.configure("EngineeringWarning.TLabel", background=colors.WARNING_SURFACE, foreground=colors.TEXT_PRIMARY, font=typography.BODY)
    style.configure("EngineeringCriticalWarningTitle.TLabel", background=colors.CRITICAL_ENGINEERING_SURFACE, foreground=colors.CRITICAL_ENGINEERING, font=typography.BODY_BOLD)
    style.configure("EngineeringCriticalWarning.TLabel", background=colors.CRITICAL_ENGINEERING_SURFACE, foreground=colors.TEXT_PRIMARY, font=typography.BODY)
    style.configure("TEntry", padding=(SM // 2, SM // 4), fieldbackground=colors.CARD_SURFACE, foreground=colors.TEXT_PRIMARY, bordercolor=colors.BORDER, insertcolor=colors.TEXT_PRIMARY)
    style.map("TEntry", bordercolor=[("focus", colors.PRIMARY), ("disabled", colors.DIVIDER)], fieldbackground=[("disabled", colors.SURFACE_ALT)])
    style.configure("TCombobox", padding=(SM // 2, SM // 4), fieldbackground=colors.CARD_SURFACE, foreground=colors.TEXT_PRIMARY, bordercolor=colors.BORDER)
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", colors.SURFACE_ALT), ("disabled", colors.SURFACE_ALT)],
        foreground=[("readonly", colors.TEXT_PRIMARY), ("disabled", colors.TEXT_MUTED)],
        bordercolor=[("focus", colors.PRIMARY), ("disabled", colors.DIVIDER)],
    )
    style.configure("HeaderTitle.TLabel", background=colors.NAVY, foreground=colors.ON_ACCENT, font=typography.APPLICATION_TITLE)
    style.configure("HeaderSubtitle.TLabel", background=colors.NAVY, foreground=colors.HEADER_MUTED_TEXT, font=typography.APPLICATION_SUBTITLE)
    style.configure("HeaderProject.TLabel", background=colors.NAVY, foreground=colors.HEADER_MUTED_TEXT, font=typography.MUTED)
    style.configure("SidebarTitle.TLabel", background=colors.SIDEBAR_SURFACE, foreground=colors.NAVY, font=typography.SECTION_TITLE)
    style.configure("TLabelFrame", background=colors.SURFACE, bordercolor=colors.BORDER, relief="solid")
    style.configure("TLabelFrame.Label", background=colors.SURFACE, foreground=colors.TEXT_SECONDARY, font=typography.SECTION_TITLE)
    style.configure("ActiveProject.TLabelframe", background=colors.SURFACE_ALT, bordercolor=colors.PRIMARY)
    style.configure("ActiveProject.TLabelframe.Label", background=colors.SURFACE_ALT, foreground=colors.PRIMARY_HOVER, font=typography.SECTION_TITLE)
    style.configure("ActiveProjectLabel.TLabel", background=colors.SURFACE_ALT, foreground=colors.TEXT_SECONDARY, font=typography.MUTED)
    style.configure("ActiveProject.TFrame", background=colors.SURFACE_ALT, bordercolor=colors.BORDER, relief="solid", borderwidth=1)
    style.configure("ActiveProjectTitle.TLabel", background=colors.SURFACE_ALT, foreground=colors.NAVY, font=typography.SECTION_TITLE)
    style.configure("ActiveProjectName.TLabel", background=colors.SURFACE_ALT, foreground=colors.PRIMARY_HOVER, font=typography.BODY_BOLD)
    style.configure("ActiveProjectValue.TLabel", background=colors.SURFACE_ALT, foreground=colors.TEXT_PRIMARY, font=typography.BODY)
    style.configure("SurfaceCard.TFrame", background=colors.CARD_SURFACE, bordercolor=colors.BORDER, relief="solid", borderwidth=1)
    style.configure("SurfaceCardTitle.TLabel", background=colors.CARD_SURFACE, foreground=colors.TEXT_SECONDARY, font=typography.SECTION_TITLE)
    style.configure("SurfaceCardContent.TFrame", background=colors.CARD_SURFACE)
    style.configure("PipePage.TFrame", background=colors.WORKSPACE_SURFACE)
    style.configure(
        "PipeInputCard.TFrame",
        background=colors.CARD_SURFACE,
        bordercolor=colors.BORDER,
        relief="solid",
        borderwidth=1,
    )
    style.configure("PipeInputCardTitle.TLabel", background=colors.CARD_SURFACE, foreground=colors.NAVY, font=typography.SECTION_TITLE)
    style.configure("PipeInputCardContent.TFrame", background=colors.CARD_SURFACE)
    style.configure(
        "PipeResultCard.TFrame",
        background=colors.RESULT_SURFACE,
        bordercolor=colors.PIPE_BORDER,
        relief="solid",
        borderwidth=1,
    )
    style.configure("PipeResultAccent.TFrame", background=colors.GOLD, width=4)
    style.configure("PipeResultCardTitle.TLabel", background=colors.RESULT_SURFACE, foreground=colors.NAVY, font=typography.SECTION_TITLE)
    style.configure("PipeResultCardContent.TFrame", background=colors.RESULT_SURFACE)
    style.configure("PipeGroup.TFrame", background=colors.CARD_SURFACE, bordercolor=colors.DIVIDER, relief="solid", borderwidth=1)
    style.configure("PipeGroupTitle.TLabel", background=colors.CARD_SURFACE, foreground=colors.NAVY, font=typography.BODY_BOLD)
    style.configure("PipeField.TLabel", background=colors.CARD_SURFACE, foreground=colors.TEXT_PRIMARY, font=typography.BODY)
    style.configure("PipeMetricLabel.TLabel", background=colors.RESULT_SURFACE, foreground=colors.TEXT_SECONDARY, font=typography.METRIC_LABEL)
    style.configure("PipeMetricValue.TLabel", background=colors.RESULT_SURFACE, foreground=colors.NAVY, font=typography.DOMINANT_RESULT)
    style.configure("PipeMetricUnit.TLabel", background=colors.RESULT_SURFACE, foreground=colors.TEXT_MUTED, font=typography.BODY)
    style.configure("PipeSupportingValue.TLabel", background=colors.RESULT_SURFACE, foreground=colors.NAVY, font=typography.RESULT_TECHNICAL)
    style.configure("PipeSecondaryMetric.TLabel", background=colors.RESULT_SURFACE, foreground=colors.GOLD_DARK, font=typography.RESULT_SECONDARY)
    style.configure("PipeReference.TLabel", background=colors.CARD_SURFACE, foreground=colors.TEXT_MUTED, font=typography.MUTED)
    style.configure("PipeStage.TLabel", background=colors.WORKSPACE_SURFACE, foreground=colors.GOLD_DARK, font=typography.SUBSECTION_TITLE)
    _configure_card(style, "InformationCard.TLabelframe", colors.SURFACE_ALT, colors.BORDER, colors.TEXT_SECONDARY)
    _configure_card(style, "InputCard.TLabelframe", colors.CARD_SURFACE, colors.BORDER, colors.TEXT_SECONDARY)
    _configure_card(style, "CalculationCard.TLabelframe", colors.INFO_SURFACE, colors.BORDER, colors.TEXT_SECONDARY)
    _configure_card(style, "ResultCard.TLabelframe", colors.RESULT_SURFACE, colors.BORDER, colors.TEXT_SECONDARY)
    _configure_card(style, "FormulaCard.TLabelframe", colors.FORMULA_SURFACE, colors.GOLD_BORDER, colors.NAVY)
    _configure_card(style, "WarningCard.TLabelframe", colors.WARNING_SURFACE, colors.WARNING, colors.WARNING)
    _configure_card(style, "ErrorCard.TLabelframe", colors.ERROR_SURFACE, colors.ERROR, colors.ERROR)
    _configure_card(style, "CriticalCard.TLabelframe", colors.CRITICAL_ENGINEERING_SURFACE, colors.CRITICAL_ENGINEERING, colors.CRITICAL_ENGINEERING)
    _configure_card(style, "FormulaStage.TLabelframe", colors.CARD_SURFACE, colors.BORDER, colors.NAVY)
    style.configure("FormulaStrip.TFrame", background=colors.SURFACE)
    _configure_formula_section(
        style,
        "FormulaEquation",
        colors.FORMULA_SOFT,
        colors.FORMULA,
        typography.FORMULA_EXPRESSION,
    )
    _configure_formula_section(style, "FormulaVariables", colors.CARD_SURFACE, colors.NAVY, typography.BODY)
    style.configure(
        "FormulaVariablesSymbol.TLabel",
        background=colors.CARD_SURFACE,
        foreground=colors.NAVY,
        font=typography.BODY_BOLD,
    )
    style.configure(
        "FormulaVariablesUnit.TLabel",
        background=colors.CARD_SURFACE,
        foreground=colors.TEXT_MUTED,
        font=typography.MUTED,
    )
    _configure_formula_section(style, "FormulaSubstitution", colors.PRIMARY_SOFT, colors.NAVY, typography.BODY)
    _configure_formula_section(
        style,
        "FormulaResult",
        colors.SUCCESS_SOFT,
        colors.SUCCESS,
        typography.FORMULA_RESULT,
    )
    _configure_formula_section(
        style,
        "FormulaNote",
        colors.SECONDARY_SURFACE,
        colors.TEXT_MUTED,
        typography.MUTED,
    )
    style.configure("PageHeader.TFrame", background=colors.BACKGROUND)
    style.configure("PageTitle.TLabel", background=colors.BACKGROUND, foreground=colors.NAVY, font=typography.PAGE_TITLE)
    style.configure("PageDescription.TLabel", background=colors.BACKGROUND, foreground=colors.TEXT_SECONDARY, font=typography.BODY)
    style.configure("Dialog.TFrame", background=colors.BACKGROUND)
    style.configure("DialogTitle.TLabel", background=colors.BACKGROUND, foreground=colors.TEXT_PRIMARY, font=typography.SECTION_TITLE)
    style.configure("DialogHint.TLabel", background=colors.BACKGROUND, foreground=colors.TEXT_SECONDARY, font=typography.MUTED)
    style.configure("Info.TLabel", background=colors.BACKGROUND, foreground=colors.TEXT_SECONDARY, font=typography.MUTED)
    style.configure("EngineeringDetails.TFrame", background=colors.RESULT_SURFACE, bordercolor=colors.DIVIDER, relief="solid", borderwidth=1)
    style.configure("EngineeringDetailsTitle.TLabel", background=colors.RESULT_SURFACE, foreground=colors.TEXT_SECONDARY, font=typography.SUBSECTION_TITLE)
    style.configure("EngineeringDetailsLabel.TLabel", background=colors.RESULT_SURFACE, foreground=colors.TEXT_SECONDARY, font=typography.MUTED)
    style.configure("EngineeringDetailsValue.TLabel", background=colors.RESULT_SURFACE, foreground=colors.TEXT_PRIMARY, font=typography.BODY_BOLD)
    style.configure("Warning.TLabel", background=colors.WARNING_SOFT, foreground=colors.WARNING, font=typography.MUTED)
    style.configure("Error.TLabel", background=colors.DANGER_SOFT, foreground=colors.DANGER, font=typography.MUTED)
    _configure_result_metric(style, "ResultMetric", colors.RESULT_SURFACE, colors.SUCCESS)
    _configure_result_metric(style, "WarningResultMetric", colors.WARNING_SURFACE, colors.WARNING)
    _configure_result_metric(style, "ErrorResultMetric", colors.ERROR_SURFACE, colors.ERROR)
    _configure_result_metric(style, "CriticalResultMetric", colors.CRITICAL_ENGINEERING_SURFACE, colors.CRITICAL_ENGINEERING)
    _configure_result_metric(style, "UnavailableResultMetric", colors.RESULT_SURFACE, colors.DIVIDER, typography.BODY_BOLD)
    _configure_result_metric(style, "TransferResultMetric", colors.GOLD_SOFT, colors.GOLD)
    _configure_result_metric(style, "TransferSecondaryMetric", colors.RESULT_SURFACE, colors.GOLD, typography.RESULT_SECONDARY)
    style.configure(
        "TransferReference.TLabel",
        background=colors.CARD_SURFACE,
        foreground=colors.TEXT_MUTED,
        font=typography.MUTED,
    )
    style.configure(
        "TransferReferenceValue.TLabel",
        background=colors.CARD_SURFACE,
        foreground=colors.NAVY_TEXT,
        font=typography.BODY_BOLD,
    )
    style.configure("TechnicalReference.TLabel", background=colors.CARD_SURFACE, foreground=colors.TEXT_MUTED, font=typography.MUTED)
    style.configure("TechnicalReferenceValue.TLabel", background=colors.CARD_SURFACE, foreground=colors.NAVY_TEXT, font=typography.BODY_BOLD)
    _configure_result_metric(style, "DischargeResultMetric", colors.GOLD_SOFT, colors.GOLD)
    _configure_result_metric(style, "DischargeLossMetric", colors.RESULT_SURFACE, colors.GOLD, typography.RESULT_SECONDARY)
    _configure_result_metric(style, "SuctionResultMetric", colors.SUCTION_SOFT, colors.SUCTION)
    _configure_result_metric(style, "SuctionLossMetric", colors.RESULT_SURFACE, colors.SUCTION, typography.RESULT_SECONDARY)
    _configure_button(style, "Primary.TButton", colors.PRIMARY, colors.PRIMARY_HOVER, colors.ON_ACCENT)
    _configure_button(style, "Secondary.TButton", colors.SECONDARY_SOFT, "#DCECF9", colors.SECONDARY)
    _configure_button(style, "Success.TButton", colors.SUCCESS, "#3F855C", colors.ON_ACCENT)
    _configure_button(style, "Warning.TButton", colors.WARNING, "#D9812F", colors.ON_ACCENT)
    _configure_button(style, "Danger.TButton", colors.DANGER, "#B8403D", colors.ON_ACCENT)
    _configure_button(style, "Neutral.TButton", colors.SURFACE_ALT, "#E6EEF1", colors.TEXT_PRIMARY)
    _configure_button(style, "PrimaryCalculate.TButton", colors.NAVY, colors.DEEP_NAVY, colors.ON_ACCENT)
    _configure_pipe_button_prototype(style)
    style.configure(
        "PipeRoundedPrimary.TButton",
        background=colors.CARD_SURFACE,
        foreground=colors.ON_ACCENT,
        borderwidth=0,
        focusthickness=0,
        padding=0,
        relief="flat",
        font=typography.BODY_BOLD,
    )
    style.map(
        "PipeRoundedPrimary.TButton",
        foreground=[
            ("disabled", "#7F9997"),
            ("pressed", colors.ON_ACCENT),
            ("active", colors.ON_ACCENT),
        ],
    )
    style.configure(
        "PipeRoundedNeutral.TButton",
        background=colors.CARD_SURFACE,
        foreground=colors.NAVY,
        borderwidth=0,
        focusthickness=0,
        padding=0,
        relief="flat",
        font=typography.BODY_BOLD,
    )
    style.map(
        "PipeRoundedNeutral.TButton",
        foreground=[("disabled", colors.TEXT_MUTED)],
    )
    style.configure(
        "PipeRoundedFormula.TButton",
        background=colors.CARD_SURFACE,
        foreground=colors.FORMULA,
        borderwidth=0,
        focusthickness=0,
        padding=0,
        relief="flat",
        font=typography.BODY_BOLD,
    )
    style.map(
        "PipeRoundedFormula.TButton",
        foreground=[
            ("disabled", colors.TEXT_MUTED),
            ("pressed", colors.PIPE_DEEP),
            ("active", colors.FORMULA),
        ],
    )
    _configure_rounded_solid_button(style, "TransferRoundedPrimary.TButton")
    _configure_rounded_solid_button(style, "DischargeRoundedPrimary.TButton")
    _configure_rounded_solid_button(style, "SuctionRoundedPrimary.TButton")
    _configure_rounded_outline_button(style, "RoundedAdd.TButton", "#117A45")
    _configure_rounded_outline_button(style, "RoundedEdit.TButton", "#0D55B8")
    _configure_rounded_outline_button(style, "RoundedDelete.TButton", "#B4232A")
    _configure_rounded_outline_button(style, "RoundedNeutral.TButton", colors.NAVY)
    _configure_rounded_outline_button(style, "RoundedClearAll.TButton", "#7A5A1B")
    _configure_rounded_outline_button(style, "RoundedFormula.TButton", colors.FORMULA)
    style.configure(
        "HeaderCommand.TButton",
        background=colors.NAVY,
        foreground=colors.ON_ACCENT,
        borderwidth=0,
        focusthickness=0,
        padding=0,
        relief="flat",
        font=typography.BODY_BOLD,
    )
    style.map("HeaderCommand.TButton", foreground=[("disabled", colors.HEADER_MUTED_TEXT)])
    _configure_button(style, "Transfer.Primary.TButton", colors.TRANSFER, "#D9690D", colors.ON_ACCENT)
    _configure_button(style, "Discharge.Primary.TButton", colors.NAVY, colors.DEEP_NAVY, colors.ON_ACCENT)
    _configure_button(style, "Suction.Primary.TButton", colors.SUCTION, "#244B69", colors.ON_ACCENT)
    style.configure("TNotebook", background=colors.BACKGROUND, bordercolor=colors.BORDER, tabmargins=(0, 0, 0, 0))
    style.configure("TNotebook.Tab", background=colors.SURFACE_ALT, foreground=colors.TEXT_SECONDARY, padding=(14, 8), font=typography.BODY_BOLD)
    style.map("TNotebook.Tab", background=[("selected", colors.PRIMARY), ("active", colors.PRIMARY_SOFT)], foreground=[("selected", colors.ON_ACCENT), ("active", colors.PRIMARY_HOVER)])
    style.configure("YSH.TNotebook", background=colors.BACKGROUND, bordercolor=colors.BORDER, tabmargins=(0, 0, 0, 0))
    style.configure("YSH.TNotebook.Tab", background=colors.NAVY, foreground=colors.ON_ACCENT, padding=(16, 9), font=typography.BODY_BOLD)
    style.map("YSH.TNotebook.Tab", background=[("selected", colors.DEEP_NAVY), ("active", colors.DEEP_NAVY)], foreground=[("selected", colors.ON_ACCENT), ("active", colors.ON_ACCENT)])
    style.configure("Data.Treeview", background=colors.SURFACE, fieldbackground=colors.SURFACE, foreground=colors.TEXT_PRIMARY, rowheight=28, bordercolor=colors.BORDER, font=typography.BODY)
    style.configure("Data.Treeview.Heading", background=colors.SURFACE_ALT, foreground=colors.TEXT_SECONDARY, font=typography.BODY_BOLD, relief="flat")
    style.map("Data.Treeview", background=[("selected", colors.SECONDARY)], foreground=[("selected", colors.ON_ACCENT)])
    style.configure("Project.Treeview", background=colors.SURFACE, fieldbackground=colors.SURFACE, foreground=colors.TEXT_PRIMARY, rowheight=28, bordercolor=colors.BORDER)
    style.configure("Project.Treeview.Heading", background=colors.SURFACE_ALT, foreground=colors.TEXT_SECONDARY, font=typography.BODY_BOLD, relief="flat")
    style.map("Project.Treeview", background=[("selected", colors.SECONDARY)], foreground=[("selected", colors.ON_ACCENT)])
    for tree_style, accent in (
        ("Transfer.Treeview", colors.TRANSFER),
        ("Discharge.Treeview", colors.DISCHARGE),
        ("Suction.Treeview", colors.SUCTION),
    ):
        _configure_engineering_tree(style, tree_style, accent)
    style.map(
        "Transfer.Treeview",
        background=[("selected", colors.GOLD_SOFT)],
        foreground=[("selected", colors.NAVY_TEXT)],
    )
    style.map(
        "Discharge.Treeview",
        background=[("selected", colors.GOLD_SOFT)],
        foreground=[("selected", colors.NAVY_TEXT)],
    )
    style.configure("Vertical.TScrollbar", background=colors.BORDER, troughcolor=colors.APP_BACKGROUND, arrowsize=12)
    style.configure("Horizontal.TScrollbar", background=colors.BORDER, troughcolor=colors.APP_BACKGROUND, arrowsize=12)
    style.configure("Status.TFrame", background=colors.NAVY)
    style.configure("Status.TLabel", background=colors.NAVY, foreground=colors.ON_ACCENT)
    style.configure("ChartSummary.TLabel", background=colors.CARD_SURFACE, foreground=colors.TEXT_SECONDARY, font=typography.MUTED)


def _configure_button(style: ttk.Style, name: str, background: str, active: str, foreground: str) -> None:
    """Configure one semantic button style with a readable active state."""
    style.configure(name, background=background, foreground=foreground, bordercolor=background, focusthickness=1, focuscolor=background, padding=(10, 6), font=typography.BODY_BOLD)
    style.map(name, background=[("active", active), ("pressed", active)], foreground=[("disabled", colors.TEXT_MUTED)])


def _configure_pipe_button_prototype(style: ttk.Style) -> None:
    """Configure the isolated modern Pipe Design button-family prototype."""
    style.configure(
        "PipePrimary.TButton",
        background=colors.PIPE,
        foreground=colors.NAVY,
        bordercolor=colors.PIPE_DEEP,
        focuscolor=colors.PIPE_DEEP,
        focusthickness=1,
        padding=(16, 8),
        font=typography.BODY_BOLD,
        relief="flat",
    )
    style.map(
        "PipePrimary.TButton",
        background=[
            ("disabled", colors.PIPE_DISABLED),
            ("pressed", colors.PIPE_DEEP),
            ("active", colors.PIPE_DARK),
        ],
        bordercolor=[
            ("disabled", colors.PIPE_DISABLED),
            ("pressed", colors.PIPE_DEEP),
            ("active", colors.PIPE_DARK),
        ],
        foreground=[("disabled", "#F5F8FC")],
    )


    style.configure(
        "PipeNeutral.TButton",
        background="#F9FBFD",
        foreground=colors.NAVY,
        bordercolor="#C8D5E3",
        focuscolor=colors.PIPE,
        focusthickness=1,
        padding=(14, 8),
        font=typography.BODY_BOLD,
        relief="flat",
    )
    style.map(
        "PipeNeutral.TButton",
        background=[
            ("disabled", "#EEF2F6"),
            ("pressed", "#D9E8EA"),
            ("active", "#E8F3F4"),
        ],
        bordercolor=[
            ("disabled", "#DCE4ED"),
            ("pressed", "#AFC8CC"),
            ("active", "#9AC9C7"),
        ],
        foreground=[("disabled", colors.TEXT_MUTED)],
    )


def _configure_rounded_outline_button(
    style: ttk.Style,
    name: str,
    foreground: str,
) -> None:
    """Configure live text for a compact image-backed outlined module action."""
    style.configure(
        name,
        background=colors.CARD_SURFACE,
        foreground=foreground,
        borderwidth=0,
        focusthickness=0,
        padding=0,
        relief="flat",
        font=typography.BODY_BOLD,
    )
    style.map(name, foreground=[("disabled", colors.TEXT_MUTED)])


def _configure_rounded_solid_button(style: ttk.Style, name: str) -> None:
    """Configure white live text for an image-backed solid primary action."""
    style.configure(
        name,
        background=colors.CARD_SURFACE,
        foreground=colors.ON_ACCENT,
        borderwidth=0,
        focusthickness=0,
        padding=0,
        relief="flat",
        font=typography.BODY_BOLD,
    )
    style.map(name, foreground=[("disabled", colors.ON_ACCENT)])


def _configure_card(style: ttk.Style, name: str, background: str, border: str, foreground: str) -> None:
    """Configure one semantic light-surface card style."""
    style.configure(name, background=background, bordercolor=border, relief="solid", borderwidth=1)
    style.configure(f"{name}.Label", background=background, foreground=foreground, font=typography.SECTION_TITLE)


def _configure_result_metric(
    style: ttk.Style,
    name: str,
    background: str,
    accent: str,
    value_font: tuple[str, int, str] = typography.RESULT,
) -> None:
    """Configure one semantic severity override for a result metric."""
    style.configure(f"{name}.TFrame", background=background)
    style.configure(f"{name}Accent.TFrame", background=accent, width=4)
    style.configure(f"{name}Label.TLabel", background=background, foreground=colors.TEXT_SECONDARY, font=typography.MUTED)
    style.configure(f"{name}Value.TLabel", background=background, foreground=colors.NAVY_TEXT, font=value_font)


def _configure_engineering_tree(
    style: ttk.Style,
    name: str,
    accent: str,
) -> None:
    """Apply the shared compact table grammar with a module-colored selection."""
    style.configure(
        name,
        background=colors.CARD_SURFACE,
        fieldbackground=colors.CARD_SURFACE,
        foreground=colors.TEXT_PRIMARY,
        rowheight=28,
        bordercolor=colors.BORDER,
        font=typography.BODY,
    )
    style.configure(
        f"{name}.Heading",
        background=colors.SURFACE_ALT,
        foreground=colors.TEXT_SECONDARY,
        font=typography.BODY_BOLD,
        relief="flat",
    )
    style.map(
        name,
        background=[("selected", accent)],
        foreground=[("selected", colors.ON_ACCENT)],
    )


def _configure_formula_section(
    style: ttk.Style,
    name: str,
    background: str,
    accent: str,
    content_font: tuple[str, int] | tuple[str, int, str],
) -> None:
    """Configure one restrained stage surface within an engineering derivation."""
    style.configure(
        f"{name}.TFrame",
        background=background,
        bordercolor=colors.BORDER,
        relief="solid",
        borderwidth=1,
    )
    style.configure(f"{name}Accent.TFrame", background=accent, width=4)
    style.configure(
        f"{name}Title.TLabel",
        background=background,
        foreground=accent,
        font=typography.SUBSECTION_TITLE,
    )
    style.configure(
        f"{name}Text.TLabel",
        background=background,
        foreground=colors.TEXT_PRIMARY,
        font=content_font,
    )


def configure_project_tree(tree: ttk.Treeview) -> None:
    """Configure active-project rows without conflating them with selection state."""
    if hasattr(tree, "tag_configure"):
        tree.tag_configure(
            "active_project",
            background=colors.PRIMARY_SOFT,
            foreground=colors.TEXT_PRIMARY,
        )
