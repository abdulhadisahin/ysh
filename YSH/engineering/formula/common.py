"""Small adapters for values already supplied by result models."""
from engineering.formula.models import FormulaStep, FormulaVariable, SelectionReason
from engineering.provenance import EngineeringValue, OverridePolicy, SourceReference, SourceType


def reason_for(source: SourceReference) -> SelectionReason:
    """Map only known origins; other explicit configurations remain configured."""
    return SelectionReason.__members__.get(source.source_type.value, SelectionReason.CONFIGURED)


def variable(symbol: str, value: float, unit: str = "", *,
             source: SourceReference | None = None,
             reason: SelectionReason | None = None,
             key: str | None = None) -> FormulaVariable:
    """Wrap a raw number without conversion or computation."""
    return FormulaVariable(symbol=symbol, value=value, unit=unit,
                           terminology_key=key or f"engineering.{symbol}",
                           source=source, reason=reason)


def used(symbol: str, value: float, unit: str = "", *,
         source: SourceReference | None = None, key: str | None = None) -> EngineeringValue:
    """Reuse Phase 2 for directly configured values, without inventing defaults."""
    return EngineeringValue(used_value=value, unit=unit, symbol=symbol,
                            terminology_key=key or f"engineering.{symbol}",
                            source=source or SourceReference(source_type=SourceType.USER_INPUT),
                            override_policy=OverridePolicy.USER_INPUT)


def step(step_id: str, symbol: str, value: float, unit: str, formula: str,
         variables: tuple[FormulaVariable, ...], order: int, **kwargs: object) -> FormulaStep:
    """Create an explanation whose substitution binds symbols to supplied values."""
    return FormulaStep(step_id=step_id, title_key=f"engineering.{symbol}",
                       formula_text=formula, variables=variables,
                       result_value=value, result_unit=unit, result_symbol=symbol,
                       display_order=order, **kwargs)
