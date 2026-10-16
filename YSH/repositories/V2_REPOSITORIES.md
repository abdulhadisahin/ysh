# V2 repository access (Phase 4)

All repositories receive an initialized `LibraryDatabase`; they never initialize,
seed or migrate it. Existing repositories/services remain unchanged. Typed,
immutable records live in `v2_models.py`; every operation uses one
`BaseDatabase.connection()` transaction and parameterized values. The private
`_v2_base.py` shares only CRUD/codec mechanics, with static table/key declarations.

| Table | Repository | Additional lookup |
| --- | --- | --- |
| sources | SourceRepository | source type, organization/document, literal substring search |
| rule_sets | RuleSetRepository | code returns **all revisions**, optional active filtering |
| systems | SystemRepository | code, list/all-active |
| circuits | CircuitRepository | code within system, list/all-active by system |
| fluids | FluidRepository | code, exact bilingual name, list/all-active |
| fluid_properties | FluidPropertyRepository | fluid, optional exact property name |
| material_properties | MaterialPropertyRepository | material, optional exact property name |
| pipe_standard_metadata | PipeStandardMetadataRepository | standard UUID |
| pipe_size_metadata | PipeSizeMetadataRepository | pipe-size UUID |
| engineering_constant_metadata | EngineeringConstantMetadataRepository | constant UUID |
| corrosion_allowance_sources | CorrosionSourceRepository | corrosion-circuit UUID; remove linkage only |

Common `create(record)`, `get(UUID)` and `update(record)` APIs return typed records;
missing reads return `None`. Lists return tuples in stable primary-key order.
Metadata uses the existing owner's UUID as its identity. Creation and updates are
separate (no implicit upsert/replacement). Update preserves the stored `created_at`
and returns the actual persisted record; callers explicitly supply `modified_at`.

`SourceRecord(reference=SourceReference(...))` wraps Phase 2 facts plus UUID and
record timestamps. The mapper translates `table`/`formula` to
`table_reference`/`formula_reference`; `record.reference` restores the exact domain
object. Enum `.value` strings are language-neutral. Dates use ISO dates, timestamps
use ISO timezone-aware datetimes, and optional fields retain `None`/SQL NULL.
Record timestamp defaults use UTC now; unknown **source** dates/status never do.
Units, symbols in reference text, temperatures and numeric values are not converted.

`v2_errors.py` exposes `RepositoryConflictError`, `RepositoryForeignKeyError`,
`RepositoryValidationError`, `RepositoryNotFoundError` (also a `KeyError`) and
`RepositoryError` for other SQLite failures. Exceptions preserve their original
cause. Invalid writes roll back; reads neither change timestamps nor seed data.

Sources, rules, systems, circuits, fluids and properties have no delete API.
Deactivate applicable master records with `update(replace(record, is_active=False))`;
factory flags are preserved unless explicitly changed. Corrosion `remove()` deletes
only the association row. FK constraints continue to protect referenced records.
Business-rule services, EngineeringValue snapshot persistence, UI integration,
interpolation, catalog seeding and bulk multi-repository transactions are deferred.
