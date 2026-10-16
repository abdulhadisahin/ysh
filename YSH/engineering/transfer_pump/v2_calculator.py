"""Real transfer sizing: explicit volume/time, with no reference-data dependency."""
from engineering.provenance import EngineeringValue, OverridePolicy, SourceReference, SourceType
from engineering.transfer_pump.v2_models import (
    CapacityStatus, TransferPumpDesignInput, TransferPumpDesignResult, positive,
)


def calculate_design(value: TransferPumpDesignInput) -> TransferPumpDesignResult:
    """Calculate Qgerekli and optional selected-pump time without margins/tolerances."""
    required = value.transfer_volume_m3 / value.target_transfer_time_h
    positive(required, 'transfer.design.required_flow')
    selected = value.selected_pump_capacity_m3_h
    time = None
    status = CapacityStatus.NO_SELECTED_PUMP
    if selected is not None:
        time = value.transfer_volume_m3 / selected
        positive(time, 'transfer.design.transfer_time')
        status = (CapacityStatus.ADEQUATE if selected >= required
                  else CapacityStatus.PUMP_CAPACITY_BELOW_REQUIRED)
    result = EngineeringValue(
        used_value=required, unit='m³/h', symbol='Qgerekli',
        source=SourceReference(source_type=SourceType.CALCULATED,
                               formula='Qgerekli = Vtransfer / tdef'),
        override_policy=OverridePolicy.LOCKED, recommended_value=required,
    )
    return TransferPumpDesignResult(input=value, required_capacity=result,
                                    transfer_time_h=time, status=status)
