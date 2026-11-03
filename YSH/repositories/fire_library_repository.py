"""Typed Fire adapter over existing generic numeric Library rows; no DDL/seed."""
from dataclasses import replace
from datetime import datetime, timezone
import json
from uuid import UUID

from core.engineering_constant import EngineeringConstant
from engineering.fire.library import FireEngineeringDataRecord, VERIFIED
from engineering.fire.enums import FireSourceStatus
from engineering.snapshots.serialization import canonical
from repositories.engineering_constant_repository import EngineeringConstantRepository
from repositories.source_repository import SourceRepository

FIRE_RECORD_PREFIX = 'FIRE.LIBRARY.'


class FireLibraryRepository:
    def __init__(self,database):
        self.constants=EngineeringConstantRepository(database)
        self.sources=SourceRepository(database)

    def _decode(self,row):
        data=json.loads(row.description)
        if data.pop('version')!=1:raise ValueError('Unsupported Fire record version')
        data.update(id=str(row.id),value=row.value,unit=row.unit)
        source=self.sources.get(UUID(data['source_id'])) if data.get('source_id') else None
        data['source']=json.loads(canonical(source.reference)) if source else None
        # Resolve the current source for recommendations. Frozen project/snapshot
        # copies never pass through this repository again.
        try:return FireEngineeringDataRecord.from_payload(data)
        except ValueError:
            if data['source_status'] not in VERIFIED:raise
            data['source_status']=FireSourceStatus.SOURCE_REQUIRED.value
            return FireEngineeringDataRecord.from_payload(data)

    def get(self,identity):
        row=self.constants.get(identity)
        return self._decode(row) if row and row.key.startswith(FIRE_RECORD_PREFIX) else None

    def get_all(self):
        return tuple(self._decode(row) for row in self.constants.get_all() if row.key.startswith(FIRE_RECORD_PREFIX))

    def save(self,record):
        source=self.sources.get(record.source_id) if record.source_id else None
        if record.source_id and source is None:raise ValueError('Unknown Fire source identity')
        record=replace(record,source=source.reference if source else None)
        current=self.constants.get(record.id)
        if current and not current.key.startswith(FIRE_RECORD_PREFIX):raise ValueError('Not a Fire record')
        revision=self._decode(current).revision+1 if current else 1
        record=replace(record,revision=revision)
        payload=record.to_payload();payload.pop('id');payload.pop('value');payload.pop('unit');payload.pop('source')
        payload['version']=1
        row=EngineeringConstant(id=record.id,key=FIRE_RECORD_PREFIX+str(record.id),display_name=record.parameter_type.value,
            value=record.value,unit=record.unit,description=json.dumps(payload,ensure_ascii=False,allow_nan=False),
            source='Fire Library / source-aware record',is_system=False,
            created_at=current.created_at if current else datetime.now(timezone.utc))
        (self.constants.update if current else self.constants.create)(row)
        return record
