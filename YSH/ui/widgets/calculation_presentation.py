"""Calculation-only action hierarchy and result surface state; no calculations."""
from tkinter import ttk
from ui.theme import colors, typography
from ui.widgets.rounded_button import (
    RoundedImageButton, create_rounded_button, NEUTRAL_BUTTON_PALETTE,
)

PRIMARY_HEIGHT = 48
SECONDARY_HEIGHT = 36


def calculation_button(parent, text, command, *, primary=False, palette=None, **options):
    """Use one native interaction/icon layout for main and secondary actions."""
    if options.get('icon_only'):
        return create_rounded_button(parent,text,command,primary=primary,palette=palette,**options)
    for key in ('icon_size','minimum_height','horizontal_padding','vertical_padding','radius'):
        options.pop(key,None)
    style='Calculation.'+options.get('style','TButton')
    options['style']=style
    ttk.Style(parent).configure(style,font=typography.BODY_BOLD if primary else typography.BODY,
        foreground=colors.WHITE if primary else colors.NAVY,padding=0,borderwidth=0,
        focusthickness=0,relief='flat')
    options.setdefault('icon_name','calculate' if primary else None)
    button=RoundedImageButton(parent,text=text,command=command,
        palette=palette if primary else NEUTRAL_BUTTON_PALETTE,
        icon_size=32 if primary else 24,minimum_height=PRIMARY_HEIGHT if primary else SECONDARY_HEIGHT,
        horizontal_padding=12 if primary else 10,vertical_padding=6 if primary else 4,
        radius=7,**options)
    button.calculation_action_role='primary' if primary else 'secondary'
    return button


def set_result_state(card, calculated):
    """Empty cards use existing glass; valid results restore opaque native surfaces."""
    if card is None:return
    def mark(widget):
        widget.result_surface_opaque=bool(calculated)
        for child in widget.winfo_children():mark(child)
    mark(card)
    card.composite_panel=True
    parent=card
    while parent is not None:
        backdrop=getattr(parent,'_workspace_backdrop',None)
        if backdrop:
            backdrop.request();break
        parent=parent.master
