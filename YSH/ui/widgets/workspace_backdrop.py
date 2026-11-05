"""Viewport-fixed branding with composited light surfaces; native text stays opaque.

Tk has no per-child alpha. Background-only frames receive composited crops;
labels and labelled cards keep their native painters with gentle opaque tones.
Controls and semantic colors are never given window alpha or overlaid artwork.
"""
from dataclasses import dataclass
from itertools import count
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageStat, ImageTk
from ui.assets import d243_watermark_logo_path
from ui.theme import colors
from ui.widgets.cards import ResultCard


PROTECTED = ('warning','critical','error','success','verified','status','source','info','unavailable')
_SURFACE_IDS = count(1)


def light_surface(rgb):
    return min(rgb)>195 and max(rgb)-min(rgb)<65


def compose_backdrop(size, emblem):
    width,height=size
    image=Image.new('RGB',size,colors.WORKSPACE_SURFACE)
    if emblem is None:return image
    side=max(820,round(max(width*1.12,height*1.15)))
    scale=side/max(emblem.size)
    logo=emblem.resize((max(1,round(emblem.width*scale)),max(1,round(emblem.height*scale))),Image.Resampling.LANCZOS)
    logo.putalpha(logo.getchannel('A').point(lambda alpha:round(alpha*.24)))
    # A small alpha-mass correction balances asymmetric artwork optically.
    alpha=logo.getchannel('A').resize((64,64),Image.Resampling.BILINEAR)
    weights=list(alpha.get_flattened_data());mass=sum(weights)
    cx=sum((i%64+.5)*value for i,value in enumerate(weights))/mass if mass else 32
    cy=sum((i//64+.5)*value for i,value in enumerate(weights))/mass if mass else 32
    dx=max(-width*.015,min(width*.015,(32-cx)/64*logo.width*.2))
    dy=max(-height*.015,min(height*.015,(32-cy)/64*logo.height*.2))
    x=round((width-logo.width)/2+dx);y=round((height-logo.height)/2+dy)
    image.paste(logo,(x,y),logo)
    return image


def composite_surface(backdrop,bounds,rgb,opacity):
    left,top,width,height=bounds
    # Off-viewport portions are plain; only the visible crop needs branding.
    patch=Image.new('RGB',(width,height),rgb)
    x0,y0=max(0,left),max(0,top)
    x1,y1=min(backdrop.width,left+width),min(backdrop.height,top+height)
    if x1>x0 and y1>y0:
        patch.paste(backdrop.crop((x0,y0,x1,y1)),(x0-left,y0-top))
    return Image.blend(patch,Image.new('RGB',patch.size,rgb),opacity)


@dataclass
class Surface:
    photo: object
    element: str
    styles: dict
    size: tuple = (1,1)
    signature: tuple | None = None


class WorkspaceBackdrop:
    def __init__(self,host):
        self.host=host;self.canvas=host.canvas;self.style=ttk.Style(host)
        self.surfaces={};self.tints={};self.pending=None;self.painting=False;self.image=None;self.size=None
        self.emblem=None;self.background_photo=None;self.paint_count=0;self.scroll_position=None;self.background_position=None
        try:
            path=d243_watermark_logo_path()
            if path:
                with Image.open(path) as source:
                    self.emblem=source.convert('RGBA')
                bounds=self.emblem.getchannel('A').getbbox()
                if bounds:self.emblem=self.emblem.crop(bounds)
        except (OSError,ValueError):pass
        self.item=self.canvas.create_image(0,0,anchor='nw',tags=('workspace_backdrop',))
        self.canvas.tag_lower(self.item,host._window)
        self.canvas.configure(yscrollcommand=self._scrolled)
        self.canvas.bind('<Configure>',self.request,add='+')
        host.content.bind('<Configure>',self.request,add='+')
        host.bind('<Destroy>',self._destroy,add='+')
        self.request()

    def _destroy(self,event):
        if event.widget is self.host and self.pending is not None:
            self.host.after_cancel(self.pending);self.pending=None

    def _scrolled(self,first,last):
        self.host.scrollbar.set(first,last)
        position=(first,last)
        if position!=self.scroll_position:
            self.scroll_position=position;self.request()

    def request(self,event=None):
        if self.painting or self.pending is not None:return
        self.pending=self.host.after(40,self.paint)

    def paint(self):
        self.pending=None
        if not self.host.winfo_viewable():return
        self.painting=True
        try:
            width,height=self.canvas.winfo_width(),self.canvas.winfo_height()
            if width<20 or height<20:return
            if self.size!=(width,height):
                self.size=(width,height);self.image=compose_backdrop(self.size,self.emblem)
                self.background_photo=ImageTk.PhotoImage(self.image,master=self.host)
                self.canvas.itemconfigure(self.item,image=self.background_photo)
            position=(self.canvas.canvasx(0),self.canvas.canvasy(0))
            if position!=self.background_position:
                self.canvas.coords(self.item,*position);self.background_position=position
            self.canvas.tag_lower(self.item,self.host._window)
            self._visit(self.host.content)
            for widget in tuple(self.surfaces):
                if not widget.winfo_exists():del self.surfaces[widget]
            for widget in tuple(self.tints):
                if not widget.winfo_exists():del self.tints[widget]
            self.paint_count+=1
        finally:self.painting=False

    def _visit(self,widget):
        if not widget.winfo_viewable():return
        if widget.winfo_toplevel() is not self.host.winfo_toplevel():return
        kind=widget.winfo_class()
        base=str(widget.cget('style')) if isinstance(widget,ttk.Widget) else ''
        original=base.split('.',2)[2] if base.startswith(('Glass.','Frost.')) else base
        # Results and every descendant keep their solid native surfaces.
        if (isinstance(widget,ResultCard) or 'result' in original.lower()) and getattr(widget,'result_surface_opaque',True):
            self._restore_native(widget)
            return
        if any(word in original.lower() for word in PROTECTED):return
        if kind in ('TFrame','TLabelframe','TLabel'):
            if kind!='TLabel' or not widget.cget('image'):
                self._surface(widget,original or kind)
        for child in widget.winfo_children():self._visit(child)

    def _surface(self,widget,base):
        color=self.style.lookup(base,'background')
        if not color:return
        try:rgb=tuple(round(value/257) for value in widget.winfo_rgb(color))
        except tk.TclError:return
        if not light_surface(rgb):return
        x=widget.winfo_rootx()-self.canvas.winfo_rootx()
        y=widget.winfo_rooty()-self.canvas.winfo_rooty()
        width,height=widget.winfo_width(),widget.winfo_height()
        if x>=self.size[0] or y>=self.size[1] or x+width<=0 or y+height<=0:return
        if width<2 or height<2:return
        opacity=.30 if color.lower() in (colors.WORKSPACE_SURFACE.lower(),'#f1f7fa') else .94 if max(rgb)-min(rgb)>12 else .80
        if widget.winfo_class()!='TFrame' and not (getattr(widget,'composite_panel',False) or base=='Fire.Card.TLabelframe'):
            self._native_tint(widget,base,(x,y,width,height),rgb,opacity)
            return
        entry=self.surfaces.get(widget)
        if entry is None:
            photo=ImageTk.PhotoImage(Image.new('RGB',(1,1),rgb),master=self.host)
            element=f'GlassSurface{next(_SURFACE_IDS)}'
            self.style.element_create(element,'image',photo,border=1,
                                      width=0,height=0,sticky='nswe')
            entry=self.surfaces[widget]=Surface(photo,element,{})
        if base not in entry.styles:
            layout=self.style.layout(base)
            if not layout:return
            name=f'Glass.{entry.element.removeprefix("GlassSurface")}.{base}'
            options=dict(layout[0][1]);options['sticky']='nswe'
            self.style.layout(name,[(entry.element,options)])
            entry.styles[base]=name
            if widget.winfo_class()=='TLabelframe':
                self.style.configure(name+'.Label',background=color)
        signature=(x,y,width,height,rgb,opacity,self.size)
        if signature!=entry.signature:
            patch=composite_surface(self.image,(x,y,width,height),rgb,opacity)
            if entry.size!=(width,height):
                entry.photo.tk.call(str(entry.photo),'configure','-width',width,'-height',height)
                entry.size=(width,height)
            entry.photo.paste(patch);entry.signature=signature
        if str(widget.cget('style'))!=entry.styles[base]:widget.configure(style=entry.styles[base])

    def _restore_native(self,widget):
        """Restore an opaque result subtree after an empty-state composite."""
        if isinstance(widget,ttk.Widget):
            style=str(widget.cget('style'))
            if style.startswith(('Glass.','Frost.')):
                widget.configure(style=style.split('.',2)[2])
        self.surfaces.pop(widget,None);self.tints.pop(widget,None)
        for child in widget.winfo_children():self._restore_native(child)

    def _native_tint(self,widget,base,bounds,rgb,opacity):
        """Never replace text/caption layouts: use a gentle opaque native tone."""
        self.surfaces.pop(widget,None)
        signature=(bounds,rgb,opacity,self.size)
        entry=self.tints.get(widget)
        if entry is not None and entry[0]==base and entry[3]==signature:
            if str(widget.cget('style'))!=entry[1]:widget.configure(style=entry[1])
            return
        x,y,width,height=bounds
        crop=self.image.crop((max(0,x),max(0,y),min(self.size[0],x+width),min(self.size[1],y+height)))
        mean=ImageStat.Stat(crop).mean
        opacity=max(opacity,.94 if widget.winfo_class()=='TLabel' else .78)
        tone='#'+''.join(f'{round(channel*opacity+sample*(1-opacity)):02x}' for channel,sample in zip(rgb,mean))
        if entry is None or entry[0]!=base:
            entry=(base,f'Frost.{next(_SURFACE_IDS)}.{base}',None,None)
        name=entry[1]
        if entry[2]!=tone:
            self.style.configure(name,background=tone)
            if widget.winfo_class()=='TLabelframe':self.style.configure(name+'.Label',background=tone)
        self.tints[widget]=(base,name,tone,signature)
        if str(widget.cget('style'))!=name:widget.configure(style=name)
