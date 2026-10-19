# Phase 16 workspace corrective pass

Starting checkpoint: `d243-v2-handoff`,
`21d7e845c9813ae77a6f8500042ea3d10b9b6134`; clean tree.
Interpreter: `.venv314/Scripts/python.exe`, Python 3.14.8.
Baseline: 1357 passed.

## Presentation contract

The scroll host has only its content viewport and vertical scrollbar. It no
longer allocates a right decoration column (formerly 120–280 px / 20%). The
content window tracks the entire viewport width.

One shared `WorkspaceWatermark` implementation places the official emblem at
the lower right of existing engineering surfaces, behind their controls. It
uses `place`, never participates in grid/pack size negotiation, and lowers once
at creation. Pipe uses the wall-result surface; discharge and suction use their
input surfaces; transfer uses the design-result or empirical-input surface,
according to the already selected mode. These surfaces have direct controls
rather than a full opaque page window covering the decoration. No new panel or
reserved empty area is introduced. Wheel routing remains with the page host.

The alpha is 12% (maximum alpha 31/255). Artwork keeps its aspect ratio, fits
within a 12 px inset, and has a maximum side of 480 px. Hidden/tiny surfaces do
not load artwork. Resize events coalesce with `after_idle`; dimensions are
quantized to 8 px and each surface caches at most six derived images. There is
no polling or repeated stacking operation. Actual visibility and subtlety still
require Windows visual acceptance.

Each live module retains a compact explicit formula button. Its separate,
scrollable Formula View 2.0 window is created only when opened, refreshed from
the existing stored-result FormulaStep provider, and released on close. The
historical view keeps its existing inline default and frozen provider. The
PNG/MathText/text renderer and all explanatory sections are preserved.

No sidebar, icon, context, tab, calculation, database, Library, engineering data,
snapshot, dependency, or minimum-main-window-size changes are included.

## Verification

- Focused contracts: 205 passed (workspace, formula, sidebar, icons, startup
  helper signatures, snapshots/history and final acceptance regressions).
- Numerical freeze: exact equality against recorded Phase 13 whole/hydraulic/
  legacy results; Pipe V2 12 cases, transfer design 36 cases, empirical 36 cases
  also exactly unchanged against their original baselines.
- Static UI helper signature audit: no invalid or dynamic forwarding calls.
- Real runtime attempt: **BLOCKED_ENVIRONMENT** at `tk.Tk()` because a usable
  `init.tcl` cannot be found. Tcl/Tk was not changed. No visual PASS is claimed.
- Full suite: **1371 passed, 0 failed** in 43.03s (1357 baseline + 14 new
  corrective cases). Existing assertions that required a dedicated watermark
  column or prohibited a separate Formula View were updated to the new contract.

## Manual Windows acceptance

Run `.venv314\Scripts\python.exe main.py` from the repository. Inspect both
normal/maximized size and 1200×700. Complete the following checks:

1. [ ] App opens.
2. [ ] Project list works: first/second project, switch, refresh, delete, empty/list transition.
3. [ ] Header icons retain the accepted 79 px canvas / approximately 72 px artwork.
4. [ ] Sidebar icons retain the accepted 40 px canvas / approximately 36 px artwork.
5. [ ] Watermark occupies no dedicated right-side column.
6. [ ] Pipe workspace uses the full available width.
7. [ ] Transfer workspace uses the full available width in DESIGN and EMPIRICAL.
8. [ ] Basma workspace uses the full available width.
9. [ ] Emme workspace uses the full available width.
10. [ ] Watermark is visible and subtle in all modules, before and after calculation and resize.
11. [ ] Watermark does not block controls, keyboard focus, or scrolling.
12. [ ] Main pages are no longer dominated by the full formula document.
13. [ ] Formula button opens the separate view; close/reopen and language switching work.
14. [ ] Formula View 2.0 retains formula, variables, coefficients/values, reasons, sources, substitution, result and compliance; Pipe no-bend explicitly explains b=0; transfer DESIGN/EMPIRICAL remain distinct.
15. [ ] Historical Formula View opens read-only with frozen steps and provenance.
16. [ ] Layout remains usable at 1200×700.
17. [ ] Icons have no clipping, text overlap, or restored heavy outer frames.
18. [ ] No startup traceback or callback error occurs.
19. [ ] App closes normally, including while a Formula View is open.

Overall status remains **PENDING_MANUAL_ACCEPTANCE** until these checks pass.
Phase 17 is outside this pass.
