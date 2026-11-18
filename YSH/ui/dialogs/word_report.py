"""Native save dialog for a frozen editable Word report."""
from tkinter import filedialog,messagebox
from engineering.snapshots.models import CalculationSnapshot


def save_snapshot_word(parent, snapshot: CalculationSnapshot | None, *, translate=None):
    from i18n.translator import Translator
    tr=translate or getattr(parent,'_translate',None) or getattr(parent,'tr',None) or Translator('tr').translate
    language=getattr(getattr(tr,'__self__',None),'language','tr')
    if snapshot is None:
        messagebox.showinfo(tr('word.export_title'),tr('report.no_snapshot'),parent=parent);return
    try:
        from reporting.models import adapt_snapshot
        from reporting.word_export import default_word_filename,export_word
        report=adapt_snapshot(snapshot,language)
        filename=filedialog.asksaveasfilename(parent=parent,title=tr('word.export_title'),defaultextension='.docx',
            filetypes=[('Word document','*.docx')],initialfile=default_word_filename(report))
        if not filename:return
        path=export_word(report,filename)
    except Exception:
        messagebox.showerror(tr('word.export_title'),tr('word.export_error'),parent=parent);return
    messagebox.showinfo(tr('word.export_title'),tr('word.export_success',path=path),parent=parent)
