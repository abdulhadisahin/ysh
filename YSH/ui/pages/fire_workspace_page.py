"""Live Fire views consume application results, never engineering equations."""
import tkinter as tk
from tkinter import ttk
from collections.abc import Mapping

from engineering.fire.enums import FireSourceStatus
from engineering.fire.hazen_williams_workflow import HWService
from engineering.pipe_design.transfer import PipeInputMode, PipeLinkStatus
from engineering.validation import ValidationError
from services.fire_hazen_williams_service import HWApplicabilityBlocked
from services.fire_workspace import FireWorkspace, FOAM_FIELDS, HW_FIELDS
from ui.theme.fire_visuals import configure_fire_visuals
from ui.widgets.scrollable_page_host import ScrollablePageHost
from ui.widgets.formula_view import FormulaReferencePanel
from ui.widgets.detail_disclosure import DetailDisclosure
from ui.widgets.formula_steps import number
from ui.fire_input_presentation import foam_percent_clarifications
from ui.widgets.fire_library_inputs import FireLibraryInputPanel


class _FireSubviews(Mapping):
    """Stable two-view lookup; indexing creates once, passive refresh uses created only."""
    def __init__(self,workspace):
        self.workspace=workspace
        self.created={}

    def __iter__(self):return iter(('foam','hw'))
    def __len__(self):return 2

    def __getitem__(self,kind):
        if kind not in ('foam','hw'):raise KeyError(kind)
        if kind not in self.created:
            view=FireCalculatorPage(self.workspace._slots[kind],self.workspace,kind)
            view.pack(fill='x',expand=True)
            self.created[kind]=view
        return self.created[kind]


class FireWorkspacePage(ttk.Frame):
    """One cached family workspace; both subviews share existing shell services."""
    def __init__(self,parent,translate,*,sources,context,project,on_snapshot,on_dirty,state=None,library=None):
        super().__init__(parent,style='Fire.TFrame')
        configure_fire_visuals(ttk.Style(self))
        self.tr=translate;self.sources=sources;self.context_provider=context;self.project_provider=project
        self.on_snapshot=on_snapshot;self.on_dirty=on_dirty
        self._library_provider=library;self._library_service=None
        self.model=FireWorkspace.from_state(state or {})
        self.columnconfigure(0,weight=1);self.rowconfigure(1,weight=1)
        self.title=ttk.Label(self,style='Fire.Title.TLabel');self.title.grid(row=0,column=0,sticky='w',padx=12,pady=8)
        self.host=ScrollablePageHost(self);self.host.grid(row=1,column=0,sticky='nsew')
        self._slots={kind:self.host.add_scrollable_page('',lambda parent:ttk.Frame(parent,style='Fire.TFrame'),kind)
                     for kind in ('foam','hw')}
        self.views=_FireSubviews(self)
        self.host.select(self.host._page_keys[self.model.active])
        self.views[self.model.active]
        self.host.bind('<<NotebookTabChanged>>',self._active,add='+')
        self.sources.subscribe(self.observe)
        self.refresh_texts();self.observe()

    def _active(self,event=None):
        active=next((key for key,host in self.host._page_keys.items() if str(host)==self.host.select()),'foam')
        self.views[active]
        if self.model.active!=active:self.model.active=active;self.on_dirty()

    def refresh_texts(self):
        self.title.configure(text=self.tr('fire.system'))
        for kind in self.views:self.host.set_page_title(kind,self.tr('fire.ui.'+kind))
        for view in tuple(self.views.created.values()):view.refresh_texts()

    def observe(self):
        self.model.set_context(self.context_provider())
        snap=self.model.pipe.snapshot
        if snap:
            current=next((s for s in self.sources.available() if s.selection_id==snap.source_selection_id),None)
            self.model.observe(current)
        for view in tuple(self.views.created.values()):view.sync()

    def library_service(self):
        if self._library_service is None and self._library_provider is not None:
            self._library_service=self._library_provider()
        return self._library_service

    def refresh_library(self):
        for view in tuple(self.views.created.values()):view.library_panel.refresh()

    def export_state(self):return self.model.export_state()

    def load_state(self,state):
        self.model=FireWorkspace.from_state(state)
        self.views[self.model.active]
        for view in tuple(self.views.created.values()):view.load_fields()
        self.host.select(self.host._page_keys[self.model.active]);self.observe()

    def clear_state(self):self.load_state({})


class FireCalculatorPage(ttk.Frame):
    def __init__(self,parent,workspace,kind):
        super().__init__(parent,style='Fire.TFrame',padding=12)
        self.workspace=workspace;self.kind=kind;self.tr=workspace.tr;self.loading=True
        self.spec=FOAM_FIELDS if kind=='foam' else HW_FIELDS
        self.columnconfigure(0,weight=1)
        self.input_card=ttk.LabelFrame(self,style='Fire.Card.TLabelframe');self.input_card.grid(row=0,column=0,sticky='ew',pady=6)
        self.input_card.columnconfigure(1,weight=1)
        self.variables={};self.labels={};self.entries={};self.meta_vars={};self.status_boxes={};self.meta_editors={}
        for index,(name,(key,unit)) in enumerate(self.spec.items()):
            self.labels[name]=ttk.Label(self.input_card,style='Fire.TLabel')
            self.labels[name].grid(row=index,column=0,sticky='w',padx=(0,12),pady=5)
            variable=tk.StringVar(self);self.variables[name]=variable
            entry=ttk.Entry(self.input_card,textvariable=variable,width=18);entry.grid(row=index,column=1,sticky='ew',pady=5)
            self.entries[name]=entry
            ttk.Label(self.input_card,text=unit,style='Fire.TLabel').grid(row=index,column=2,padx=8)
            variable.trace_add('write',lambda *_,n=name:self._edit(n))
        self.clarifications=()
        if kind=='foam':
            self.concentration_help=ttk.Label(self.input_card,style='Fire.TLabel',wraplength=540)
            self.concentration_help.grid(row=4,column=0,columnspan=3,sticky='ew',pady=(3,5))
            self.concentration_warning=ttk.Label(self.input_card,style='Fire.Status.TLabel',wraplength=540)
            self.concentration_warning.grid(row=5,column=0,columnspan=3,sticky='ew',pady=4)
            self.concentration_warning.grid_remove()
        self.scope=ttk.Label(self,style='Fire.TLabel',wraplength=540);self.scope.grid(row=1,column=0,sticky='ew',pady=6)
        if kind=='hw':self._link_controls()
        self.disclosure=DetailDisclosure(self,'','',style='Fire.TFrame',body_style='Fire.TFrame')
        self.disclosure.grid(row=3,column=0,sticky='ew',pady=6)
        self.disclosure.body.columnconfigure(0,weight=1)
        self.meta_labels=[];self.meta_groups={};self.meta_reason_controls={}
        for index,name in enumerate(self.spec):
            group=ttk.LabelFrame(self.disclosure.body,style='Fire.Card.TLabelframe');group.grid(row=index,column=0,sticky='ew',pady=4)
            group.columnconfigure(1,weight=1);self.meta_labels.append((group,self.spec[name][0]))
            self.meta_vars[name]={};self.meta_editors[name]={};self.meta_groups[name]=group
            for row,field in enumerate(('status','document','recommended','reason')):
                label=ttk.Label(group,style='Fire.TLabel');label.grid(row=row,column=0,sticky='w',padx=(0,8),pady=3)
                self.meta_labels.append((label,'fire.ui.recommended_percent' if kind=='foam' and name=='foam_fraction' and field=='recommended' else 'fire.ui.'+field))
                variable=tk.StringVar(self);self.meta_vars[name][field]=variable
                if field=='status':
                    widget=ttk.Combobox(group,textvariable=variable,state='readonly',width=34)
                    self.status_boxes[name]=widget
                else:widget=ttk.Entry(group,textvariable=variable)
                widget.grid(row=row,column=1,sticky='ew',pady=3)
                self.meta_editors[name][field]=widget
                if field=='reason':self.meta_reason_controls[name]=(label,widget)
                variable.trace_add('write',lambda *_,n=name,f=field:self._meta(n,f))
        self.library_panel=FireLibraryInputPanel(self.input_card,self)
        self.library_panel.grid(row=6,column=0,columnspan=3,sticky='ew',pady=4)
        self.actions=ttk.Frame(self,style='Fire.TFrame');self.actions.grid(row=4,column=0,sticky='ew',pady=8)
        self.calculate_button=ttk.Button(self.actions,style='Fire.Primary.TButton',command=self.calculate);self.calculate_button.grid(row=0,column=0,padx=(0,8))
        self.clear_button=ttk.Button(self.actions,style='Fire.Secondary.TButton',command=self.clear);self.clear_button.grid(row=0,column=1)
        self.pdf_button=ttk.Button(self.actions,style='Fire.Secondary.TButton',command=self.pdf,state='disabled');self.pdf_button.grid(row=0,column=2,padx=8)
        self.status=ttk.Label(self,style='Fire.Status.TLabel',wraplength=540);self.status.grid(row=6,column=0,sticky='ew',pady=6)
        self.result_card=ttk.Frame(self,style='Fire.Result.TFrame');self.result_card.grid(row=5,column=0,sticky='ew',pady=8)
        self.result_card.columnconfigure(0,weight=1)
        self.result_labels=[]
        for index in range(4 if kind=='foam' else 2):
            label=ttk.Label(self.result_card,style='Fire.Result.TLabel' if index==0 else 'Fire.Support.TLabel',wraplength=540)
            label.grid(row=index,column=0,sticky='ew',pady=4);self.result_labels.append(label)
        self.formula=FormulaReferencePanel(self,lambda:[],self.tr,step_provider=self.steps,
            module_key='fire_foam_system' if kind=='foam' else 'fire_hazen_williams',separate_window=True)
        self.formula.grid(row=7,column=0,sticky='ew',pady=6)
        self.load_fields();self.loading=False

    @property
    def model(self):return self.workspace.model

    def _link_controls(self):
        self.link=ttk.LabelFrame(self,style='Fire.Card.TLabelframe');self.link.grid(row=2,column=0,sticky='ew',pady=6)
        self.link.columnconfigure(1,weight=1)
        self.service_var=tk.StringVar(self);self.mode_var=tk.StringVar(self);self.source_var=tk.StringVar(self)
        self.link_labels=[]
        for row,key in enumerate(('service','mode','pipe')):
            label=ttk.Label(self.link,style='Fire.TLabel');label.grid(row=row,column=0,sticky='w',padx=(0,8));self.link_labels.append((label,'fire.ui.'+key))
        self.service_box=ttk.Combobox(self.link,textvariable=self.service_var,state='readonly');self.service_box.grid(row=0,column=1,sticky='ew',pady=4)
        self.mode_box=ttk.Combobox(self.link,textvariable=self.mode_var,state='readonly');self.mode_box.grid(row=1,column=1,sticky='ew',pady=4)
        self.source_box=ttk.Combobox(self.link,textvariable=self.source_var,state='readonly');self.source_box.grid(row=2,column=1,sticky='ew',pady=4)
        self.service_box.bind('<<ComboboxSelected>>',self._service);self.mode_box.bind('<<ComboboxSelected>>',self._mode)
        buttons=ttk.Frame(self.link,style='Fire.TFrame');buttons.grid(row=3,column=0,columnspan=2,sticky='w')
        self.link_buttons=[]
        for col,action in enumerate(('link','update','keep')):
            button=ttk.Button(buttons,command=lambda a=action:self.pipe_action(a));button.grid(row=0,column=col,padx=(0,6),pady=6);self.link_buttons.append((button,'fire.ui.'+action))
        self.pipe_status=ttk.Label(self.link,style='Fire.TLabel',wraplength=540);self.pipe_status.grid(row=4,column=0,columnspan=2,sticky='ew',pady=4)

    def _edit(self,name):
        if self.loading:return
        if self.kind=='foam' and name=='foam_fraction':self.entries[name].state(['!invalid'])
        self.model.set_field(self.kind,name,self.variables[name].get());self._dirty()

    def _meta(self,name,field):
        if self.loading:return
        text=self.meta_vars[name][field].get()
        if field=='status':
            text=self.source_choices.get(text,'SOURCE_REQUIRED')
            if name not in self.model.library_inputs.links and text in ('SOURCE_VERIFIED','SOURCE_VERIFIED_CONTEXT_DEPENDENT','DERIVED_FROM_VERIFIED_RULE'):
                text='SOURCE_REQUIRED'
                self.loading=True;self.meta_vars[name][field].set(self.tr('fire.ui.source.SOURCE_REQUIRED'));self.loading=False
        self.model.metadata[self.kind][name][field]=text;self.model.invalidate(self.kind);self._dirty()

    def _dirty(self):
        self.workspace.on_dirty();self.sync(message='fire.ui.changed')

    def _service(self,event=None):
        self.model.service=self.service_choices[self.service_var.get()];self.model.invalidate('hw');self._dirty()
        self.library_panel.refresh()

    def _mode(self,event=None):
        self.model.mode=self.mode_choices[self.mode_var.get()]
        if self.model.mode is PipeInputMode.MANUAL:self.model.pipe=self.model.pipe.to_manual()
        self.model.invalidate('hw');self._dirty()

    def pipe_action(self,action):
        selection=(self.source_choices_pipe.get(self.source_var.get()) if action=='link' else
            next((s for s in self.workspace.sources.available() if self.model.pipe.snapshot and s.selection_id==self.model.pipe.snapshot.source_selection_id),None))
        if selection is None and action!='keep':self.sync(message='fire.ui.pipe_missing');return
        try:self.model.use_pipe(selection,action)
        except ValueError:self.sync(message='fire.ui.pipe_missing');return
        self.load_fields();self._dirty()

    def load_fields(self):
        previous=self.loading;self.loading=True
        for name,value in self.model.fields[self.kind].items():self.variables[name].set(value)
        self.loading=previous
        self.refresh_texts()

    def calculate(self):
        self.model.set_context(self.workspace.context_provider())
        self.library_panel.refresh()
        for entry in self.entries.values():entry.state(['!invalid'])
        try:
            result=self.model.calculate(self.kind,project_id=self.workspace.project_provider())
        except HWApplicabilityBlocked:
            self.sync(message='fire.ui.blocked');return
        except ValidationError as error:
            field=error.issue.field_key or ''
            name=field if field in self.spec else next((n for n,(key,_) in self.spec.items() if key==field),None)
            if field in ('percent','fraction'):name='foam_fraction'
            label=self.tr(self.spec[name][0]) if name in self.spec else ''
            if name in self.entries:
                self.entries[name].state(['invalid']);self.entries[name].focus_set()
            self.sync(message='fire.ui.invalid');self.status.configure(text=self.tr('fire.ui.invalid')+' '+label);return
        except (ValueError,TypeError):self.sync(message='fire.ui.invalid');return
        self.sync()
        try:self.workspace.on_snapshot(self.model.snapshots[self.kind])
        except Exception:self.status.configure(text=self.tr('history.persistence_failed'))

    def steps(self):
        result=self.model.results[self.kind]
        return result.formula_steps if result else ()

    def pdf(self):
        snapshot=self.model.snapshots[self.kind]
        if snapshot is not None:
            from ui.dialogs.pdf_report import save_snapshot_pdf
            save_snapshot_pdf(self,snapshot)

    def clear(self):
        fresh=FireWorkspace()
        self.model.fields[self.kind]=fresh.fields[self.kind];self.model.metadata[self.kind]=fresh.metadata[self.kind]
        if self.kind=='hw':self.model.pipe=fresh.pipe;self.model.mode=fresh.mode;self.model.service=fresh.service
        self.model.library_inputs.contexts[self.kind]=''
        for name in self.library_panel.names:
            self.model.library_inputs.links.pop(name,None);self.model.library_inputs.stale.pop(name,None);self.model.library_inputs.kept.pop(name,None)
        self.model.invalidate(self.kind);self.load_fields();self.workspace.on_dirty();self.sync()

    def sync(self,message=None):
        if hasattr(self,'library_panel'):self.library_panel.sync()
        if self.kind=='foam':
            self.clarifications=foam_percent_clarifications(self.variables['foam_fraction'].get())
            if self.clarifications:
                self.concentration_warning.configure(text=self.tr(self.clarifications[0].message_key))
                self.concentration_help.grid_remove()
                self.concentration_warning.grid()
            else:
                self.concentration_warning.grid_remove()
                self.concentration_help.grid()
        result=self.model.results[self.kind]
        state='normal' if result else 'disabled'
        self.pdf_button.configure(state=state);self.formula._toggle.configure(state=state)
        if not result:
            if self.formula.expanded:self.formula.toggle()
            for label in self.result_labels:label.configure(text='—')
            self.status.configure(text=self.tr(message or 'fire.ui.empty'))
        else:
            rows=list(result.summary)
            rows.sort(key=lambda r:r.key!=result.primary_result_key)
            for label,row in zip(self.result_labels,rows):
                label.configure(text=self.tr(row.label_key)+'\n'+row.symbol+' = '+number(row.value)+' '+row.unit)
            messages=tuple(dict.fromkeys(self.tr(m.message_key) for m in result.warnings))
            self.status.configure(text='\n'.join(messages) or self.tr('fire.ui.calculated'))
        if self.kind=='hw':
            previous=self.loading;self.loading=True
            self.service_var.set(next(k for k,v in self.service_choices.items() if v==self.model.service))
            self.mode_var.set(next(k for k,v in self.mode_choices.items() if v==self.model.mode))
            readonly=self.model.mode is PipeInputMode.LINKED
            for name in ('flow_lpm','inside_diameter_mm'):self.entries[name].configure(state='readonly' if readonly else 'normal')
            current=self.source_var.get()
            self.source_choices_pipe={f'{s.selected_standard_code or ""} · Di {number(s.actual_internal_diameter_mm)} mm · r{s.revision} · {str(s.selection_id)[:8]}':s for s in self.workspace.sources.available()}
            self.source_box.configure(values=tuple(self.source_choices_pipe))
            if current not in self.source_choices_pipe:self.source_var.set(next(iter(self.source_choices_pipe),''))
            snap=self.model.pipe.snapshot
            self.pipe_status.configure(text=(self.tr('discharge.pipe.status.'+self.model.pipe.status.value)+
                f' · Di {number(snap.values.actual_internal_diameter_mm)} mm · '+self.tr('fire.ui.revision')+f' {snap.source_revision}'
                if snap and readonly else self.tr('fire.ui.pipe_missing') if readonly else self.tr('fire.value.MANUAL')))
            self.loading=previous

    def refresh_texts(self):
        self.input_card.configure(text=self.tr('fire.ui.inputs'))
        if self.kind=='foam':self.concentration_help.configure(text=self.tr('fire.ui.percent_help'))
        for name,(key,unit) in self.spec.items():self.labels[name].configure(text=self.tr(key))
        self.library_panel.refresh_texts()
        self.scope.configure(text=self.tr('fire.ui.mixture' if self.kind=='foam' else 'fire.ui.water_scope'))
        self.disclosure._title=self.tr('fire.ui.provenance')
        self.disclosure._toggle.configure(text=('▾ ' if self.disclosure.expanded else '▸ ')+self.disclosure._title)
        for widget,key in self.meta_labels:widget.configure(text=self.tr(key))
        self.source_choices={self.tr('fire.ui.source.'+s.value):s.value for s in (
            FireSourceStatus.USER_PROJECT_ASSUMPTION,FireSourceStatus.SOURCE_REQUIRED,
            FireSourceStatus.WORKBOOK_REFERENCE_ONLY,FireSourceStatus.SOURCE_VERIFIED_CONTEXT_DEPENDENT,
            FireSourceStatus.SOURCE_CONFLICT,FireSourceStatus.SOURCE_IDENTIFIED_BUT_NOT_ACCESSIBLE,
            FireSourceStatus.NOT_CONFIGURED,FireSourceStatus.OUT_OF_SCOPE,FireSourceStatus.SOURCE_VERIFIED,
            FireSourceStatus.DERIVED_FROM_VERIFIED_RULE)}
        previous=self.loading;self.loading=True
        for name,box in self.status_boxes.items():
            box.configure(values=tuple(self.source_choices))
            for field,var in self.meta_vars[name].items():
                value=self.model.metadata[self.kind][name][field]
                var.set(next(k for k,v in self.source_choices.items() if v==value) if field=='status' else value)
        self.loading=previous
        for button,key in ((self.calculate_button,'fire.ui.calculate'),(self.clear_button,'fire.ui.clear'),(self.pdf_button,'fire.ui.pdf')):button.configure(text=self.tr(key))
        if self.kind=='hw':
            self.service_choices={self.tr('fire.value.'+s.value):s for s in HWService}
            self.mode_choices={self.tr('fire.value.'+s.value):s for s in PipeInputMode}
            self.service_box.configure(values=tuple(self.service_choices));self.mode_box.configure(values=tuple(self.mode_choices))
            for widget,key in self.link_labels+self.link_buttons:widget.configure(text=self.tr(key))
        self.formula.refresh_texts();self.sync()
