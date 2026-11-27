"""Pages and frozen snapshots must obtain formula steps from the same shared functions.

Two independent step builders caused the Word-button gating bugs (the page and the snapshot disagreed
about a decoration, so the 'current result' check failed). Keeping a single source prevents a repeat.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    "ui/pages/discharge_head_loss_page.py": ("discharge_formula_steps",),
    "ui/pages/suction_npsh_page.py": ("suction_formula_steps",),
    "ui/pages/transfer_pump_page.py": ("transfer_formula_steps",),
    "ui/pages/pipe_design_page.py": ("apply_selection_geometry", "pipe_material_source_steps"),
}
FORBIDDEN_IN_PAGES = ("hydraulic_steps(", "suction_steps(", "design_steps(", "empirical_steps(", "selection_geometry_steps(")


def test_pages_use_the_shared_snapshot_step_functions() -> None:
    for page, required in PAGES.items():
        source = (ROOT / page).read_text(encoding="utf-8")
        for name in required:
            assert name in source, f"{page} must call {name}"
        for name in FORBIDDEN_IN_PAGES:
            assert name not in source, f"{page} builds steps itself via {name}; use engineering.snapshots.builders"


def test_snapshot_builders_use_the_same_functions() -> None:
    source = (ROOT / "engineering/snapshots/builders.py").read_text(encoding="utf-8")
    for name in ("discharge_formula_steps(result)", "suction_formula_steps(result)", "transfer_formula_steps(result)",
                 "apply_selection_geometry(steps,selection)"):
        assert name in source
