"""Additive Transfer Pump page state; legacy regression payloads remain empirical."""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import date
from enum import Enum
from uuid import UUID

from engineering.provenance import SourceReference, SourceType, VerificationStatus
from engineering.transfer_pump.v2_models import PumpIntegrationContext, TransferPumpMode, user_source


def _source_payload(source: SourceReference) -> dict[str, object]:
    result = {}
    for item in fields(source):
        value = getattr(source, item.name)
        result[item.name] = value.value if isinstance(value, Enum) else value.isoformat() if isinstance(value, date) else value
    return result


def _source_restore(payload: dict[str, object]) -> SourceReference:
    values = {item.name: payload[item.name] for item in fields(SourceReference) if item.name in payload}
    values['source_type'] = SourceType(values.get('source_type', SourceType.USER_INPUT))
    if values.get('verification_status') is not None:
        values['verification_status'] = VerificationStatus(values['verification_status'])
    for name in ('effective_date', 'verification_date'):
        if values.get(name) is not None:
            values[name] = date.fromisoformat(values[name])
    return SourceReference(**values)


@dataclass(frozen=True, slots=True, kw_only=True)
class TransferPumpPageState:
    """Raw editable design inputs can be saved incomplete without losing empirical fields."""
    mode: TransferPumpMode = TransferPumpMode.DESIGN
    volume_text: str = ''
    target_time_text: str = ''
    pump_capacity_text: str = ''
    context: PumpIntegrationContext = field(default_factory=PumpIntegrationContext)
    volume_source: SourceReference = field(default_factory=user_source)
    target_time_source: SourceReference = field(default_factory=user_source)

    def to_payload(self) -> dict[str, object]:
        """Use stable enums, UUID strings and ISO dates; no calculated result is persisted as input."""
        context = {f.name: (str(value) if isinstance(value := getattr(self.context, f.name), UUID) else value)
                   for f in fields(self.context)}
        return dict(version=1, mode=self.mode.value, volume_text=self.volume_text,
            target_time_text=self.target_time_text, pump_capacity_text=self.pump_capacity_text,
            context=context, volume_source=_source_payload(self.volume_source),
            target_time_source=_source_payload(self.target_time_source))

    @classmethod
    def from_page_payload(cls, page: dict[str, object]) -> TransferPumpPageState:
        """Missing V2 namespace is always the original empirical mode, never design."""
        if 'transfer_v2' not in page:
            return cls(mode=TransferPumpMode.EMPIRICAL)
        payload = page['transfer_v2']
        if not isinstance(payload, dict) or type(payload.get('version')) is not int or payload['version'] != 1:
            raise ValueError('Unsupported Transfer Pump page state version')
        values = {f.name: payload.get('context', {}).get(f.name) for f in fields(PumpIntegrationContext)}
        for name in ('system_id','circuit_id','fluid_id','selected_pump_reference_id'):
            if values[name] is not None:
                values[name] = UUID(values[name])
        return cls(mode=TransferPumpMode(payload['mode']),
            volume_text=str(payload.get('volume_text', '')),
            target_time_text=str(payload.get('target_time_text', '')),
            pump_capacity_text=str(payload.get('pump_capacity_text', '')),
            context=PumpIntegrationContext(**values),
            volume_source=_source_restore(payload.get('volume_source', {})),
            target_time_source=_source_restore(payload.get('target_time_source', {})))
