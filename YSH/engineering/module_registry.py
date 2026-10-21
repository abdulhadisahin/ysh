"""Product applicability, deliberately independent of classification rules."""
from dataclasses import dataclass
from enum import StrEnum

from engineering.system_context import SystemContext


class ModuleCode(StrEnum):
    """Stable existing page identifiers."""
    PIPE_DESIGN = "pipe_design"
    TRANSFER_PUMP = "transfer_pump"
    DISCHARGE = "discharge_head_loss"
    SUCTION_NPSH = "suction_npsh"
    # Historical identities only; deliberately absent from live navigation MODULES.
    FIRE_FOAM_SYSTEM = "fire_foam_system"
    FIRE_HAZEN_WILLIAMS = "fire_hazen_williams"


@dataclass(frozen=True, slots=True)
class ModuleDefinition:
    """Metadata for existing navigation; no new icons or engineering criteria."""
    code: ModuleCode
    name_key: str
    display_order: int
    fuel_only: bool = False
    required_context: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ModuleAvailability:
    """Visibility is retained; unavailable modules expose a localized reason."""
    definition: ModuleDefinition
    enabled: bool
    reason_key: str | None = None


MODULES = (
    ModuleDefinition(ModuleCode.PIPE_DESIGN, "page.pipe.tab", 0),
    ModuleDefinition(ModuleCode.TRANSFER_PUMP, "page.transfer.tab", 1, True),
    ModuleDefinition(ModuleCode.DISCHARGE, "page.discharge.tab", 2),
    ModuleDefinition(ModuleCode.SUCTION_NPSH, "page.suction.tab", 3),
)


def module_availability(context: SystemContext, *, unavailable: bool = False) -> tuple[ModuleAvailability, ...]:
    """Undefined preserves legacy access; fuel-only is application scope, never TL."""
    result = []
    for module in sorted(MODULES, key=lambda item: item.display_order):
        restricted = module.fuel_only and context.system is not None and (
            context.system.code.upper() != "FUEL" or unavailable or not context.is_active)
        result.append(ModuleAvailability(module, not restricted,
                      "context.module.fuel_only" if restricted else None))
    return tuple(result)
