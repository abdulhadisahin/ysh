"""Test-only native Tk mapping/layout barrier; no sleeps or relaxed bounds."""
from time import monotonic


def settle_geometry(root, *widgets, timeout=3.0):
    """Pump Tk until mapped geometry is unchanged across complete event passes.

    Never remap an individual control: an actually hidden control must fail.
    The deadline bounds failure diagnostics rather than delaying successful tests.
    """
    targets=(root,*widgets)
    previous=None
    root.update_idletasks()
    root.update()
    deadline=monotonic()+timeout
    while monotonic()<deadline:
        root.update_idletasks()
        root.update()
        root.update_idletasks()
        geometry=tuple((item.winfo_viewable(),item.winfo_rootx(),item.winfo_rooty(),
                        item.winfo_width(),item.winfo_height()) for item in targets)
        mapped=all(visible and width>1 and height>1 for visible,_,_,width,height in geometry)
        if mapped and geometry==previous:
            return
        previous=geometry
    raise AssertionError(f'Tk mapping/layout did not settle: actual={previous}')
