"""Darcy friction-factor methods including deterministic Colebrook solving."""
from __future__ import annotations
import math
def turbulent_friction_factor(reynolds:float,relative_roughness:float,tolerance:float=1e-12,iterations:int=100)->float:
    """Solve Colebrook-White by fixed-point iteration."""
    factor=.25/(math.log10(relative_roughness/3.7+5.74/(reynolds**.9))**2)
    for _ in range(iterations):
        new=1/(-2*math.log10(relative_roughness/3.7+2.51/(reynolds*math.sqrt(factor))))**2
        if abs(new-factor)<tolerance:return new
        factor=new
    raise ValueError("Colebrook-White friction factor did not converge.")
