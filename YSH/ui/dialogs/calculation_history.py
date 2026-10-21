"""Lazy immutable calculation browser. All engineering content comes from frozen records."""
from __future__ import annotations
from collections.abc import Callable
import json
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from uuid import UUID
from services.snapshot_history_service import SnapshotHistoryService, HistoryError
from ui.widgets.formula_view import FormulaReferencePanel
from ui.widgets.scrollable_frame import ScrollableFrame
from ui.widgets.detail_disclosure import DetailDisclosure
from ui.history_presentation import (MODULE_LABELS, scalar, result_text, context_names,
    summary_values, primary_result, stage_label, recorded_checks, recorded_warnings, recorded_state, recorded_sources, frozen_pipe, timestamp)
from ui.theme.history_visuals import configure_history_visuals, HISTORY_SOFT
from ui.theme.pipe_pilot import MODULE_ACCENTS
from ui.theme import colors, typography
from ui.theme.spacing import SM,MD


def history_summary(snapshot: object) -> str:
    """Format only recorded summary values; tolerate absent optional summaries."""
    return '; '.join(result_text(v) for v in summary_values(snapshot.evidence)) or '—'


class CalculationHistoryWindow(tk.Toplevel):
    """Read-only snapshot list and lazy selected details; no engineering reconstruction."""
    def __init__(self,parent:tk.Misc,service:SnapshotHistoryService,
                 project:Callable[[],UUID|None],translate:Callable[[str],str],owner:object)->None:
        super().__init__(parent)
        self.transient(parent);self.geometry('1366x768');self.minsize(900,550)
        self._service,self._project,self._translate,self._owner=service,project,translate,owner
        configure_history_visuals(ttk.Style(self))
        self.configure(background=colors.WORKSPACE_SURFACE)
        self.columnconfigure(0,weight=1);self.rowconfigure(2,weight=1)
        self._rows={};self._legacy={};self._selected_id=None;self._display={};self._formula_panel=None
        self._search=tk.StringVar();self._module=tk.StringVar();self._count=tk.StringVar()
        header=ttk.Frame(self,style='History.Header.TFrame');header.grid(row=0,column=0,sticky='ew',padx=MD,pady=(MD,SM))
        self._title=ttk.Label(header,style='History.Title.TLabel');self._title.grid(row=0,column=0,sticky='w')
        self._subtitle=ttk.Label(header,style='History.Subtitle.TLabel');self._subtitle.grid(row=1,column=0,sticky='w')
        toolbar=ttk.Frame(self,style='History.Card.TFrame');toolbar.grid(row=1,column=0,sticky='ew',padx=MD,pady=(0,SM));toolbar.columnconfigure(1,weight=1)
        self._search_label=ttk.Label(toolbar,style='History.Text.TLabel');self._search_label.grid(row=0,column=0,padx=(0,SM))
        self._search_entry=ttk.Entry(toolbar,textvariable=self._search,style='History.TEntry');self._search_entry.grid(row=0,column=1,sticky='ew')
        self._module_box=ttk.Combobox(toolbar,textvariable=self._module,state='readonly',width=23,style='History.TCombobox');self._module_box.grid(row=0,column=2,padx=SM)
        self._module_box.bind('<<ComboboxSelected>>',lambda event:self._render_list())
        self._refresh_button=ttk.Button(toolbar,command=self.refresh,style='History.Secondary.TButton');self._refresh_button.grid(row=0,column=3)
        self._panes=panes=ttk.Panedwindow(self,orient='horizontal');panes.grid(row=2,column=0,sticky='nsew',padx=MD,pady=(0,SM))
        frame=ttk.Frame(panes,style='History.Card.TFrame');frame.rowconfigure(1,weight=1);frame.columnconfigure(0,weight=1)
        ttk.Label(frame,textvariable=self._count,style='History.Metadata.TLabel').grid(row=0,column=0,sticky='e',pady=(0,SM))
        self._columns=('date','module','system','circuit','summary','state')
        self._tree=ttk.Treeview(frame,columns=self._columns,show='headings',selectmode='browse',height=12,style='History.Treeview')
        self._tree.grid(row=1,column=0,sticky='nsew')
        scrollbar=ttk.Scrollbar(frame,orient='vertical',command=self._tree.yview);scrollbar.grid(row=1,column=1,sticky='ns');self._tree.configure(yscrollcommand=scrollbar.set)
        horizontal=ttk.Scrollbar(frame,orient='horizontal',command=self._tree.xview);horizontal.grid(row=2,column=0,sticky='ew');self._tree.configure(xscrollcommand=horizontal.set)
        for key,width in zip(self._columns,(205,185,130,130,190,160)): self._tree.column(key,width=width,minwidth=100,stretch=key=='summary')
        self._tree.tag_configure('even',background=colors.WHITE);self._tree.tag_configure('odd',background=colors.RESULT_SURFACE)
        for key,accent in MODULE_ACCENTS.items():self._tree.tag_configure(key,foreground=accent)
        self._empty=ttk.Label(self._tree,style='History.Badge.TLabel',wraplength=320,justify='center')
        self._scroll=scroll=ScrollableFrame(panes,style='History.Card.TFrame');self._body=scroll.content
        self._body.configure(style='History.Body.TFrame');self._body.columnconfigure(0,weight=1);scroll.set_wheel_active(True)
        self._body.bind('<Configure>',self._fit_details,add='+')
        panes.add(frame,weight=5);panes.add(scroll,weight=4);panes.bind('<Configure>',self._balance_panes,add='+')
        self._actions=ttk.Frame(self,style='History.Body.TFrame',padding=SM);self._actions.grid(row=3,column=0,sticky='ew',padx=MD)
        self._notice=ttk.Label(self,style='History.Metadata.TLabel',wraplength=950);self._notice.grid(row=4,column=0,sticky='ew',padx=MD,pady=SM)
        self._tree.bind('<<TreeviewSelect>>',self._select)
        self._search.trace_add('write',lambda *args:self._render_list())
        owner.register_localizable(self);self.protocol('WM_DELETE_WINDOW',self._close)
        self.refresh_texts();self.refresh()

    def refresh_texts(self)->None:
        tr=self._translate;self.title(tr('history.title'));self._title.configure(text=tr('history.title'))
        self._subtitle.configure(text=tr('history.visual.subtitle'));self._search_label.configure(text=tr('history.visual.search'))
        self._refresh_button.configure(text=tr('action.refresh'))
        selected=getattr(self,'_module_choices',{}).get(self._module.get())
        self._module_choices={tr('history.visual.all'):None,**{tr(label):key for key,label in MODULE_LABELS.items()}}
        self._module_box.configure(values=tuple(self._module_choices));self._module.set(next(label for label,key in self._module_choices.items() if key==selected))
        for key in self._columns:self._tree.heading(key,text=tr('history.visual.'+key) if key in ('system','circuit') else tr('history.'+key))
        self._display.clear();self._render_list();self._render_selected()

    def refresh(self)->None:
        """Retain the existing explicit current-project history queries."""
        try:
            project_id=self._project();snapshots=self._service.list(project_id);legacy=self._service.legacy(project_id)
        except HistoryError as error:
            self._notice.configure(text=self._translate(str(error)));return
        self._rows={str(s.snapshot_id):s for s in snapshots};self._legacy={str(row.id):row for row in legacy}
        self._selected_id=None;self._display.clear()
        self._notice.configure(text=self._translate('history.readonly')+' '+self._translate('history.session' if project_id is None else 'history.frozen'))
        self._render_list();self._render_selected()

    def _row(self,key,snapshot):
        if key not in self._display:
            evidence=snapshot.evidence
            lang=getattr(getattr(self._translate,'__self__',None),'language','tr')
            context=context_names(evidence,lang)
            label=self._translate(MODULE_LABELS.get(snapshot.module_code,'history.module'))
            stage=stage_label(snapshot.stage,self._translate)
            self._display[key]=(timestamp(snapshot.created_at),label+(' · '+stage if stage!='—' else ''),
                context[0],context[1],primary_result(snapshot.module_code,evidence),recorded_state(evidence,self._translate))
        return self._display[key]

    def _render_list(self)->None:
        if not hasattr(self,'_module_choices'):return
        for item in self._tree.get_children():self._tree.delete(item)
        query=self._search.get().strip().casefold();module=self._module_choices.get(self._module.get());latest=set();visible=[]
        for key,snapshot in self._rows.items():
            state='history.latest' if snapshot.module_code not in latest else 'history.historical';latest.add(snapshot.module_code)
            if module and snapshot.module_code!=module:continue
            frozen=self._row(key,snapshot);values=frozen[:-1]+(frozen[-1]+' · '+self._translate(state),)
            if query and query not in ' '.join(str(v) for v in values).casefold():continue
            self._tree.insert('','end',iid=key,tags=('even' if len(visible)%2==0 else 'odd',snapshot.module_code.value),values=values);visible.append(key)
        for key,row in self._legacy.items():
            if module and row.calculation_type!=module:continue
            values=(row.created_at.strftime('%d.%m.%Y · %H:%M:%S %z'),self._translate(MODULE_LABELS.get(row.calculation_type,'history.legacy')),'—','—','—',self._translate('history.legacy'))
            if query and query not in ' '.join(values).casefold():continue
            iid='legacy:'+key;self._tree.insert('','end',iid=iid,values=values);visible.append(iid)
        self._count.set(f"{len(visible)} {self._translate('history.visual.records')}")
        if visible:self._empty.place_forget()
        else:
            self._empty.configure(text=self._translate('history.visual.no_results' if query or module else 'history.visual.empty'));self._empty.place(relx=.5,rely=.5,anchor='center')
        if self._selected_id in visible:self._tree.selection_set(self._selected_id)
        elif self._selected_id is not None:self._selected_id=None;self._render_selected()

    def _select(self,_event:object=None)->None:
        selected=self._tree.selection();key=selected[0] if selected else None
        if key==self._selected_id:return
        self._selected_id=key;self._render_selected()

    def _section(self,key,row):
        frame=ttk.LabelFrame(self._body,text=self._translate('history.visual.'+key),style='History.Section.TLabelframe')
        frame.grid(row=row,column=0,sticky='ew',pady=(0,SM));frame.columnconfigure(0,weight=1);return frame

    def _text(self,parent,text,style='History.Text.TLabel',row=0):
        label=ttk.Label(parent,text=text,style=style,wraplength=320,justify='left');label.grid(row=row,column=0,sticky='ew',pady=2);return label

    def _render_selected(self)->None:
        for child in self._body.winfo_children():child.destroy()
        for child in self._actions.winfo_children():child.destroy()
        self._formula_panel=None;self._pdf_button=None;tr=self._translate;key=self._selected_id
        if key is None:self._text(self._body,tr('history.visual.select'));return
        if key.startswith('legacy:'):
            row=self._legacy.get(key.removeprefix('legacy:'))
            if row is None:return
            self._text(self._body,tr('history.visual.readonly'),'History.Badge.TLabel')
            self._text(self._body,tr('history.incomplete'),row=1);self._raw({'inputs':row.inputs,'outputs':row.outputs},2);return
        snapshot=self._rows.get(key)
        if snapshot is None:return
        evidence=snapshot.evidence;module=snapshot.module_code.value
        title=tr(MODULE_LABELS[module]);stage=stage_label(snapshot.stage,tr)
        self._text(self._body,title+(' · '+stage if stage!='—' else ''),'History.'+module+'.TLabel')
        self._text(self._body,tr('history.visual.readonly'),'History.Badge.TLabel',1)
        self._text(self._body,primary_result(module,evidence),'History.'+module+'.Result.TLabel',2)
        summary=self._section('results',3)
        self._text(summary,'\n'.join(result_text(v) for v in summary_values(evidence)) or '—')
        context=self._section('context',4)
        lang=getattr(getattr(tr,'__self__',None),'language','tr')
        names=context_names(evidence,lang)
        self._text(context,'\n'.join(f"{tr('history.visual.'+key)}: {name}" for key,name in zip(('system','circuit','fluid'),names)))
        for index,(name,value) in enumerate(frozen_pipe(evidence),1):
            if name=='mode':value=tr('discharge.pipe.linked' if value=='LINKED' else 'discharge.pipe.manual')
            elif name=='status':value=tr('discharge.pipe.status.'+value)
            self._text(context,f"{tr('history.visual.pipe_'+name)}: {scalar(value)}",row=index)
        status=self._section('status',5);checks=recorded_checks(evidence)
        for i,check in enumerate(checks):self._text(status,tr('formula2.check.'+check['status']),row=i)
        if not checks:self._text(status,tr('history.visual.no_status'))
        for i,finding in enumerate(recorded_warnings(evidence),len(checks)+1):
            if finding.get('recorded_text'):
                self._text(status,finding['recorded_text'],'History.Warning.TLabel',i);continue
            code=finding.get('code','');message=tr('history.visual.velocity_warning' if code.startswith('velocity.') else 'warning.npsh.message' if code=='npsh.available_not_above_required' else 'history.visual.stored_warning')
            numbers=' · '.join(f"{tr('history.visual.'+name)}: {scalar(finding.get(field))} {finding.get('unit') or ''}" for name,field in (('actual','actual_value'),('lower','lower_bound'),('upper','upper_bound')) if finding.get(field) is not None)
            role='Critical' if finding.get('severity') in ('ERROR','CRITICAL_WARNING') else 'Warning'
            self._text(status,message+('\n'+numbers if numbers else ''),'History.'+role+'.TLabel',i)
        sources=recorded_sources(evidence)
        provenance=DetailDisclosure(self._body,tr('history.visual.sources'),tr('history.visual.sources_hint'),style='History.Body.TFrame',body_style='History.Body.TFrame',summary_style='History.Metadata.TLabel')
        provenance.grid(row=6,column=0,sticky='ew',pady=(0,SM))
        if not sources:self._text(provenance.body,'—')
        for i,source in enumerate(sources):
            text=' · '.join(tr('formula2.'+name+'.'+source[name]) for name in ('source_type','verification_status') if source.get(name))
            self._text(provenance.body,text or '—',row=i)
        overrides=[v for step in evidence.get('steps',()) for v in step.get('used_values',()) if v.get('override_reason')]
        for i,value in enumerate(overrides,len(sources)):
            text=f"{tr('formula2.overridden')} · {value.get('symbol') or ''}\n{tr('formula2.recommended')}: {scalar(value.get('recommended_value'))} · {tr('formula2.used')}: {scalar(value.get('used_value'))}\n{value['override_reason']}"
            self._text(provenance.body,text,row=i)
        metadata=self._section('record',7)
        self._text(metadata,timestamp(snapshot.created_at)+'\n'+tr('history.visual.record_id')+': '+str(snapshot.snapshot_id)[:8]+'…\n'+scalar(snapshot.model_version),'History.Metadata.TLabel')
        self._raw(snapshot.to_payload(),8)
        self._formula_panel=panel=FormulaReferencePanel(self._actions,lambda:[],tr,
            toggle_button_factory=lambda parent,text,command:ttk.Button(parent,text=text,command=command,style='History.Primary.TButton'),
            step_provider=lambda:snapshot.formula_steps,
            module_key=snapshot.module_code.value, historical=True, separate_window=True)
        panel.grid(row=0,column=0,sticky='w')
        from ui.dialogs.pdf_report import save_snapshot_pdf
        self._pdf_button=ttk.Button(self._actions,text=tr('history.visual.pdf'),style='History.Secondary.TButton',command=lambda:save_snapshot_pdf(self,snapshot))
        self._pdf_button.grid(row=0,column=1,sticky='w',padx=SM)

    def _raw(self,data:dict,row:int)->None:
        section=ttk.LabelFrame(self._body,text=self._translate('history.evidence'),style='History.Section.TLabelframe')
        section.grid(row=row,column=0,sticky='ew');section.columnconfigure(0,weight=1)
        holder=[]
        def toggle():
            if not holder:
                content=ScrolledText(section,height=10,width=30,wrap='word');content.grid(row=1,column=0,sticky='ew')
                content.insert('1.0',json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2));content.configure(state='disabled');holder.append(content)
            else:(holder[0].grid_remove if holder[0].winfo_manager() else holder[0].grid)()
        ttk.Button(section,text=self._translate('history.details'),command=toggle,style='History.Secondary.TButton').grid(row=0,column=0,sticky='w')

    def _fit_details(self,_event=None):
        width=max(160,self._scroll.canvas.winfo_width()-48)
        def fit(parent):
            for child in parent.winfo_children():
                if isinstance(child,ttk.Label) and abs(int(float(child.cget('wraplength') or 0))-width)>8:child.configure(wraplength=width)
                fit(child)
        fit(self._body)

    def _balance_panes(self,event):
        if event.width<800 or getattr(self,'_pane_width',None)==event.width:return
        self._pane_width=event.width;self._panes.sashpos(0,round(event.width*.55))

    def _close(self)->None:
        self._owner.unregister_localizable(self);self.destroy()
