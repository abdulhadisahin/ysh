"""Emme owns its applied input while sharing discovery with Basma."""
from engineering.pipe_design.transfer import PipeTransferProjectState
from services.discharge_workflow import DischargeWorkflow
from services.pipe_source_discovery import PipeSourceDiscovery


class SuctionWorkflow(DischargeWorkflow):
    """Reuse explicit Phase 7 decisions for the independent suction owner."""

    def __init__(self, state: PipeTransferProjectState | None = None, *,
                 discovery: PipeSourceDiscovery | None = None) -> None:
        """Start manual or restore the project's exact applied suction snapshot."""
        super().__init__(state, module="suction", discovery=discovery)
