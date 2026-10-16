"""Typed V2 data access; no seeding, UI, or engineering calculations."""
from __future__ import annotations

from repositories._v2_base import _Repository
from repositories.v2_models import PipeStandardMetadata, PipeSizeMetadata


class PipeStandardMetadataRepository(_Repository[PipeStandardMetadata]):
    _table = "pipe_standard_metadata"
    _model = PipeStandardMetadata
    _key = "standard_id"


class PipeSizeMetadataRepository(_Repository[PipeSizeMetadata]):
    _table = "pipe_size_metadata"
    _model = PipeSizeMetadata
    _key = "pipe_size_id"
