"""Source-aware Fire reference records; no numerical defaults or calculators."""
from dataclasses import dataclass, field, asdict
from datetime import date
from enum import StrEnum
import json
import math
from uuid import UUID, uuid4

from engineering.fire.enums import FireSourceStatus
from engineering.provenance import SourceReference, SourceType, VerificationStatus
from engineering.snapshots.serialization import canonical


class FireParameter(StrEnum):
    APPLICATION_RATE = 'FIRE.FOAM.APPLICATION_RATE'
    DURATION = 'FIRE.FOAM.DURATION'
    CONCENTRATION = 'FIRE.FOAM.CONCENTRATION'
    HW_COEFFICIENT = 'FIRE.HW.COEFFICIENT'


UNITS = {FireParameter.APPLICATION_RATE:'L/(min·m²)', FireParameter.DURATION:'min',
         FireParameter.CONCENTRATION:'1', FireParameter.HW_COEFFICIENT:'1'}
FIELD_PARAMETERS = {'application_density_lpm_m2':FireParameter.APPLICATION_RATE,
                    'application_duration_min':FireParameter.DURATION,
                    'foam_fraction':FireParameter.CONCENTRATION,
                    'hazen_williams_c':FireParameter.HW_COEFFICIENT}
FIRE_CATEGORIES = dict(zip(('fire_foam_rate','fire_foam_duration','fire_foam_concentration','fire_hw'),FireParameter))
VERIFIED = (FireSourceStatus.SOURCE_VERIFIED,FireSourceStatus.SOURCE_VERIFIED_CONTEXT_DEPENDENT)


@dataclass(frozen=True, slots=True, kw_only=True)
class FireEngineeringDataRecord:
    parameter_type: FireParameter
    value: float
    unit: str
    context: str
    service: str
    applicability: str
    source_status: FireSourceStatus = FireSourceStatus.SOURCE_REQUIRED
    source_id: UUID | None = None
    source: SourceReference | None = None
    notes: str = ''
    revision: int = 1
    is_active: bool = True
    id: UUID = field(default_factory=uuid4)
    system_family: str = 'fire'

    def __post_init__(self):
        if not isinstance(self.parameter_type,FireParameter) or not isinstance(self.source_status,FireSourceStatus):
            raise ValueError('Invalid Fire parameter/status')
        if isinstance(self.value,bool) or not isinstance(self.value,(int,float)) or not math.isfinite(self.value) or self.value<=0:
            raise ValueError('Positive finite Fire value required')
        if self.parameter_type is FireParameter.CONCENTRATION and self.value>1:
            raise ValueError('Canonical concentration is a fraction in (0,1]')
        if self.unit!=UNITS[self.parameter_type] or self.system_family!='fire':
            raise ValueError('Invalid canonical Fire unit/family')
        if not isinstance(self.id,UUID) or self.source_id is not None and not isinstance(self.source_id,UUID):
            raise ValueError('Invalid Fire identity')
        if type(self.revision) is not int or self.revision<1 or type(self.is_active) is not bool:
            raise ValueError('Invalid Fire revision/active state')
        for name in ('context','service','applicability','notes'):
            if not isinstance(getattr(self,name),str):raise ValueError('Fire metadata requires text')
        if self.service not in ('foam','water','seawater','fuel','unknown'):
            raise ValueError('Explicit source service required')
        if self.source is not None and not isinstance(self.source,SourceReference):raise ValueError('Invalid source')
        if self.source_status is FireSourceStatus.WORKBOOK_REFERENCE_ONLY and (
            self.source is None or self.source_id is None or not (self.source.document or '').strip()):
            raise ValueError('Reference-only value requires an identified reference document')
        if self.source_status in VERIFIED:
            if not self.context.strip():raise ValueError('Verified recommendation requires explicit applicability')
            source=self.source
            if (source is None or self.source_id is None or source.verification_status is not VerificationStatus.VERIFIED
                or not (source.document or '').strip() or not (source.source_organization or '').strip()
                or not any((getattr(source,key) or '').strip() for key in ('part','section','article','table','formula'))):
                raise ValueError('Verified Fire data requires verified, named, located source evidence')
            if source.document.replace('\\','/').rsplit('/',1)[-1].casefold() in ('yangın söndürme.xlsx','yangin sondurme.xlsx'):
                raise ValueError('Approved workbook is reference-only, never a verified production rule')

    @property
    def display_name(self):return self.context

    @property
    def verification_status(self):return self.source.verification_status if self.source else None

    def applicable(self,context,service):
        return self.is_active and bool(self.context.strip()) and self.context==context.strip() and self.service==service

    @property
    def recommendable(self):
        return self.is_active and bool(self.context.strip()) and self.source_status in (*VERIFIED,FireSourceStatus.WORKBOOK_REFERENCE_ONLY)

    def to_payload(self):return json.loads(canonical(asdict(self)))

    @classmethod
    def from_payload(cls,payload):
        values=dict(payload)
        values['id']=UUID(values['id']);values['parameter_type']=FireParameter(values['parameter_type'])
        values['source_status']=FireSourceStatus(values['source_status'])
        if values.get('source_id'):values['source_id']=UUID(values['source_id'])
        if values.get('source'):
            source=dict(values['source']);source['source_type']=SourceType(source['source_type'])
            if source.get('verification_status'):source['verification_status']=VerificationStatus(source['verification_status'])
            for key in ('effective_date','verification_date'):
                if source.get(key):source[key]=date.fromisoformat(source[key])
            values['source']=SourceReference(**source)
        return cls(**values)

    def evidence_reason(self):
        return f'Fire Library {self.id} · r{self.revision} · {self.context} · {self.service} · {self.applicability}'
