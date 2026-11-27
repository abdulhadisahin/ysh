"""Golden-value regression tests: calculation results must not drift unless a change is intended.

Regenerate the reference after an *intended* engineering change with:
    YSH_UPDATE_GOLDEN=1 python -m pytest tests/regression
and review the diff of golden_calculations.json before committing it.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import pytest

from .cases import run_all

GOLDEN = Path(__file__).with_name("golden_calculations.json")
REL_TOL = 1e-9


def _compare(actual, expected, path: str, problems: list[str]) -> None:
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            if key not in actual:
                problems.append(f"{path}.{key}: missing in result")
            elif key not in expected:
                problems.append(f"{path}.{key}: new field not in golden file")
            else:
                _compare(actual[key], expected[key], f"{path}.{key}", problems)
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            problems.append(f"{path}: length {len(actual)} != {len(expected)}")
            return
        for index, (a, e) in enumerate(zip(actual, expected)):
            _compare(a, e, f"{path}[{index}]", problems)
    elif isinstance(expected, float) or isinstance(actual, float):
        try:
            if not math.isclose(float(actual), float(expected), rel_tol=REL_TOL, abs_tol=1e-12):
                problems.append(f"{path}: {actual!r} != {expected!r}")
        except (TypeError, ValueError):
            problems.append(f"{path}: {actual!r} != {expected!r}")
    elif actual != expected:
        problems.append(f"{path}: {actual!r} != {expected!r}")


@pytest.fixture
def results(material_service, pipe_size_service, engineering_constant_service):
    return run_all(material_service, pipe_size_service, engineering_constant_service)


def test_golden_file_is_in_sync_or_updated(results):
    if os.environ.get("YSH_UPDATE_GOLDEN") == "1":
        GOLDEN.write_text(json.dumps(results, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        pytest.skip("golden file regenerated")
    assert GOLDEN.exists(), "golden_calculations.json is missing; run with YSH_UPDATE_GOLDEN=1"
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert set(golden) == set(results), f"scenario set changed: {sorted(set(golden) ^ set(results))}"


def test_every_scenario_matches_golden_values(results):
    if os.environ.get("YSH_UPDATE_GOLDEN") == "1":
        pytest.skip("golden file regenerated")
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    problems: list[str] = []
    for name in sorted(golden):
        _compare(results.get(name), golden[name], name, problems)
    assert not problems, "Calculation results drifted:\n" + "\n".join(problems[:40])


def test_scenarios_are_deterministic(material_service, pipe_size_service, engineering_constant_service):
    first = run_all(material_service, pipe_size_service, engineering_constant_service)
    second = run_all(material_service, pipe_size_service, engineering_constant_service)
    assert first == second
