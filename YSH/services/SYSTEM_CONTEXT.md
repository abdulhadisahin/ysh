# Project system context (Phase 12)

`SystemContext` is optional project metadata stored under `system_context`,
namespace version 1, inside the existing workspace schema version 1. Each project
owns its selection. An absent namespace means undefined context; no system or
fluid is inferred from numeric inputs or module use. Missing/inactive references
retain UUIDs and saved labels and produce a visible status. Invalid circuit
relationships are reported on load and cannot be selected as a new valid context.

`SystemContextService` reads Phase 4 System/Circuit/Fluid repositories. Small
catalogs and relationship statuses are cached until explicit `reload()`. No fluid
property repository is read and no startup master-data writes occur.

Three **application defaults**, `FUEL` (Yakıt), `FRESH_WATER` (Tatlı Su), and `OIL`
(Yağ), have stable UUID5 identities. They are not database/factory seed rows.
Stored user codes/identities take precedence, including inactive codes, so user
deactivation and edits are never overwritten. Defaults provide no circuits,
fluids, properties, coefficients or standards. Their IDs live in project JSON;
future database-backed rule associations must explicitly map them to real master
rows rather than assume that fallback IDs are database foreign keys.

Module definitions retain the existing order and tabs. Pipe, discharge and
suction remain available. Fuel Transfer Pump is available for `FUEL`; other
defined systems disable its tab with a readable reason. Undefined context retains
all four modules. A missing/inactive Fuel system cannot grant fuel applicability.
This is **application product scope**, never a TL rule or engineering approval.
Pump-suction applicability remains permissive because no actual circuit-purpose
taxonomy is configured. No speculative circuit restrictions are inferred.

Context edits update navigation and future-result metadata only. They do not
publish a pipe, revise an existing selection, apply a downstream snapshot,
invalidate prior outputs, or calculate anything. On the next normal pipe
calculation/publication, system/circuit/fluid IDs are copied and the existing
signature-based revision advances at most once. The old corrosion-allowance
circuit ID is not substituted for the new V2 project circuit identity.
Applied Basma/Emme snapshots keep their prior context and values until the normal
explicit source update. Transfer design and empirical calculations copy context
into new inputs and leave previous results intact.

Density, viscosity, vapor pressure, roughness, material, corrosion allowance and
stress are never injected. Existing pipe advisory velocity warnings still use
the legacy corrosion-circuit/line-role workflow independently of project context.
Aligning that criterion scope is deferred to explicit rule integration; no silent
engineering behavior change is made here. Formula View, bend controls and global
branding/layout styling remain unchanged.
