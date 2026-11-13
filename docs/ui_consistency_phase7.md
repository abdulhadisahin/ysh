# D243 V2 Final — Güncel kapsam notu

Güncel kabul: `D243-V2-FINAL` → `c9c8dfe8096a128302867d2ece630d9ebb3b5dd7`,
**2080 passed, 0 failed**, Windows paket **RELEASE_READY**.
[Güncel kullanıcı akışı](../README.md), [developer handoff](../YSH/docs/AI_HANDOVER.md)
ve [release kaydı](V2_FINAL_RELEASE.md) esas alınır.

Aşağıdaki Phase 7 metni tarihsel kayıttır. Sonraki kabul edilmiş UX geçişleri;
compact sayısal alanlar, sabit sidebar ikon/metin kolonları, tek ikincil araç
satırı, ortak kaynak durumları, dekoratif sağ üst gemi ve viewport filigranını
korur. Girdi alanları çevreden daha solid; boş sonuçlar geçirgen görünümlü,
hesaplanmış sonuçlar opaktır. Metinler/kontroller/uyarılar opak kalır.
Aşağıdaki eski stil adları, test sayısı ve bekleyen görsel kabul bu son durumu
iptal eden güncel talimatlar değildir.

---

# D243 V2 — Phase 7: Application-wide UX consistency and visual polish

Accepted base: `5db4217c64a3ee28ee5c45086fa504a33d783553`, **1970 passed**.
The starting worktree contains only the approved untracked reference workbook,
`docs/references/Yangın Söndürme.xlsx`. It is not production data and is neither
edited nor staged in this phase.

## Common hierarchy and presentation decisions

The common reading order is title/context, primary inputs, optional source/context,
calculation action, primary result, supporting values/status, and secondary tools.
Existing page layouts are retained where their engineering stages require it.
This pass reuses the current ttk theme and card helpers; it introduces no new UI,
Library, persistence or calculation architecture.

- Calculation page headings use the existing `PAGE_TITLE` token. Shared section
  headers wrap their title and description to their actual viewport instead of
  requesting an unnecessarily wide page. Shared result metrics wrap long labels
  and values without changing their backing variable, number formatting or unit.
- `CARD_PADDING = (MD, SM)` and `CONTROL_PADDING = (SM, XS)` express the existing
  master spacing. Actual InformationCard padding now agrees with its theme role;
  Fire cards and inputs use the same spacing. Borders remain one pixel and the
  existing native card shapes/rounded Fuel actions remain intact.
- Fire entries and readonly comboboxes explicitly opt into Fire-scoped field,
  focus and disabled styles. Fuel identities, Fire red, shell cyan, amber warnings
  and critical engineering colors remain distinct. No global recoloring is used.
- Calculate remains the primary action. Clear, Formula View and PDF remain
  secondary. Unstyled contextual ttk actions explicitly use the existing module
  secondary roles; Fire secondary actions use white surfaces with readable text.
  PipeSelection Update/Keep Current controls now follow the same
  contextual principle as Fire Library controls: hidden in manual/current states,
  visible when a linked source is stale/missing/changed. Existing disabled-state
  eligibility and explicit update/keep semantics remain authoritative.
- PipeSelection notices wrap to the card width; stale notices use the existing
  amber `StatusWarning` role. Fire empty/changed/calculated information uses an
  info role, invalid input an error role, and blocked/engineering/low-percent
  warnings retain amber. Source-required metadata remains compact and neutral.
- Fuel PDF captions are resource-backed in TR/EN and match the concise secondary
  action used by Fire/History. After a page edit, the entry is refreshed after
  existing result invalidation callbacks. Export is permitted only while the
  frozen snapshot's formula steps are still present in current displayed results.
  The click guard also checks this condition. No recalculation or Library lookup
  occurs. Frozen snapshots are retained; History can still export old records.
- Generated Fire Library UUIDs move from Formula View's normal reason prose to
  its existing collapsed technical details. The normal reason is localized and
  retains revision/context/service/applicability. Original FormulaSteps, selection
  reasons, arbitrary user explanations and persisted IDs remain unchanged.
- History source statuses are localized. Workflow version and record UUID belong
  to a collapsed record diagnostics disclosure, rather than ordinary context.
  The existing raw-evidence inspection remains available. Record values and
  provenance are displayed from frozen evidence, never current Library records.

## Module and shared surface review

| Surface | Retained hierarchy / module-specific exception |
| --- | --- |
| Pipe Design | Diameter and wall/bend stages remain separate; selected/required pipe results retain primary emphasis. Source context and staged actions are preserved. |
| Transfer | Design and empirical modes remain distinct. Required capacity is primary in design; transfer-time context and empirical chart/reference tools remain supporting. |
| Discharge | Hs remains primary, hhat/local/pipe losses supporting. Local-loss tables retain their own horizontal/vertical scroll behavior. |
| Suction / ENPY | Hydraulic-loss and ENPY actions remain separate engineering stages. ENPY is primary when available; no merged calculator is introduced. |
| Foam | Inputs precede source summaries and calculation. Vfoam is primary. Percent entry, canonical fraction and the single low-percent clarification are preserved. |
| Hazen-Williams | Delta-p HW is primary; CHW remains distinct from Darcy roughness. Service and PipeSelection controls retain explicit applicability. |
| Library | Existing master list/editor styling and Fire's Foam/HW grouping fit the same workspace. No new categories, editor fields, family selector or data rules are added. |
| Formula View | Existing step selector, aligned variable/value/unit tables, source disclosures and separate scroll window are retained; generated IDs are diagnostic only. |
| History | Shared filters/module identity/primary summary remain; Fire source labels now use the same localized language. Historical inspection never recalculates. |
| PDF entry | Secondary current-result action on calculation pages; frozen-record action in History. No renderer, report content or snapshot changes. |
| Shell | Full-height approximately 300px sidebar, large logo, cyan shell and red Fire selector are unchanged. No header branding or watermark is introduced. |

## Localization, scroll and acceptance policy

TR and EN controls are rendered and checked at **1100×700, 1280×800, 1440×900 and
1700×1000**. The accepted V1 LocalizationManager deliberately pins the product to
TR. EN acceptance directly selects its existing English translator catalogue in
the isolated test application; this does not change the production language
policy or persist an English preference.

Calculation checks include all six pages inside the real shell, control bounds,
readable viewport dimensions, active-tab wheel ownership, page bottom reachability
and the fixed sidebar. Shared-window checks cover Library editing, History and a
Formula View populated from a frozen record. Existing nested table/canvas wheel
routing is retained; no scroll architecture is replaced.

The tests use isolated databases and synthetic sources only. Focused contracts
also cover warning roles, readonly controls, exact metric values/units, PDF stale
eligibility including partial engineering stages, explicit Update/Keep Current,
localized historical source states and diagnostic-only generated IDs.

Nozzle and seawater Hazen-Williams remain **BLOCKED / SOURCE_REQUIRED**. All Pipe,
Transfer, Discharge, Suction/ENPY, Foam and HW equations, parsing, margins/defaults,
DB schema, Library rules, snapshot semantics, History logic and PDF generation
remain unchanged. User Guide and Developer Guide are not regenerated.

No repeated screenshots or startup benchmarks are performed. Automated geometry
does not substitute for human visual judgement: **USER REVIEW REQUIRED**.
Remaining visual acceptance consists of reviewing the actual application;
no new engineering feature or release packaging is started automatically.

## Validation

Final full regression on the final Phase 7 code: **1996 passed, 0 failed in
314.49 seconds (0:05:14)**. The accepted 1970 tests and 26 new consistency cases
pass. The finalization run completed on 2026-11-04 using only `.venv314` Python.
Its complete output was retained outside the repository for audit.

Focused validation: 26 Phase 7 cases passed (158.02s); the final shared-style/PDF
checks passed 14 cases (10.89s), and the narrow/wide metric unit-proximity check
passed (10.38s). Existing related Formula/History/visual checks also passed.

No new UX/code edits were made during finalization. The workbook SHA256 remains
`bd9aa871454c184afdb45e14bd0c008818d49701d5cc92e1de7ca89126159474`;
the workbook remains an **approved untracked reference input** and is excluded
from the commit. Startup was not benchmarked during finalization.

Manual visual acceptance: **USER REVIEW REQUIRED**.
Overall result: **PHASE7_PASS_WITH_USER_REVIEW**.
