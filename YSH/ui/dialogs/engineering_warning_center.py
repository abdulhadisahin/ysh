"""Read-only warning list; owns no engineering or project state."""
import tkinter as tk
from tkinter import ttk
from ui.warning_center_state import MODULE_LABELS
from ui.theme.spacing import MD, SM
from ui.theme import colors


def summary_text(summary, tr):
    return tr('center.summary', completed=summary.completed_count,
              info=summary.info_count, warning=summary.warning_count,
              stale=summary.stale_count, source=summary.source_required_count,
              error=summary.error_count)


class EngineeringWarningCenter:
    def __init__(self, parent, translate):
        self.tr = translate
        self.window = tk.Toplevel(parent)
        self.window.transient(parent)
        self.window.geometry('900x480')
        self.window.minsize(620, 300)
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(2, weight=1)
        self.summary = ttk.Label(self.window, wraplength=840, style='Info.TLabel')
        self.summary.grid(row=0, column=0, sticky='ew', padx=MD, pady=SM)
        self.empty = ttk.Label(self.window, style='Info.TLabel')
        self.empty.grid(row=1, column=0, sticky='w', padx=MD, pady=SM)
        frame = ttk.Frame(self.window)
        frame.grid(row=2, column=0, sticky='nsew', padx=MD)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(frame, columns=('module', 'status', 'message', 'source'), show='headings')
        for column, width in (('module', 170), ('status', 130), ('message', 360), ('source', 180)):
            self.tree.column(column, width=width, minwidth=100, stretch=column=='message')
        for status, color in (('INFO', colors.TEXT_PRIMARY), ('WARNING', colors.GOLD_DARK),
                              ('SOURCE_REQUIRED', colors.GOLD_DARK), ('STALE', colors.WARNING),
                              ('ERROR', colors.ERROR), ('BLOCKED', colors.ERROR)):
            self.tree.tag_configure(status, foreground=color)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vertical = ttk.Scrollbar(frame, orient='vertical', command=self.tree.yview)
        vertical.grid(row=0, column=1, sticky='ns')
        horizontal = ttk.Scrollbar(frame, orient='horizontal', command=self.tree.xview)
        horizontal.grid(row=1, column=0, sticky='ew')
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.detail = tk.Text(self.window, height=4, wrap='word', state='disabled')
        self.detail.grid(row=3, column=0, sticky='ew', padx=MD, pady=SM)
        self.tree.bind('<<TreeviewSelect>>', self._select)
        self.close = ttk.Button(self.window, command=self.window.destroy, style='Neutral.TButton')
        self.close.grid(row=4, column=0, sticky='e', padx=MD, pady=SM)
        self._rows = {}
        self._previous = None

    def render(self, summary, translate):
        self.tr = translate
        self.window.title(translate('center.title'))
        self.summary.configure(text=summary_text(summary, translate))
        self.empty.configure(text=translate('center.empty') if not summary.items else '')
        self.close.configure(text=translate('common.close'))
        for column in ('module', 'status', 'message', 'source'):
            self.tree.heading(column, text=translate('center.' + column))
        rows = tuple((translate(MODULE_LABELS[item.module_id]),
                      translate('center.status.' + item.severity.value),
                      item.detail or translate(item.message_key), item.source, item.severity.value) for item in summary.items)
        if rows == self._previous:
            return
        self._previous = rows
        self.tree.delete(*self.tree.get_children())
        self._rows = {}
        for row in rows:
            identity = self.tree.insert('', 'end', values=(row[0], row[1], row[2].splitlines()[0], row[3]), tags=(row[4],))
            self._rows[identity] = row
        self._select()

    def _select(self, event=None):
        selected = self.tree.selection()
        row = self._rows.get(selected[0]) if selected else None
        self.detail.configure(state='normal')
        self.detail.delete('1.0', 'end')
        if row:
            self.detail.insert('1.0', row[2] + ('\n' + row[3] if row[3] else ''))
        self.detail.configure(state='disabled')
