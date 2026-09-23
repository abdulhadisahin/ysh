"""Reference-ship model for fuel transfer pump estimates."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from uuid import UUID, uuid4
def _now()->datetime:return datetime.now(timezone.utc)
@dataclass(slots=True)
class PumpReference:
    """A user-managed ship fuel and pump capacity reference."""
    ship_name:str; fuel_capacity_m3:float; pump_capacity_m3h:float; description:str=""; source:str="User"; id:UUID=field(default_factory=uuid4); created_at:datetime=field(default_factory=_now); modified_at:datetime=field(default_factory=_now)
    def to_dict(self)->dict[str,object]: """Serialize the record.""";data=asdict(self);data["id"]=str(self.id);data["created_at"]=self.created_at.isoformat();data["modified_at"]=self.modified_at.isoformat();return data
