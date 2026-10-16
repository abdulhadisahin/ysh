# Phase 8: Discharge V2 workflow

Basma now owns a `DischargeWorkflow` around the Phase 7 project transfer state.
The source controls are separate from engineering warnings and local hydraulic
inputs. Pipe standard/DN/NPS/Schedule/OD/wall and applied source revision are
shown as context; only actual Di and Q feed hydraulics.

## Explicit source actions

1. Complete the existing Pipe Design diameter and wall inputs.
2. In Basma, use **Create / refresh source**. This explicit compatibility action
   calls the existing V2 Pipe Design service using current inputs. No legacy
   theoretical diameter or nominal name is converted into a hydraulic Di.
3. Select an applicable result and use **Link selected source** (or explicitly
   choose linked mode). Sources are displayed by standard, DN, actual Di, Q and
   revision; UUIDs remain technical identity. Existing multiple sources are
   selectable without automatically choosing the latest.
4. Use **Calculate** to calculate Basma. Creating/refreshing a source never
   applies it or calculates Basma automatically. Refreshing the selected source
   retains its UUID and uses the Phase 7 revision helper. A changed source marks
   an existing link stale and retains all applied values and prior results.
5. **Update** applies the current revision of the same source, invalidates the
   prior hydraulic result and leaves L/k/viscosity/local losses/Hgeo unchanged.
   **Keep current values** preserves snapshot, result and stale/kept status.
6. Switching to manual retains current Q/Di as editable starting values and
   clears the driving link. Source changes then have no effect on Basma.

A source with no selected geometry cannot be newly linked. Missing/unavailable
sources retain historical applied Q/Di and permit explicit calculation using
those values. Provisional upstream rule status is carried and disclosed; no TL
verification or rule-compliance claim is inferred. Editing Pipe Design fields
alone does not publish a new result: source publication is explicit.

## Engineering and result ownership

`DischargeV2Input` separates `PipeInputState` from immutable local-loss entries,
viscosity, length, roughness, Hgeo and explicit material selection. The new
service entry point delegates to the existing shared hydraulic path, including
all numeric validation and warning generation. Local K/count validation follows
the existing dialog's nonnegative domain. Transferred material context never
selects library roughness implicitly. Explicit library roughness is resolved
once and the actual k is retained in the result's used inputs.

`DischargeV2Result` extends the existing typed hydraulic result with exact used
Q/actual Di/Hgeo and the typed input/source snapshot. The legacy result fields
(V, Re, f, hf, hL, hhat, Hs, Ktotal, regime, warnings) remain compatible with the
existing renderer and Formula View. Hs remains Hgeo + hhat. There are no added
pressure-head modes, TL rules, strength data or fluid-property lookups.

Q/Di widgets are readonly in linked mode. Calculate reads applied values only,
including when stale, and does not resolve live Pipe Design inputs. Even a
programmatic write to those display variables cannot replace linked inputs.
Local fields remain independent. V is now included in supporting result metrics.
Existing shared two-decimal Turkish-comma result formatting is retained; input
and persisted numerical precision is not rounded. Formula View is unchanged.

## Persistence and boundaries

Minimal MainWindow wiring carries the existing top-level `pipe_transfer`
namespace between Basma and the project-state JSON mechanism. The workspace and
namespace versions both remain 1; sources and independent suction transfer state
are preserved. No repositories, tables, migrations or DB paths change. Legacy
Basma payloads still load manual, including preserving saved manual roughness.
Closing/clearing a project clears its source list and links. Clearing the current
Basma calculation detaches its pipe input while retaining project source choices.

All source/state/UI callback tests run without a Tk interpreter. The existing
hydraulic core, Pipe Design engineering, Emme/ENPY, Transfer Pump, Formula View,
branding and shell layout are unchanged. Startup/package audits and full Emme
integration remain separate later phases.
