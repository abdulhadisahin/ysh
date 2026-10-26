"""Versioned project navigation; independent of engineering system context."""
from dataclasses import dataclass, field

FAMILIES = {'fuel': 'navigation.fuel', 'fire': 'fire.system'}
MODULES = {
    'fuel': ('pipe_design', 'transfer_pump', 'discharge_head_loss', 'suction_npsh'),
    'fire': ('foam', 'hw'),
}


@dataclass
class WorkspaceNavigation:
    active_system_family: str = 'fuel'
    last_active_module_by_family: dict[str, str] = field(
        default_factory=lambda: {family: modules[0] for family, modules in MODULES.items()})

    def to_payload(self):
        return {'version': 1, 'active_system_family': self.active_system_family,
                'last_active_module_by_family': dict(self.last_active_module_by_family)}

    @classmethod
    def from_workspace(cls, workspace):
        """Missing/unknown navigation preferences safely use deterministic defaults."""
        result = cls()
        raw = workspace.get('navigation', {})
        if not isinstance(raw, dict) or raw.get('version') != 1:
            return result
        family = raw.get('active_system_family')
        if isinstance(family, str) and family in FAMILIES:
            result.active_system_family = family
        modules = raw.get('last_active_module_by_family', {})
        if isinstance(modules, dict):
            for family, allowed in MODULES.items():
                if modules.get(family) in allowed:
                    result.last_active_module_by_family[family] = modules[family]
        return result
