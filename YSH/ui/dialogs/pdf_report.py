"""Native export interaction; the selected immutable snapshot is the sole input."""
from __future__ import annotations
from tkinter import filedialog, messagebox
from engineering.snapshots.models import CalculationSnapshot


def save_snapshot_pdf(parent: object, snapshot: CalculationSnapshot | None) -> None:
    """Cancel quietly and report export errors without affecting engineering results."""
    if snapshot is None:
        messagebox.showinfo('PDF Raporu', 'Önce başarılı bir hesap kaydı oluşturun.', parent=parent)
        return
    try:
        from reporting.models import adapt_snapshot
        from reporting.export import default_filename, export_pdf
        report = adapt_snapshot(snapshot)
        filename = filedialog.asksaveasfilename(parent=parent, title='PDF Raporu Oluştur',
            defaultextension='.pdf', filetypes=[('PDF Dosyası', '*.pdf')],
            initialfile=default_filename(report))
        if not filename:
            return
        path = export_pdf(report, filename)
    except Exception:
        messagebox.showerror('PDF Raporu',
            'PDF kaydedilemedi. Klasörü, dosya yazma iznini ve boş disk alanını kontrol edin.', parent=parent)
        return
    messagebox.showinfo('PDF Raporu', f'PDF raporu oluşturuldu:\n{path}', parent=parent)
