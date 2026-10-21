"""History-only master styling with restrained module identity, no data policy."""
from tkinter import ttk
from ui.theme import colors, typography
from ui.theme.pipe_pilot import MODULE_ACCENTS, PIPE_INPUT_BORDER
from ui.theme.formula_visuals import identity
from ui.theme.spacing import XS,SM,MD
from ui.theme.fire_identity import FIRE_ACCENT, FIRE_LABELS

HISTORY_MODULE_ACCENTS = {**MODULE_ACCENTS, **dict.fromkeys(FIRE_LABELS, FIRE_ACCENT)}

HISTORY_ACCENT='#526F86'
HISTORY_SOFT='#EDF4F8'


def configure_history_visuals(style: ttk.Style) -> None:
    style.configure('History.Header.TFrame',background=HISTORY_SOFT,padding=(MD,SM))
    style.configure('History.Title.TLabel',background=HISTORY_SOFT,foreground=colors.NAVY,font=typography.PAGE_TITLE)
    style.configure('History.Subtitle.TLabel',background=HISTORY_SOFT,foreground=colors.TEXT_SECONDARY,font=typography.MUTED)
    style.configure('History.Body.TFrame',background=colors.WHITE)
    style.configure('History.Card.TFrame',background=colors.WHITE,bordercolor=PIPE_INPUT_BORDER,borderwidth=1,relief='solid',padding=SM)
    style.configure('History.Section.TLabelframe',background=colors.WHITE,bordercolor=PIPE_INPUT_BORDER,borderwidth=1,padding=SM)
    style.configure('History.Section.TLabelframe.Label',background=colors.WHITE,foreground=colors.NAVY,font=typography.BODY_BOLD)
    style.configure('History.Text.TLabel',background=colors.WHITE,foreground=colors.TEXT_PRIMARY,font=typography.BODY)
    style.configure('History.Metadata.TLabel',background=colors.WHITE,foreground=colors.TEXT_SECONDARY,font=typography.MUTED)
    style.configure('History.Badge.TLabel',background=HISTORY_SOFT,foreground=colors.NAVY,font=typography.BODY_BOLD,padding=XS)
    style.configure('History.TEntry',fieldbackground=colors.WHITE,bordercolor=PIPE_INPUT_BORDER,padding=(SM,XS))
    style.configure('History.TCombobox',fieldbackground=colors.WHITE,bordercolor=PIPE_INPUT_BORDER,padding=(SM,XS))
    for control in ('TEntry','TCombobox'): style.map('History.'+control,bordercolor=[('focus',HISTORY_ACCENT)])
    style.configure('History.Primary.TButton',background=colors.NAVY,foreground=colors.WHITE,padding=(MD,SM),font=typography.BODY_BOLD)
    style.map('History.Primary.TButton',background=[('active',HISTORY_ACCENT)])
    style.configure('History.Secondary.TButton',background=colors.WHITE,foreground=colors.NAVY,padding=(MD,SM))
    style.configure('History.Treeview',rowheight=32,background=colors.WHITE,fieldbackground=colors.WHITE,borderwidth=0,font=typography.BODY)
    style.configure('History.Treeview.Heading',background=colors.SURFACE_ALT,foreground=colors.NAVY,font=typography.BODY_BOLD,padding=SM)
    style.map('History.Treeview',background=[('selected',HISTORY_SOFT)],foreground=[('selected',colors.NAVY)])
    for key,accent in HISTORY_MODULE_ACCENTS.items():
        prefix,_,dark,soft,_=identity(key)
        style.configure('History.'+key+'.TLabel',background=soft,foreground=dark,font=typography.SECTION_TITLE,padding=XS)
        style.configure('History.'+key+'.Result.TLabel',background=soft,foreground=dark,font=typography.RESULT,padding=SM)
    for role,surface,text in (('Warning',colors.WARNING_SURFACE,colors.GOLD_DARK),('Critical',colors.ERROR_SURFACE,colors.CRITICAL_ENGINEERING),('Info',colors.INFO_SURFACE,colors.NAVY)):
        style.configure('History.'+role+'.TLabel',background=surface,foreground=text,font=typography.BODY,padding=XS)
