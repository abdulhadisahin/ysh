"""Project family stored exclusively in the existing navigation namespace."""
FAMILY_KEYS = {'fuel': 'project.family.fuel', 'fire': 'project.family.fire'}


def project_family(workspace: dict[str, object]) -> str:
    """Recover a stored stable family ID, otherwise use the legacy Fuel fallback."""
    navigation = workspace.get('navigation')
    if isinstance(navigation, dict):
        family = navigation.get('active_system_family')
        if isinstance(family, str) and family in FAMILY_KEYS:
            return family
    return 'fuel'


def family_navigation(family: str) -> dict[str, object]:
    if family not in FAMILY_KEYS:
        raise ValueError('Unknown project system family')
    return {'version': 1, 'active_system_family': family}
