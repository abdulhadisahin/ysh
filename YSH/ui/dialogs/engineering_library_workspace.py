"""One modeless, lazy engineering library workspace behind existing entry points."""
from __future__ import annotations

from dataclasses import fields
from enum import Enum
import tkinter as tk
from tkinter import ttk
from uuid import UUID
from collections.abc import Callable

from engineering.provenance import SourceType, VerificationStatus
from engineering.fire.library import FireParameter, FIRE_CATEGORIES
from engineering.fire.enums import FireSourceStatus
from services.engineering_library_service import EngineeringLibraryService, LibraryError
from services.library_catalog import VISIBLE_CATEGORIES as CATEGORIES, CATEGORY_BY_CODE, PROPERTY_CODES, HIDDEN_LIBRARY_CATEGORIES
from ui.library_controller import LibraryController, EditMode
from ui.widgets.scrollable_frame import ScrollableFrame
from ui.widgets.formula_steps import number, source_rows
from ui.widgets.detail_disclosure import DetailDisclosure
from ui.library_presentation import detail_group, ordered_editor_fields
from ui.theme import colors, typography
from ui.theme.library_visuals import configure_library_visuals, verification_role, fire_source_role, PANE_WEIGHTS, pane_positions
from ui.theme.spacing import SM, MD
from engineering.catalog_completion import OperatingFluidProperty, MechanicalGradeProperty


from i18n.catalog_text import catalog_text
from services.library_scope import scoped, visible_categories, allowed_fluid_ids, row_visible, category_visible


def _scope_categories(window):
    family=getattr(window,'_family',None);show=getattr(window,'_show_all',None)
    return CATEGORIES if not family or (show is not None and show.get()) else visible_categories(family,CATEGORIES)


def localized_library_value(key: str, value: object, translate: Callable[[str], str]) -> object:
    """Translate known display terms while leaving stored identifiers and source facts intact."""
    if isinstance(value,str) and value.startswith('catalog.'):
        return translate(value)
    if key == 'classification':return translate('catalog.classification.'+str(value))
    if key == 'concentration_basis' and value:return translate('catalog.'+str(value))
    if key == 'national_adoption_status':return translate('engineering.verification.'+str(value))
    constant_names = {'Corrosion Allowance': 'corrosion_allowance', 'Design Pressure': 'design_pressure',
        'Safety Factor': 'safety_factor', 'Weld Factor': 'weld_factor',
        'Display Decimal Places': 'display_decimal_places'}
    if key == 'display_name' and value in constant_names:
        return translate('constant.'+constant_names[value])
    if key == 'source' and value in ('User', 'USER_INPUT'):
        return translate('library2.manual_user')
    if key == 'audit_scope' and value:
        return translate('sourceaudit.scope.'+value)
    if key == 'property_name':
        label = translate('engineering.property.'+str(value))
        return value if label == 'engineering.property.'+str(value) else label
    if key in ('code','id','designation'):return value
    return catalog_text(translate,value)


def record_label(record: object, translate: Callable[[str], str] | None = None) -> str:
    if isinstance(record,MechanicalGradeProperty):
        limit=str(record.minimum_value)+' … '+str(record.maximum_value) if record.maximum_value is not None else '≥ '+str(record.minimum_value)
        return f'{record.property_name}: {limit} {record.unit} · {record.thickness_above_mm} < t ≤ {record.thickness_up_to_mm} mm'
    if isinstance(record,OperatingFluidProperty):
        name=translate('engineering.property.'+record.property_name) if translate else record.property_name
        return f'{name}: {record.value} {record.unit} · {record.reference_temperature_c} °C · {record.reference_salinity_g_kg} g/kg · {record.reference_pressure_mpa} MPa'
    """Use engineering identities in pickers rather than prominently showing UUIDs."""
    if hasattr(record,'parameter_type'):
        label=translate('library2.category.'+next(k for k,v in FIRE_CATEGORIES.items() if v==record.parameter_type)) if translate else record.parameter_type.value
        return label+' · '+record.context+' · r'+str(record.revision)
    if hasattr(record,'reference'):
        source=record.reference
        from engineering.source_verification import source_label_key
        kind=translate(source_label_key(source)) if translate else source.source_type.value
        return ' · '.join(str(v) for v in (kind,source.source_organization,source.document,source.revision) if v)
    if hasattr(record,'outside_diameter_mm'):
        return f'{record.standard} · {record.nominal_diameter} · OD {record.outside_diameter_mm} / s {record.wall_thickness_mm} / ID {record.inside_diameter_mm} mm'
    if hasattr(record,'catalog_summary'):
        if translate is None:return record.catalog_summary
        source=translate('engineering.verification.'+record.verification)
        if hasattr(record,'property_name'):
            value=str(record.default_value)+' '+record.unit if record.default_value is not None else translate('engineering.status.SOURCE_REQUIRED')
            temperature=' @ '+str(record.reference_temperature_c)+' °C' if record.reference_temperature_c is not None else ''
            return catalog_text(translate,record.name)+' / '+translate('engineering.property.'+record.property_name)+': '+value+temperature+' · '+source
        if hasattr(record,'roughness_mm'):
            value=str(record.roughness_mm)+' mm' if record.roughness_mm is not None else translate('engineering.status.SOURCE_REQUIRED')
            return catalog_text(translate,record.name)+': ε = '+value+' · '+source
        low,high=(record.hard_min,record.hard_max) if record.rule_nature=='HARD_LIMIT' else (record.recommended_min,record.recommended_max)
        limits=('≥ '+str(low) if low is not None else '')+(' … ' if low is not None and high is not None else '')+('≤ '+str(high) if high is not None else '')
        return catalog_text(translate,record.name)+': '+(limits+' '+record.unit if limits else source)+' · '+record.source_authority
    if hasattr(record,'property_name'):
        name=localized_library_value('property_name',record.property_name,translate) if translate else record.property_name
        label=' · '.join(str(v) for v in (catalog_text(translate,getattr(record,'name_tr',None)),name,f'{record.value} {record.unit}') if v)
        if getattr(record,'reference_temperature_c',None) is not None: label+=f' · {record.reference_temperature_c} °C'
        return label
    return ' · '.join(str(localized_library_value(key,getattr(record,key),translate) if translate else getattr(record,key)) for key in
        ('code','designation','nominal_diameter','name_tr','display_name','ship_name','property_name')
        if getattr(record,key,None) is not None) or str(getattr(record,'id',''))


def record_verification(record: object) -> VerificationStatus | None:
    """Read an existing row status only; never look up linked sources per table row."""
    return getattr(record, 'verification_status', getattr(getattr(record,'reference',None),'verification_status',None))


def visible_detail(value: object) -> bool:
    """Omit missing display metadata while retaining numeric zero and False."""
    return value is not None and value != '' and value != {} and value != () and value != []


class EngineeringLibraryWorkspace(tk.Toplevel):
    """Browse first; an explicit editor draft never autosaves or modifies project data."""
    def __init__(self, parent: tk.Misc, service: EngineeringLibraryService,
                 translate: Callable[[str], str], owner: object, category: str = 'systems', family: str | None = None) -> None:
        """Load only the initial category after the user opens Libraries."""
        super().__init__(parent)
        self.transient(parent)
        self.geometry('1366x768');self.minsize(960,560)
        configure_library_visuals(ttk.Style(self))
        self.configure(background=colors.WORKSPACE_SURFACE)
        self._controller=LibraryController(service)
        self._family=family if scoped(family) else None
        self._show_all=tk.BooleanVar(value=False);self._fluid_ids=None
        self._controller.row_filter=self._row_in_scope
        self._translate=translate;self._owner=owner
        self._group=tk.StringVar();self._category=tk.StringVar();self._parent=tk.StringVar()
        self._search=tk.StringVar();self._active=tk.StringVar();self._ownership=tk.StringVar();self._verification=tk.StringVar()
        self._status=tk.StringVar();self._edit_vars={};self._edit_choices={}
        self._choice_cache={};self._row_map={}
        self.columnconfigure(0,weight=1);self.rowconfigure(2,weight=1)
        header=ttk.Frame(self,style='Library.Header.TFrame');header.grid(row=0,column=0,sticky='ew',padx=MD,pady=(MD,SM))
        self._header_title=ttk.Label(header,style='Library.Title.TLabel');self._header_title.grid(row=0,column=0,sticky='w')
        self._header_subtitle=ttk.Label(header,style='Library.Subtitle.TLabel');self._header_subtitle.grid(row=1,column=0,sticky='w',pady=(SM//2,0))
        header.columnconfigure(0,weight=1)
        self._scope_check=ttk.Checkbutton(header,variable=self._show_all,command=self._scope_changed)
        if self._family:self._scope_check.grid(row=0,column=1,rowspan=2,sticky='e')
        top=ttk.Frame(self,padding=SM,style='Library.Card.TFrame');top.grid(row=1,column=0,sticky='ew',padx=MD,pady=(0,SM))
        for column in range(3): top.columnconfigure(column, weight=1 if column==1 else 0)
        self._group_box=ttk.Combobox(top,textvariable=self._group,state='readonly',width=28)
        self._group_box.grid(row=0,column=0,sticky='ew',padx=(0,8))
        self._category_box=ttk.Combobox(top,textvariable=self._category,state='readonly',width=30)
        self._category_box.grid(row=0,column=1,sticky='ew',padx=(0,8))
        self._parent_box=ttk.Combobox(top,textvariable=self._parent,state='readonly',width=30,style='Library.TCombobox')
        self._parent_box.grid(row=0,column=2,sticky='ew')
        self._group_box.bind('<<ComboboxSelected>>',self._choose_group)
        self._category_box.bind('<<ComboboxSelected>>',self._choose_category)
        self._parent_box.bind('<<ComboboxSelected>>',self._choose_parent)
        self._group_box.grid_remove();self._category_box.grid_remove()
        self._search_label=ttk.Label(top,style='Library.Heading.TLabel');self._search_label.grid(row=0,column=0,sticky='w')
        ttk.Entry(top,textvariable=self._search,style='Library.TEntry').grid(row=0,column=1,sticky='ew',padx=8)
        self._advanced_button=ttk.Button(top,command=self._toggle_filters,style='Library.Secondary.TButton')
        self._advanced_button.grid(row=0,column=2,sticky='e')
        self._parent_label=ttk.Label(top,style='Library.Field.TLabel')
        self._parent_label.grid(row=1,column=0,sticky='w',pady=(6,0))
        self._parent_box.grid_configure(row=1,column=1,columnspan=2,pady=(6,0))
        filters=self._advanced_filters=ttk.Frame(top,style='Library.Body.TFrame')
        filters.grid(row=2,column=0,columnspan=3,sticky='ew',pady=(8,0))
        filters.grid_remove()
        self._filter_labels=[]
        self._filter_boxes=[]
        for col,var in enumerate((self._active,self._ownership,self._verification)):
            box=ttk.Combobox(filters,textvariable=var,state='readonly',width=21,style='Library.TCombobox')
            filters.columnconfigure(col,weight=1)
            label=ttk.Label(filters,style='Library.Field.TLabel');label.grid(row=0,column=col,sticky='w');self._filter_labels.append(label)
            box.grid(row=1,column=col,sticky='ew',padx=(0,6));box.bind('<<ComboboxSelected>>',lambda _:self._render_rows())
            self._filter_boxes.append(box)
        panes=self._panes=ttk.Panedwindow(self,orient='horizontal');panes.grid(row=2,column=0,sticky='nsew',padx=MD)
        navigation=ttk.Frame(panes,style='Library.Card.TFrame',width=205)
        navigation.columnconfigure(0,weight=1);navigation.rowconfigure(0,weight=1)
        self._navigation=ttk.Treeview(navigation,show='tree',selectmode='browse',style='LibraryNav.Treeview')
        self._navigation.column('#0',width=208,minwidth=196,stretch=True)
        self._navigation.grid(row=0,column=0,sticky='nsew')
        nav_scroll=ttk.Scrollbar(navigation,orient='vertical',command=self._navigation.yview)
        nav_scroll.grid(row=0,column=1,sticky='ns');self._navigation.configure(yscrollcommand=nav_scroll.set)
        self._navigation.tag_configure('group',font=typography.BODY_BOLD,foreground=colors.TEXT_SECONDARY)
        self._navigation.bind('<<TreeviewSelect>>',self._choose_navigation)
        listing=ttk.Frame(panes,style='Library.Card.TFrame',width=430);listing.columnconfigure(0,weight=1);listing.rowconfigure(1,weight=1)
        ttk.Label(listing,textvariable=self._category,style='Library.Heading.TLabel').grid(row=0,column=0,sticky='w',pady=(0,6))
        self._record_count=tk.StringVar()
        ttk.Label(listing,textvariable=self._record_count,style='Library.Field.TLabel').grid(row=0,column=1,sticky='e',padx=8)
        self._tree=ttk.Treeview(listing,columns=('name','value','ownership','verification','active'),show='headings',selectmode='browse',style='Library.Data.Treeview')
        self._tree.grid(row=1,column=0,columnspan=2,sticky='nsew')
        scrollbar=ttk.Scrollbar(listing,orient='vertical',command=self._tree.yview)
        scrollbar.grid(row=1,column=2,sticky='ns');self._tree.configure(yscrollcommand=scrollbar.set)
        horizontal=ttk.Scrollbar(listing,orient='horizontal',command=self._tree.xview)
        horizontal.grid(row=2,column=0,columnspan=2,sticky='ew');self._tree.configure(xscrollcommand=horizontal.set)
        for key,width in (('name',190),('value',80),('ownership',130),('verification',150),('active',90)):
            self._tree.column(key,width=width,minwidth=80,stretch=(key=='name'))
        self._tree.tag_configure('even',background=colors.CARD_SURFACE)
        self._tree.tag_configure('odd',background=colors.RESULT_SURFACE)
        self._table_empty=ttk.Label(self._tree,wraplength=280,justify='center',style='Library.Muted.TLabel')
        self._tree.bind('<<TreeviewSelect>>',self._select_record)
        scroll=self._detail_scroll=ScrollableFrame(panes,width=320,style='Library.Card.TFrame');scroll.set_wheel_active(True);self._body=scroll.content
        self._body.configure(style='Library.Body.TFrame')
        self._body.bind('<Configure>',self._fit_detail_text,add='+')
        self._body.columnconfigure(1,weight=1)
        for pane,weight in zip((navigation,listing,scroll),PANE_WEIGHTS): panes.add(pane,weight=weight)
        panes.bind('<Configure>',self._balance_panes,add='+')
        actions=ttk.Frame(self,padding=SM,style='Library.Workspace.TFrame');actions.grid(row=3,column=0,sticky='ew',padx=SM)
        self._buttons={}
        for col,(key,command) in enumerate((('new',self._new),('edit',self._edit),('save',self._save),('cancel',self._cancel),('refresh',self._reload))):
            button=ttk.Button(actions,command=command,style='Library.Primary.TButton' if key in ('new','save') else 'Library.Secondary.TButton');button.grid(row=0,column=col,padx=(0,8));self._buttons[key]=button
        ttk.Label(self,textvariable=self._status,wraplength=1050,style='Library.Muted.TLabel').grid(row=4,column=0,sticky='ew',padx=10,pady=(0,8))
        self._search.trace_add('write',lambda *_:self._render_rows())
        self.protocol('WM_DELETE_WINDOW',self._close)
        owner.register_localizable(self)
        try:
            if category in HIDDEN_LIBRARY_CATEGORIES:
                category = CATEGORY_BY_CODE[category].parent
            self._controller.browse(category)
            self.refresh_texts()
        except LibraryError:
            owner.unregister_localizable(self);self.destroy()
            raise

    def _categories_in_scope(self):
        return _scope_categories(self)

    def _row_in_scope(self,category,row):
        if self._show_all.get() or not self._family:return True
        if self._fluid_ids is None:
            try:self._fluid_ids=allowed_fluid_ids(self._family,self._controller.service.list_display_records('fluid_specifications'))
            except Exception:self._fluid_ids=None
        return row_visible(self._family,category,row,self._fluid_ids)

    def set_family(self,family):
        family=family if scoped(family) else None
        if family==self._family:return
        self._family=family;self._fluid_ids=None;self._show_all.set(False)
        (self._scope_check.grid if family else self._scope_check.grid_remove)()
        self._scope_changed()

    def _scope_changed(self):
        self._choice_cache.clear()
        current=CATEGORY_BY_CODE[self._controller.category]
        if not self._show_all.get() and not category_visible(self._family,current):
            self.show_category(next(c.code for c in self._categories_in_scope()))
            return
        self.refresh_texts();self._render_rows()

    def show_category(self, category: str) -> None:
        """Reuse the existing window, retaining an unfinished draft until canceled."""
        if category in HIDDEN_LIBRARY_CATEGORIES:
            category = CATEGORY_BY_CODE[category].parent
        if self._family and not category_visible(self._family,CATEGORY_BY_CODE[category]):self._show_all.set(True)
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
        self._header_title.configure(text=tr('library.visual.title'))
        self._header_subtitle.configure(text=tr('library.visual.subtitle'))
        self._search_label.configure(text=tr('library2.search'))
        self._advanced_button.configure(text=tr('library2.filters'))
        self._parent_label.configure(text=tr('library2.relationship'))
        self._table_empty.configure(text=tr('library2.no_records'))
        for label,key in zip(self._filter_labels,('library2.active','library2.ownership','formula2.source.verification_status')):
            label.configure(text=tr(key))
        self._scope_check.configure(text=tr('library2.show_all'))
        self._refresh_navigation()
        self._groups={tr(f'library2.group.{c.group}'):c.group for c in self._categories_in_scope()}
        self._group_box.configure(values=tuple(self._groups))
        current=CATEGORY_BY_CODE[self._controller.category]
        self._group.set(tr(f'library2.group.{current.group}'))
        self._categories={tr(f'library2.category.{c.code}'):c.code for c in self._categories_in_scope() if c.group==current.group}
        self._category_box.configure(values=tuple(self._categories));self._category.set(tr(f'library2.category.{current.code}'))
        (self._parent_label.grid if current.parent else self._parent_label.grid_remove)()
        (self._parent_box.grid if current.parent else self._parent_box.grid_remove)()
        parents=self._controller.service.list_display_records(current.parent) if current.parent else ()
        self._parents={tr('library2.choose_parent'):None}
        self._parents.update({record_label(r,tr):getattr(r,CATEGORY_BY_CODE[current.parent].key_field) for r in parents})
        self._parent_box.configure(values=tuple(self._parents),state='readonly' if current.parent else 'disabled')
        self._parent.set(next((label for label,value in self._parents.items() if value==self._controller.parent_id),tr('library2.choose_parent')))
        self._filters=[{tr('library2.all'):None,tr('library2.active'):True,tr('library2.inactive'):False},
                       {tr('library2.all'):None,**{tr(f'library2.ownership.{v}'):v for v in ('factory','user','reference','application')}},
                       {tr('library2.all'):None,**{tr(f'formula2.verification_status.{v.value}'):v.value for v in VerificationStatus}}]
        if current.code in ('fluid_specifications','material_surfaces','engineering_rules'):
            from engineering.catalog import VERIFICATIONS
            self._filters[2]={tr('library2.all'):None,**{tr('engineering.verification.'+v):v for v in VERIFICATIONS}}
        for box,var,choices in zip(self._filter_boxes,(self._active,self._ownership,self._verification),self._filters):
            box.configure(values=tuple(choices));var.set(next(iter(choices)))
        for key,button in self._buttons.items(): button.configure(text=tr(f'library2.{key}'))
        for key in ('name','value','ownership','verification','active'): self._tree.heading(key,text=tr(f'library2.{key}'))
        self._fluid_specs={}
        if current.code=='fluids':
            for record in self._controller.service.list_records('fluid_specifications'):
                self._fluid_specs.setdefault(record.fluid_id,[]).append(record)
        self._configure_catalog_columns()
        self._render_rows()
        self._render_editor() if self._controller.mode is not EditMode.BROWSE else self._render_details()

    def _configure_catalog_columns(self):
        tr=self._translate
        headings=('library2.name','library2.value','library2.ownership','library2.verification','library2.active')
        if self._controller.category=='engineering_rules':
            headings=('library2.name','engineering.reference','library2.field.rule_nature','engineering.source','library2.verification')
        elif self._controller.category=='material_surfaces':
            headings=('library2.name','engineering.property.absolute_roughness','library2.field.material_name','library2.field.surface_condition','library2.verification')
        for column,key in zip(('name','value','ownership','verification','active'),headings):self._tree.heading(column,text=tr(key))

    def _catalog_row(self,record):
        tr=self._translate;verification=tr('engineering.verification.'+record.verification)
        if self._controller.category=='material_surfaces':
            roughness=number(record.roughness_mm)+' mm' if record.roughness_mm is not None else tr('engineering.status.SOURCE_REQUIRED')
            return (record.name,roughness,record.material_name,record.surface_condition,verification)
        low,high=(record.hard_min,record.hard_max) if record.rule_nature=='HARD_LIMIT' else (record.recommended_min,record.recommended_max)
        bounds=('≥ '+number(low) if low is not None else '')+(' … ' if low is not None and high is not None else '')+('≤ '+number(high) if high is not None else '')
        return (record.name,bounds+' '+record.unit if bounds else tr('engineering.status.SOURCE_REQUIRED'),
                tr('engineering.nature.'+record.rule_nature),record.source_authority,verification)

    def _render_fluid_specs(self,row):
        tr=self._translate;fluid=self._controller.selected
        records=self._fluid_specs.get(fluid.id,())
        if not records:
            ttk.Label(self._body,text=tr('library2.catalog.no_properties'),wraplength=260,style='Library.Muted.TLabel').grid(row=row,column=0,columnspan=2,sticky='w')
            return row+1
        names=('source_min','source_max','source_nominal','default_value','default_method','unit',
               'reference_temperature_c','source_authority','source_document','verification')
        for record in records:
            region=ttk.LabelFrame(self._body,text=tr('engineering.property.'+record.property_name),padding=SM,style='Library.Section.TLabelframe')
            region.grid(row=row,column=0,columnspan=2,sticky='ew',pady=(0,8));region.columnconfigure(1,weight=1)
            for index,name in enumerate(names):
                value=getattr(record,name)
                if name=='default_method':value=tr('engineering.method.'+value)
                elif name=='verification':value=tr('engineering.verification.'+value)
                elif value is None or value=='':value=tr('report.not_recorded')
                elif isinstance(value,(float,int)):value=number(value)
                ttk.Label(region,text=tr('library2.field.'+name),style='Library.Field.TLabel',wraplength=115).grid(row=index*2,column=0,columnspan=2,sticky='nw',pady=(4,1))
                ttk.Label(region,text=str(value),style='Library.Value.TLabel',wraplength=150).grid(row=index*2+1,column=0,columnspan=2,sticky='nw',pady=(0,3))
            row+=1
        return row

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
            if c.category in FIRE_CATEGORIES:
                display=number(value*100 if row.parameter_type is FireParameter.CONCENTRATION else value)+' '+('%' if row.parameter_type is FireParameter.CONCENTRATION else row.unit)
            owner=c.service.ownership(c.category,row)
            active=getattr(row,'is_active',None)
            self._tree.insert('', 'end',iid=key,tags=('even' if index%2==0 else 'odd',),values=self._catalog_row(row) if c.category in ('engineering_rules','material_surfaces') else (record_label(row,self._translate) or self._translate(f'library2.category.{c.category}'),display,self._translate(f'library2.ownership.{owner}'),
                self._translate('engineering.verification.'+row.verification) if hasattr(row,'verification') else self._translate('fire.ui.source.'+row.source_status.value) if c.category in FIRE_CATEGORIES else self._translate(f'formula2.verification_status.{record_verification(row).value}') if record_verification(row) else '',
                self._translate('library2.active' if active else 'library2.inactive') if active is not None else ''))
        self._record_count.set(f"{len(rows)} {self._translate('library2.record_count')}")
        if rows: self._table_empty.place_forget()
        else:
            filtered=bool(self._search.get()) or any(choices.get(var.get()) is not None for choices,var in zip(self._filters,(self._active,self._ownership,self._verification)))
            self._table_empty.configure(text=self._translate('library.visual.no_matches' if filtered else 'library2.no_records'))
            self._table_empty.place(relx=.5,rely=.5,anchor='center')
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
            ttk.Label(self._body,text=tr('library2.read_first'),wraplength=260,style='Library.Muted.TLabel').grid(row=0,column=0,columnspan=2,sticky='w')
            return
        detail=c.service.details(c.category,c.selected)
        heading=record_label(c.selected,tr)
        ttk.Label(self._body,text=heading if len(heading)<=140 else heading[:137]+'…',wraplength=260,
                  style='Library.Heading.TLabel').grid(row=0,column=0,columnspan=2,sticky='ew',pady=(0,6))
        state=tr('library2.editable' if detail.editable else 'library2.read_only')
        ttk.Label(self._body,text=f"{tr(f'library2.ownership.{detail.ownership}')} · {state}",
                  wraplength=260,style='Library.Info.TLabel' if detail.editable else 'Library.Muted.TLabel').grid(row=1,column=0,columnspan=2,sticky='w',pady=(0,8))
        groups={}
        for key,value in detail.values:
            if self._controller.category in FIRE_CATEGORIES and key=='source_id':continue
            value=localized_library_value(key,value,tr)
            if visible_detail(value): groups.setdefault(detail_group(key),[]).append((key,value))
        row=self._render_fluid_specs(2) if c.category=='fluids' else 2
        for group,items in groups.items():
            if group in ('technical','relationships','source'):
                region=DetailDisclosure(self._body,tr(f'library2.section.{group}'),style='Library.Body.TFrame',body_style='Library.Body.TFrame')
                body=region.body
            else:
                region=ttk.LabelFrame(self._body,text=tr(f'library2.section.{group}'),padding=SM,style='Library.Section.TLabelframe')
                body=region
            region.grid(row=row,column=0,columnspan=2,sticky='ew',pady=(0,8))
            body.columnconfigure(1,weight=1)
            for index,(key,value) in enumerate(items):
                value_style='Library.'+verification_role(value)+'.TLabel' if isinstance(value,VerificationStatus) else 'Library.Value.TLabel'
                if isinstance(value,bool):
                    value=tr(('library2.active' if value else 'library2.inactive') if key=='is_active' else ('library2.yes' if value else 'library2.no'))
                elif key in ('verification','default_method','rule_nature') and hasattr(c.selected,'verification'):
                    prefix={'verification':'verification','default_method':'method','rule_nature':'nature'}[key]
                    value=tr('engineering.'+prefix+'.'+value)
                elif isinstance(value,VerificationStatus): value=tr(f'formula2.verification_status.{value.value}')
                elif isinstance(value,FireSourceStatus):
                    value_style='Library.'+fire_source_role(value)+'.TLabel'
                    value=tr('fire.ui.source.'+value.value)
                elif isinstance(value,FireParameter):
                    value=tr('library2.category.'+next(code for code,parameter in FIRE_CATEGORIES.items() if parameter==value))
                elif self._controller.category in FIRE_CATEGORIES and key=='service':value=tr('fire.library.service.'+value)
                elif isinstance(value,float): value=number(value)
                elif hasattr(value,'isoformat'): value=value.isoformat()
                ttk.Label(body,text=tr(f'library2.field.{key}'),wraplength=260,style='Library.Field.TLabel').grid(row=index*2,column=0,columnspan=2,sticky='w',pady=(5,1))
                ttk.Label(body,text=str(value),wraplength=260,justify='left',style=value_style).grid(row=index*2+1,column=0,columnspan=2,sticky='ew',pady=(0,3))
            row+=1
        for source in detail.sources:
            rows=source_rows(source,tr)
            primary=' · '.join(value for key in (tr('formula2.source.verification_status'),tr('formula2.source.source_type')) for name,value in rows if name==key)
            region=DetailDisclosure(self._body,tr('library2.source_details'),primary,wraplength=260,style='Library.Body.TFrame',body_style='Library.Body.TFrame',summary_style='Library.'+verification_role(source.verification_status)+'.TLabel')
            region.grid(row=row,column=0,columnspan=2,sticky='ew',pady=(0,8))
            for index,(key,value) in enumerate(rows):
                ttk.Label(region.body,text=f'{key}: {value}',wraplength=260,justify='left',style='Library.Field.TLabel').grid(row=index,column=0,sticky='w',pady=2)
            row+=1
        self._status.set(tr('library2.protected') if not detail.editable else '')

    def _toggle_filters(self) -> None:
        (self._advanced_filters.grid_remove if self._advanced_filters.winfo_manager() else self._advanced_filters.grid)()

    def _refresh_navigation(self) -> None:
        categories=_scope_categories(self)
        for item in self._navigation.get_children(): self._navigation.delete(item)
        priority=('materials','fluids','pipes','engineering_rules','constants','corrosion')
        groups=tuple(g for g in priority if any(c.group==g for c in categories))+tuple(g for g in dict.fromkeys(c.group for c in categories) if g not in priority)
        for group in groups:
            parent='group:'+group
            self._navigation.insert('', 'end',iid=parent,text=self._translate(f'library2.group.{group}'),open=group==CATEGORY_BY_CODE[self._controller.category].group,tags=('group',))
            if group=='fire':
                for subgroup in ('foam','hw'):
                    self._navigation.insert(parent,'end',iid='group:fire:'+subgroup,
                        text=self._translate('fire.library.group.'+subgroup),open=True,tags=('group',))
            for category in categories:
                if category.group==group:
                    branch='group:fire:'+('hw' if category.code=='fire_hw' else 'foam') if group=='fire' else parent
                    key='fire.library.nav.'+category.code if group=='fire' else f'library2.category.{category.code}'
                    self._navigation.insert(branch,'end',iid=category.code,text=self._translate(key))
        self._navigation.selection_set(self._controller.category)
        self._navigation.see(self._controller.category)

    def _choose_navigation(self, _event: object = None) -> None:
        selected=self._navigation.selection()
        if not selected:return
        target=selected[0]
        if target.startswith('group:'):
            group=target.split(':',1)[1]
            target=next((c.code for c in _scope_categories(self) if c.group==group),target)
        if target not in CATEGORY_BY_CODE or target==self._controller.category:return
        self.show_category(target)
        if self._controller.category!=selected[0]: self._navigation.selection_set(self._controller.category)

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
            if label in choices:
                label+=f' ({len(choices)})' if self._controller.category in FIRE_CATEGORIES else f' [{identity}]'
            choices[label]=identity
        return choices

    def _render_editor(self) -> None:
        self._clear_body();c=self._controller;tr=self._translate
        for box in (self._group_box,self._category_box,self._parent_box): box.configure(state='disabled')
        self._tree.configure(selectmode='none')
        for key in ('new','edit','refresh'): self._buttons[key].configure(state='disabled')
        for key in ('save','cancel'): self._buttons[key].configure(state='normal')
        ttk.Label(self._body,text=tr('library.visual.create_mode' if c.mode is EditMode.CREATE else 'library.visual.edit_mode'),
                  style='Library.Heading.TLabel').grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,8))
        row=1
        if c.category in FIRE_CATEGORIES:
            ttk.Label(self._body,text=tr('library2.category.'+c.category),wraplength=260,
                      style='Library.Value.TLabel').grid(row=1,column=0,columnspan=2,sticky='ew')
        previous_group=None
        for field in ordered_editor_fields(CATEGORY_BY_CODE[c.category].fields):
            group=detail_group(field.name)
            if group!=previous_group and c.category not in FIRE_CATEGORIES:
                ttk.Label(self._body,text=tr(f'library2.section.{group}'),style='Library.Heading.TLabel').grid(
                    row=row*2,column=0,columnspan=2,sticky='w',pady=(SM,4))
                previous_group=group;row+=1
            label_key=f'formula2.source.{field.name}' if c.category=='sources' else f'library2.field.{field.name}'
            if c.category=='fire_foam_concentration' and field.name=='value':label_key='fire.library.canonical_value'
            ttk.Label(self._body,text=tr(label_key),wraplength=260,style='Library.Field.TLabel').grid(row=row*2,column=0,columnspan=2,sticky='nw',pady=(SM,3))
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
                elif field.kind.startswith('engineering_'):
                    from engineering.catalog import METHODS,VERIFICATIONS,NATURES
                    values={'engineering_method':METHODS,'engineering_verification':VERIFICATIONS,'engineering_nature':NATURES}[field.kind]
                    prefix={'engineering_method':'method','engineering_verification':'verification','engineering_nature':'nature'}[field.kind]
                    choices={tr('engineering.'+prefix+'.'+v):v for v in values}
                elif field.kind=='property': choices={localized_library_value('property_name',v,tr):v for v in PROPERTY_CODES[c.category]}
                elif field.kind=='fire_status': choices={tr('fire.ui.source.'+v.value):v for v in FireSourceStatus}
                elif field.kind=='fire_service': choices={tr('fire.library.service.'+v):v for v in ('foam','water','seawater','fuel','unknown')}
                if choices is not None:
                    current=next((key for key,value in choices.items() if value==raw),'')
                    if raw is not None and not current and raw not in choices.values():
                        current=tr('library2.missing_reference') if c.category in FIRE_CATEGORIES else f'{tr("library2.missing_reference")} {raw}';choices[current]=raw
                    self._edit_choices[field.name]=choices
                    var=tk.StringVar(value=current)
                    widget=ttk.Combobox(self._body,textvariable=var,values=tuple(choices),state='readonly',width=26,style='Library.TCombobox')
                    if field.name=='system_id': widget.bind('<<ComboboxSelected>>',self._editor_system_changed)
                else:
                    var=tk.StringVar(value='' if raw is None else raw.isoformat() if hasattr(raw,'isoformat') else str(raw))
                    widget=ttk.Entry(self._body,textvariable=var,width=26,style='Library.TEntry')
                self._edit_vars[field.name]=var
            self._edit_vars[field.name]=var
            if c.mode is EditMode.EDIT and field.name==CATEGORY_BY_CODE[c.category].key_field:
                widget.configure(state='disabled')
            if c.category in FIRE_CATEGORIES and field.name=='unit':widget.configure(state='readonly')
            widget.grid(row=row*2+1,column=0,columnspan=2,sticky='ew',pady=3)
            row+=1
        self._status.set(tr('library2.edit_notice'))

    def _fit_detail_text(self, _event: object = None) -> None:
        """Wrap mounted text to its local viewport, without reading records again."""
        width=max(160,self._detail_scroll.canvas.winfo_width()-48)
        def fit(parent):
            for child in parent.winfo_children():
                if isinstance(child,ttk.Label) and abs(int(float(child.cget('wraplength') or 0))-width)>8:
                    child.configure(wraplength=width)
                fit(child)
        fit(self._body)

    def _balance_panes(self, event: tk.Event) -> None:
        """Apply shared proportions on window resize; retain manual sash adjustments."""
        if event.width<800 or getattr(self,'_pane_layout_width',None)==event.width:
            return
        self._pane_layout_width=event.width
        for index,position in enumerate(pane_positions(event.width)):
            self._panes.sashpos(index,position)

    def _capture_draft(self) -> None:
        for key,var in self._edit_vars.items():
            raw=var.get();self._controller.draft[key]=self._edit_choices[key].get(raw) if key in self._edit_choices else raw

    def _editor_system_changed(self, _event: object = None) -> None:
        self._capture_draft();self._controller.draft['circuit_id']=None;self._render_editor()

    def _choose_group(self, _event: object = None) -> None:
        group=self._groups[self._group.get()]
        self.show_category(next(c.code for c in self._categories_in_scope() if c.group==group))

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
        if self._controller.category in FIRE_CATEGORIES:
            refresh_fire=getattr(getattr(self,'_owner',None),'refresh_fire_library_choices',None)
            if callable(refresh_fire):refresh_fire()
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
