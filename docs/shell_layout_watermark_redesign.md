# D243 V2 — Shell / layout / watermark visual redesign

Accepted base: `bbca41ba7883d2ab7c1b396d19e8a516bb4f0436`, 1996 passing tests.
This user-approved visual direction supersedes the earlier watermark-removal
decision and the earlier 128px sidebar-logo target. The branding assets themselves
are unchanged.

## Visible changes

- The engineering profile/circuit/fluid strip and its explanation no longer
  occupy the main workspace. Its cached project context, services, availability
  checks, persistence and propagation remain intact. The same existing selector
  component is available from **Project → Engineering context…** in a separate
  modeless editor. Family selection remains authoritative in the left sidebar.
- The full-height 300px sidebar is preserved. Its canonical D243 logo is 176px.
  Project actions use equal-width cells in a two-column grid, uniform 44px minimum
  height, 32px existing icons and equal horizontal/vertical gaps. The fifth action
  occupies the same-width left cell of the third row; no oversized final button
  or duplicate plus sign remains. The bounded footer retains project metadata
  scrolling, while the project list/empty state retains its expanding area.
- Fuel and Fire calculation viewports display a large, partially cropped,
  viewport-fixed canonical D243 logo behind native content. Its canvas item is
  below the content window and has no click/focus bindings. Decorative image
  bounds do not participate in the content scroll region.
- Tk/ttk cannot assign native per-child alpha. Background-only frames use
  **runtime alpha compositing**, while text labels and labelled cards keep
  **unaltered native ttk layouts/painters** and gentle opaque background tones
  sampled from that composition. There is no image element in a label or card
  caption layout and no whole-window opacity. Text retains its foreground/font;
  entries, buttons, images, semantic notices and dark/accent surfaces remain
  opaque. The controlled translucent feeling prioritizes readable results.
- Compositing is scoped to active calculation viewports. Formula/Library/History
  dialogs, sidebar and floating editors do not receive this decoration. Surfaces
  are cached by widget, geometry and viewport; scroll/resize requests coalesce,
  and unchanged crops are not re-rendered. No recurring polling is introduced.
- Cyan/turquoise shell accents, red Fire selection, original module colors,
  amber warnings, error/success roles and the complete existing icon family are
  preserved. The optional small ship detail is omitted to keep navigation clear.

## Freeze and validation

No engineering equations, parsing/defaults, DB schema/migrations, source matching,
Fire/Fuel calculations, snapshots, Formula View logic, History semantics or PDF
generation are changed. Nozzle and seawater HW remain blocked. The approved
untracked `docs/references/Yangın Söndürme.xlsx` is neither edited nor staged.

Geometry acceptance covers TR/EN at 1100×700, 1280×800, 1440×900 and 1700×1000,
all six calculation pages, native control bounds, equal project-action cells,
project-area availability, background stacking and content-only scroll bounds.
Focused checks also cover optional context editing without state changes,
unchanged source-image bytes, opaque controls/text/semantic colors and window
alpha remaining 1.0.

One isolated normal launch reported **Startup over 15 seconds: False**. No
repeated startup benchmarks or screenshot attempts were performed. The isolated
prototype window was used during the earlier pass. Final user inspection uses
the separately titled **CORRECTIVE FINAL** window with the committed source.

Manual acceptance: **manual user visual review required**.
Final validation: **2010 passed, 0 failed in 683.08s (0:11:23)** on the final
corrective code. This is the accepted 1996 tests plus 11 retained redesign cases
and three new corrective workflow/text-painter cases. The final focused group
passed **30 tests in 89.83s**, including actual Foam/HW flows and the shared
Formula/History/Library windows; the eight TR/EN geometry combinations also pass.
Legacy visual expectations were updated only for the newly requested logo/button
dimensions, bounded footer and content-only scroll region; interaction/state,
numerical and frozen-data checks remain in place.

Starting corrective state: branch `d243-v2-handoff`, HEAD
`bbca41ba7883d2ab7c1b396d19e8a516bb4f0436`, with the prior redesign's 20 related
partial files and the approved untracked reference. Useful changes were retained.
No unexpected unrelated modifications were found. The workbook remains unchanged
and untracked, SHA256
`bd9aa871454c184afdb45e14bd0c008818d49701d5cc92e1de7ca89126159474`.
Outcome: **PASS_WITH_USER_REVIEW**; visual acceptance remains **USER REVIEW REQUIRED**.

## Layering corrective — current worktree continuation

The user reported incomplete Foam presentation and disappearing text in the
initial visual prototype. The calculator itself reproduced 945 L correctly; the
regression was isolated to custom image elements replacing label/caption layouts.
Those replacements are removed. Labels and labelled cards now retain their full
native draw trees, with only soft background-color treatment. Image compositing
is confined to non-text frames behind native child widgets. The large decorative
logo remains below the content window and cannot cover controls or text.

The 176px sidebar logo now occupies a full-width, explicitly center-anchored plate
with symmetric padding. Geometry checks compare its center to the sidebar center.
The equal project-button grid and hidden main context strip are retained. The
existing optional context editor remains available without changing project state.

Real application smoke checks exercise manual Foam (945 L), source-linked Foam
with an override (1134 L), native label painters, Formula View, PDF export and
generation, actual session History receipt, immutable snapshots and stale PDF
disabling. At 1100×700 the computed primary result was also below the visible
viewport; successful Fire calculations now reveal that existing result without
recalculating or changing any data. HW's water reference result remains
2.3717829024660286 bar. Nozzle and
seawater methods remain blocked. A single corrected normal source launch remained
below 15 seconds. One Computer Use capture attempt returned `FrameArrived timed
out`; it is not retried and is not a functional blocker. **USER REVIEW REQUIRED**.
