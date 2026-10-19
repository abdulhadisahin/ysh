"""Display-only binding of stable FormulaStep identities to audited artwork."""
from __future__ import annotations

from engineering.formula.models import FormulaStep


STEP_ASSET_KEYS = {
    "pipe.D": "pipe_diameter",
    "pipe.stress": "allowable_stress",
    "pipe.s0": "base_wall_thickness",
    "pipe.b": "bend_allowance",
    "pipe.wall": "required_wall_thickness",
    "discharge.hf": "pipe_friction_loss",
    "suction.hf": "pipe_friction_loss",
    "discharge.hL": "local_loss",
    "suction.hL": "local_loss",
    "suction.ENPYm": "available_enpy",
}

# Keep original files and resolver paths intact. These pictures do not express
# the accepted equations and must not be used by live, legacy or frozen views.
QUARANTINED_ASSETS = {
    "base_wall_thickness": "20σ(v+pc) in PNG differs from 20σv+pc",
    "local_loss": "PNG denominator D^5 differs from accepted D^4",
}

_EXPECTED_TEXT = {
    "pipe.D": "D = √((4 × Qm³/s) / (π × V))",
    "pipe.stress": "σallow = Rp0.2 / B",
    "pipe.b": "b = 0.4 × (da / R) × s0",
    "discharge.hf": "hf = 6.4 × 10⁶ × f × L × Q² / Di⁵",
    "suction.hf": "hf = 6.4 × 10⁶ × f × L × Q² / Di⁵",
    "suction.ENPYm": "ENPYm = PE/(ρg) − Pb/(ρg) − HEgeo − he",
}


def step_asset_names(step: FormulaStep) -> tuple[str, ...]:
    """Return only artwork that describes this stored step, without live lookups."""
    key = STEP_ASSET_KEYS.get(step.step_id)
    if key is None or key in QUARANTINED_ASSETS:
        return ()
    expected = _EXPECTED_TEXT.get(step.step_id)
    if expected is not None and step.formula_text != expected:
        return ()
    if step.step_id == "pipe.wall":
        if step.formula_text not in ("s = s0 + c + b", "formula2.required_wall"):
            return ()
        if any(v.symbol in ("tolerance", "minimum") for v in step.variables):
            return ()
    return (key,)
