# D243 V2 database migrations

Phase 3 adds schema only. Runtime paths remain `ApplicationPaths` paths under
`%LOCALAPPDATA%/YSH/data`. Tests supply temporary paths; this work does not open,
upgrade, or rewrite real runtime databases or source-tree legacy `.db` files.

## Transaction and version contract

`BaseDatabase.initialize()` starts `BEGIN IMMEDIATE` before inspecting schema,
serializing concurrent initializers. `migrations.migrate()` uses a savepoint and
ordered N -> N+1 functions. The entire upgrade is atomic, including first-time
version-table creation. Version advances only after each successful step. Any
failure rolls back every step in that initialization and raises `MigrationError`
with the database/version and original exception. Do not use `executescript`
inside a migration: SQLite may implicitly commit the surrounding transaction.

Both databases retain a single-row `schema_version(version INTEGER NOT NULL)`
format. Multiple records, negative/noninteger versions and newer versions are
rejected without changing the database. Already-current databases are untouched;
seeds are not reapplied on each reopen.

## Libraries: 4 -> 5

Legacy upgrade stages are explicit: 0 -> 1 creates base tables, 1 -> 2 prepares
pipe data, 2 -> 3 reconciles historic free-text pipe standards, 3 -> 4 prepares
corrosion circuits, 4 -> 5 creates the empty V2 relations. Pipe preparation is
idempotent for both pre-standard and already-standard-aware historical shapes.
The pre-existing pipe copy/transform migration is retained for pre-v3 libraries,
now inside the atomic upgrade. No existing v4 table is rebuilt or altered.

Preserved tables: `materials`, `engineering_constants`, `pump_references`,
`pipe_standards`, `pipe_sizes`, `corrosion_allowance_circuits`, `schema_version`.
The last table advances its version record; other v4 rows remain byte-for-byte
identical at the SQL-value level, including timestamps, descriptions and IDs.

New tables (all initially empty):

| Table | Purpose / foreign keys |
| --- | --- |
| sources | Phase 2 source categories, organization/document/part/section/article, table/formula references, revision, effective/verification dates, verification status and notes |
| rule_sets | Versioned code/revision identity, organization, activity and verification; source_id -> sources |
| systems | Future bilingual system identities and factory/activity flags |
| circuits | Future bilingual circuit identities; system_id -> systems; code unique within a system |
| fluids | Future bilingual fluid identities and factory/activity flags |
| fluid_properties | Named numeric property, exact unit, optional temperature in deg C; fluid_id -> fluids, source_id -> sources |
| material_properties | Mechanical properties, allowable stress or roughness by property name/unit/optional temperature; material_id -> materials, source_id -> sources, rule_set_id -> rule_sets |
| pipe_standard_metadata | standard_id -> pipe_standards (one-to-one); optional standard family and source_id -> sources |
| pipe_size_metadata | pipe_size_id -> pipe_sizes (one-to-one); optional NPS, Schedule, tolerance and tolerance unit, source_id -> sources |
| engineering_constant_metadata | constant_id -> engineering_constants (one-to-one); source_id -> sources, rule_set_id -> rule_sets, system_id -> systems, circuit_id -> circuits; selection rationale |
| corrosion_allowance_sources | corrosion_circuit_id -> corrosion_allowance_circuits (one-to-one); source_id -> sources, rule_set_id -> rule_sets, circuit_id -> circuits |

These sidecar relations avoid changing existing positional repository inserts.
Engineering criteria continue to use existing `engineering_constants` values;
there is no competing constants/value table. Phase 2 enums define the permitted
source/status SQL CHECK values. Unknown metadata is NULL, including verification
status. A document's presence does not imply verification. Rule revisions share
a code but have distinct IDs; known `(code, revision)` pairs are unique. SQLite
allows multiple NULL revisions because unknown revision is not an asserted fact.

Foreign keys are enabled on every BaseDatabase connection. New foreign keys
use SQLite's default NO ACTION: referenced data cannot be silently removed.
New activity/factory flags have boolean CHECK constraints. New dates are nullable
ISO date TEXT (application boundary: `date.isoformat()`); new timestamps require
explicit ISO UTC-aware values following existing application conventions. No
existing timestamp or date is reinterpreted or backfilled.

### Explicit indexes

Each index supports an otherwise-unindexed foreign-key lookup/deletion check:

| Index | Table.column |
| --- | --- |
| idx_rule_sets_source | rule_sets.source_id |
| idx_fluid_properties_fluid | fluid_properties.fluid_id |
| idx_fluid_properties_source | fluid_properties.source_id |
| idx_material_properties_material | material_properties.material_id |
| idx_material_properties_source | material_properties.source_id |
| idx_material_properties_rule | material_properties.rule_set_id |
| idx_pipe_standard_metadata_source | pipe_standard_metadata.source_id |
| idx_pipe_size_metadata_source | pipe_size_metadata.source_id |
| idx_constant_metadata_source | engineering_constant_metadata.source_id |
| idx_constant_metadata_rule | engineering_constant_metadata.rule_set_id |
| idx_constant_metadata_system | engineering_constant_metadata.system_id |
| idx_constant_metadata_circuit | engineering_constant_metadata.circuit_id |
| idx_corrosion_sources_source | corrosion_allowance_sources.source_id |
| idx_corrosion_sources_rule | corrosion_allowance_sources.rule_set_id |
| idx_corrosion_sources_circuit | corrosion_allowance_sources.circuit_id |

Other new foreign keys are covered by primary/unique indexes, including the
leading system_id in circuits' unique(system_id, code). No speculative active-flag
indexes are added.

## Projects: unversioned -> global version 1

Existing `projects`, `calculations`, and `project_states` survive unchanged.
`schema_version` is the only new table. `project_states.schema_version` continues
to describe the serialized payload and is never updated by database migration.

For genuinely older project tables, missing descriptive/timestamp columns are
added without dropping the table, and a legacy `project_id` column can be renamed
to `id`. Extra columns and stable IDs are retained. Missing timestamps stay empty
(the existing legacy convention); no verification/current timestamp is invented.
A missing stable identifier or name causes rollback and a clear migration error.
Current three-table project databases require no column changes.

## Seeds and deferred work

Existing EN 10220 and corrosion seed definitions/values are unchanged and used
only in their historic setup stages. v4 -> v5 does not run seeds. No new systems,
circuits, fluids, properties, TL rules, ASME dimensions, tolerances or K values
are inserted. Factory Yakıt/Tatlı Su/Yağ system records and their circuit content
are deferred to the System Definition phase; Deniz Suyu is not added as a new
required system. Existing corrosion rows, including historic defaults, remain.

A local-loss library is deferred: current K values remain user/project-state
content, and there is no verified catalog to migrate. Full EngineeringValue
persistence, source repositories/services, rule content, date serialization,
new property selection and calculation/UI integration belong to later phases.
Existing values are not retroactively assigned verification/provenance.

## Verification

Frozen v4 and unversioned-project DDL fixtures are captured from starting commit
8e2b7a0, with synthetic user records in every existing table. Tests cover fresh
schemas, v4 upgrade, unchanged rows/DDL, legacy upgrades, full rollback/retry,
source/status constraints, versioned rules, foreign keys, exact index inventory,
reopening, concurrent initialization, unsupported/ambiguous versions and missing
steps. Numeric freeze checks use the same 16 engineering values before/after.
