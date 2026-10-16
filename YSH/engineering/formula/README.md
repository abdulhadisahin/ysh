# Formula View 2.0

Calculators produce authoritative results. Services retain the exact inputs
resolved for those results. Module adapters in this package lazily expose frozen
`FormulaStep` records to `ui.widgets.formula_steps`. Adapters never evaluate a
rule, fit a regression, select a pipe, resolve a link, query a repository, or
calculate an engineering result.

Selected values reuse Phase 2 `EngineeringValue` and `SourceReference`.
Classification, selection reason, suitability, and upstream snapshot identity
are independent. Synchronization notices remain in the existing source panel.
The renderer owns formatting, optional sections, tables, source details and the
existing PNG / MathText / text fallbacks. Raw numbers are never rounded in domain
records. Small nonzero inputs use a two-decimal scientific mantissa so viscosity
is not presented as zero.

The legacy `FormulaSection` provider remains compatible. Legacy loaded pipe
results without captured inputs expose available outputs without reconstructing
historical inputs from editable controls. No explanation strings or new display
state are persisted. Historical snapshot persistence remains Phase 14 work.
