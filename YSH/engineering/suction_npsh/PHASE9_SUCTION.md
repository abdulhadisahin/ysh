# Phase 9: Suction/ENPY V2 and automatic pipe discovery

## Normal workflow and ownership

A successful normal Pipe Design diameter or wall calculation now notifies the
workspace. When the combined existing inputs suffice, the existing V2 service
produces the authoritative `PipeSelection`; no engineering formulas or selection
rules are changed. A partial/invalid request does not fabricate a source. A
previous completed selection remains historical until a new result is produced.
A result without selected geometry is retained as an unavailable source.

`PipeSourceDiscovery` reads only the current project's existing Phase 7
`PipeTransferProjectState.selections`. There is no second registry, new table,
polling loop, DB scan, redraw-triggered calculation or duplicated dataset.
Discovery checks real selected geometry and finite positive Q/Di. Provisional
rule statuses are preserved: hydraulic applicability is not a compliance claim.

Basma and Emme now use the shared mode/source controls. The normal visible
buttons are Update and Keep current values; no create/refresh registry or
separate bind step is required. Choosing Pipe Design mode explicitly applies
the sole applicable result. Multiple results require a visible source choice.
With zero results, an inline message preserves the current inputs. Discovery
alone cannot choose linked mode, replace an applied snapshot or calculate.

Both modules share one project state but own independent `PipeInputState`s.
Publishing a new revision changes observations only. The old Q/actual Di and
existing hydraulic/ENPY results remain. Update explicitly applies the current
source revision and invalidates the downstream result; Keep retains the old
snapshot/results and stale semantics. Switching to manual clears the driving
link and retains starting Q/Di. Missing sources retain historical applied values
and allow calculation from them. Clearing the producing Pipe Design page removes
its owned source; closing a project clears all of that project's source state.

## Suction and ENPY calculation

`SuctionV2Input` contains the applied/manual pipe state plus local viscosity/unit,
length, roughness, explicit material selection and immutable local-loss entries.
`ENPYV2Input` keeps raw PE/Pb values and units, density, signed HEgeo and optional
external NPSHr independent of the pipe source.

`calculate_suction_loss_v2` delegates to the existing shared hydraulic path.
`calculate_enpy_v2` reuses the existing `calculate_enpy` service and authoritative
`SuctionNPSHCalculator.calculate_enpy` arithmetic, without recalculating hydraulics.
The combined V2 method composes those same two stages. V/Re/f/hf/hL/he, pressure
conversion, absolute PE/Pb meaning, density, HEgeo sign, optional NPSHr and
existing margin/warnings remain unchanged. There is no automatic +1 m margin,
manufacturer data inference, fluid-property lookup or new TL check.

Typed results extend the legacy result properties with exact used Q/actual Di,
typed local inputs, hydraulic stage and source trace. Existing Formula View
receives stored results; no Formula View implementation changes are made. Its
staged suction-loss alias is supplied by the new result model. Link notices
remain separate from engineering warnings. Linked Q/Di entries are readonly;
Calculate uses applied inputs even if display variables are modified, never live
upstream values. Shared two-decimal Turkish-comma formatting remains unchanged.

Material context never infers roughness. An explicit Emme material selection
resolves k once and retains the actual used k in the typed result. Saved manual
roughness is preserved on load. The material selector now invokes the existing
suction warning renderer rather than an undefined velocity-warning callback.

## Persistence and compatibility

The existing `pipe_transfer` namespace and workspace both retain version 1.
Libraries remain schema 5 and projects schema 1. No repositories, migrations,
tables or runtime DB paths change. Page-local legacy inputs/text still load;
legacy Emme remains manual even when Q/Di happen to match a source.

Pipe Design stores only its optional owning `pipe_selection_id` alongside its
existing page state; the complete result remains in the existing authoritative
selection collection. Restored ownership retains UUID/revision continuity.
Older Phase 8 saved sources remain discoverable and their applied links remain
valid. Without an explicit saved producing-page identity, a later newly produced
result starts a new lineage; identity is never inferred from matching numbers.
Both owners and all sources round-trip once through the existing project JSON.

## Deferred work

Formula View 2.0, startup performance, package-size audit and global UI/icon/
watermark polish remain later phases. Transfer Pump is unchanged.

The requested bend UI simplification is recorded only: eventually remove the
separate bend on/off control, make bend calculation part of Pipe Design flow,
and represent **no bend** explicitly with b = 0. A numeric coefficient such as
1 must not be a hidden off flag unless the engineering model defines it.
No bend UI, bend formula or pipe engineering rule is changed in Phase 9.
