"""One modeless, lazy engineering library workspace behind existing entry points."""
from __future__ import annotations

from dataclasses import fields
from enum import Enum
import tkinter as tk
from tkinter import ttk
from uuid import UUID
from collections.abc import Callable

from engineering.provenance import SourceType, VerificationStatus
from services.engineering_library_service import EngineeringLibraryService, LibraryError
from services.library_catalog import CATEGORIES, CATEGORY_BY_CODE, PROPERTY_CODES
from ui.library_controller import LibraryController, EditMode
from ui.widgets.scrollable_frame import ScrollableFrame
from ui.widgets.formula_steps import number, source_rows


def record_label(record: object, translate: Callable[[str], str] | None = None) -> str:
    """Use engineering identities in pickers rather than prominently showing UUIDs."""
    if hasattr(record,'reference'):
        source=record.reference
        kind=translate(f'formula2.source_type.{source.source_type.value}') if translate else source.source_type.value
        return ' · '.join(str(v) for v in (kind,source.source_organization,source.document,source.revision) if v)
    if hasattr(record,'outside_diameter_mm'):
        return f'{record.standard} · {record.nominal_diameter} · OD {record.outside_diameter_mm} / s {record.wall_thickness_mm} / ID {record.inside_diameter_mm} mm'
    if hasattr(record,'property_name'):
        label=f'{record.property_name} · {record.value} {record.unit}'
        if record.reference_temperature_c is not None: label+=f' · {record.reference_temperature_c} °C'
        return label
    return ' · '.join(str(getattr(record,key)) for key in
        ('code','designation','nominal_diameter','name_tr','display_name','ship_name','property_name')
        if getattr(record,key,None) is not None) or str(getattr(record,'id',''))


class EngineeringLibraryWorkspace(tk.Toplevel):
    """Browse first; an explicit editor draft never autosaves or modifies project data."""
    def __init__(self, parent: tk.Misc, service: EngineeringLibraryService,
                 translate: Callable[[str], str], owner: object, category: str = 'systems') -> None:
        """Load only the initial category after the user opens Libraries."""
        super().__init__(parent)
        self.transient(parent)
        self.geometry('1120x740');self.minsize(900,560)
        self._controller=LibraryController(service)
        self._translate=translate;self._owner=owner
        self._group=tk.StringVar();self._category=tk.StringVar();self._parent=tk.StringVar()
        self._search=tk.StringVar();self._active=tk.StringVar();self._ownership=tk.StringVar();self._verification=tk.StringVar()
        self._status=tk.StringVar();self._edit_vars={};self._edit_choices={}
        self._choice_cache={};self._row_map={}
        self.columnconfigure(0,weight=1);self.rowconfigure(1,weight=1)
        top=ttk.Frame(self,padding=10);top.grid(row=0,column=0,sticky='ew')
        for column in range(3): top.columnconfigure(column, weight=1)
        self._group_box=ttk.Combobox(top,textvariable=self._group,state='readonly',width=28)
        self._group_box.grid(row=0,column=0,sticky='ew',padx=(0,8))
        self._category_box=ttk.Combobox(top,textvariable=self._category,state='readonly',width=30)
        self._category_box.grid(row=0,column=1,sticky='ew',padx=(0,8))
        self._parent_box=ttk.Combobox(top,textvariable=self._parent,state='readonly',width=30)
        self._parent_box.grid(row=0,column=2,sticky='ew')
        self._group_box.bind('<<ComboboxSelected>>',self._choose_group)
        self._category_box.bind('<<ComboboxSelected>>',self._choose_category)
        self._parent_box.bind('<<ComboboxSelected>>',self._choose_parent)
        self._search_label=ttk.Label(top);self._search_label.grid(row=1,column=0,sticky='w',pady=(8,0))
        ttk.Entry(top,textvariable=self._search).grid(row=2,column=0,sticky='ew',padx=(0,8))
        filters=ttk.Frame(top);filters.grid(row=2,column=1,columnspan=2,sticky='ew')
        self._filter_boxes=[]
        for col,var in enumerate((self._active,self._ownership,self._verification)):
            box=ttk.Combobox(filters,textvariable=var,state='readonly',width=21)
            box.grid(row=0,column=col,padx=(0,6));box.bind('<<ComboboxSelected>>',lambda _:self._render_rows())
            self._filter_boxes.append(box)
        panes=ttk.Panedwindow(self,orient='horizontal');panes.grid(row=1,column=0,sticky='nsew',padx=10)
        listing=ttk.Frame(panes);listing.columnconfigure(0,weight=1);listing.rowconfigure(0,weight=1)
        self._tree=ttk.Treeview(listing,columns=('name','value','ownership','active'),show='headings',selectmode='browse')
        self._tree.grid(row=0,column=0,sticky='nsew')
        scrollbar=ttk.Scrollbar(listing,orient='vertical',command=self._tree.yview)
        scrollbar.grid(row=0,column=1,sticky='ns');self._tree.configure(yscrollcommand=scrollbar.set)
        for key in ('name','value','ownership','active'): self._tree.column(key,width=130,stretch=True)
        self._tree.bind('<<TreeviewSelect>>',self._select_record)
        scroll=ScrollableFrame(panes);scroll.set_wheel_active(True);self._body=scroll.content
        self._body.columnconfigure(1,weight=1)
        panes.add(listing,weight=3);panes.add(scroll,weight=2)
        actions=ttk.Frame(self,padding=10);actions.grid(row=2,column=0,sticky='ew')
        self._buttons={}
        for col,(key,command) in enumerate((('new',self._new),('edit',self._edit),('save',self._save),('cancel',self._cancel),('refresh',self._reload))):
            button=ttk.Button(actions,command=command);button.grid(row=0,column=col,padx=(0,8));self._buttons[key]=button
        ttk.Label(self,textvariable=self._status,wraplength=1050).grid(row=3,column=0,sticky='ew',padx=10,pady=(0,8))
        self._search.trace_add('write',lambda *_:self._render_rows())
        self.protocol('WM_DELETE_WINDOW',self._close)
        owner.register_localizable(self)
        try:
            self._controller.browse(category)
            self.refresh_texts()
        except LibraryError:
            owner.unregister_localizable(self);self.destroy()
            raise

    def show_category(self, category: str) -> None:
        """Reuse the existing window, retaining an unfinished draft until canceled."""
        try:
            self._controller.browse(category)
            self._choice_cache.clear()
            self.refresh_texts()
        except LibraryError as error:
            current=CATEGORY_BY_CODE[self._controller.category]
            self._group.set(self._translate(f'library2.group.{current.group}'))
            self._category.set(self._translate(f'library2.category.{current.code}'))
            self._status.set(self._translate(error.key))
        self.deiconify();self.lift();self.focus_set()

    def refresh_texts(self) -> None:
        """Localize chrome and selected data without discarding raw editor precision."""
        if self._controller.mode is not EditMode.BROWSE: self._capture_draft()
        tr=self._translate
        self.title(tr('library2.title'))
        self._search_label.configure(text=tr('library2.search'))
        self._groups={tr(f'library2.group.{c.group}'):c.group for c in CATEGORIES}
        self._group_box.configure(values=tuple(self._groups))
        current=CATEGORY_BY_CODE[self._controller.category]
        self._group.set(tr(f'library2.group.{current.group}'))
        self._categories={tr(f'library2.category.{c.code}'):c.code for c in CATEGORIES if c.group==current.group}
        self._category_box.configure(values=tuple(self._categories));self._category.set(tr(f'library2.category.{current.code}'))
        parents=self._controller.service.list_records(current.parent) if current.parent else ()
        self._parents={tr('library2.choose_parent'):None}
        self._parents.update({record_label(r,tr):getattr(r,CATEGORY_BY_CODE[current.parent].key_field) for r in parents})
        self._parent_box.configure(values=tuple(self._parents),state='readonly' if current.parent else 'disabled')
        self._parent.set(next((label for label,value in self._parents.items() if value==self._controller.parent_id),tr('library2.choose_parent')))
        self._filters=[{tr('library2.all'):None,tr('library2.active'):True,tr('library2.inactive'):False},
                       {tr('library2.all'):None,**{tr(f'library2.ownership.{v}'):v for v in ('factory','user','reference','application')}},
                       {tr('library2.all'):None,**{tr(f'formula2.verification_status.{v.value}'):v.value for v in VerificationStatus}}]
        for box,var,choices in zip(self._filter_boxes,(self._active,self._ownership,self._verification),self._filters):
            box.configure(values=tuple(choices));var.set(next(iter(choices)))
        for key,button in self._buttons.items(): button.configure(text=tr(f'library2.{key}'))
        for key in ('name','value','ownership','active'): self._tree.heading(key,text=tr(f'library2.{key}'))
        self._render_rows()
        self._render_editor() if self._controller.mode is not EditMode.BROWSE else self._render_details()

    def _render_rows(self) -> None:
        if not hasattr(self,'_filters'): return
        selected=self._tree.selection()
        for item in self._tree.get_children(): self._tree.delete(item)
        self._row_map={}
        c=self._controller
        rows=c.filtered(self._search.get(),*(choices.get(var.get()) for choices,var in zip(self._filters,(self._active,self._ownership,self._verification))))
        for index,row in enumerate(rows):
            key=str(getattr(row,CATEGORY_BY_CODE[c.category].key_field));self._row_map[key]=row
            value=getattr(row,'value',getattr(row,'wall_thickness_mm',None))
            display=number(value) if isinstance(value,(int,float)) else ''
            owner=c.service.ownership(c.category,row)
            active=getattr(row,'is_active',None)
            self._tree.insert('', 'end',iid=key,values=(record_label(row,self._translate) or self._translate(f'library2.category.{c.category}'),display,self._translate(f'library2.ownership.{owner}'),
                self._translate('library2.active' if active else 'library2.inactive') if active is not None else ''))
        if selected and selected[0] in self._row_map and c.mode is EditMode.BROWSE:
            self._tree.selection_set(selected[0])

    def _clear_body(self) -> None:
        for child in self._body.winfo_children(): child.destroy()
        self._edit_vars={};self._edit_choices={}

    def _render_details(self) -> None:
        self._clear_body();c=self._controller;tr=self._translate
        self._group_box.configure(state='readonly');self._category_box.configure(state='readonly')
        self._parent_box.configure(state='readonly' if CATEGORY_BY_CODE[c.category].parent else 'disabled')
        self._tree.configure(selectmode='browse')
        self._buttons['new'].configure(state='normal' if CATEGORY_BY_CODE[c.category].model else 'disabled')
        editable=c.selected is not None and c.service.can_edit(c.category,c.selected)
        self._buttons['edit'].configure(state='normal' if editable else 'disabled')
        self._buttons['refresh'].configure(state='normal')
        for key in ('save','cancel'): self._buttons[key].configure(state='disabled')
        if c.selected is None:
            ttk.Label(self._body,text=tr('library2.read_first'),wraplength=420).grid(row=0,column=0,columnspan=2,sticky='w')
            return
        detail=c.service.details(c.category,c.selected)
        ttk.Label(self._body,text=tr(f'library2.ownership.{detail.ownership}'),wraplength=420).grid(row=0,column=0,columnspan=2,sticky='w')
        for row,(key,value) in enumerate(detail.values,1):
            label=tr(f'library2.field.{key}')
            if isinstance(value,bool):
                value=tr(('library2.active' if value else 'library2.inactive') if key=='is_active' else ('library2.yes' if value else 'library2.no'))
            elif isinstance(value,VerificationStatus): value=tr(f'formula2.verification_status.{value.value}')
            elif isinstance(value,float): value=number(value)
            elif hasattr(value,'isoformat'): value=value.isoformat()
            ttk.Label(self._body,text=label).grid(row=row,column=0,sticky='nw',padx=(0,8),pady=2)
            ttk.Label(self._body,text=str(value),wraplength=300,justify='left').grid(row=row,column=1,sticky='nw',pady=2)
        row=len(detail.values)+1
        for source in detail.sources:
            rows=source_rows(source,tr)
            primary=' · '.join(value for key,value in rows if key in (tr('formula2.source.source_type'),tr('formula2.source.document'),tr('formula2.source.verification_status')))
            ttk.Label(self._body,text=primary,wraplength=420).grid(row=row,column=0,columnspan=2,sticky='w',pady=8)
            body=ttk.Frame(self._body);body.grid(row=row+2,column=0,columnspan=2,sticky='ew');body.grid_remove()
            for index,(key,value) in enumerate(rows):
                ttk.Label(body,text=f'{key}: {value}',wraplength=420,justify='left').grid(row=index,column=0,sticky='w',pady=2)
            def toggle(frame: ttk.Frame = body) -> None:
                (frame.grid_remove if frame.winfo_manager() else frame.grid)()
            ttk.Button(self._body,text=tr('library2.source_details'),command=toggle).grid(row=row+1,column=0,columnspan=2,sticky='w')
            row+=3
        self._status.set(tr('library2.protected') if not detail.editable else '')

    def _reference_choices(self, target: str, field_name: str) -> dict[str, object]:
        parent=None
        if target=='circuits': parent=self._controller.draft.get('system_id')
        cache_key=(target,parent)
        if cache_key not in self._choice_cache:
            records=self._controller.service.list_records(target,parent)
            self._choice_cache[cache_key]=tuple(r for r in records if getattr(r,'is_active',True)
                and not (target=='systems' and self._controller.service.ownership(target,r)=='application'))
        choices={'':None}
        for record in self._choice_cache[cache_key]:
            identity=getattr(record,CATEGORY_BY_CODE[target].key_field)
            label=record_label(record,self._translate)
            if label in choices: label+=f' [{identity}]'
            choices[label]=identity
        return choices

    def _render_editor(self) -> None:
        self._clear_body();c=self._controller;tr=self._translate
        for box in (self._group_box,self._category_box,self._parent_box): box.configure(state='disabled')
        self._tree.configure(selectmode='none')
        for key in ('new','edit','refresh'): self._buttons[key].configure(state='disabled')
        for key in ('save','cancel'): self._buttons[key].configure(state='normal')
        for row,field in enumerate(CATEGORY_BY_CODE[c.category].fields):
            label_key=f'formula2.source.{field.name}' if c.category=='sources' else f'library2.field.{field.name}'
            ttk.Label(self._body,text=tr(label_key)).grid(row=row,column=0,sticky='nw',padx=(0,8),pady=3)
            raw=c.draft.get(field.name)
            if field.kind=='bool':
                var=tk.BooleanVar(value=True if raw is None else raw)
                widget=ttk.Checkbutton(self._body,variable=var)
            else:
                choices=None
                if field.target: choices=self._reference_choices(field.target,field.name)
                elif field.kind in ('verification','source_type'):
                    enum=VerificationStatus if field.kind=='verification' else SourceType
                    prefix='verification_status' if field.kind=='verification' else 'source_type'
                    choices={'':None,**{tr(f'formula2.{prefix}.{v.value}'):v for v in enum}}
                elif field.kind=='property': choices={v:v for v in PROPERTY_CODES[c.category]}
                if choices is not None:
                    current=next((key for key,value in choices.items() if value==raw),'')
                    if raw is not None and not current and raw not in choices.values():
                        current=f'{tr("library2.missing_reference")} {raw}';choices[current]=raw
                    self._edit_choices[field.name]=choices
                    var=tk.StringVar(value=current)
                    widget=ttk.Combobox(self._body,textvariable=var,values=tuple(choices),state='readonly',width=34)
                    if field.name=='system_id': widget.bind('<<ComboboxSelected>>',self._editor_system_changed)
                else:
                    var=tk.StringVar(value='' if raw is None else raw.isoformat() if hasattr(raw,'isoformat') else str(raw))
                    widget=ttk.Entry(self._body,textvariable=var,width=36)
                self._edit_vars[field.name]=var
            self._edit_vars[field.name]=var
            if c.mode is EditMode.EDIT and field.name==CATEGORY_BY_CODE[c.category].key_field:
                widget.configure(state='disabled')
            widget.grid(row=row,column=1,sticky='ew',pady=3)
        self._status.set(tr('library2.edit_notice'))

    def _capture_draft(self) -> None:
        for key,var in self._edit_vars.items():
            raw=var.get();self._controller.draft[key]=self._edit_choices[key].get(raw) if key in self._edit_choices else raw

    def _editor_system_changed(self, _event: object = None) -> None:
        self._capture_draft();self._controller.draft['circuit_id']=None;self._render_editor()

    def _choose_group(self, _event: object = None) -> None:
        group=self._groups[self._group.get()]
        self.show_category(next(c.code for c in CATEGORIES if c.group==group))

    def _choose_category(self, _event: object = None) -> None:
        self.show_category(self._categories[self._category.get()])

    def _choose_parent(self, _event: object = None) -> None:
        try:
            self._controller.browse(self._controller.category,self._parents[self._parent.get()])
            self._render_rows();self._render_details()
        except LibraryError as error: self._status.set(self._translate(error.key))

    def _select_record(self, _event: object = None) -> None:
        if self._controller.mode is not EditMode.BROWSE: return
        selected=self._tree.selection()
        if not selected: return
        try:
            self._controller.select(UUID(selected[0]));self._render_details()
        except LibraryError as error: self._status.set(self._translate(error.key))

    def _new(self) -> None:
        self._begin(True)

    def _edit(self) -> None:
        self._begin(False)

    def _begin(self, create: bool) -> None:
        try:
            self._controller.begin(create=create);self._render_editor()
        except LibraryError as error: self._status.set(self._translate(error.key))

    def _save(self) -> None:
        self._capture_draft()
        if not self._controller.save():
            if self._controller.error_key: self._status.set(self._translate(self._controller.error_key))
            return
        self._choice_cache.clear()
        try:
            self.refresh_texts()
            self._status.set(self._translate(self._controller.error_key or 'library2.saved'))
        except LibraryError:
            self._controller.records=();self._controller.selected=None
            self._render_rows();self._render_details()
            self._status.set(self._translate('library2.saved_refresh_required'))

    def _cancel(self) -> None:
        self._controller.cancel()
        try: self.refresh_texts()
        except LibraryError:
            self._render_details();self._status.set(self._translate('library2.error.storage'))
        self._buttons['refresh'].configure(state='normal')

    def _reload(self) -> None:
        try:
            self._choice_cache.clear();self._controller.service.refresh()
            self._controller.browse(self._controller.category,self._controller.parent_id);self.refresh_texts()
            refresh_context=getattr(self._owner,'refresh_library_context_choices',None)
            if callable(refresh_context): refresh_context()
        except LibraryError as error: self._status.set(self._translate(error.key))

    def _close(self) -> None:
        if self._controller.mode is not EditMode.BROWSE:
            self._status.set(self._translate('library2.error.finish_edit'));return
        self._owner.unregister_localizable(self);self.destroy()
        refresh_context=getattr(self._owner,'refresh_library_context_choices',None)
        if callable(refresh_context): refresh_context()
