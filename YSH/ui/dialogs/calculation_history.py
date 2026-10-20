"""Lazy project history and read-only Formula View backed entirely by frozen payloads."""
from __future__ import annotations

from collections.abc import Callable
import json
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from uuid import UUID

from services.snapshot_history_service import SnapshotHistoryService, HistoryError
from ui.widgets.formula_view import FormulaReferencePanel
from ui.widgets.formula_steps import number
from ui.widgets.scrollable_frame import ScrollableFrame


def history_summary(snapshot: object) -> str:
    """Format frozen summary values, never current calculated values."""
    return '; '.join(f"{v['symbol']} = {number(v['value'])} {v['unit']}" for v in snapshot.evidence['summary'])


class CalculationHistoryWindow(tk.Toplevel):
    """No editing, deletion, restoration, or engineering repository lookups."""
    def __init__(self, parent: tk.Misc, service: SnapshotHistoryService,
                 project: Callable[[], UUID | None], translate: Callable[[str],str], owner: object) -> None:
        """Load only the selected project's history when this window is opened."""
        super().__init__(parent)
        self.transient(parent);self.geometry('1180x760');self.minsize(900,550)
        self._service,self._project,self._translate,self._owner=service,project,translate,owner
        self.columnconfigure(0,weight=1);self.rowconfigure(2,weight=1)
        self._notice=ttk.Label(self,wraplength=1100,justify='left')
        self._notice.grid(row=0,column=0,sticky='ew',padx=12,pady=8)
        self._refresh_button=ttk.Button(self,command=self.refresh)
        self._refresh_button.grid(row=1,column=0,sticky='w',padx=12)
        panes=ttk.Panedwindow(self,orient='vertical');panes.grid(row=2,column=0,sticky='nsew',padx=12,pady=8)
        frame=ttk.Frame(panes);frame.rowconfigure(0,weight=1);frame.columnconfigure(0,weight=1)
        self._tree=ttk.Treeview(frame,columns=('date','module','stage','summary','state'),show='headings',selectmode='browse',height=8)
        self._tree.grid(row=0,column=0,sticky='nsew')
        scrollbar=ttk.Scrollbar(frame,orient='vertical',command=self._tree.yview)
        scrollbar.grid(row=0,column=1,sticky='ns');self._tree.configure(yscrollcommand=scrollbar.set)
        horizontal=ttk.Scrollbar(frame,orient='horizontal',command=self._tree.xview)
        horizontal.grid(row=1,column=0,sticky='ew');self._tree.configure(xscrollcommand=horizontal.set)
        for key in ('date','module','stage','summary','state'):
            self._tree.column(key,width=220 if key=='date' else 180 if key!='summary' else 380,
                              minwidth=180 if key=='date' else 120,stretch=True)
        scroll=ScrollableFrame(panes);self._body=scroll.content;self._body.columnconfigure(0,weight=1)
        scroll.set_wheel_active(True)
        panes.add(frame,weight=1);panes.add(scroll,weight=3)
        self._tree.bind('<<TreeviewSelect>>',self._select)
        self._rows={};self._selected_id=None
        owner.register_localizable(self)
        self.protocol('WM_DELETE_WINDOW',self._close)
        self.refresh_texts();self.refresh()

    def refresh_texts(self) -> None:
        """Re-localize frozen evidence without a live value lookup or recomputation."""
        tr=self._translate
        self.title(tr('history.title'));self._refresh_button.configure(text=tr('action.refresh'))
        for key in ('date','module','stage','summary','state'): self._tree.heading(key,text=tr(f'history.{key}'))
        self._render_list()
        self._render_selected()

    def refresh(self) -> None:
        """Explicitly query current-project history; never scan it during application startup."""
        try:
            project_id=self._project()
            snapshots=self._service.list(project_id)
            legacy=self._service.legacy(project_id)
        except HistoryError as error:
            self._notice.configure(text=self._translate(str(error)))
            return
        self._rows={str(s.snapshot_id):s for s in snapshots}
        self._legacy={str(row.id):row for row in legacy}
        self._selected_id=None
        self._notice.configure(text=self._translate('history.readonly')+'\n'+
                               self._translate('history.session' if project_id is None else 'history.frozen'))
        self._render_list();self._render_selected()

    def _render_list(self) -> None:
        for item in self._tree.get_children(): self._tree.delete(item)
        latest=set()
        from engineering.module_registry import MODULES
        names={m.code:m.name_key for m in MODULES}
        for key,snapshot in self._rows.items():
            state='history.latest' if snapshot.module_code not in latest else 'history.historical'
            latest.add(snapshot.module_code)
            self._tree.insert('','end',iid=key,values=(snapshot.created_at.astimezone().isoformat(timespec='seconds'),
                self._translate(names[snapshot.module_code]),self._translate(f'history.stage.{snapshot.stage}'),
                history_summary(snapshot),self._translate(state)))
        for key,row in getattr(self,'_legacy',{}).items():
            self._tree.insert('','end',iid='legacy:'+key,values=(row.created_at.isoformat(),
                self._translate(names.get(row.calculation_type,row.calculation_type)),
                self._translate('history.legacy'),'',''))

    def _select(self, _event: object = None) -> None:
        selected=self._tree.selection()
        self._selected_id=selected[0] if selected else None
        self._render_selected()

    def _render_selected(self) -> None:
        for child in self._body.winfo_children(): child.destroy()
        key=self._selected_id
        if key is None: return
        tr=self._translate
        if key.startswith('legacy:'):
            row=getattr(self,'_legacy',{}).get(key.removeprefix('legacy:'))
            if row is None: return
            ttk.Label(self._body,text=tr('history.incomplete'),wraplength=1050).grid(row=0,column=0,sticky='w')
            self._raw({'inputs':row.inputs,'outputs':row.outputs},1)
            return
        snapshot=self._rows.get(key)
        if snapshot is None: return
        context=snapshot.context
        language=getattr(getattr(tr,'__self__',None),'language','en')
        names=[(ref.name_en or ref.name_tr) if language=='en' else ref.name_tr
               for ref in (context.system,context.circuit,context.fluid) if ref is not None]
        ttk.Label(self._body,text=tr('history.readonly')+'\n'+' · '.join(names)+
                  f'\n{snapshot.created_at.isoformat()} · {snapshot.model_version}',wraplength=1050).grid(row=0,column=0,sticky='w')
        from ui.dialogs.pdf_report import save_snapshot_pdf
        ttk.Button(self._body, text='PDF Raporu Oluştur',
                   command=lambda: save_snapshot_pdf(self, snapshot)).grid(row=3, column=0, sticky='w', pady=8)
        panel=FormulaReferencePanel(self._body,lambda:[],tr,
                                    step_provider=lambda:snapshot.formula_steps,
                                    module_key=snapshot.module_code.value, historical=True)
        panel.grid(row=1,column=0,sticky='ew',pady=8)
        panel.toggle()
        self._raw(snapshot.evidence,2)

    def _raw(self, data: dict, row: int) -> None:
        section=ttk.LabelFrame(self._body,text=self._translate('history.evidence'),padding=8)
        section.grid(row=row,column=0,sticky='ew');section.columnconfigure(0,weight=1)
        content=ScrolledText(section,height=12,wrap='word')
        content.grid(row=1,column=0,sticky='ew')
        content.insert('1.0',json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2))
        content.configure(state='disabled');content.grid_remove()
        def toggle() -> None:
            (content.grid_remove if content.winfo_manager() else content.grid)()
        ttk.Button(section,text=self._translate('history.details'),command=toggle).grid(row=0,column=0,sticky='w')

    def _close(self) -> None:
        self._owner.unregister_localizable(self);self.destroy()
