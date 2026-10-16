# Phase 14: immutable calculation history

Successful explicit calculations emit a success event after the current result
and Formula View are available. The application freezes the actual result,
actually used inputs, applied pipe-link state, context names/identities,
EngineeringValue overrides, source metadata, findings and FormulaSteps. Field
changes, project loads, source discovery and failed calculations do not emit
history. Pipe diameter and wall, suction hydraulics and ENPY, and transfer design
and empirical modes remain separate successful stages.

`CalculationSnapshot` schema 1 has a UUID, timezone-aware creation time, module,
stage and stable calculation-model token. Its canonical JSON evidence is the
deep immutability boundary; consumers receive detached copies. JSON preserves
raw numeric precision and units, stores enum values/UUID strings/ISO dates, and
rejects nonfinite numbers and unsupported runtime objects. Historical typed
decoding is restricted to explanation/context classes and validates version,
ownership and record identity; it cannot dynamically import payload types.

Project-owned snapshots use the existing `calculations` table. The reserved
`snapshot:<module>:<UUID>` calculation type fits its existing project/type unique
constraint. Each append is one transactional INSERT; collisions cannot update a
record, and legacy upsert rejects the reserved namespace. No database schema,
migration or workspace-state version changes. History does not enter page-state
payloads. Existing project deletion semantics are unchanged.

Calculations made without an active project are explicitly session-only. They
appear under the session notice, are not written to a fabricated project, are
not attached silently to a later project and do not survive application exit.
Persistent history requires calculating while a saved project is active.

The Project menu opens calculation history lazily. Records are newest-first by
creation time and UUID, with a latest-per-module label, stage and frozen summary.
Historical Formula View receives only the stored FormulaSteps. It never invokes
a calculator, source/library resolver, context refresh or upstream selection
lookup. TR/EN presentation uses the existing renderer; raw evidence is expandable
and read-only. There is no restore, rollback or snapshot-delete action. Original
legacy saved records are marked incomplete and expose only their existing facts;
missing provenance is never synthesized from today's catalogs.

Persistence/capture failure is reported separately and leaves the successful
current result intact. Corrupt/unsupported stored history fails explicitly rather
than being recomputed. No calculations, engineering criteria, TL data, bend UI,
global styling or dependencies change.

Validation: Phase 14 tests cover frozen precision/provenance/context, library
edits, linked/manual/stale/missing input, staged success hooks, multiple records,
project isolation, failed writes, corrupt payloads and frozen Formula View.
Numerical freeze comparisons match Phase 13 exactly, including original baseline
pipe V2 and transfer calculators. GUI smoke reaches the real main.py entrypoint
with an isolated profile but is BLOCKED_ENVIRONMENT at Tk construction because
the mandated Python 3.14 installation cannot locate a usable init.tcl; no window
or GUI workflow is claimed to have been verified visually.
