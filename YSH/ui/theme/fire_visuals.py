"""Opt-in live Fire roles; existing page styles remain untouched."""
from ui.theme.fire_identity import FIRE_ACCENT, FIRE_DARK, FIRE_SOFT
from ui.theme import colors, typography
from ui.theme.spacing import CARD_PADDING, CONTROL_PADDING, SM, MD
from ui.theme.pipe_pilot import PIPE_INPUT_BORDER


def configure_fire_visuals(style):
    for role,foreground in (('Verified',colors.SUCCESS),('Info',colors.NAVY),
                            ('Warning',colors.GOLD_DARK),('Muted',colors.TEXT_SECONDARY)):
        style.configure('Fire.Source.'+role+'.TLabel',background=colors.WHITE,
                        foreground=foreground,font=typography.MUTED)
    style.configure('Fire.TFrame',background=colors.WHITE)
    style.configure('Fire.Title.TLabel',background=colors.WHITE,foreground=FIRE_DARK,font=typography.PAGE_TITLE)
    style.configure('Fire.TLabel',background=colors.WHITE,foreground=colors.TEXT_PRIMARY,font=typography.BODY)
    style.configure('Fire.Card.TLabelframe',background=colors.WHITE,bordercolor=PIPE_INPUT_BORDER,borderwidth=1,relief='solid',padding=CARD_PADDING)
    style.configure('Fire.Card.TLabelframe.Label',background=colors.WHITE,foreground=FIRE_DARK,font=typography.SECTION_TITLE)
    style.configure('Fire.Result.TFrame',background=FIRE_SOFT,padding=12)
    style.configure('Fire.Result.TLabel',background=FIRE_SOFT,foreground=FIRE_DARK,font=typography.RESULT)
    style.configure('Fire.Support.TLabel',background=FIRE_SOFT,foreground=FIRE_DARK,font=typography.BODY_BOLD)
    style.configure('Fire.Primary.TButton',background=FIRE_ACCENT,foreground=colors.WHITE,padding=(MD,SM))
    style.map('Fire.Primary.TButton',background=[('active',FIRE_DARK)])
    style.configure('Fire.Secondary.TButton',padding=(MD,SM),foreground=FIRE_DARK,
                    background=colors.WHITE,bordercolor=PIPE_INPUT_BORDER,font=typography.BODY)
    style.map('Fire.Secondary.TButton',background=[('disabled',colors.SURFACE_ALT),('active',FIRE_SOFT)],
              foreground=[('disabled',colors.TEXT_MUTED)])
    for control in ('TEntry','TCombobox'):
        name='Fire.'+control
        style.configure(name,padding=CONTROL_PADDING,fieldbackground=colors.WHITE,
                        foreground=colors.TEXT_PRIMARY,bordercolor=PIPE_INPUT_BORDER)
        style.map(name,bordercolor=[('focus',FIRE_ACCENT)],
                  fieldbackground=[('disabled',colors.SURFACE_ALT),('readonly',colors.WHITE)],
                  foreground=[('disabled',colors.TEXT_MUTED),('readonly',colors.TEXT_PRIMARY)])
    for role,surface,foreground in (('Info',colors.INFO_SURFACE,colors.NAVY),
                                    ('Error',colors.ERROR_SURFACE,colors.CRITICAL_ENGINEERING)):
        style.configure('Fire.'+role+'.TLabel',background=surface,foreground=foreground,
                        padding=SM,font=typography.BODY)
    style.configure('Fire.Status.TLabel',background=colors.WARNING_SURFACE,foreground=colors.GOLD_DARK,
                    padding=8,font=typography.BODY)
