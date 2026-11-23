"""Sidebar icon lanes and native left-aligned text are independent of captions."""
from types import SimpleNamespace
import tkinter as tk
from tkinter import ttk, font
import pytest

from ui.main_window import MainWindow
from ui.widgets.rounded_button import ADD_BUTTON_PALETTE
from .test_fire_phase5cd_navigation import application, shell
from .test_ui_consistency_phase7 import review_language


@pytest.mark.parametrize('size',[(1100,700),(1440,900)])
@pytest.mark.parametrize('language',['tr','en'])
def test_sidebar_fixed_columns_preserve_geometry(shell,size,language):
    w=shell;root=w._root;old=w._localization.language
    try:
        review_language(w,language);root.deiconify();root.geometry(f'{size[0]}x{size[1]}');root.update()
        from .test_toolbar_sidebar_cleanup import assert_compact_sidebar
        assert_compact_sidebar(w)
        buttons=(w._toolbar_new,w._toolbar_open,w._toolbar_save,w._toolbar_save_as,w._toolbar_delete)
        assert w._sidebar.winfo_width()==300
        widths=[button.winfo_width() for button in buttons]
        assert max(widths)-min(widths)<=1
        heights={button.winfo_height() for button in buttons}
        assert len(heights)==1
        for index,button in enumerate(buttons):
            assert button._square_size==86 and button._icon_size==79
            assert button._icon_only and button.cget('text')==''
            assert button.cget('command')
            if index:assert button.winfo_rootx()>buttons[index-1].winfo_rootx()
    finally:w._localization.set_language(old)


def test_rendered_icon_centers_and_text_lane_ignore_icon_aspect_and_label_length(shell):
    root=shell._root;root.deiconify()
    window=tk.Toplevel(root);window.geometry('260x120')
    calls=[]
    try:
        buttons=[]
        for index,(width,height,text) in enumerate(((16,32,'A'),(32,16,'Refresh'))):
            button=MainWindow._create_sidebar_button(window,text,lambda i=index:calls.append(i),
                style='RoundedAdd.TButton',palette=ADD_BUTTON_PALETTE,icon_name='new')
            button.pack(fill='x')
            icon=tk.PhotoImage(master=button,width=width,height=height);icon.put('#FFFFFF',to=(0,0,width,height))
            button._icon_image=SimpleNamespace(rendered=icon)
            button.configure(text=text);buttons.append(button)
        root.update()
        centers=[];prefixes=[]
        for button in buttons:
            image=button._create_surface(240,44,'#102B46','#102B46')
            white=[x for x in range(240) if image.get(x,22)==(255,255,255)]
            assert white
            centers.append((min(white)+max(white))/2)
            label=button._icon_text(button._logical_text)
            prefixes.append(label[:len(label)-len(label.lstrip())])
            button.invoke()
        assert centers==[21.5,21.5]
        assert prefixes[0]==prefixes[1]
        assert calls==[0,1]
    finally:window.destroy()
