"""Snapshot identity plus immutable canonical calculation evidence."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from uuid import UUID, uuid4

from engineering.module_registry import ModuleCode
from engineering.formula.models import FormulaStep
from engineering.system_context import SystemContext
from engineering.snapshots.serialization import canonical, decode


@dataclass(frozen=True, slots=True, kw_only=True)
class CalculationSnapshot:
    """Nested mutable results are copied into canonical JSON, never retained by reference."""
    module_code: ModuleCode
    stage: str
    model_version: str
    evidence_json: str
    project_id: UUID | None = None
    snapshot_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda:datetime.now(timezone.utc))
    schema_version: int = 1

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError('Unsupported snapshot schema')
        if not isinstance(self.module_code,ModuleCode) or not isinstance(self.snapshot_id,UUID):
            raise ValueError('Invalid snapshot identity/module')
        if self.project_id is not None and not isinstance(self.project_id,UUID):
            raise ValueError('Invalid snapshot project')
        if not isinstance(self.created_at,datetime) or self.created_at.utcoffset() is None:
            raise ValueError('Snapshot time must be timezone aware')
        if not self.stage or not self.model_version:
            raise ValueError('Snapshot calculation model is required')
        evidence=json.loads(self.evidence_json)
        if not isinstance(evidence,dict) or not {'facts','steps','context','summary'} <= evidence.keys():
            raise ValueError('Incomplete snapshot evidence')
        if not evidence['steps'] or not evidence['facts']:
            raise ValueError('Snapshot requires successful calculation evidence')
        canonical(evidence)
        decode(SystemContext,evidence['context'])
        for step in evidence['steps']: decode(FormulaStep,step)
        object.__setattr__(self,'evidence_json',canonical(evidence))

    @property
    def evidence(self) -> dict[str, object]:
        """Return a detached copy: callers cannot change immutable history."""
        return json.loads(self.evidence_json)

    @property
    def formula_steps(self) -> tuple[FormulaStep, ...]:
        """Read frozen steps without a calculator, source resolver or live context."""
        return tuple(decode(FormulaStep,item) for item in self.evidence['steps'])

    @property
    def context(self) -> SystemContext:
        """Read historical names and identities independently of today's catalogs."""
        return decode(SystemContext,self.evidence['context'])

    def to_payload(self) -> dict[str, object]:
        """Serialize stable UUIDs/enums and ISO timestamps with a dedicated version."""
        return {'snapshot_schema_version':self.schema_version,'snapshot_id':str(self.snapshot_id),
                'project_id':str(self.project_id) if self.project_id else None,
                'module_code':self.module_code.value,'stage':self.stage,'model_version':self.model_version,
                'created_at':self.created_at.isoformat(),'evidence':self.evidence}

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> CalculationSnapshot:
        """Reject unsupported/corrupt payloads instead of rebuilding history from current data."""
        return cls(schema_version=payload['snapshot_schema_version'],snapshot_id=UUID(payload['snapshot_id']),
            project_id=UUID(payload['project_id']) if payload.get('project_id') else None,
            module_code=ModuleCode(payload['module_code']),stage=payload['stage'],model_version=payload['model_version'],
            created_at=datetime.fromisoformat(payload['created_at']),evidence_json=canonical(payload['evidence']))

    def to_json(self) -> str:
        """Return deterministic, full-precision storage representation."""
        return canonical(self.to_payload())
