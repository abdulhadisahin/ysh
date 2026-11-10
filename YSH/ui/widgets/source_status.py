"""Compact source presentation. Callers supply existing provenance/state flags."""
from tkinter import ttk
from ui.theme import colors


def source_text(translate, origin, *, linked=False, override=False, stale=False):
    parts=[translate('source.state.'+origin)]
    if linked and origin!='linked':parts.append(translate('source.state.linked'))
    if linked and not stale:parts.append(translate('source.state.current'))
    if override:parts.append(translate('source.state.override'))
    if stale:parts.append(translate('source.state.stale'))
    return ' · '.join(parts)


def source_style(widget, normal, *, override=False, stale=False):
    """Keep native geometry/fonts; source conditions share opaque semantic colors."""
    # An explicit source conflict/error must never be softened by an override.
    lower=normal.lower()
    if '.error.' in lower or '.critical.' in lower or ('.warning.' in lower and not stale):
        return normal
    role='Stale' if stale else 'Override' if override else None
    if role is None:return normal
    name='SourceStatus.'+role+'.'+normal
    if isinstance(widget,ttk.Widget):
        ttk.Style(widget).configure(name,
            background=colors.WARNING_SURFACE if stale else colors.INFO_SURFACE,
            foreground=colors.GOLD_DARK if stale else colors.NAVY)
    return name
