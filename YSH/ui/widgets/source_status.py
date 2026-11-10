"""Compact source presentation. Callers supply existing provenance/state flags."""
from tkinter import ttk
from ui.theme import colors


def library_source_name(record, translate):
    """A human name/context only; identity remains in the caller's object map."""
    def compact(text):
        text=' '.join(text.split())
        return text if len(text)<=48 else text[:47]+'…'
    document=compact(record.source.document) if record.source and record.source.document else ''
    context=compact(record.context)
    return ' · '.join(dict.fromkeys(part for part in (document,context) if part)) or translate('source.state.library')


def pipe_source_name(translate, standard, nominal, revision):
    return ' · '.join(part for part in (standard,nominal,
        translate('discharge.pipe.revision')+' '+str(revision)) if part)


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
