"""Read-only project warning projections; no calculators, repositories or widgets."""
from dataclasses import dataclass
from enum import StrEnum


class WarningStatus(StrEnum):
    INFO = 'INFO'
    WARNING = 'WARNING'
    SOURCE_REQUIRED = 'SOURCE_REQUIRED'
    STALE = 'STALE'
    ERROR = 'ERROR'
    BLOCKED = 'BLOCKED'
    OUT_OF_RANGE = 'OUT_OF_RANGE'
    CRITICAL = 'CRITICAL'


FAMILY_MODULES = {
    'fuel': ('pipe_design', 'transfer_pump', 'discharge_head_loss', 'suction_npsh'),
    'fire': ('foam', 'hw'),
    'seawater': ('pipe_design', 'discharge_head_loss', 'suction_npsh'),
}


@dataclass(frozen=True)
class EngineeringWarning:
    module_id: str
    severity: WarningStatus
    code: str
    message_key: str = ''
    detail: str = ''
    source: str = ''


@dataclass(frozen=True)
class ModuleWarningState:
    module_id: str
    items: tuple[EngineeringWarning, ...] = ()
    completed_count: int = 0


@dataclass(frozen=True)
class EngineeringWarningSummary:
    items: tuple[EngineeringWarning, ...] = ()
    completed_count: int = 0

    def count(self, status):
        return sum(item.severity == status for item in self.items)

    @property
    def info_count(self): return self.count(WarningStatus.INFO)
    @property
    def warning_count(self): return self.count(WarningStatus.WARNING)
    @property
    def stale_count(self): return self.count(WarningStatus.STALE)
    @property
    def source_required_count(self): return self.count(WarningStatus.SOURCE_REQUIRED)
    @property
    def error_count(self):
        return sum(self.count(status) for status in (WarningStatus.ERROR,WarningStatus.BLOCKED,WarningStatus.OUT_OF_RANGE,WarningStatus.CRITICAL))


def aggregate_warnings(family, states):
    """Filter twice by stable family/module IDs and deduplicate current messages."""
    allowed = FAMILY_MODULES.get(family, ())
    unique = {}
    completed = {}
    for state in states:
        if state.module_id not in allowed:
            continue
        completed[state.module_id] = state.completed_count
        for item in state.items:
            if item.module_id == state.module_id:
                unique.setdefault((item.module_id, item.code, item.severity), item)
    return EngineeringWarningSummary(tuple(unique.values()), sum(completed.values()))
