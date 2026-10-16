"""Typed V2 data access; no seeding, UI, or engineering calculations."""
from __future__ import annotations

from repositories._v2_base import _Repository
from repositories.v2_models import EngineeringConstantMetadata


class EngineeringConstantMetadataRepository(_Repository[EngineeringConstantMetadata]):
    _table = "engineering_constant_metadata"
    _model = EngineeringConstantMetadata
    _key = "constant_id"
