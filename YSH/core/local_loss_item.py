"""Local hydraulic-loss input model."""
from __future__ import annotations
from dataclasses import dataclass
@dataclass(slots=True)
class LocalLossItem:
    """One component quantity and Darcy local-loss coefficient."""
    name:str;quantity:int;k_coefficient:float
    @property
    def subtotal_k(self)->float:"""Return quantity multiplied by K.""";return self.quantity*self.k_coefficient
