"""Native export interaction; the selected immutable snapshot is the sole input."""
from __future__ import annotations
from tkinter import filedialog, messagebox
from engineering.snapshots.models import CalculationSnapshot


def save_snapshot_pdf(parent: object, snapshot: CalculationSnapshot | None, *, translate=None) -> None:
    """Cancel quietly and report export errors without affecting engineering results."""
    from i18n.translator import Translator
    tr = translate or getattr(parent, '_translate', None) or getattr(parent, 'tr', None) or Translator('tr').translate
    language = getattr(getattr(tr, '__self__', None), 'language', 'tr')
    if snapshot is None:
        messagebox.showinfo(tr('report.export_title'), tr('report.no_snapshot'), parent=parent)
        return
    try:
        from reporting.models import adapt_snapshot
        from reporting.export import default_filename, export_pdf
        report = adapt_snapshot(snapshot, language=language)
        filename = filedialog.asksaveasfilename(parent=parent, title=tr('report.export_title'),
            defaultextension='.pdf', filetypes=[('PDF', '*.pdf')],
            initialfile=default_filename(report))
        if not filename:
            return
        path = export_pdf(report, filename)
    except Exception:
        messagebox.showerror(tr('report.export_title'), tr('report.export_error'), parent=parent)
        return
    messagebox.showinfo(tr('report.export_title'), tr('report.export_success', path=path), parent=parent)
