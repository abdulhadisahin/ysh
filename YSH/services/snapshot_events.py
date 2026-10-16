"""Small success-event bridge; assembly and persistence stay outside page callbacks."""
from __future__ import annotations


def notify_success(page: object, stage: str, result: object, *, selection: object = None) -> None:
    """Notify only an attached workflow; loading/editing/discovery never calls this bridge."""
    listener=getattr(page,'_snapshot_listener',None)
    if not callable(listener): return
    panel=getattr(page,'_warning_panel',None)
    findings=getattr(panel,'findings',getattr(page,'_engineering_findings',()))
    listener(stage,result,selection,tuple(findings))
