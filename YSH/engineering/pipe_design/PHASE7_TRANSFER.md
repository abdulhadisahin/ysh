# Phase 7: controlled PipeSelection transfer

`PipeSelection` is the authoritative Pipe Design result. Each new result has a
UUID `selection_id` and starts at revision 1. Recalculating the same lineage is
explicit: call `revise_selection(previous, result)`, or pass `previous_selection`
to `PipeDesignService.calculate_v2`. Reads never change identity or revision.

The revision signature comprises Q, selected pipe row ID, actual Di, OD, selected
wall, selected standard ID/code, DN, NPS, Schedule, material ID, fluid ID, system
ID and circuit ID. Changes to theoretical D, design/actual velocity, temperature,
wall-calculation internals, rule status, provenance notes or presentation metadata
alone do not invalidate hydraulic inputs. If no geometry is selected, publishing
that result marks a previous link source-unavailable. These results are not
applicable as a new hydraulic snapshot.

`PipeInputState` belongs independently to discharge or suction. Its typed modes
are MANUAL and LINKED. An explicit `link_to(selection)` captures immutable
`PipeSelectionSnapshot` values and source UUID/revision/time. The actual stored
Di is copied; theoretical D and DN never substitute for it. Geometry from a
provisional result is usable, but `upstream_status` remains in the snapshot and
trace: transfer makes no new rule-compliance or verification claim. Existing
Phase 2 dimension/material source references are retained without relabelling
them as direct user input.

`observe` and `PipeTransferProjectState.with_selection` change observations only.
They cannot calculate hydraulics or replace applied Q/Di. `update` applies the
same source explicitly; a different source needs `link_to`. `keep_current`
records the observed revision while keeping the old snapshot and stale status.
A further source change clears that decision flag. `to_manual` clears the driving
link and can retain values as starting inputs. Missing sources retain all applied
values; exact UUID lookup never chooses an arbitrary latest selection.

The additive `calculate_with_pipe` methods on discharge/suction and
`calculate_suction_loss_with_pipe` on suction consume only `used_values`.
They delegate to the existing hydraulic services and add link trace metadata.
Material roughness still requires the existing explicit material argument;
transferred material context never silently overrides manual roughness.

`transfer_serialization` encodes complete selections and the smaller applied
snapshots as primitive JSON objects. Enums use stable values; UUIDs and ISO dates
are strings. Identity and revision are mandatory when decoding a selection.
Unknown record fields are ignored; unknown transfer versions are rejected by the
typed reader. No timestamp is invented during load. The namespace `pipe_transfer`
has version 1; the existing workspace `schema_version` remains 1 and both DB
schemas remain unchanged (libraries 5, projects 1).

`ProjectPersistenceService.save_with_pipe_transfer` and
`open_with_pipe_transfer` use the existing project-state JSON repository. A legacy
save that omits this namespace preserves the saved namespace, including future
opaque versions. Explicitly saving an empty transfer state clears its links.
Legacy projects without the namespace load as MANUAL, optionally retaining parsed
legacy Q/Di; matching numbers never create provenance. On typed load only source
observations are refreshed, and applied historical values remain unchanged.

Final page controls and Formula View integration remain for phases 8/9. No UI,
calculation formula, engineering rule, repository, migration, factory data,
branding or runtime dependency changes are part of this phase.
