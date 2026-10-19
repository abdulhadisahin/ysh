# Formula asset audit — Phase A

Checkpoint: d243-v2-handoff, 2da178d542e503d1e965541137ddba92a9f08323, clean.
Python 3.14.8, required .venv314 interpreter only. Baseline: 1379 passed,
one cache permission warning, 44.16 s. Phase A focused coverage: 142 passed.

## Inventory and actual resolution

All eight files are real RGBA PNGs. The `.png.png` suffix is their actual source
filename, not a packaging/resolver transformation. FORMULA_ASSET_FILENAMES holds
complete names; formula_asset_path joins resources/formulas without appending an
extension. There is no lookup failure from the double suffix. No files renamed.
The Phase 17 ZIP contains all eight files with exact source hashes; the spec
still includes the entire resources directory. **No release rebuild is performed
in this corrective task until its UI is accepted.**

| Exact source path / filename | Pixels | Bytes | Production reference | Phase 17 package |
|---|---|---:|---|---|
| `C:\Users\Özberk\Documents\ysh\YSH\resources\formulas\formula_boru_capi.png.png` | 1448×1086 | 388397 | Yes / dynamic | Yes, exact hash |
| `C:\Users\Özberk\Documents\ysh\YSH\resources\formulas\formula_boru_surtunme_kaybi.png.png` | 1448×1086 | 353664 | Yes / dynamic | Yes, exact hash |
| `C:\Users\Özberk\Documents\ysh\YSH\resources\formulas\formula_bukum_ilavesi.png.png` | 1448×1086 | 297266 | Yes / dynamic | Yes, exact hash |
| `C:\Users\Özberk\Documents\ysh\YSH\resources\formulas\formula_enpy.png.png` | 1448×1086 | 240517 | Yes / dynamic | Yes, exact hash |
| `C:\Users\Özberk\Documents\ysh\YSH\resources\formulas\formula_lokal_kayip.png.png` | 1448×1086 | 382526 | Yes / dynamic | Yes, exact hash |
| `C:\Users\Özberk\Documents\ysh\YSH\resources\formulas\formula_musaade_edilebilir_gerilme.png.png` | 1448×1086 | 369034 | Yes / dynamic | Yes, exact hash |
| `C:\Users\Özberk\Documents\ysh\YSH\resources\formulas\formula_temel_et_kalinligi.png.png` | 1448×1086 | 277024 | Yes / dynamic | Yes, exact hash |
| `C:\Users\Özberk\Documents\ysh\YSH\resources\formulas\formula_toplam_et_kalinligi.png.png` | 1448×1086 | 265949 | Yes / dynamic | Yes, exact hash |

Before: FormulaStep → step_sections → FormulaSection without asset_names →
existing PNG renderer sees an empty list → MathText/text. Legacy asset keys
existed but were not carried by the new renderer. PNG-first already existed in
the shared fallback chain; the FormulaStep bridge was missing.

After: stored FormulaStep stable step_id → ui/formula_asset_policy.py → audited
asset key → FormulaSection.asset_names → ui/assets.py resolver → PNG-first →
MathText → native text. This is display-only: no FormulaStep/schema mutation,
no live Library query and no recalculation. Frozen steps use the same mapping.

| Stable step id | Dedicated key | Display policy |
|---|---|---|
| pipe.D | pipe_diameter | PNG first for the matching equation |
| pipe.stress | allowable_stress | PNG for Rp0.2/B; configured stress stays text |
| pipe.s0 | base_wall_thickness | Quarantined wrong artwork; MathText/text |
| pipe.b | bend_allowance | Active bend only; no-bend explicitly remains b=0 |
| pipe.wall | required_wall_thickness | Base sum PNG; configured tolerance/minimum stays full stored expression |
| discharge.hf / suction.hf | pipe_friction_loss | PNG first |
| discharge.hL / suction.hL | local_loss | Quarantined wrong artwork; MathText/text |
| suction.ENPYm | available_enpy | PNG first |

Transfer, Re, friction-factor regimes, actual geometry/velocity, margins and
configured rules have no dedicated matching PNG; existing MathText/text remains.
Matching equation guards prevent applying an old picture to a different frozen
formula with the same ID.

## Visual inspection findings — reported before replacement

Every original image was opened and inspected. Diameter, Rp0.2/B allowable
stress, active-bend 0.4(da/R)s0, base total-wall sum, friction D^5 and ENPY match
their intended base relationships (artwork uses some legacy symbol labels).
Transparent surrounding whitespace is substantial; the original 260 px max-side
makes equations small. ENPY's right margin is particularly tight; any display
fit must preserve the complete alpha silhouette rather than crop the equation.

Two original pictures are mathematically unsuitable:

- `formula_temel_et_kalinligi.png.png`: denominator is drawn as
  `20 σmüs · (v + pc)`. Accepted formula is `(20 σallow · v) + pc`.
- `formula_lokal_kayip.png.png`: denominator is `D^5`. Accepted local loss is
  `Di^4`; only pipe friction uses the fifth power.

The mismatch was reported to the user before any replacement. Neither image was
edited/replaced, and neither engineering equation was changed. Their files stay
resolvable/packaged for audit, but a common quarantine prevents showing them in
live, legacy or historical Formula View. Correct stored MathText/text is the safe
fallback. **Replacement of these two prepared PNGs remains open.**

No active bend picture is used for no-bend or an unspecified precomputed bend.
The simple total-wall picture never replaces configured tolerance/minimum rules.
