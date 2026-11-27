"""Project-family scoping for the engineering library (presentation only; no data changes)."""
from __future__ import annotations

FLUID_GROUPS = {'fuel': frozenset({'DIESEL_FUEL', 'AVIATION_FUEL', 'HEAVY_FUEL'}),
                'fire': frozenset({'FRESH_WATER'}), 'seawater': frozenset({'SEA_WATER'})}
# Pipe materials/roughness, pipe standards, engineering rules, constants and sources stay
# visible for every family; only family-specific groups differ.
FAMILY_GROUPS = {
    'fuel': ('materials', 'fluids', 'pipes', 'engineering_rules', 'constants', 'pumps', 'sources', 'settings'),
    'seawater': ('materials', 'fluids', 'pipes', 'engineering_rules', 'constants', 'corrosion', 'sources', 'settings'),
    'fire': ('fire', 'materials', 'fluids', 'pipes', 'engineering_rules', 'constants', 'sources', 'settings'),
}
FLUID_CATEGORIES = frozenset({'fluids', 'fluid_properties', 'fluid_specifications'})


def scoped(family: str | None) -> bool:
    return family in FAMILY_GROUPS


def category_visible(family: str | None, category) -> bool:
    return not scoped(family) or category.group in FAMILY_GROUPS[family]


def visible_categories(family: str | None, categories) -> tuple:
    return tuple(c for c in categories if category_visible(family, c))


def allowed_fluid_ids(family: str | None, specifications) -> frozenset | None:
    """Fluids whose every recorded group belongs to the family (same rule as project fluids)."""
    if not scoped(family):
        return None
    allowed = FLUID_GROUPS[family]
    groups: dict = {}
    for spec in specifications:
        groups.setdefault(spec.fluid_id, set()).add(spec.fluid_group)
    return frozenset(i for i, g in groups.items() if g and g <= allowed)


def row_visible(family: str | None, category: str, row, fluid_ids) -> bool:
    if not scoped(family):
        return True
    if category in FLUID_CATEGORIES and fluid_ids is not None:
        identity = row.id if category == 'fluids' else getattr(row, 'fluid_id', None)
        return identity in fluid_ids
    if category == 'engineering_rules':
        group = getattr(row, 'fluid_group', '') or ''
        return getattr(row, 'system_family', '') in ('', family) and (not group or group in FLUID_GROUPS[family])
    return True


def material_relevant(family: str | None, *texts) -> bool:
    """Cu-Ni 90/10 pipe materials are offered only to seawater projects (presentation only)."""
    if family == 'seawater' or not scoped(family):
        return True
    from engineering.pipe_design.wall_standards import material_code
    joined = ' '.join(str(t or '') for t in texts)
    code = material_code(joined)
    return not ('CUNI' in code or 'CUPRONICKEL' in code)
