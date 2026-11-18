# D243 V2.1 — Project Engineering Context

This feature extends the existing `SystemContext`, project JSON and read-only Warning Center. The project family remains authoritative in persisted navigation; the context editor does not provide a second family selector. Hydraulic calculators do not query the Library.

## User workflow

Open **Project → Project Engineering Context** on an active project. Select fluid, material/surface condition, rule source profile, line type and explicit applicability. Mechanical material is optional and uses existing verified mechanical-property handling.

Compatible empty viscosity/roughness fields on Basma and viscosity/roughness/density fields on Emme are populated. Existing nonempty inputs are retained and compared with the selected reference. Pipe uses the selected rule profile without adding unrelated physical-property fields. Fresh-water Fire context can select the existing water service; seawater hydraulic applicability remains blocked.

Each applied value retains the source record, default and actually used value. Editing a value affects that calculation only. **Update Linked Values** adopts a new reference and updates a previously linked value while preserving overrides. **Keep Current** retains the applied value and its stale notice. **Use Selected Reference** explicitly resets an override. **Use as Project Default** is an explicit action, keyed by reference record identity so F-76 defaults cannot leak into F-44. Other calculations are never silently overwritten.

Save/close/reopen preserves context and applied links. A changed context/reference makes an existing result noncurrent for PDF; recalculation captures a new basis. Explicit Library refresh compares source records, not recomputed historical results.

## Catalog and migration

Library schema **5 → 6** adds `fluid_specifications`, `material_surfaces` and `engineering_rules`, with foreign keys and indexes. Existing tables, user rows and IDs are retained. Fluid/profile code collisions reuse the existing parent identity. Migration is transactional and idempotent. Project DB schema is unchanged.

Factory seed totals: **28 fluid-property records (14 fluids), 10 surface profiles, 23 engineering rules (6 profiles)**. Factory reference rows are protected; user-owned records use the existing explicit Library editor.

- F-76: density 800–876 kg/m³ at 15 °C, derived default 838; viscosity 1.7–4.3 cSt at 40 °C, derived default 3.0. Source MIL-DTL-16884R.
- F-44: density 788–845 kg/m³ at 15 °C, derived default 816.5. Viscosity ≤7 cSt at −20 °C has **no derived default**. Source MIL-DTL-5624X.
- ISO 8217:2024 marine grades are explicit SOURCE_REQUIRED records where verified properties are unavailable. Water, seawater, oil and air identities likewise do not invent property defaults.
- Surface roughness distinguishes material and condition. The six approved numeric references are RECOMMENDATION records; exact source editions were not supplied. PVC/GRE/cast-iron/corroded-carbon profiles remain SOURCE_REQUIRED. Roughness is absolute ε, never a substituted Darcy friction factor.

VERIFIED, LIMITED_APPLICABILITY, RECOMMENDATION and SOURCE_REQUIRED remain separate. Source ranges, nominal values, derived/project defaults, used values, reference temperatures and derivation methods are stored separately.

## Rules and applicability

The **7 m/s Fuel criterion is D243**, not TL, ISO or a manufacturer hard limit. Its catalog record is the sole numeric authority. A selected manufacturer recommendation can coexist with it as a distinct finding. Calculations remain advisory/nonblocking under this criterion.

Velocity policy is record-configurable: within bounds OK; up to 10% deviation WARNING; larger deviation OUT_OF_RANGE; extreme flow velocity at ≥5× an upper bound (or below 1/5 of a lower bound) CRITICAL. HARD_LIMIT exceedance goes directly OUT_OF_RANGE, with no yellow grace band. These visual statuses do not change arithmetic or validation rules.

Everllence values are the user-approved starting recommendation profile. The exact engine/project-guide edition is deliberately unspecified: the public L27/38 guide's HFO delivery recommendation differs from the approved starting profile, so these are not asserted as universal manufacturer requirements. See the [official guide](https://www.everllence.com/applications/projectguides/4stroke/Propulsion/PG_P-IMO_L2738.pdf).

TL Fire Fighting Ship suction 2 m/s, delivery 4 m/s and NPSH-margin reference 1 m are separate scoped records: [Chapter 11, July 2019, C.5.3.3 and C.5.1](https://turkloydu.org/pdf-files/turk-loydu-kurallari/cilt-c/chapter-11-fire-fighting-ships-2019-JULY.pdf). Fire velocity integration requires explicit Fire Fighting Ships scope. The NPSH record is available to the rule evaluator; it does not change generic ENPY or add a new Fire NPSH calculator.

The user-approved TL <500 GT material limits require explicit scope/material/fluid matching and remain LIMITED_APPLICABILITY; exact edition/clause confirmation is noted in the record. Cu-Ni source-specific maxima, ballast/bilge and Wärtsilä numeric rules remain SOURCE_REQUIRED. Selecting a profile never certifies overall project compliance.

## Frozen evidence

At successful calculation capture, the adapter freezes identities, source ranges/temperatures, library/project default, actual formula input, override status, source metadata, applicable rules and findings into snapshot FormulaStep engineering-basis metadata. Formula View and PDF read that frozen basis. Rendering never queries current Library data or recalculates a historical result. Old snapshots lacking the metadata remain legacy/missing rather than being enriched with current references.

CalculationSnapshot remains immutable. Existing family lock, PipeSelection, Nozzle blocker, seawater blocker, formulas, generic ENPY convention and shell layout remain unchanged.

## Validation

Focused domain, migration, persistence, native Tk, Library, warning, Formula View and PDF tests cover the feature; full pytest is deliberately excluded from this implementation pass. Native dialog geometry is checked at 1100×700 and 1440×900 in TR/EN. Final visual acceptance: **USER REVIEW REQUIRED**.

The approved untracked `docs/references/Yangın Söndürme.xlsx` is not a data seed or packaging input and is excluded from this change.

Final focused validation (overlapping groups, not a full-suite run):
- Context/Library/migration/Warning Center/TR-EN/native geometry: **194 passed, 126.62 s**.
- Snapshot/Formula View/rule/UI/family-lock compatibility: **216 passed, 85.92 s**.
- Final frozen-PDF material-source presentation: **1 passed, 17.99 s**.
- Basma/Emme numerical compatibility, Fire live flows and existing PDF V2 checks passed in the integration group; its only initial failure was a new fixture missing required timestamps, corrected and covered by the subsequent passing migration/context group.

The English engineering-basis sample was rasterized for visual inspection. Final application visual acceptance remains **USER REVIEW REQUIRED**, especially context selection/Update/Keep actions and yellow/red/black warning presentation.

## Library v6 visibility corrective

The v6 records already existed; no migration, seed values or runtime DB rows were changed. The previous shell offered only the four legacy Library menu commands, Engineering Rules was nested under Sources, and selecting a Fluid identity did not display its authoritative v6 specifications.

Library now provides direct **Fluids / Fuels**, **Engineering Rules** and **Material / Surface Roughness** commands alongside the existing entries. The six principal engineering groups are placed first in Library navigation. Selecting a group opens its primary category; all previous categories remain available. Selecting a fluid shows its existing specification records, including limits, nominal/default, method, unit, temperature, authority/document and verification. Rule and surface tables use category-specific headings and values.

`fluid_properties`, `material_properties`, `sources` and `systems` are optional existing normalization/user-record tables, not evidence of missing v6 seeds. Current fluid specifications, surface profiles and rule records carry their own reference metadata; system defaults are also provided by the existing context service without persisting artificial seed rows. These empty tables remain untouched.

The Project menu's existing **Project Engineering Context** entry was verified through its real Tk callback. Its selections populate compatible page fields through the existing context controller; calculation-only overrides remain protected. No competing project model or new inheritance mechanism was introduced.

Manual acceptance: **USER REVIEW REQUIRED** for category discoverability, F-76/F-44 and marine-fuel browsing, roughness, rule/source details and project-linked field changes in the updated application.

Corrective focused validation: **96 passed** across three disjoint groups: v6 Library visibility/menu/native browsing (3, 29.03 s), Library/context service and protection contracts (84, 33.81 s), native context/inheritance/persistence/geometry (9, 41.31 s). Full pytest was not run. Runtime v6 counts were checked read-only; the approved untracked Excel reference and release tag remain unchanged.

## Project start and calculation-page selection corrective

The former page-local “System/Fluid” selector represented velocity-service categories, not fluid identities. The four legacy material entries supplied mechanical strength or legacy roughness; they were not the expanded v6 surface catalog. These are no longer the visible physical-material/fluid selection path in the composed application.

New Fuel Project now exposes a shared catalog form after the mandatory System Family choice: Fluid/Fuel, Pipe Material, Surface Condition, Service/System, Line Type and Rule Profile. Options come from the existing Engineering Catalog Service. The same form is used by Project → Project Engineering Context. Initial selections and linked page values are saved with the new project, including before an ordinary subsequent Save.

Pipe, Basma and Emme display a compact project-linked identity panel. Project editing is directly accessible there. The old velocity-service and legacy roughness pickers are hidden in the composed pages; their compatibility state remains available for old project payloads. The standalone legacy page API is preserved. Pipe's existing validated strength-material/Rp0.2 selector remains separately labelled: selecting a surface never manufactures a yield-strength value or an unsupported alloy grade.

Basma uses linked viscosity and roughness. Density is displayed explicitly as a reference, not as a new input to discharge arithmetic. Emme uses linked fluid identity, viscosity, density and roughness. Surface roughness remains absolute epsilon, not Darcy friction factor. A missing source/default is never replaced with an invented value.

**Override for this calculation** opens an explicit per-module catalog form. It uses the same SystemContext contract inside the existing engineering-links namespace, without adding another project/family model or DB schema. An alternate fluid/material remains local; manual numeric overrides are retained. **Use project context** restores project references while retaining manual numeric overrides. Update/Keep/reference actions remain available in the project context inspector. A default from a different module-only fluid/surface cannot be silently promoted into the project's selected reference.

On successful capture the existing snapshot builder receives the actual module context. The frozen engineering basis records actual fluid/material/surface, context override scope, original project fluid, reference/default/used values and applicable cached rules. Formula/PDF rendering still reads frozen evidence only; old snapshots are not rebuilt from today's Library.

Manual acceptance remains **USER REVIEW REQUIRED** for the new-project selectors, compact page identity panels, alternate-fluid action, separate validated strength source and context-update/Keep workflows. No formulas, catalog seed values, D243 criterion, warning severity policy, family lock, Nozzle/seawater blockers, release tag or approved Excel reference are changed.

Selection-corrective validation: **67 passed in 144.51 s** across new-project/native selection, context service/UI and family-lock groups. Final identity/default-override guard and input-mode checks: **9 passed in 65.25 s** (8 overlap, 68 distinct focused tests overall). Geometry covers 1100×700 and 1440×900; panel captions are checked in TR/EN. Full pytest was not run.
