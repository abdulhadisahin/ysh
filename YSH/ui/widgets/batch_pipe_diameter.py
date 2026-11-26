"""Editable spreadsheet-like input rows; results never become single-pipe state."""
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace

from services.batch_pipe_diameter import calculate_rows
from i18n.validation import render_validation_issue
from ui.formatting import format_user_number


class BatchPipeDiameterTable(ttk.LabelFrame):
    COLUMNS=('name','flow','velocity','diameter','dn')

    def __init__(self,parent,service,standard,translate,on_dirty=lambda:None):
        super().__init__(parent,padding=10)
        self.service=service;self.standard=standard;self.tr=translate;self.on_dirty=on_dirty
        self.inputs={};self.results={};self.editor=None;self.active=None
        self.columnconfigure(0,weight=1)
        self.actions=ttk.Frame(self);self.actions.grid(row=0,column=0,sticky='ew',pady=(0,6))
        self.add_button=ttk.Button(self.actions,command=self.add_row)
        self.add_button.pack(side='left')
        self.delete_button=ttk.Button(self.actions,command=self.delete_rows)
        self.delete_button.pack(side='left',padx=6)
        self.calculate_button=ttk.Button(self.actions,command=self.calculate,style='PipePrimary.TButton')
        self.calculate_button.pack(side='left',padx=6)
        self.tree=ttk.Treeview(self,columns=self.COLUMNS,show='headings',height=5,selectmode='extended')
        self.tree.grid(row=1,column=0,sticky='nsew')
        for column,width in zip(self.COLUMNS,(160,100,90,180,165)):
            self.tree.column(column,width=width,minwidth=60,stretch=True,anchor='w' if column in ('name','dn') else 'e')
        self.scroll=ttk.Scrollbar(self,orient='vertical',command=self._scroll)
        self.scroll.grid(row=1,column=1,sticky='ns');self.tree.configure(yscrollcommand=self.scroll.set)
        self.message=ttk.Label(self,wraplength=600)
        self.message.grid(row=2,column=0,columnspan=2,sticky='w',pady=(5,0))
        self.tree.tag_configure('invalid',foreground='#8E1028')
        self.tree.bind('<ButtonRelease-1>',self._click)
        self.tree.bind('<Return>',lambda e:self._edit_active())
        self.tree.bind('<F2>',lambda e:self._edit_active())
        self.tree.bind('<Tab>',lambda e:self._move(1))
        self.tree.bind('<Shift-Tab>',lambda e:self._move(-1))
        self.tree.bind('<Delete>',lambda e:self.delete_rows())
        self.tree.bind('<<TreeviewSelect>>',self._show_row_issue)
        self.tree.bind('<MouseWheel>',lambda e:self.finish_edit(),add='+')
        self.tree.bind('<Configure>',lambda e:self.finish_edit(),add='+')
        self.refresh_texts()
        self.add_row(dirty=False)

    def refresh_texts(self):
        self.configure(text=self.tr('batch.title'))
        for column in self.COLUMNS:self.tree.heading(column,text=self.tr('batch.'+column))
        self.add_button.configure(text=self.tr('common.add'))
        self.delete_button.configure(text=self.tr('common.delete'))
        self.calculate_button.configure(text=self.tr('batch.calculate'))
        self.message.configure(text=self.tr('batch.guidance'))
        for identity in self.inputs:self._render(identity)

    def add_row(self,values=('', '', ''),*,dirty=True):
        self.finish_edit()
        identity=self.tree.insert('', 'end')
        self.inputs[identity]=tuple(values);self._render(identity)
        self.active=(identity,0);self.tree.selection_set(identity);self.tree.focus(identity);self.tree.see(identity)
        if dirty:self.on_dirty()
        return identity

    def delete_rows(self):
        self.finish_edit()
        for identity in self.tree.selection():
            self.inputs.pop(identity,None);self.results.pop(identity,None);self.tree.delete(identity)
        rows=self.tree.get_children()
        self.active=(rows[0],0) if rows else None
        self.on_dirty()
        return 'break'

    def set_cell(self,identity,column,text):
        if column not in range(3):raise ValueError('Result cells are read-only')
        values=list(self.inputs[identity])
        if values[column]==text:return
        values[column]=text;self.inputs[identity]=tuple(values)
        self.results.pop(identity,None);self._render(identity);self.on_dirty()
        self.message.configure(text=self.tr('batch.guidance'))

    def _render(self,identity):
        result=self.results.get(identity)
        diameter=dn=''
        if result:
            if result.issue:
                dn=render_validation_issue(result.issue,SimpleNamespace(translate=self.tr))
            elif result.diameter_mm is not None:
                diameter=format_user_number(result.diameter_mm)
                dn=result.dn or self.tr('batch.no_dn')
        self.tree.item(identity,values=(*self.inputs[identity],diameter,dn),tags=('invalid',) if result and result.issue else ())

    def invalidate_results(self,*_args):
        self.results.clear()
        for identity in self.inputs:self._render(identity)
        self.message.configure(text=self.tr('batch.guidance'))

    def _show_row_issue(self,_event=None):
        selected=self.tree.selection()
        result=self.results.get(selected[0]) if selected else None
        if result and result.issue:self.message.configure(text=self.tree.set(selected[0],'dn'))

    def calculate(self):
        self.finish_edit()
        rows=self.tree.get_children()
        calculated=calculate_rows(self.service,[self.inputs[i] for i in rows],self.standard())
        for identity,result in zip(rows,calculated):
            self.results[identity]=result;self._render(identity)
        self.message.configure(text=self.tr('batch.complete',count=sum(r.diameter_mm is not None for r in calculated),errors=sum(r.issue is not None for r in calculated)))

    def _click(self,event):
        identity=self.tree.identify_row(event.y)
        column=self.tree.identify_column(event.x)
        if identity and column and self.tree.identify_region(event.x,event.y)=='cell':
            index=int(column[1:])-1
            self.finish_edit()
            self.active=(identity,min(index,2))
            if index<3:self.start_edit(identity,index)
            else:self.message.configure(text=str(self.tree.set(identity,'dn')) or self.tr('batch.guidance'))

    def _edit_active(self):
        if self.active:self.start_edit(*self.active)
        return 'break'

    def start_edit(self,identity,column):
        if column not in range(3):return
        self.finish_edit();self.tree.see(identity);self.tree.update_idletasks()
        bounds=self.tree.bbox(identity,self.COLUMNS[column])
        if not bounds:return
        self.active=(identity,column)
        self.tree.selection_set(identity);self.tree.focus(identity)
        self.edit_original=self.inputs[identity][column]
        self.edit_value=tk.StringVar(self,value=self.edit_original)
        self.editor=ttk.Entry(self.tree,textvariable=self.edit_value,justify='left' if column==0 else 'right')
        self.editor.place(x=bounds[0],y=bounds[1],width=bounds[2],height=bounds[3])
        self.edit_value.trace_add('write',lambda *_:self.set_cell(identity,column,self.edit_value.get()))
        self.editor.bind('<Tab>',lambda e:self._move(1))
        self.editor.bind('<Shift-Tab>',lambda e:self._move(-1))
        self.editor.bind('<Return>',lambda e:self._move_row(1))
        self.editor.bind('<Down>',lambda e:self._move_row(1))
        self.editor.bind('<Up>',lambda e:self._move_row(-1))
        self.editor.bind('<Escape>',lambda e:self.finish_edit(cancel=True))
        self.editor.bind('<FocusOut>',lambda e:self.finish_edit() if e.widget is self.editor else None)
        self.editor.focus_set();self.editor.select_range(0,'end')

    def finish_edit(self,*,cancel=False):
        editor,self.editor=self.editor,None
        if editor is not None:
            if cancel and self.active:self.set_cell(*self.active,self.edit_original)
            editor.destroy()
        return 'break'

    def _move(self,step):
        if not self.active:return 'break'
        identity,column=self.active;rows=list(self.tree.get_children())
        index=rows.index(identity)*3+column+step
        self.finish_edit()
        if index<0:index=0
        if index>=len(rows)*3:rows.append(self.add_row())
        self.start_edit(rows[index//3],index%3)
        return 'break'

    def _move_row(self,step):
        if not self.active:return 'break'
        identity,column=self.active;rows=list(self.tree.get_children())
        index=max(0,rows.index(identity)+step)
        self.finish_edit()
        if index>=len(rows):rows.append(self.add_row())
        self.start_edit(rows[index],column)
        return 'break'

    def _scroll(self,*args):
        self.finish_edit();self.tree.yview(*args)

    def export_inputs(self):
        self.finish_edit()
        return [list(self.inputs[i]) for i in self.tree.get_children()]

    def load_inputs(self,rows):
        self.finish_edit()
        self.tree.delete(*self.tree.get_children());self.inputs.clear();self.results.clear();self.active=None
        if isinstance(rows,list):
            for row in rows:
                if isinstance(row,(list,tuple)) and len(row)==3 and all(isinstance(v,str) for v in row):self.add_row(row,dirty=False)
        if not self.inputs:self.add_row(dirty=False)
        self.message.configure(text=self.tr('batch.guidance'))
