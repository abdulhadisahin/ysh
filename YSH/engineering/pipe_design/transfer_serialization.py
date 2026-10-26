"""Versioned language-neutral project-state codec for pipe transfer only."""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date, datetime
from enum import Enum
import json
import math
from types import UnionType
from typing import get_args, get_origin, get_type_hints
from uuid import UUID

from engineering.pipe_design.v2_models import PipeSelection
from engineering.pipe_design.transfer import PipeTransferProjectState

NAMESPACE = "pipe_transfer"
VERSION = 1


def _encode(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (UUID, date, datetime)):
        return str(value) if isinstance(value, UUID) else value.isoformat()
    if is_dataclass(value):
        return {f.name: _encode(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, tuple):
        return [_encode(v) for v in value]
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    raise ValueError("Unsupported or non-finite pipe-transfer value")


def _decode(target: type, value: object) -> object:
    origin, args = get_origin(target), get_args(target)
    if origin is UnionType:
        if value is None and type(None) in args:
            return None
        for option in args:
            if option is type(None):
                continue
            try:
                return _decode(option, value)
            except (ValueError, TypeError):
                pass
        raise ValueError("Invalid optional/union field")
    if origin is tuple:
        if not isinstance(value, list):
            raise ValueError("Expected selection array")
        return tuple(_decode(args[0], v) for v in value)
    if target is UUID:
        return UUID(value)
    if target in (date, datetime):
        return target.fromisoformat(value)
    if isinstance(target, type) and issubclass(target, Enum):
        return target(value)
    if is_dataclass(target):
        if not isinstance(value, dict):
            raise ValueError("Expected pipe-transfer object")
        # A persisted selection must never acquire a new identity on read.
        if target is PipeSelection and not {"selection_id", "revision"} <= value.keys():
            raise ValueError("Persisted selection identity/revision required")
        hints = get_type_hints(target)
        return target(**{f.name: _decode(hints[f.name], value[f.name])
                         for f in fields(target) if f.name in value})
    if target is float:
        if type(value) not in (float, int) or not math.isfinite(value):
            raise ValueError("Expected finite number")
        return value
    if type(value) is not target:
        raise ValueError("Invalid primitive field type")
    return value


def selection_to_dict(selection: PipeSelection) -> dict[str, object]:
    """Encode the complete authoritative result, not just its hydraulic subset."""
    return _encode(selection)


def pipe_input_to_dict(state) -> dict[str, object]:
    """Serialize one independent downstream owner without observing live selections."""
    from engineering.pipe_design.transfer import PipeInputState
    if not isinstance(state, PipeInputState):
        raise TypeError('PipeInputState required')
    return _encode(state)


def pipe_input_from_dict(payload: dict[str, object]):
    """Restore the exact supplied applied/observed state; no refresh on decode."""
    from engineering.pipe_design.transfer import PipeInputState
    return _decode(PipeInputState, payload)


def selection_from_dict(payload: dict[str, object]) -> PipeSelection:
    """Restore identity, revision, rules and Phase 2 provenance explicitly."""
    return _decode(PipeSelection, payload)


def transfer_to_dict(state: PipeTransferProjectState) -> dict[str, object]:
    """Encode stable field names; collection order is normalized by source UUID."""
    payload = _encode(state)
    payload["selections"] = sorted(payload["selections"], key=lambda s: s["selection_id"])
    return {"version": VERSION, **payload}


def transfer_from_dict(payload: dict[str, object]) -> PipeTransferProjectState:
    """Load applied values unchanged, refreshing only exact-source observations."""
    if type(payload.get("version")) is not int or payload["version"] != VERSION:
        raise ValueError("Unsupported pipe-transfer payload version")
    return _decode(PipeTransferProjectState, payload).refresh()


def transfer_json(state: PipeTransferProjectState) -> str:
    """Canonical JSON useful for deterministic storage comparisons and exports."""
    return json.dumps(transfer_to_dict(state), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def transfer_from_workspace(workspace: dict[str, object]) -> PipeTransferProjectState:
    """Missing namespace is always manual; matching legacy values never imply links."""
    if NAMESPACE in workspace:
        return transfer_from_dict(workspace[NAMESPACE])
    from engineering.pipe_design.transfer import PipeInputState, PipeValues
    from engineering.input_parsing import parse_engineering_float

    def manual(page: str, diameter: str, flow: str) -> PipeInputState:
        fields_payload = workspace.get(page, {})
        fields_payload = fields_payload.get("fields", {}) if isinstance(fields_payload, dict) else {}
        fields_payload = fields_payload if isinstance(fields_payload, dict) else {}
        def number(key: str) -> float | None:
            try:
                return parse_engineering_float(str(fields_payload.get(key, "")), field_name=key, allow_empty=True)
            except (ValueError, TypeError):
                return None
        return PipeInputState(manual_values=PipeValues(
            actual_internal_diameter_mm=number(diameter), flow_rate_m3_h=number(flow)))
    return PipeTransferProjectState(discharge=manual("discharge_head_loss", "d", "q"),
                                    suction=manual("suction_npsh", "diameter", "flow"))
