# Formula / Library corrective pass — acceptance record

Starting branch: d243-v2-handoff. Starting commit:
2da178d542e503d1e965541137ddba92a9f08323. Clean initial tree.
Interpreter: `C:\Users\Özberk\Documents\ysh\.venv314\Scripts\python.exe`, Python 3.14.8.
Baseline: **1379 passed**, one cache permission warning, 44.16 s.

## Phase A: prepared equation artwork

See [FORMULA_ASSET_AUDIT.md](FORMULA_ASSET_AUDIT.md) for the eight exact paths,
filenames, dimensions, bytes, dynamic-reference/package status and equation map.
All original PNGs were opened and inspected. Their `.png.png` filenames are real;
the resolver and packaging do not add extensions. No asset was renamed/edited.

The root cause was a missing display adapter: FormulaStep cards constructed a
FormulaSection without asset_names. The shared renderer already preferred PNG,
but had nothing to resolve. Stable step IDs now select audited artwork through
ui/formula_asset_policy.py; localized titles are never identifiers.

Six original PNGs are mathematically suitable for their matching base equations:
diameter, Rp0.2/B allowable stress, active bend, base total-wall sum, friction loss
and ENPY. The same friction picture serves discharge and suction. Transfer and
other steps without matching pictures keep MathText/native text.

**Two prepared pictures are wrong and remain quarantined, not replaced:**

- Base-wall image draws `20σ(v+pc)` instead of `(20σv)+pc` in the denominator.
- Local-loss image draws D^5 instead of the accepted D^4.

These findings were reported before replacement. Their original files remain
resolvable and packaged for audit, but live, legacy and frozen views cannot show
them as equations. Correct stored MathText/text and a short localized explanation
are used. A mixed legacy section containing a quarantined picture falls back as
a whole rather than letting one valid image hide the other equation. Replacement
of these two PNGs remains an explicit open item, not a claimed PNG acceptance.

No-bend b=0 never receives an active-bend PNG. Configured stress is not replaced
by Rp0.2/B artwork. Configured tolerance/minimum wall rules retain the complete
stored expression, rather than being replaced by the simple total-wall picture.
Historical FormulaSteps use this exact display policy after ordinary snapshot
decode, without modifying the frozen payload, looking up current Library truth
or recalculating.

Phase A commit: `45ab710` — D243 V2: repair formula asset mapping and PNG rendering.
Phase A focused result: 142 passed.

## Phase B: Formula View presentation

- Full Formula View stays an explicit, separate modeless window. Default size is
  920×640, resizable with scrolling; the main app minimum stays 1200×700.
- One outer card per existing FormulaStep, compact classification/verification
  header, plain titled sections instead of deeply nested borders, compact tables,
  and emphasized result. Step count, check outcome and raw values are unchanged.
- Long provenance/reference/technical detail uses a shared disclosure. Summaries
  include available organization/document/verification and are bounded to 180
  characters; all original rows remain available on expansion. NULL and empty
  source fields do not render. No verification is inferred from source presence.
- Formula artwork retains the complete alpha silhouette (threshold 1, 2% safe
  margin), aspect ratio, no upscaling, maximum 560×280. Only transparent outer
  whitespace is trimmed in memory. Original files remain unchanged.
- Resize events are quantized/coalesced using after_idle; the existing bounded
  asset cache is reused. Active image references belong to each native label;
  pending resize callbacks are canceled on destruction. No polling or eager
  startup formula decode is introduced.
- PNG → MathText → native text remains the rendering chain for valid artwork;
  unsupported/configured/no-bend cases keep their authoritative stored expression.

## Phase B: Library presentation

- All **17 categories / 8 groups** appear in a selected-state left Treeview.
  Navigation is generated from existing static catalog metadata; it does not
  enumerate Library datasets. Same modeless lazy window/service composition.
- Center table keeps the existing four useful columns, clearer 30 px rows,
  alternating neutral surfaces, navy selection, explicit record count, horizontal
  overflow scrollbar and a native no-match state. Verbose provenance stays in the
  selected-record panel.
- Search is prominent; active/ownership/verification filters share one expandable
  advanced row, initially collapsed. Existing choices/query/filter semantics are
  unchanged. The relationship picker stays available only where applicable.
- Right panel groups existing fields into basic information, engineering data,
  ownership/state, verification, source/description, relationships and technical
  details. UUID/technical groups can collapse. Long record headings truncate only
  the heading, not the underlying field/provenance data.
- Ownership and editable/read-only state appear together once for the selection.
  Protected Edit remains disabled; controller/service protection still enforces
  it independently. Drafts survive rejected navigation. Explicit Save/Cancel,
  duplicate/FK/soft-inactive behavior and full-precision editor variables stay intact.
- Editor sections use the existing allowlisted fields, kinds and relationship
  choices. No hard-delete action, interpolation, CuNi/TL seed, repository or data
  policy was added.

## Visible TL label/provenance audit

The legacy immutable table has no in-repository verified SourceReference,
document revision, verification date or verified table provenance. That is not
proof the historic numbers are wrong; it means the UI must not assert a verified
production rule. No external source verification or numerical table edit was made.

| Visible location before | Provenance status | Corrective display |
|---|---|---|
| Pipe button: Türk Loydu Tablo 8.9 | No verified provenance in legacy table | A/B source notes |
| Dialog title: Türk Loydu Tablo 8.9 — A/B | Same | Reference notes — source verification required |
| Dialog footer: Source TL, Part 8, Table 8.9 | Same | Explicit unverified legacy-note warning |
| Safety-factor reference note (TR/EN), B=1.80 attributed to exact TL table | Unsupported hardcoded authority claim | Used B is user input; legacy source verification required |
| Weld-factor reference note (TR/EN), v=1 attributed to TL | Unsupported hardcoded authority claim | Used v is the calculation input; production source verification required |

The six original table rows, default B=1.8, actual user B/v inputs and equations
remain exactly unchanged. The 3D convention and empirical-transfer disclaimers
already deny TL authority and remain. Actual verified source metadata/labels from
records and frozen steps are preserved; no blanket removal of TL source names.

## Verification and release boundary

- Final focused suite: **252 passed in 20.34 s**.
- Final full suite: **1432 passed, 0 failed, in 40.94 s** — all 1379 baseline
  cases plus 53 new corrective cases. No skip/xfail or test removal was added.
- Tests cover inventory/double suffix/source-frozen paths, stable keys, PNG-first,
  missing/invalid-image fallbacks, quarantined artwork, active/no-bend/configured
  guards, frozen step decode, bounded aspect-safe image geometry, source disclosure,
  NULL source data, result/check presence, complete category navigation, detail
  grouping and TL warning labels. Existing service/controller/protection tests remain.
- Numerical whole/hydraulic/legacy outputs equal the recorded Phase 13 baseline;
  original Pipe V2 12, transfer design 36 and empirical 36 cases remain exactly equal.
- Controlled source runtime uses only the required interpreter, a disposable
  LOCALAPPDATA profile and the already bundled matching Tcl/Tk 9.0.4 scripts. No
  Python/Tcl installation or global environment setting is changed.
- Real Tk smoke passes all four modules, calculations, Formula View, PNG/MathText/
  TkAgg, SQLite, project save/reopen, Library and History. Additional checks pass
  all 17 categories/8 groups, filters/search/empty state, rejected navigation with
  retained draft, protected read-only selection, seven valid PNG cards, safe
  fallbacks, frozen payload equality after resize and normal close. No callback
  traceback was observed. Human visual/readability acceptance is still pending.
- No engineering/service/repository/schema/migration/snapshot or watermark file
  was changed. No dependency added. Source factory protection and DB paths stay.
- The spec still packages the complete resources directory and discovers all
  application UI modules. All eight formula files were hash-matched inside the
  existing Phase 17 ZIP. **No new EXE/ZIP was built**, as requested pending acceptance.
  The old ZIP SHA-256 remains
  `a456e014db80ba19237922eac0a85fb9ceee9bd3398261aea972c436f2544263`.
  That ZIP does not yet contain this corrective source/UI pass.

## Manual Windows acceptance — current source, new package only after approval

Use the required .venv314 interpreter in the normal working Windows environment.
Record PASS/FAIL and inspect normal size, narrower Formula View and 1200×700 main
window. Two quarantined pictures explicitly use safe fallbacks until corrected:

1. [ ] App opens.
2. [ ] Formula View opens separately and can close/reopen.
3. [ ] Pipe theoretical diameter shows the intended PNG.
4. [ ] Pipe Rp0.2/B allowable stress shows the intended PNG; configured stress does not.
5. [ ] Base wall uses the correct MathText/text denominator; wrong PNG is not shown.
6. [ ] Active bend shows the intended bend PNG.
7. [ ] No-bend explicitly displays b=0 and its reason, without active-bend artwork.
8. [ ] Base final wall shows its PNG; configured tolerance/minimum stays explicit.
9. [ ] Basma hf shows the friction PNG.
10. [ ] Basma hL shows correct D^4 MathText/text; wrong D^5 PNG is not shown.
11. [ ] Emme hf shows its PNG and hL uses the correct D^4 fallback.
12. [ ] ENPY PNG appears fully, with no clipped symbols or +1 m addition.
13. [ ] Transfer/other unmapped equations use MathText/text; valid mapped PNGs win.
14. [ ] Formula layout is readable, centered and responsive without giant blank cards.
15. [ ] Source summaries remain compact; complete provenance expands/collapses, including frozen history.
16. [ ] Library opens.
17. [ ] Grouped category navigation is clearer and complete.
18. [ ] Table, selection, no-match state and horizontal overflow are readable.
19. [ ] Detail/edit/provenance panels are readable; technical details remain accessible.
20. [ ] Filters, editing, draft retention and factory/reference protection behave unchanged.
21. [ ] No startup/callback traceback; legacy A/B notes clearly require source verification.
22. [ ] App closes normally.

Open items: corrected base-wall/local-loss PNGs, human visual acceptance, and a
later release rebuild only after acceptance. Watermark remains deliberately
unchanged; the user's later decision is a large fixed background or removal.
Overall status: **PENDING_MANUAL_ACCEPTANCE**. No further phase starts automatically.
