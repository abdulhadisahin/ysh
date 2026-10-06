# Engineering Warning System — Phases 8A–8B

## Scope and result policy

Phase 8A defines source-controlled domain rules only. It does not add warning
UI, alter calculation formulas, or block a mathematically valid result because
it falls outside a recommended range.

- `ERROR`: invalid or mathematically impossible input. Existing validation may
  block calculation.
- `ENGINEERING_WARNING`: valid calculation outside a referenced recommended or
  typical range. The result remains available.
- `CRITICAL_WARNING`: a strong engineering condition requiring attention. A
  mathematically valid result remains available.

Existing `ValidationIssue` values adapt to `ERROR` findings through the shared
warning-domain model, rather than being duplicated as new threshold rules.

## Initial enabled velocity matrix

Source: `MAN_EVERLLENCE_MARINE_PROJECT_GUIDE` — MAN / Everllence marine project
guide recommended flow rates. These ranges are recommendations, not hard
validity limits.

| System | Line role | Recommended velocity |
| --- | --- | --- |
| Diesel fuel | suction | 0.5–1.0 m/s |
| Diesel fuel | delivery | 1.5–2.0 m/s |
| Lube oil | suction | 0.5–1.0 m/s |
| Lube oil | delivery | 1.5–2.5 m/s |
| Sea water | suction | 1.0–1.5 m/s |
| Sea water | delivery | 1.5–2.5 m/s |

## NPSH rule

Source: `HYDRAULIC_INSTITUTE_ANSI_HI_9_6_1`. When NPSHr is supplied and
available ENPYm/NPSHA does not exceed it, the evaluator returns a
`CRITICAL_WARNING`. No percentage-margin threshold is inferred in this phase.

## Future material-specific extension

The source registry records inactive Wärtsilä material-specific sea-water
delivery guidance for galvanized steel (2.5 m/s), 10/90 CuNiFe (3.0 m/s), and
70/30 CuNi (4.5 m/s). These rules are not enabled because the current material
selection does not reliably identify those exact material classes.

## Current V2 context availability

- The Suction module intrinsically supplies the suction line role.
- The Discharge module intrinsically supplies the delivery-side context, but
  neither hydraulic page exposes diesel, lube-oil, or sea-water system choice.
- Both hydraulic pages can select a material for roughness, but current names
  and designations are not a safe normalized material-class key for the future
  Wärtsilä rules.
- The Suction module already has an optional NPSHr input.

## Phase 8B context and presentation

Phase 8B adds only the context needed by the enabled rules and a reusable
result-preserving warning panel. Stable context identifiers live in
`core.engineering_context`:

- `DIESEL_FUEL` — Dizel Yakıt
- `LUBE_OIL` — Yağlama Yağı
- `SEA_WATER` — Deniz Suyu
- `SUCTION` — Emiş
- `DELIVERY` — Basma

Pipe Design persists an optional **Hat Görevi**. Its circuit mapping is
`FUEL → DIESEL_FUEL`, `SEA_WATER → SEA_WATER`, with no enabled reference rule
for `BOILER_BLOWDOWN`. Discharge persists an optional **Sistem / Akışkan** and
uses `DELIVERY`; Suction persists the same selector and uses `SUCTION`.
Legacy state without those selectors stays valid and produces no contextual
velocity warning until the user explicitly selects context.

Warnings are displayed beside results through
`ui.widgets.engineering_warning_panel.EngineeringWarningPanel`. It lists the
actual value, referenced range/value, and concise source title. Multiple
findings are deduplicated and ordered critical before engineering guidance.
No panel is shown when there are no findings.

An engineering or critical warning never clears a valid calculated result.
Existing invalid-input validation remains separate and blocking where it was
already blocking. NPSH/ENPY now shows the Phase 8A critical finding whenever
`ENPYm <= NPSHr`; no low-margin percentage rule has been added.

Material-specific Wärtsilä rules remain deferred, and no Transfer Pump warning
rule is introduced. Final warning visual refinement remains deferred to the
visual-overhaul phase.
