# Phase 10: design capacity and empirical vessel estimation

## Audit of the pre-existing empirical model

The legacy `TransferPumpCalculator` uses ordinary least squares on saved
reference-vessel rows. x is fuel capacity in m³; y is recorded transfer-pump
capacity in m³/h. Its coefficients are computed for the actual current dataset:

- xm = sum(x)/n; ym = sum(y)/n
- m = sum((x-xm)*(y-ym))/sum((x-xm)^2)
- b = ym - m*xm
- estimated Q = m*Vfuel + b
- estimated emptying time = Vfuel/estimated Q (h), then hours*60 (minutes)

No fixed production regression coefficient or bundled reference-vessel dataset
is configured by this path. The existing user-managed `pump_references` table
stores ship name, fuel capacity, pump capacity, description, source text, UUID
and timestamps. Its repository returns rows in ship-name order; the unchanged
service/calculator preserve that order and floating-point operation sequence.
The model also reports R² and extrapolation/errors. Source metadata previously
came from the row's free-text source field, not verified manufacturer documents.
The table represents reference ships, not approved manufacturer pump selections.
No new records or source documents are seeded in Phase 10.

The existing page/chart/Formula View consume these estimates. They are not
silently propagated to Pipe Design, Basma or Emme. The legacy capacity basis
still supports m³ or tonnes with its pre-existing 0.83 t/m³ conversion. The
existing Q12=V/12 comparison remains numerically unchanged but is explicitly a
12-hour comparison, not a mandatory target, classification rule or regression
prediction. No legacy conversion coefficient is introduced into the new design
path.

## Distinct engineering paths

`TransferPumpMode` persists DESIGN or EMPIRICAL independently of localized labels.
The new page defaults to Design Capacity. Its inputs are transferable volume in
m³, explicit target time in hours, and optional actual pump capacity in m³/h.

`calculate_design` implements only:

- Qgerekli = Vtransfer/tdef
- optional ttransfer = Vtransfer/Qtulumba
- optional suitability: Qtulumba >= Qgerekli, with no tolerance band

All entered quantities must be finite and positive. Derived overflow/nonpositive
results are rejected rather than clamped or returned as infinity. A missing
selected pump is informational, not an invalid design. There is no preset target
time, default margin, pump-count/duty/standby rule, efficiency, power calculation,
manufacturer record or pump curve. Optional explicit margin support is deferred;
base required flow remains distinct from absent margin-adjusted output fields.

`TransferPumpService.calculate_v2` dispatches typed design/empirical requests.
The design path never reads reference records. The empirical path delegates to
unchanged `calculate_from_capacity_input`/`calculate` and stores its original
result plus immutable snapshots of the actual used reference rows. The existing
calculator, coefficients, regression results and both emptying-time units remain
unchanged. Empirical output never populates required design flow.

## Provenance and future integration

Existing Phase 2 SourceReference/EngineeringValue represent provenance. Design
volume/time default honestly to USER_INPUT. Explicit project/configured criterion
sources can be supplied and preserved; none are inferred or labelled TL.
Qgerekli and empirical predicted capacity are CALCULATED. Used reference rows
are REFERENCE_VESSEL_DATA with their actual source text retained as notes and
UNVERIFIED status; no documents or verification claims are fabricated.

`PumpIntegrationContext` retains optional system/circuit/fluid and selected-pump
reference UUIDs, required head, available/required NPSH and an external NPSH margin.
These default to None and are never computed here. Required flow is exposed in
m³/h for a future explicit PipeSelection action. Live flow/head/NPSH links,
manufacturer-library/curve design, and circular automatic propagation are deferred.
No Basma, Emme/ENPY or Pipe Design calculations/linkage behavior change.

## Page, persistence and Formula View

Design and empirical modes own separate input variables and stored results.
Mode switching changes visibility, not engineering values or calculation results.
The existing empirical CRUD/chart/results remain available, clearly labelled as
an empirical estimate rather than a required design capacity or TL formula.
The new design panel presents required flow, optional actual transfer time and
capacity suitability using the existing shared two-decimal Turkish-comma display.
Internal precision is retained. Formula View remains the existing implementation;
it projects the active mode's stored results without recalculation or new source/
rationale panels.

The page's additive `transfer_v2` namespace has version 1 and stable mode values,
raw design fields, optional context and existing provenance records. UUIDs use
strings, dates use ISO forms and enums use stable values. Incomplete inputs can
be saved. Legacy page payloads lacking this namespace always load EMPIRICAL;
no saved estimate becomes Qgerekli. Both modes' inputs survive mode switching and
project JSON round-trip. Existing project payload version 1 and database schemas
(libraries 5, projects 1), repositories and runtime DB paths are unchanged.

## Deferred requirements

Optional explicit margins, actual pump-library/curve selection, head/NPSH links,
Formula View 2.0, startup/package audits and global UI polish remain later work.
Bend UI refinement remains deferred: remove its separate on/off control later,
include bend naturally in Pipe Design flow, represent no bend explicitly as b=0,
and never use numeric 1 as a hidden off flag. No bend behavior is changed here.
