"""Library-only master visual roles; no query, ownership or engineering policy."""
from tkinter import ttk
from ui.theme import colors, typography
from ui.theme.pipe_pilot import PIPE_INPUT_BORDER, PIPE_WORKSPACE
from ui.theme.spacing import XS, SM, MD

LIBRARY_ACCENT = '#0E7490'
LIBRARY_SOFT = '#ECF7FA'
PANE_WEIGHTS = (2, 4, 3)


def pane_positions(width: int) -> tuple[int, int]:
    """Keep weighted panes readable at the supported Library window sizes."""
    total=sum(PANE_WEIGHTS)
    left=max(196,round(width*PANE_WEIGHTS[0]/total))
    second=min(width-300,max(left+320,round(width*sum(PANE_WEIGHTS[:2])/total)))
    return left,second


def verification_role(status: object) -> str:
    """Present only an explicit verification status; absent status stays neutral."""
    return {'VERIFIED':'Verified', 'PARTIALLY_VERIFIED':'Warning', 'USER_SUPPLIED':'Info',
            'UNVERIFIED':'Warning', 'DEPRECATED':'Error'}.get(getattr(status,'value',status),'Muted')


def configure_library_visuals(style: ttk.Style) -> None:
    """Register on explicit Library open, without restyling global defaults."""
    style.configure('Library.Workspace.TFrame',background=PIPE_WORKSPACE)
    style.configure('Library.Card.TFrame',background=colors.WHITE,padding=SM,
                    borderwidth=1,relief='solid',bordercolor=PIPE_INPUT_BORDER)
    style.configure('Library.Body.TFrame',background=colors.WHITE)
    style.configure('Library.Header.TFrame',background=LIBRARY_SOFT,padding=(MD,SM))
    style.configure('Library.Title.TLabel',background=LIBRARY_SOFT,foreground=colors.NAVY,font=typography.PAGE_TITLE)
    style.configure('Library.Subtitle.TLabel',background=LIBRARY_SOFT,foreground=colors.TEXT_SECONDARY,font=typography.MUTED)
    style.configure('Library.Heading.TLabel',background=colors.WHITE,foreground=colors.NAVY,font=typography.SECTION_TITLE)
    style.configure('Library.Field.TLabel',background=colors.WHITE,foreground=colors.TEXT_SECONDARY,font=typography.MUTED)
    style.configure('Library.Value.TLabel',background=colors.WHITE,foreground=colors.TEXT_PRIMARY,font=typography.BODY)
    style.configure('Library.Section.TLabelframe',background=colors.WHITE,bordercolor=PIPE_INPUT_BORDER,
                    borderwidth=1,relief='solid',padding=SM)
    style.configure('Library.Section.TLabelframe.Label',background=colors.WHITE,foreground=LIBRARY_ACCENT,font=typography.BODY_BOLD)
    for control in ('TEntry','TCombobox'):
        style.configure('Library.'+control,padding=(SM,XS),fieldbackground=colors.WHITE,
                        foreground=colors.TEXT_PRIMARY,bordercolor=PIPE_INPUT_BORDER)
        style.map('Library.'+control,bordercolor=[('focus',LIBRARY_ACCENT)],
                  fieldbackground=[('disabled',colors.SURFACE_ALT),('readonly',colors.WHITE)],
                  foreground=[('disabled',colors.TEXT_MUTED),('readonly',colors.TEXT_PRIMARY)])
    style.configure('Library.Primary.TButton',padding=(MD,SM),background=LIBRARY_ACCENT,
                    foreground=colors.WHITE,font=typography.BODY_BOLD)
    style.map('Library.Primary.TButton',background=[('active',colors.NAVY),('disabled',colors.SURFACE_ALT)],
              foreground=[('disabled',colors.TEXT_MUTED)])
    style.configure('Library.Secondary.TButton',padding=(MD,SM),background=colors.WHITE,
                    foreground=colors.NAVY,bordercolor=PIPE_INPUT_BORDER,font=typography.BODY)
    style.map('Library.Secondary.TButton',background=[('active',LIBRARY_SOFT)],foreground=[('disabled',colors.TEXT_MUTED)])
    for role,surface,foreground in (('Verified',colors.SUCCESS_SURFACE,colors.SUCCESS),
        ('Warning',colors.WARNING_SURFACE,colors.GOLD_DARK),('Info',colors.INFO_SURFACE,colors.NAVY),
        ('Error',colors.ERROR_SURFACE,colors.CRITICAL_ENGINEERING),('Muted',colors.SURFACE_ALT,colors.TEXT_SECONDARY)):
        style.configure('Library.'+role+'.TLabel',background=surface,foreground=foreground,padding=XS,font=typography.MUTED)
    for tree,rowheight in (('Library.Data.Treeview',32),('LibraryNav.Treeview',30)):
        style.configure(tree,rowheight=rowheight,background=colors.WHITE,fieldbackground=colors.WHITE,
                        foreground=colors.TEXT_PRIMARY,font=typography.BODY,borderwidth=0)
        style.map(tree,background=[('selected',LIBRARY_SOFT)],foreground=[('selected',colors.NAVY)])
    style.configure('Library.Data.Treeview.Heading',background=colors.SURFACE_ALT,
                    foreground=colors.NAVY,font=typography.BODY_BOLD,padding=(SM,SM))
