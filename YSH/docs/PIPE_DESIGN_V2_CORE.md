# D243 V2 Pipe Design engineering core (Phase 6)

## Entry points and compatibility

`PipeDesignService.calculate()` and the existing calculator APIs keep their
legacy behavior and serialized result shape. Their UI, DN recommendation,
warnings and constants are unchanged. `wall_from_stress()` holds the same
pressure/bend/additive arithmetic, with exactly the old operation order.

Opt in with `PipeDesignService.calculate_v2(PipeDesignV2Input(...))`, or invoke
`PipeDesignV2Calculator.calculate(request, real_candidates)` without storage.
The service reads only the selected standard's actual library rows. Optional
preloaded Phase 4 `PipeSizeMetadata` and `SourceReference` maps carry NPS/Schedule
and source facts, without N+1 metadata queries. Metadata percent fields alone do
not configure a tolerance formula. No schema, repository, seed or persistence
contract changes are needed. New V2 results are not saved into legacy snapshots.

## Selection and actual dimensions

Theoretical D still uses the original calculator and m³/h / 3600 conversion.
Initial candidate selection minimizes actual ID >= D, then OD, wall, nominal
label, NPS, Schedule and stable row UUID. Input iteration order cannot change an
equivalent choice. Standard UUID is mandatory; an optional standard code also
limits initial selection. Inactive standards produce no configured candidate.

Stored ID is authoritative. Only missing ID is derived as nominal OD - 2s.
Nominal dimensions are never silently replaced by tolerance-reduced dimensions.
After pressure-wall evaluation, final wall selection minimizes available wall
>= final requirement within the initial standard UUID/code, DN/NPS and OD context.
Ties use actual ID, Schedule and row UUID. It also requires final actual ID >= D,
so a thicker wall cannot silently invalidate the original flow-sizing constraint.
There is no automatic nominal-size escalation. No match returns
`NO_STANDARD_WALL_MATCH`; it does not round thickness or invent geometry.

Final actual velocity is 4(Q/3600)/(pi*(actual_ID/1000)^2), with a separate
`velocity_within_design` result. The candidate and the final selected row are
separate: final actual dimensions/velocity remain None if no final wall matches.
Dimension-standard source, material-standard source and engineering-rule source
are distinct fields and are never substituted for one another.

## Rule configuration and source gates

`AllowableStressRule` supports:

- LEGACY_RP02: original Rp0.2/B, explicitly described as unverified legacy
  compatibility, never relabelled as a verified current TL rule.
- FACTOR_BASED_STEEL_RULE: minimum of caller-configured applicable strength/factor
  terms only. No A/B factors or applicable-term list are supplied by production.
- DIRECT_TABLE_RULE: exact configured temperature row only; no interpolation,
  extrapolation, default temperature or fallback to steel. No CuNi rows are shipped.
- USER_PROVIDED_RULE: an explicitly supplied allowable stress, identified as user
  input unless the caller provides provenance. It is not an automatic TL rule.

Configured steel/table rules, tolerance formulas and minimum-wall values require
an explicitly VERIFIED SourceReference with a nonempty document reference.
This gate consumes caller-supplied verification facts; it does not independently
verify documents or mark existing library records verified. No such production
rule data is added in Phase 6. Test fixtures are clearly synthetic, not standards.

Manufacturing tolerance is an injectable, typed allowance formula plus explicit
negative percentage (0 <= a < 100) and source. There is **no built-in active**
formula or EN/ASME tolerance value. Tests alone demonstrate the proposed
`a/(100-a)*s0` relationship using a synthetic configured rule. Missing formula or
percentage returns RULE_NOT_CONFIGURED; unverified supplied content returns
SOURCE_REQUIRED without invoking the formula.

Minimum wall is an explicitly configured applicable-context value and source;
there is no TL lookup table or universal minimum. Missing values remain None.
Design temperature is optional domain context and is never defaulted to 20°C.
The caller must choose applicable material/temperature/pipe rules explicitly.

## Wall breakdown and incomplete results

Results expose s0, b, used c, optional t, calculated wall, optional minimum,
final required wall and a real selected standard wall. Calculated wall retains
legacy s0+c+b and adds t only when available. Final wall is max(calculated,
configured minimum); without a minimum it temporarily equals calculated wall.

Missing tolerance/minimum rules remain visible as RuleValue(None, status, detail).
Geometry may still be returned for provisional legacy-compatible sizing, but the
overall status is RULE_NOT_CONFIGURED or SOURCE_REQUIRED, never a complete-rule
SUCCESS. A missing allowable-stress rule prevents wall calculation entirely.
SUCCESS means the configured selection path completed, **not** TL certification;
the actual source/verification status remains available, including legacy stress.

Phase 2 EngineeringValue wrappers retain supplied recommendations, used values,
override state and reason. Raw request velocity/v/c are explicit caller inputs;
callers with library/recommended provenance should supply their original wrappers.
Scalar/unit/symbol mismatches are validation failures. Automatically calculated
stress/t/minimum wrappers preserve governing source references; other results stay
numeric. No existing record is assigned fabricated verification metadata.

`fuel_velocity_criterion()` exposes the user-approved 7 m/s D243 project maximum
as D243_CRITERION, not TL. It does not replace existing line-role warning ranges,
change the requested design velocity, or add blocking behavior.

## Source-verification blockers and deferred integration

BLOCKED_SOURCE_VERIFICATION (no production activation):

- current TL steel applicable terms and A/B factors;
- CuNi temperature-dependent allowable stress tables;
- product-standard manufacturing-tolerance percentages and applicable formula;
- TL minimum-wall tables and applicability conditions.

Legacy pressure, bend and corrosion behavior remains available without asserting
new TL verification. No new welded-pipe or corrosion factors are introduced.
Future work must connect verified records, rule applicability and design-temperature
UI inputs. System Definition, final Pipe Design UI, Formula View 2.0, warning
integration of final velocity and PipeSelection persistence remain deferred.
