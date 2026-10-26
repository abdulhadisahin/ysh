"""Opt-in live Fire roles; existing page styles remain untouched."""
from ui.theme.fire_identity import FIRE_ACCENT, FIRE_DARK, FIRE_SOFT
from ui.theme import colors, typography


def configure_fire_visuals(style):
    style.configure('Fire.TFrame',background=colors.WHITE)
    style.configure('Fire.Title.TLabel',background=colors.WHITE,foreground=FIRE_DARK,font=typography.PAGE_TITLE)
    style.configure('Fire.TLabel',background=colors.WHITE,foreground=colors.TEXT_PRIMARY,font=typography.BODY)
    style.configure('Fire.Card.TLabelframe',background=colors.WHITE,bordercolor='#D6E3EA',padding=12)
    style.configure('Fire.Card.TLabelframe.Label',background=colors.WHITE,foreground=FIRE_DARK,font=typography.SECTION_TITLE)
    style.configure('Fire.Result.TFrame',background=FIRE_SOFT,padding=12)
    style.configure('Fire.Result.TLabel',background=FIRE_SOFT,foreground=FIRE_DARK,font=typography.RESULT)
    style.configure('Fire.Support.TLabel',background=FIRE_SOFT,foreground=FIRE_DARK,font=typography.BODY_BOLD)
    style.configure('Fire.Primary.TButton',background=FIRE_ACCENT,foreground=colors.WHITE,padding=(14,8))
    style.map('Fire.Primary.TButton',background=[('active',FIRE_DARK)])
    style.configure('Fire.Secondary.TButton',padding=(12,8),foreground=FIRE_DARK)
    style.configure('Fire.Status.TLabel',background=colors.WARNING_SURFACE,foreground=colors.GOLD_DARK,
                    padding=8,font=typography.BODY)
