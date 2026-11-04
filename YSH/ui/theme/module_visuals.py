"""Shared calculation-page visual roles, derived from the accepted Pipe pilot.

These tokens carry no engineering or verification meaning. Legacy global colors
and the Pipe implementation remain unchanged.
"""
from types import MappingProxyType
from tkinter import ttk
from ui.theme import colors, typography
from ui.theme.pipe_pilot import MODULE_ACCENTS, PIPE_WORKSPACE, PIPE_INPUT_BORDER
from ui.theme.spacing import XS, SM, MD

TRANSFER_ACCENT = MODULE_ACCENTS['transfer_pump']
DISCHARGE_ACCENT = MODULE_ACCENTS['discharge_head_loss']
SUCTION_ACCENT = MODULE_ACCENTS['suction_npsh']
# Dark tones provide readable text and white-on-color actions.
MODULES = MappingProxyType({
    'transfer_pump': ('Transfer', TRANSFER_ACCENT, '#1D4ED8', '#EFF6FF', 'TransferSecondaryMetric'),
    'discharge_head_loss': ('Discharge', DISCHARGE_ACCENT, '#4338CA', '#F1F0FF', 'DischargeLossMetric'),
    'suction_npsh': ('Suction', SUCTION_ACCENT, '#9A3412', '#FFF4EB', 'SuctionLossMetric'),
})


def configure_module_visuals(style: ttk.Style) -> None:
    """Register one shared card/control language with three restrained identities."""
    for prefix, accent, dark, soft, supporting in MODULES.values():
        style.configure(prefix+'Workspace.TFrame', background=PIPE_WORKSPACE)
        style.configure(prefix+'Page.TLabelframe', background=PIPE_WORKSPACE, borderwidth=0)
        style.configure(prefix+'Page.TLabelframe.Label', background=PIPE_WORKSPACE,
                        foreground=dark, font=typography.SECTION_TITLE)
        style.configure(prefix+'PageTitle.TLabel', background=PIPE_WORKSPACE,
                        foreground=colors.NAVY, font=typography.PAGE_TITLE)
        style.configure(prefix+'PageDescription.TLabel', background=PIPE_WORKSPACE,
                        foreground=colors.TEXT_SECONDARY, font=typography.MUTED)
        for role, surface in (('Input', colors.WHITE), ('Result', soft)):
            name=prefix+role+'Card.TLabelframe'
            style.configure(name, background=surface, bordercolor=PIPE_INPUT_BORDER,
                            borderwidth=1, relief='solid', padding=(MD, SM))
            style.configure(name+'.Label', background=surface, foreground=dark,
                            font=typography.SECTION_TITLE)
            style.configure(prefix+role+'.TFrame', background=surface)
            style.configure(prefix+role+'.TLabel', background=surface,
                            foreground=colors.TEXT_PRIMARY, font=typography.BODY)
        style.configure(prefix+'Info.TLabel', background=colors.INFO_SURFACE,
                        foreground=colors.NAVY, padding=XS, font=typography.MUTED)
        for control in ('TEntry', 'TCombobox'):
            name=prefix+'.'+control
            style.configure(name, fieldbackground=colors.WHITE, foreground=colors.TEXT_PRIMARY,
                            bordercolor=PIPE_INPUT_BORDER, padding=(SM, XS))
            style.map(name, bordercolor=[('focus', accent)],
                      fieldbackground=[('disabled', colors.SURFACE_ALT), ('readonly', colors.WHITE)],
                      foreground=[('disabled', colors.TEXT_MUTED), ('readonly', colors.TEXT_PRIMARY)])
        style.configure(prefix+'Secondary.TButton', padding=(MD, SM),
                        foreground=colors.NAVY, background=colors.WHITE, bordercolor=PIPE_INPUT_BORDER)
        style.map(prefix+'Secondary.TButton', background=[('active', soft)],
                  foreground=[('disabled', colors.TEXT_MUTED)])
        for metric, size in ((prefix+'ResultMetric', 30), (supporting, 16)):
            style.configure(metric+'.TFrame', background=soft)
            style.configure(metric+'Accent.TFrame', background=accent)
            style.configure(metric+'Label.TLabel', background=soft,
                            foreground=colors.TEXT_SECONDARY, font=typography.METRIC_LABEL)
            style.configure(metric+'Value.TLabel', background=soft, foreground=dark,
                            font=(typography.FONT_FAMILY, size, 'bold'))
