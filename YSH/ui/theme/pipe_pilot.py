"""Isolated Pipe visual-pilot tokens on the existing ttk theme; no engineering meaning."""
from __future__ import annotations

from types import MappingProxyType
from tkinter import ttk

from ui.theme import colors, typography
from ui.theme.spacing import XS, SM, MD

# Future identities are a design plan only. Other module styles are not applied.
MODULE_ACCENTS = MappingProxyType({
    'pipe_design': '#0D9488', 'transfer_pump': '#2563EB',
    'discharge_head_loss': '#6366F1', 'suction_npsh': '#EA7C32',
})
PIPE_ACCENT = MODULE_ACCENTS['pipe_design']
PIPE_DARK = '#0F766E'
PIPE_SOFT = '#ECFDF8'
PIPE_BORDER = '#99D9D1'
PIPE_WORKSPACE = '#F1F7FA'
PIPE_INPUT_BORDER = '#D6E3EA'
PIPE_LIGHT_BLUE = '#EFF6FF'
PIPE_HOVER = '#11877E'


def configure_pipe_pilot(style: ttk.Style) -> None:
    """Register only Pipe-prefixed surfaces, controls and actions in the shared theme."""
    style.configure('PipePage.TFrame', background=PIPE_WORKSPACE)
    style.configure('PipePageHeader.TFrame', background=PIPE_WORKSPACE)
    style.configure('PipePageTitle.TLabel', background=PIPE_WORKSPACE, foreground=colors.NAVY,
                    font=typography.PAGE_TITLE)
    style.configure('PipePageDescription.TLabel', background=PIPE_WORKSPACE,
                    foreground=colors.TEXT_SECONDARY, font=typography.MUTED)
    style.configure('PipeInputCard.TFrame', background=colors.WHITE, bordercolor=PIPE_INPUT_BORDER,
                    borderwidth=1, relief='solid')
    style.configure('PipeInputCardTitle.TLabel', background=colors.WHITE,
                    foreground=colors.NAVY, font=typography.SECTION_TITLE)
    style.configure('PipeInputCardContent.TFrame', background=colors.WHITE)
    style.configure('PipeGroup.TFrame', background=colors.WHITE, borderwidth=0, relief='flat')
    style.configure('PipeSection.TFrame', background=colors.WHITE, bordercolor=PIPE_INPUT_BORDER,
                    borderwidth=1, relief='solid', padding=(MD, SM))
    style.configure('PipeGroupTitle.TLabel', background=colors.WHITE, foreground=PIPE_DARK,
                    font=typography.BODY_BOLD)
    style.configure('PipeField.TLabel', background=colors.WHITE, foreground=colors.TEXT_PRIMARY,
                    font=typography.BODY)
    style.configure('PipeInputValue.TLabel', background=colors.WHITE, foreground=colors.NAVY,
                    font=typography.RESULT_TECHNICAL)
    style.configure('PipeUnit.TLabel', background=colors.WHITE, foreground=colors.TEXT_MUTED,
                    font=typography.MUTED)
    style.configure('PipeInfo.TLabel', background=PIPE_LIGHT_BLUE, foreground=colors.INFO,
                    font=typography.MUTED, padding=XS)
    style.configure('PipeSourceWarning.TLabel', background=colors.WARNING_SURFACE,
                    foreground=colors.GOLD_DARK, font=typography.MUTED, padding=XS)
    style.configure('PipeStage.TLabel', background=PIPE_WORKSPACE, foreground=PIPE_DARK,
                    font=typography.SUBSECTION_TITLE)
    style.configure('PipeResultCard.TFrame', background=PIPE_SOFT, bordercolor=PIPE_BORDER,
                    borderwidth=1, relief='solid')
    style.configure('PipeResultAccent.TFrame', background=PIPE_ACCENT, width=4)
    style.configure('PipeResultCardTitle.TLabel', background=PIPE_SOFT, foreground=PIPE_DARK,
                    font=typography.SECTION_TITLE)
    style.configure('PipeResultCardContent.TFrame', background=PIPE_SOFT)
    for name in ('PipeMetricLabel', 'PipeMetricUnit'):
        style.configure(name+'.TLabel', background=PIPE_SOFT, foreground=colors.TEXT_SECONDARY,
                        font=typography.METRIC_LABEL)
    style.configure('PipeMetricValue.TLabel', background=PIPE_SOFT, foreground=PIPE_DARK,
                    font=(typography.FONT_FAMILY, 30, 'bold'))
    style.configure('PipeSupportingValue.TLabel', background=PIPE_SOFT, foreground=colors.NAVY,
                    font=typography.RESULT_TECHNICAL)
    style.configure('PipeSecondaryMetric.TLabel', background=PIPE_SOFT, foreground=PIPE_DARK,
                    font=typography.RESULT_SECONDARY)
    style.configure('Pipe.TEntry', padding=(SM, XS), fieldbackground=colors.WHITE,
                    foreground=colors.TEXT_PRIMARY, bordercolor=PIPE_INPUT_BORDER)
    style.map('Pipe.TEntry', bordercolor=[('focus', PIPE_ACCENT), ('disabled', colors.DIVIDER)])
    style.configure('Pipe.TCombobox', padding=(SM, XS), fieldbackground=colors.WHITE,
                    foreground=colors.TEXT_PRIMARY, bordercolor=PIPE_INPUT_BORDER)
    style.map('Pipe.TCombobox', fieldbackground=[('readonly', colors.WHITE), ('disabled', colors.SURFACE_ALT)],
              foreground=[('readonly', colors.TEXT_PRIMARY), ('disabled', colors.TEXT_MUTED)],
              bordercolor=[('focus', PIPE_ACCENT)])
    style.configure('PipeSecondary.TButton', padding=(MD, SM), background=colors.WHITE,
                    bordercolor=PIPE_INPUT_BORDER, foreground=colors.NAVY, font=typography.BODY)
    style.map('PipeSecondary.TButton', background=[('active', PIPE_SOFT)],
              foreground=[('disabled', colors.TEXT_MUTED)])
