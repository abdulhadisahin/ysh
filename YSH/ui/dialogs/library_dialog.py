"""Reusable ttk editor for local engineering-library records."""
from __future__ import annotations
import tkinter as tk
from collections.abc import Callable, Sequence
from typing import Any
from tkinter import messagebox, ttk
from uuid import UUID

class LibraryDialog:
    """Provides searchable CRUD controls for one service-backed library."""
    def __init__(self, parent: tk.Misc, title: str, columns: Sequence[tuple[str, str]], fields: Sequence[tuple[str, str]], list_items: Callable[[], Sequence[Any]], create_item: Callable[..., Any], update_item: Callable[[Any], Any], delete_item: Callable[[UUID], None], get_item: Callable[[UUID], Any]) -> None:
        """Create a modal dialog using supplied service operations only."""
        self._title, self._columns, self._fields = title, columns, fields
        self._list_items, self._create_item, self._update_item = list_items, create_item, update_item
        self._delete_item, self._get_item, self._editing = delete_item, get_item, None
        self._dialog=tk.Toplevel(parent); self._dialog.title(title); self._dialog.transient(parent); self._dialog.geometry("980x580"); self._dialog.minsize(760,460)
        self._build(); self._refresh(); self._dialog.grab_set(); self._dialog.bind("<Escape>",lambda event:self._close())
    def _build(self)->None:
        frame=ttk.Frame(self._dialog,padding=12);frame.pack(fill="both",expand=True); frame.columnconfigure(0,weight=1);frame.rowconfigure(1,weight=1)
        top=ttk.Frame(frame);top.grid(row=0,column=0,sticky="ew",pady=(0,8)); ttk.Label(top,text="Search:").pack(side="left");self._search=tk.StringVar();self._search.trace_add("write",lambda *_:self._refresh());ttk.Entry(top,textvariable=self._search,width=40).pack(side="left",padx=6)
        self._tree=ttk.Treeview(frame,columns=[key for key,_ in self._columns],show="headings",selectmode="browse")
        for key,label in self._columns:self._tree.heading(key,text=label);self._tree.column(key,width=150,anchor="w")
        self._tree.grid(row=1,column=0,sticky="nsew"); self._tree.bind("<Double-1>",lambda event:self._edit());self._tree.bind("<Return>",lambda event:self._edit());self._tree.bind("<Delete>",lambda event:self._delete())
        actions=ttk.Frame(frame);actions.grid(row=2,column=0,sticky="e",pady=(8,0));ttk.Button(actions,text="Add",command=self._add).pack(side="left");ttk.Button(actions,text="Edit",command=self._edit).pack(side="left",padx=5);ttk.Button(actions,text="Delete",command=self._delete).pack(side="left");ttk.Button(actions,text="Close",command=self._close).pack(side="left",padx=(16,0))
    def _refresh(self)->None:
        for row in self._tree.get_children():self._tree.delete(row)
        query=self._search.get().casefold()
        for item in self._list_items():
            values=tuple(self._display(item,key) for key,_ in self._columns)
            if not query or query in " ".join(values).casefold():self._tree.insert("","end",iid=str(item.id),values=values)
    @staticmethod
    def _display(item:Any,key:str)->str:
        value=getattr(item,key)
        return "Not verified" if value is None else str(value)
    def _selected(self)->Any|None:
        selected=self._tree.selection()
        return self._get_item(UUID(selected[0])) if selected else None
    def _add(self)->None:self._open_editor(None)
    def _edit(self)->None:
        item=self._selected()
        if item is not None:self._open_editor(item)
    def _open_editor(self,item:Any|None)->None:
        editor=tk.Toplevel(self._dialog);editor.title(f"{'Edit' if item else 'Add'} {self._title.rstrip('s')}");editor.transient(self._dialog);editor.grab_set();body=ttk.Frame(editor,padding=14);body.grid();variables:dict[str,tk.StringVar]={}
        for row,(key,label) in enumerate(self._fields):
            ttk.Label(body,text=f"{label}:").grid(row=row,column=0,sticky="w",pady=3);variables[key]=tk.StringVar(value="" if item is None or getattr(item,key) is None else str(getattr(item,key)));ttk.Entry(body,textvariable=variables[key],width=48).grid(row=row,column=1,sticky="ew",padx=(8,0),pady=3)
        def save()->None:
            try:
                values={key:self._convert(key,var.get().strip()) for key,var in variables.items()}
                if item is None:self._create_item(**values)
                else:
                    for key,value in values.items():setattr(item,key,value)
                    self._update_item(item)
            except (ValueError,LookupError) as error:
                messagebox.showerror("Invalid Library Record",str(error),parent=editor);return
            editor.destroy();self._refresh()
        buttons=ttk.Frame(body);buttons.grid(row=len(self._fields),column=1,sticky="e",pady=(12,0));ttk.Button(buttons,text="Cancel",command=editor.destroy).pack(side="left");ttk.Button(buttons,text="Save",command=save).pack(side="left",padx=(6,0));editor.bind("<Return>",lambda event:save());editor.bind("<Escape>",lambda event:editor.destroy());editor.focus_set()
    @staticmethod
    def _convert(key:str,value:str)->object:
        if key in {"yield_strength_mpa"}:return None if not value else float(value)
        if key in {"roughness_mm","outside_diameter_mm","wall_thickness_mm","inside_diameter_mm","value"}:return float(value)
        return value
    def _delete(self)->None:
        item=self._selected()
        if item is None:return
        if messagebox.askyesno("Delete Library Record",f"Delete '{getattr(item,'display_name',getattr(item,'name',getattr(item,'key','record')))}'?",parent=self._dialog):
            try:self._delete_item(item.id)
            except (ValueError,LookupError) as error:messagebox.showerror("Cannot Delete",str(error),parent=self._dialog);return
            self._refresh()
    def _close(self)->str:
        self._dialog.grab_release();self._dialog.destroy();return "break"
