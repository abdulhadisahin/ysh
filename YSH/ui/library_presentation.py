"""Pure presentation grouping; category/edit/query policies stay in the service."""
from __future__ import annotations


def detail_group(name: str) -> str:
    """Place existing fields into readable sections without changing their values."""
    if name in ("id", "created_at", "modified_at"):
        return "technical"
    if name.startswith("verification"):
        return "verification"
    if name in ("is_system", "is_factory", "is_active", "ownership"):
        return "ownership"
    if name.endswith("_id"):
        return "relationships"
    if name in ("source", "document", "revision", "notes", "description"):
        return "source"
    if name in ("code", "name", "name_tr", "name_en", "designation", "standard",
                "display_name", "ship_name", "key", "property_name"):
        return "basic"
    return "engineering"


def ordered_editor_fields(fields: tuple) -> tuple:
    """Keep each visual section contiguous without changing the field allowlist."""
    groups = {}
    for field in fields:
        groups.setdefault(detail_group(field.name), []).append(field)
    return tuple(field for group in groups.values() for field in group)
