# Fire Phase 6 — Source-aware engineering Library

## Recovery and scope

Accepted base: `69d428100cc0a214c69601b4f54bae20a352f168` on
`d243-v2-handoff`; last accepted regression: 1877 passed. The interrupted work
was inspected with branch/HEAD/status, diff stat, full tracked diff and the
three new files before continuation. No reset, checkout, clean or discard was
performed. All seven partial files were intended Phase 6 work (classification A):

| File | Purpose |
| --- | --- |
| `YSH/services/engineering_library_service.py` | Shared Library service adapter |
| `YSH/services/fire_workspace.py` | Live recommendation/link state |
| `YSH/services/library_catalog.py` | Four Fire categories |
| `YSH/ui/dialogs/engineering_library_workspace.py` | Existing Library editor integration |
| `YSH/engineering/fire/library.py` | Typed source-aware record |
| `YSH/repositories/fire_library_repository.py` | Existing numeric storage adapter |
| `YSH/services/fire_library_inputs.py` | Detached project link payload |

There was no unrelated or suspicious source change. The sole approved reference
was the existing untracked `docs/references/Yangın Söndürme.xlsx`. Initial focused
tests found 17 passes followed by a missing Fire fixture in the old
all-categories test. The fixture and category-count expectations were extended,
without weakening their existing coverage.

## Parameters and family semantics

| Stable parameter ID | Canonical unit | Visible calculation unit |
| --- | --- | --- |
| `FIRE.FOAM.APPLICATION_RATE` | L/(min·m²) | L/(min·m²) |
| `FIRE.FOAM.DURATION` | min | min |
| `FIRE.FOAM.CONCENTRATION` | 1, fraction | % |
| `FIRE.HW.COEFFICIENT` | 1 | 1 |

The left sidebar remains the sole authoritative project System Family selector.
Its `fuel`/`fire` IDs, navigation persistence and Phase 5F shell are unchanged.
Fire categories imply `system_family=fire`; this invariant is validated and stored
as record metadata. It is not an editable field, and is omitted from record
details. There is no duplicate “Sistem tipi” or fuel/fire input in the editor.
The Library remains global, so browsing Fire reference records does not mutate
the active project family.

The optional `context` field is labelled **Uygulanabilirlik / Alt sistem
(isteğe bağlı)** / **Applicability / Subsystem (optional)**. It is a free-text,
source-specific context key for product, protected space, material/condition or
similar finer applicability. No subsystem choices are invented. Matching is
explicit and exact, after input whitespace trimming; blank is never a wildcard
recommendation. Verified records require a declared context. A separate optional
source-scope description preserves explanatory applicability text.

`service` is the source's medium/workflow applicability, not System Family.
Foam requests match `foam`; HW requests match the existing explicit service and
captured fluid gate. Engineering System Profile, Devre and Akışkan semantics are
not merged with these Library context keys.

## Storage and source validation

No schema, migration or Fire-specific table was added. The typed adapter reuses
`engineering_constants`: the numeric value/unit remain numeric columns; reserved
`FIRE.LIBRARY.<UUID>` keys identify Fire records and version-1 JSON in the existing
description field carries parameter, context, status, source ID, revision and
active/notes metadata. Each record update is one existing repository write.
Revisions increment explicitly. `SourceRepository` / `SourceReference` provide
actual source facts, including revision/dates when present.

Both the shared and legacy Fuel constant views exclude this reserved namespace.
Legacy constant editing cannot modify/delete Fire records. The legacy Fuel
default initialization still sees only its own constants, including when Fire
rows were created first. Existing Fuel values and lookup semantics are retained.

No new source-status vocabulary is introduced. `SOURCE_VERIFIED` and
`SOURCE_VERIFIED_CONTEXT_DEPENDENT` require a linked source with VERIFIED
verification, organization, document and a real locator (part/section/article/
table/formula), plus declared applicability. Missing provenance is rejected.
The repository re-resolves the source ID on save, preventing a detached fake
reference object from upgrading an unverified stored source. If a source loses
verification, current Library reads downgrade its recommendation to
`SOURCE_REQUIRED`; frozen project/history copies retain their original facts.

`WORKBOOK_REFERENCE_ONLY` requires an identified reference document and explicit
selection. The approved workbook cannot be promoted to a verified production
rule. `SOURCE_REQUIRED`, `NOT_CONFIGURED` and other unresolved statuses remain
distinct and are not automatically recommended. Manual text metadata alone
cannot manufacture verified calculation evidence: unbacked verified claims in
the live workspace are treated as `SOURCE_REQUIRED`.

## Input workflow

Protected area A stays a direct manual input. For q, t, Cfoam and CHW the existing
used-value entries remain, with concise recommended/used/source summaries.
Selection controls are inside an optional disclosure. No recommendation means
recommended “—”, source required, editable manual field and no inserted value.
Lookup is local and explicit. Applicable records are active, parameter-matched,
context/service-matched and have a recommendation-permitting source status.
Multiple matches are displayed deterministically but never arbitrarily selected,
including when only one record exists.

**Use** explicitly applies the selected record and its value. A manual edit of
used value keeps the recommendation and requires an override reason when the
values differ. Existing `EngineeringValue` and override policy validation are
reused. The calculation always uses used value. Linked source/recommendation
metadata is read-only; manual input is available by explicit detachment.

**Refresh** observes record/source changes and marks stale without replacing
used values or existing results. **Keep current** explicitly retains the frozen
record/revision and current result. **Update** applies the latest applicable
recommendation/provenance but preserves used value; differing used/recommended
values require a reason. Explicit link/context/input updates invalidate the live
result; observing a Library change alone leaves the already calculated result
and its snapshot untouched. Shared Library saves notify the cached Fire views;
Library refresh/close and input-side refresh also observe changes. No background
polling or runtime source fetch is introduced.

Cfoam records use canonical fraction. The Library list and calculation summaries
show percent; the record editor labels canonical fraction clearly and fixes the
canonical unit. Selecting .03 produces visible 3; visible 6 means .06; visible
0,03 means .0003. Unchanged linked display preserves the exact canonical source
fraction rather than introducing a floating-point display round-trip override.
The existing single low-percent clarification remains nonblocking and unique.

CHW remains distinct from Darcy roughness k. Library linkage does not change
manual Di, PipeSelection, flow, stale/update/keep behavior for linked pipes or
the water-only calculation gate. A seawater/fuel/unknown reference cannot enable
an unsupported calculation.

## Projects and immutable calculation evidence

Existing Fire workspace JSON gains an additive version-1 `library_inputs` block:
context keys, frozen record/source copies and explicit keep-current preferences.
Link presence denotes Library mode; absence denotes manual mode. Used values and
override reasons remain in existing input/metadata fields. No widget objects or
second editable System Family are persisted. Old projects without the block
remain manual, even if new Library records happen to have identical numbers.
Reading a saved link needs no current Library query.

`EngineeringValue` freezes actual used/recommended values, source and override
reason. Its existing selection-reason field carries record/revision/context
identity. The snapshot's existing generic Fire facts additionally retain a
structured `library_inputs` copy, including record UUID/revision, source facts,
used/recommended values, reason and keep state. Global CalculationSnapshot schema
remains 1; workflow/domain formulas and versions are unchanged.

History, Formula View and PDF read the frozen snapshot. They neither resolve
current Library records nor recalculate. Existing source/recommendation/override
report rows provide concise provenance; the complete Library record is not
dumped into the PDF. Changing a Library record later cannot rewrite history.

## Reference and runtime policy

No Fire production defaults or reference records are seeded. All synthetic
fixtures are explicitly TEST_ONLY and use isolated test databases. q=5 and t=30
are not universal rules; 3% requires actual product/context evidence. The workbook
is development/reference-only, not read at runtime or packaged as required data.
Internet access and external source fetches during calculations are absent.
No dependencies were added.

The approved workbook remains unchanged and untracked, excluded from staging:
**approved untracked reference input**. SHA256:
`bd9aa871454c184afdb45e14bd0c008818d49701d5cc92e1de7ca89126159474`.

## Validation and remaining blockers

Focused suite: **495 passed (141.51s)**. Coverage includes source-less verification
rejection, unit/value validation, empty Library/manual behavior, all four
parameters and overrides, percent/fraction behavior, explicit multi-match
selection, exact context matching, revisions/stale/keep/update, legacy projects,
Fuel namespace isolation, PipeSelection independence, structured snapshot,
History/Formula View/PDF freeze and TR/EN controls. Input and shared Library
geometry checks cover 1100x700, 1280x800, 1440x900 and 1700x1000.

Full regression: **1927 passed, 0 failed (186.30s)**: the 1877 accepted tests
plus 50 new/expanded Phase 6 test cases. Overall:
**PHASE6_PASS_WITH_SOURCE_BLOCKERS**. Functional integration and regression pass;
the unresolved engineering sources below and user visual review remain explicit.

Normal isolated launch did not exceed 15 seconds. No repeated startup benchmarks
or screenshot capture attempts were performed. Manual visual acceptance:
**USER REVIEW REQUIRED**, and does not block this phase solely for unavailable
automation. Phase 5F full-height sidebar, 128px logo, cyan shell and red Fire
selector are retained.

Unresolved source blockers remain explicit:
- Universal foam application-rate source: UNRESOLVED.
- Universal foam duration source: UNRESOLVED.
- Universal foam concentration source: UNRESOLVED / CONTEXT DEPENDENT.
- Seawater HW applicability: BLOCKED / SOURCE_REQUIRED.
- Nozzle production source: BLOCKED / SOURCE_REQUIRED.

The next appropriate step is user review and acquisition/verification of actual
context-specific sources. No Nozzle, seawater, other-system work, User Guide or
Developer Guide is started here.
