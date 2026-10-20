"""Formula-only presentation roles using the accepted master module tokens."""
from tkinter import ttk
from ui.theme import colors, typography
from ui.theme.module_visuals import MODULES
from ui.theme.pipe_pilot import PIPE_ACCENT, PIPE_DARK, PIPE_SOFT, PIPE_INPUT_BORDER
from ui.theme.spacing import XS, SM, MD

IDENTITIES = {
    'pipe_design': ('FVPipe', PIPE_ACCENT, PIPE_DARK, PIPE_SOFT, 'page.pipe.tab'),
    **{key: ('FV'+value[0], value[1], value[2], value[3], {
        'transfer_pump':'page.transfer.tab', 'discharge_head_loss':'page.discharge.tab',
        'suction_npsh':'page.suction.tab'}[key]) for key,value in MODULES.items()},
}
DEFAULT_IDENTITY = ('FVNeutral', colors.NAVY, colors.NAVY, colors.INFO_SURFACE, 'formula.view_title')


def identity(module_key: str | None) -> tuple:
    """Unknown/legacy callers keep neutral chrome; no inference from engineering values."""
    return IDENTITIES.get(module_key, DEFAULT_IDENTITY)


def configure_formula_visuals(style: ttk.Style) -> None:
    """Add opt-in formula roles; no main module or Library style is overwritten."""
    style.configure('FVContainer.TLabelframe', background=colors.WHITE, borderwidth=0, padding=MD)
    for prefix,accent,dark,soft,_ in (*IDENTITIES.values(), DEFAULT_IDENTITY):
        style.configure(prefix+'Header.TFrame', background=soft, padding=(MD, SM))
        style.configure(prefix+'Title.TLabel', background=soft, foreground=dark, font=typography.SECTION_TITLE)
        style.configure(prefix+'Module.TLabel', background=soft, foreground=colors.TEXT_SECONDARY, font=typography.BODY)
        style.configure(prefix+'Stage.TLabelframe', background=colors.WHITE, bordercolor=PIPE_INPUT_BORDER,
                        borderwidth=1, relief='solid', padding=MD)
        style.configure(prefix+'Stage.TLabelframe.Label', background=colors.WHITE, foreground=dark,
                        font=typography.SECTION_TITLE)
        style.configure(prefix+'Heading.TLabel', background=colors.WHITE, foreground=dark, font=typography.BODY_BOLD)
        style.configure(prefix+'Result.TLabel', background=soft, foreground=dark,
                        font=typography.DOMINANT_RESULT, padding=SM)
        style.configure(prefix+'Accent.TFrame', background=accent, height=3)
        style.configure(prefix+'Selector.TCombobox', padding=(SM, XS), fieldbackground=soft,
                        foreground=dark, font=typography.BODY_BOLD)
        style.map(prefix+'Selector.TCombobox', fieldbackground=[('readonly', soft)],
                  foreground=[('readonly', dark)], bordercolor=[('focus', accent)])
    for role,surface,foreground in (
        ('Info',colors.INFO_SURFACE,colors.NAVY), ('Verified',colors.SUCCESS_SURFACE,colors.SUCCESS),
        ('Warning',colors.WARNING_SURFACE,colors.GOLD_DARK), ('Error',colors.ERROR_SURFACE,colors.CRITICAL_ENGINEERING),
        ('Muted',colors.SURFACE_ALT,colors.TEXT_SECONDARY), ('Override',colors.WARNING_SURFACE,colors.GOLD_DARK)):
        style.configure('FV'+role+'.TLabel', background=surface, foreground=foreground,
                        font=typography.BODY, padding=XS)
    style.configure('FVBody.TFrame', background=colors.WHITE)
    style.configure('FVText.TLabel', background=colors.WHITE, foreground=colors.TEXT_PRIMARY, font=typography.BODY)
    style.configure('FVMetadata.TLabel', background=colors.WHITE, foreground=colors.TEXT_SECONDARY, font=typography.MUTED)
    style.configure('FVTableHeader.TLabel', background=colors.SURFACE_ALT, foreground=colors.NAVY, font=typography.BODY_BOLD)
    style.configure('FVSubstitution.TLabel', background=colors.SURFACE_ALT,
                    foreground=colors.NAVY, font=("Consolas", 11), padding=SM)
