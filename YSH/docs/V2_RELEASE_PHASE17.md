# D243 V2 — Phase 17 release engineering

Status: **PENDING_MANUAL_ACCEPTANCE**. The final EXE launches and closes in the
controlled Windows environment; a human clean-PC acceptance run is still required.

## Checkpoint and frozen scope

- Branch: d243-v2-handoff; initial commit 94bc328602adb512476fc9bf015e95598f0edfff; clean.
- Required interpreter: `C:\Users\Özberk\Documents\ysh\.venv314\Scripts\python.exe`, Python 3.14.8 x64.
- Baseline: 1371 passed, one cache permission warning, 43.58 s.
- Final: **1379 passed, 0 failed**, 42.57 s. Eight meaningful release tests added;
  two packaging contract modules updated for version-aware hooks.
- Focused coverage: 149 passed before the final image optimization; final focused
  startup/resource/packaging/chart/icon/sidebar group: 61 passed, 2.41 s.
- Numerical whole/hydraulic/legacy freeze equals the recorded Phase 13 baseline;
  Pipe V2 12 cases, transfer design 36 and empirical 36 remain exactly equal.
- No engineering/domain/service/repository/schema/data/snapshot/Library/context
  change. Libraries remain v5, projects v1, writable data remains
  `%LOCALAPPDATA%\YSH\data`. No new engineering values or tolerance rules.
- No UI redesign: header/sidebar sizes, watermark, workspace and Formula View
  retain their accepted semantics. Product metadata uses the existing 0.1.0
  manifest version; no new versioning system.

## Profile before optimization

Method: fresh subprocesses of the required interpreter, `-X importtime`, scoped
`perf_counter` timestamps, and cProfile. Only disposable LOCALAPPDATA directories
were used. No production diagnostic prints or profiling hooks were added.

Normal source startup still reports unavailable init.tcl. The Python installation
was not repaired. Controlled GUI measurements use matching standalone Tcl/Tk
9.0.4 scripts supplied only to the test processes; they are not normal-environment
acceptance claims. The original chart (and, for the process-clock replay, original
asset loader) was loaded from the starting commit into the test process, without
changing checkout files. The original three GUI measurements were recorded before
the asset optimization. First runs are cold-ish, not cache-flushed benchmarks.

Ordinary source bootstrap, script entry to infrastructure initialization complete:

| Run | Before | After chart lazy import |
|---|---:|---:|
| First | 2.615 s | 0.548 s |
| Warm 1 | 1.176 s | 0.497 s |
| Warm 2 | 1.497 s | 0.494 s |

Parent process elapsed including interpreter start, failed Tk probe and teardown:
2.874 / 1.477 / 1.807 s before; 0.698 / 0.679 / 0.664 s after. These are not
usable-window timings. Formula, Library workspace and History UI were not loaded;
Matplotlib changed from loaded to absent at this boundary.

Controlled GUI, script-entry clock (approximately, not millisecond guarantees):

| Run | MainWindow begins before/after | Construction before/after | First usable drawing before/after |
|---|---|---|---|
| First | 3.54 / 0.71 s | 19.62 / 3.16 s | 26.23 / 6.64 s |
| Warm 1 | 1.45 / 0.52 s | 20.17 / 2.22 s | 23.97 / 4.79 s |
| Warm 2 | 1.73 / 0.49 s | 19.12 / 2.18 s | 24.10 / 5.22 s |

Warm first-drawing average improves by approximately 79%. Main window is real,
mapped and processed with `root.update`; this does not replace human usability
inspection. The baseline cProfile after the chart change but before the image
change showed asset loading at 18.54 s, ImageTk construction at 14.44 s and
MainWindow construction at 19.13 s. Matplotlib imported through the transfer chart
and contributed about a second to the import chain. Pillow is needed at startup
for the existing visible branding/icons and remains eager.

An additional controlled replay uses the parent's pre-spawn monotonic timestamp,
so it includes interpreter startup rather than starting at script entry:

| Process-clock stage | Original checkpoint replay | Final code |
|---|---:|---:|
| Process start → infrastructure initialized | 1.57 s | 0.63 s |
| Process start → MainWindow constructor begins | 1.82 s | 0.82 s |
| MainWindow construction duration | 17.35 s | 3.02 s |
| Process start → first usable drawing | 22.15 s | 6.49 s |

This pair uses warm OS/data caches; original chart and asset-loader code are
replayed from the starting commit only inside the profiling subprocess. It is
not presented as an additional cold benchmark.

Applied changes and evidence:

1. Defer Matplotlib/TkAgg and the chart canvas until the chart is mapped. Hidden
   updates retain the latest model; mapping renders it; the canvas is reused.
   Formula MathText was already lazy and is unchanged. Fresh-process import,
   latest-model/map/cache tests and actual frozen TkAgg smoke cover this boundary.
2. Evaluate only the selected image fit policy; the former eager dictionary
   evaluated every crop/fit even when unused.
3. Upload only the displayed image to Tk. `LoadedImage.source` retains a compatible
   handle alias to `rendered`; no consumer independently displayed/transformed
   the former full-size Tk copy (the header only retained it). The canonical file
   remains untouched. All **53 PNG display renditions are pixel-identical** before
   and after, using actual family fit modes. Existing geometry/icon tests pass.

All four pages remain eagerly constructed. A page/navigation rewrite was not
justified after the narrow fixes. Library categories and historical snapshots
remain lazy. Library schema initialization occurs twice on the same database
instance (constructor and application initialization); the redundant warm check
is about 1 ms. It is retained to preserve lifecycle/schema safety. No global DB
cache or migration shortcut was introduced.

## Packaging audit and configuration

Before: onedir/console YSH output, explicit Tcl/Tk 8.6 paths/DLL names, broad
Matplotlib collect_all, full resources folder and compatibility runtime hook.
There was **no existing comparable dist** in this checkout; old size/file count,
differences and percentage savings are N/A. The historical approximate 100 MB
claim was not treated as a measurement.

After: same onedir architecture, windowed `D243/D243.exe`, approved D243 icon and
Windows ProductName/FileDescription, version 0.1.0. Tcl/Tk DLLs are discovered for
the actual interpreter; missing init.tcl/tk.tcl resources abort the build.
Official PyInstaller hooks collect Matplotlib data/fonts, Pillow and SQLite;
TkAgg is the selected Matplotlib backend. Broad collect_all was replaced only
with this explicit required-backend configuration, then verified in the frozen
payload using PNG, MathText and a real TkAgg canvas. No formula PNG was removed.

Runtime versions: Python 3.14.8, Tcl/Tk 9.0.4, SQLite 3.50.4, Matplotlib 3.11.2,
Pillow 12.3.0, NumPy 2.5.4, contourpy 1.4.0, cycler 0.12.1, fonttools 4.67.0,
kiwisolver 1.5.1, packaging 26.3, pyparsing 3.3.3, python-dateutil 2.9.0.post0.
PyInstaller 6.22.3 / hooks-contrib 2026.8 were installed as build tools only;
no application runtime dependency declaration changed.

Tcl/Tk packaging inputs: the interpreter DLLs both report 9.0.4; the installed
Python runtime and its cached installation ZIP contain no loose init.tcl/tk.tcl.
Matching script libraries (including license.terms) were extracted into a separate
build resource directory from official upstream tags:

- [Tcl core-9-0-4](https://github.com/tcltk/tcl/tree/core-9-0-4/library), archive
  `https://codeload.github.com/tcltk/tcl/zip/refs/tags/core-9-0-4`, SHA-256
  `e6a6d861b3fd75dd00c2c71b5b0f859022fa9b59207819a2417d93b9ab634f46`.
- [Tk core-9-0-4](https://github.com/tcltk/tk/tree/core-9-0-4/library), archive
  `https://codeload.github.com/tcltk/tk/zip/refs/tags/core-9-0-4`, SHA-256
  `e41bcf9d9ba318ac2975dffcd1ae4f89061f61649c7ed3bf4f5c362e5e6c24f0`.

Only each archive's library/ contents and license.terms were used. Scripts are
paired with the existing Python 3.14 DLLs, not another Python environment. No
installation, registry or global Tcl/Tk environment setting was modified.
The frozen runtime hook points to its own `_internal/_tcl_data` / `_tk_data`,
verified in the outside-repository copy with TCL_LIBRARY/TK_LIBRARY cleared.

Actual final build, from the repository:

```powershell
$env:TCL_LIBRARY = 'C:\Users\Özberk\Documents\Codex\2026-10-15\files-pasted-by-the-user-d243\work\phase17\tk_runtime\tcl9.0'
$env:TK_LIBRARY = 'C:\Users\Özberk\Documents\Codex\2026-10-15\files-pasted-by-the-user-d243\work\phase17\tk_runtime\tk9.0'
$env:D243_BUILD_PROBE = '1'
& 'C:\Users\Özberk\Documents\ysh\.venv314\Scripts\python.exe' -m PyInstaller .\build\ysh.spec --noconfirm --clean --workpath .\build\pyinstaller --distpath .\dist
```

Build PASS. Meaningful warnings were reviewed: platform-conditional Unix/macOS,
optional image/format/document extras and static-analysis pseudo-module exports
(e.g. numpy._core scalar names, collections.abc and sqlite3 exception names).
Actual imports, SQLite, PNG, MathText and TkAgg pass frozen execution. No missing
D243 module or required DLL/resource was observed. Optional libraries were not
installed merely to silence warnings.

## Database and dead-asset inventory

The sole tracked source-tree DB is
`YSH/work/verification-localappdata/YSH/data/projects.sqlite3`, 16,384 bytes,
legacy projects/sqlite_sequence schema. Classification: **C, stale validation /
development DB**. The only textual reference is the previous acceptance audit;
production uses ApplicationPaths and projects.db/libraries.db. It is retained in
source but excluded by the resources-only data manifest. It is not a production
seed and is absent from the final package. No private project records were read
or copied into the release. No binary seed database is required; existing code
bootstraps the normal per-user databases.

Audited all 55 resource files and dynamic action/status/library/formula/empty-state
maps, Python loaders, spec, tests and acceptance docs. Candidates include legacy
`resources/ysh_logo.png`, `resources/ysh.ico` and duplicate D243 derivatives.
The old icon remains referenced by the legacy installer; old loader names and
public size-specific branding paths still exist. Duplicates alone are not proof
of dead dynamic paths. **No source asset was deleted or individually excluded.**
All 55 packaged resource files have exactly the source SHA-256, including the
canonical emblem. Formula assets and Pillow plugins are retained. Package
correctness takes precedence over arbitrary size reduction.

Project tests, venvs, git data, phase docs, profiles, logs, validation DB and build
outputs are absent from the shipped data manifest. Python application modules
are frozen in PYZ. The optional build-only probe shares this PYZ/hooks but is
not part of COLLECT, the final directory or ZIP. The older Inno Setup configuration
is not a Phase 17 deliverable and was not run.

## Final measured package

| Category | Bytes | Files |
|---|---:|---:|
| Application EXE + PYZ | 9,498,276 | 1 |
| Other runtime dependencies | 13,987,464 | 72 |
| Python runtime | 8,187,556 | 2 |
| SQLite | 1,718,208 | 2 |
| Tcl/Tk | 10,938,796 | 1029 |
| Matplotlib | 14,599,666 | 212 |
| NumPy | 27,788,477 | 38 |
| Pillow | 11,242,496 | 6 |
| Branding assets | 21,875,772 | 11 |
| Empty-state illustrations | 7,398,809 | 6 |
| Formula PNGs | 2,574,377 | 8 |
| Other illustrations | 3,252,351 | 2 |
| UI icons | 34,317,761 | 28 |

Total: **167,380,009 bytes / 1417 files** (about 159.63 MiB).
EXE: **9,498,276 bytes**. PNG/ICO resources total 69,419,070 bytes; the largest
single dependency is NumPy OpenBLAS (20,589,056 bytes). Pillow AVIF support is
retained rather than pruned speculatively. No before/after size claim is made.

Output: `dist/D243/D243.exe`. Release ZIP: `dist/D243_V2_Windows_x64.zip`,
**110,774,019 bytes** (about 105.64 MiB), created only after frozen smoke PASS.
Only the complete D243 runtime folder is archived. ZIP CRC, 1417 file entries,
EXE equality, and no database/test/probe payload checks pass.

ZIP SHA-256:
`a456e014db80ba19237922eac0a85fb9ceee9bd3398261aea972c436f2544263`

EXE SHA-256:
`b73f4fb7dd6e110d6e789add8b7160d3e7dca646f2cc4a415cd63f575f5475e7`

The EXE is **unsigned**. Its resource icon exactly equals the approved D243 ICO;
ProductName/FileDescription are D243 Boru ve Tulumba Boyutlandırma Programı.
No signing infrastructure or Defender/SmartScreen bypass was introduced.

Full hashed file inventory, source asset inventory, frozen probe result and SHA
sidecar are delivered beside the ZIP, outside the runtime folder. No binaries,
logs, profiles or inventory scratch files are committed to Git.

## Packaged runtime evidence

The final distribution was copied outside the repository. With Tcl/Tk environment
paths cleared, the frozen build-only checker passed: real mapped MainWindow
(~6.98 s), Tcl/Tk 9.0.4 using the copied package directories, D243 PNG/alpha/
LANCZOS resources, all formula PNGs, MathText/fonts, a real TkAgg canvas, Pipe
(including b=0), transfer design, discharge, suction/ENPY, typed FormulaStep
rendering, all four module/formula windows, SQLite foreign keys/integrity,
project create/save/close/reopen, Library, History and normal close. All data
was disposable. Source regression tests separately cover empirical numerical
freeze and historical immutability.

The **actual final D243.exe**, not the checker, was also launched directly from
the outside-repository folder without a Python command or activated venv. It
opened the D243 window and exited normally via its window close handler. A
second launch using the probe's existing compatible project/library databases
also opened and closed normally. Logs report frozen=True and resource paths
inside the isolated copy; the release did not access the user's real databases.
This proves controlled packaged launch, not a human clean-machine acceptance run.

## Deferred items and final manual Windows acceptance

Further watermark placement and broader workspace aesthetics experimentation
are deliberately deferred by the user. They were not redesigned or treated as
release blockers. Page-level lazy navigation and the negligible duplicate DB
check remain deferred. TL steel A/B, CuNi production temperature table,
manufacturing tolerance production rule, and TL minimum wall production rule
remain **NOT_CONFIGURED / SOURCE_REQUIRED**. They were not populated.

Use the **final packaged EXE**, not source Python, on normal Windows (ideally a
clean offline PC with no Python installation). Extract the whole ZIP first:

1. [ ] Launch D243.exe.
2. [ ] No init.tcl error.
3. [ ] Main window appears.
4. [ ] D243 logo/icon is correct in the window, taskbar and Explorer.
5. [ ] Project list loads.
6. [ ] Create a disposable project.
7. [ ] Pipe calculation, including Bükme yok, works.
8. [ ] Formula View opens; formula images, MathText and explanatory sections work.
9. [ ] Transfer DESIGN and EMPIRICAL calculations/chart work and remain distinct.
10. [ ] Basma calculation works.
11. [ ] Emme/ENPY calculation works.
12. [ ] Libraries open normally.
13. [ ] History and a frozen historical Formula View open correctly.
14. [ ] Save the project.
15. [ ] Close.
16. [ ] Reopen the final EXE.
17. [ ] Reopen the saved project and verify its values/history.
18. [ ] Close normally.
19. [ ] Note cold-ish and warm startup times (three runs if practical).
20. [ ] Confirm no Python installation, source checkout, venv or internet is required.

Until human acceptance is recorded: **PENDING_MANUAL_ACCEPTANCE**. No later
phase is started automatically.
