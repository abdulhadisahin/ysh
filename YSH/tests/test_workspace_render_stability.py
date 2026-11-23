"""Complete watermark fitting and deterministic viewport resource lifecycles."""
import tkinter as tk
from tkinter import ttk

import pytest
from PIL import Image

from ui.widgets.scrollable_frame import ScrollableFrame
from ui.widgets.workspace_backdrop import (
    WorkspaceBackdrop, compose_backdrop, watermark_bounds, load_watermark_emblem,
)
from ui.theme import colors
from ui.assets import d243_watermark_logo_path
from .test_fire_phase5cd_navigation import application, shell


@pytest.mark.parametrize('size',[(760,390),(1100,700),(1440,900),(1700,1000)])
@pytest.mark.parametrize('source_size',[(400,600),(600,400),(500,500)])
def test_complete_watermark_fits_including_bottom_edge(size,source_size):
    emblem=Image.new('RGBA',source_size,(30,60,90,255))
    # A distinct bottom line represents the previously clipped office name.
    emblem.paste((210,30,50,255),(0,source_size[1]-20,source_size[0],source_size[1]))
    before=emblem.tobytes()
    x,y,width,height=watermark_bounds(size,source_size)
    assert x>0 and y>0 and x+width<size[0] and y+height<size[1]
    assert width/height==pytest.approx(source_size[0]/source_size[1],rel=.005)
    result=compose_backdrop(size,emblem)
    assert result.size==size and emblem.tobytes()==before
    # Compare the entire fitted region, preserving alpha and every bottom row.
    expected=Image.new('RGB',size,colors.WORKSPACE_SURFACE)
    fitted=emblem.resize((width,height),Image.Resampling.LANCZOS)
    fitted.putalpha(fitted.getchannel('A').point(lambda alpha:round(alpha*.24)))
    expected.paste(fitted,(x,y),fitted)
    assert result.tobytes()==expected.tobytes()
    assert result.getpixel((x+width//2,y+height-1))!=result.getpixel((0,0))


def test_decoded_emblem_is_shared_without_mutating_source(tmp_path,monkeypatch):
    path=tmp_path/'emblem.png'
    Image.new('RGBA',(80,100),(30,60,90,255)).save(path)
    reads=[];original=Image.open
    def opened(*args,**kwargs):
        reads.append(args[0]);return original(*args,**kwargs)
    monkeypatch.setattr(Image,'open',opened)
    first=load_watermark_emblem(path);before=first.tobytes()
    second=load_watermark_emblem(path)
    assert first is second and reads==[path]
    compose_backdrop((1100,700),first)
    assert first.tobytes()==before


@pytest.mark.parametrize('size',[(760,390),(1100,700),(1440,900)])
def test_canonical_watermark_keeps_the_complete_office_name_region(size):
    emblem=load_watermark_emblem(d243_watermark_logo_path())
    x,y,width,height=watermark_bounds(size,emblem.size)
    result=compose_backdrop(size,emblem)
    fitted=emblem.resize((width,height),Image.Resampling.LANCZOS)
    fitted.putalpha(fitted.getchannel('A').point(lambda alpha:round(alpha*.24)))
    expected=Image.new('RGB',(width,height),colors.WORKSPACE_SURFACE)
    expected.paste(fitted,(0,0),fitted)
    # The canonical lower arc contains "Dizayn Proje Ofisi". Verify all of
    # that region, including the bottom edge, reaches the composed viewport.
    name_top=height*3//4
    actual_region=result.crop((x,y+name_top,x+width,y+height))
    expected_region=expected.crop((0,name_top,width,height))
    assert actual_region.tobytes()==expected_region.tobytes()
    from PIL import ImageChops
    assert ImageChops.difference(actual_region,Image.new('RGB',actual_region.size,colors.WORKSPACE_SURFACE)).getbbox()
    assert 0<=x and 0<=y and x+width<=size[0] and y+height<=size[1]


@pytest.fixture
def viewport():
    root=tk.Tk();root.geometry('800x600')
    host=ScrollableFrame(root);host.pack(fill='both',expand=True)
    backdrop=WorkspaceBackdrop(host);root.update();backdrop.paint()
    try:yield root,host,backdrop
    finally:root.destroy()


def test_explicit_paint_consumes_pending_timer_and_destroy_cancels_it(viewport):
    root,host,backdrop=viewport
    backdrop.request();old_job=backdrop.pending
    assert old_job in root.tk.call('after','info')
    backdrop.paint()
    assert old_job not in root.tk.call('after','info')
    assert backdrop.pending is None
    backdrop.request();job=backdrop.pending
    backdrop.request()
    assert backdrop.pending==job
    host.destroy()
    assert job not in root.tk.call('after','info')
    assert backdrop.pending is None
    backdrop.request();backdrop.paint()
    assert backdrop.pending is None
    root.update()


def test_resize_and_unchanged_paint_keep_one_background(viewport):
    root,host,backdrop=viewport
    ttk.Frame(host.content,height=1800).pack(fill='x')
    for size in ('1100x700','1440x900','1100x700'):
        root.geometry(size);root.update();backdrop.paint()
        assert backdrop.size==(host.canvas.winfo_width(),host.canvas.winfo_height())
        assert host.canvas.find_withtag('workspace_backdrop')==(backdrop.item,)
        assert host.canvas.find_all().index(backdrop.item)<host.canvas.find_all().index(host._window)
        photo=backdrop.background_photo;images=set(root.tk.call('image','names'))
        backdrop.paint();backdrop.paint()
        assert backdrop.background_photo is photo
        assert set(root.tk.call('image','names'))==images
        host.canvas.yview_moveto(.5);root.update();backdrop.paint()
        assert tuple(host.canvas.coords(backdrop.item))==(
            host.canvas.canvasx(0),host.canvas.canvasy(0))
        assert host.canvas.find_withtag('workspace_backdrop')==(backdrop.item,)
        host.canvas.yview_moveto(0);root.update();backdrop.paint()


def test_repeated_fuel_fire_navigation_reuses_widgets_and_backgrounds(shell):
    window=shell;root=window._root;root.deiconify();root.geometry('1100x700')
    def visit():
        found=[]
        for family in ('fuel','fire'):
            window._show_family(family,dirty=False);root.update()
            host=window._page_host if family=='fuel' else window._fire_workspace.host
            for viewport in host._page_keys.values():
                host.select(viewport);root.update()
                backdrop=viewport._workspace_backdrop;backdrop.paint()
                assert viewport.canvas.find_withtag('workspace_backdrop')==(backdrop.item,)
                found.append((viewport,backdrop,backdrop.emblem,backdrop.background_photo))
        return found
    def widgets(widget):
        return 1+sum(widgets(child) for child in widget.winfo_children())
    first=visit();count=widgets(root);images=set(root.tk.call('image','names'))
    assert len(first)==6 and len({id(item[2]) for item in first})==1
    for _ in range(2):
        assert visit()==first
        assert widgets(root)==count
        assert set(root.tk.call('image','names'))==images
