"""Separate design and empirical explanations; no regression is fitted here."""
from engineering.formula.common import step, used, variable
from engineering.formula.models import CalculationClassification, CheckStatus, FormulaCheck, FormulaStep, SelectionReason
from engineering.transfer_pump.v2_models import CapacityStatus, TransferPumpDesignResult, TransferPumpEmpiricalResult


def design_steps(result: TransferPumpDesignResult) -> tuple[FormulaStep, ...]:
    """Copy Phase 10 outputs and its explicit capacity adequacy outcome."""
    inp = result.input
    volume = variable("Vtransfer", inp.transfer_volume_m3, "m³", source=inp.volume_source,
                      key="transfer.design.volume")
    time = variable("tdef", inp.target_transfer_time_h, "h", source=inp.target_time_source,
                    key="transfer.design.target_time")
    check = FormulaCheck(status=CheckStatus.NOT_CONFIGURED, reason_key="formula2.no_pump")
    if inp.selected_pump_capacity_m3_h is not None:
        check = FormulaCheck(status=CheckStatus.PASS if result.status is CapacityStatus.ADEQUATE else CheckStatus.WARNING,
                             actual_value=inp.selected_pump_capacity_m3_h,
                             reference_value=result.required_flow_m3_h, operator=">=",
                             reason_key="formula2.capacity_check")
    steps = [step("transfer.required", "Qgerekli", result.required_flow_m3_h, "m³/h",
                  "Qgerekli = Vtransfer / tdef", (volume, time), 0, check=check,
                  used_values=(used("tdef", inp.target_transfer_time_h, "h", source=inp.target_time_source,
                                    key="transfer.design.target_time"),))]
    if result.transfer_time_h is not None:
        steps.append(step("transfer.time", "ttransfer", result.transfer_time_h, "h",
                          "ttransfer = Vtransfer / Qtulumba",
                          (volume, variable("Qtulumba", inp.selected_pump_capacity_m3_h, "m³/h",
                                            key="transfer.design.pump_capacity")), 1))
    return tuple(steps)


def empirical_steps(result: TransferPumpEmpiricalResult) -> tuple[FormulaStep, ...]:
    """Show the existing model, used reference vessels and its precomputed estimate."""
    estimate = result.estimate
    model = estimate.regression_model
    if model is None or estimate.predicted_pump_capacity_m3h is None:
        return ()
    volume = variable("Vfuel", result.resolution.volume_m3, "m³", key="field.fuel_capacity")
    options = dict(classification=CalculationClassification.EMPIRICAL_REFERENCE_ESTIMATE,
                   selection_reason=SelectionReason.REFERENCE_VESSEL_DATA,
                   sources=tuple(dict.fromkeys(row.source for row in result.references)))
    steps = [step("transfer.empirical", "Qpump", estimate.predicted_pump_capacity_m3h, "m³/h",
                  "Qpump = m × Vfuel + b", (volume,
                  variable("m", model.slope, key="formula.regression_slope"),
                  variable("b", model.intercept, "m³/h", key="formula.regression_intercept"),
                  variable("R²", model.r_squared, key="formula2.r_squared")), 0, **options)]
    from dataclasses import replace
    evidence = tuple(
        replace(variable(symbol, value, unit, source=row.source,
                         reason=SelectionReason.REFERENCE_VESSEL_DATA, key=key), context=row.ship_name)
        for row in result.references
        for symbol, value, unit, key in (
            ("Vfuel", row.fuel_capacity_m3, "m³", "field.fuel_capacity"),
            ("Qpump", row.pump_capacity_m3_h, "m³/h", "field.pump_capacity"))
    )
    steps[0] = replace(steps[0], reference_variables=evidence)
    if estimate.estimated_emptying_time_hours is not None:
        steps.append(step("transfer.empirical_time", "ttransfer", estimate.estimated_emptying_time_hours,
                          "h", "t = Vfuel / Qpump",
                          (volume, variable("Qpump", estimate.predicted_pump_capacity_m3h, "m³/h")), 1, **options))
    return tuple(steps)
