"""Regression tests for approved pipe-design formulas."""
from __future__ import annotations
from pytest import approx
import math
from core.pipe_size import PipeSize
from engineering.pipe_design.calculator import PipeDesignCalculator
from engineering.pipe_design.models import PipeDiameterInput, WallThicknessInput
def test_diameter_formula_uses_m3h_to_si_conversion() -> None:
    """Diameter is calculated with cubic metres per second internally."""
    result=PipeDesignCalculator().calculate_diameter(PipeDiameterInput(3600,1))
    assert result.diameter_m==approx((4/3.141592653589793)**.5)
    assert result.diameter_mm==approx(result.diameter_m*1000)
def test_dn_recommendation_selects_first_suitable_size() -> None:
    """The approved first-suitable distinct-DN recommendation is applied."""
    calculator=PipeDesignCalculator();result=calculator.calculate_diameter(PipeDiameterInput(10,2));sizes=[PipeSize("DN50",60,3,54),PipeSize("DN100",114,3,108),PipeSize("DN80",89,3,83)]
    result=calculator.recommend_dn(result,sizes);assert result.minimum_matching_dn=="DN50";assert result.recommended_dn=="DN50"


def test_dn_recommendation_groups_multiple_wall_rows_by_nominal_dn() -> None:
    """Multiple EN 10220 walls cannot be mistaken for successive DN sizes."""
    calculator = PipeDesignCalculator()
    result = calculator.calculate_diameter(PipeDiameterInput(10, 2))
    sizes = [
        PipeSize("DN50", 60.3, 2.9, 54.5, "EN 10220"),
        PipeSize("DN50", 60.3, 5.6, 49.1, "EN 10220"),
        PipeSize("DN80", 88.9, 3.2, 82.5, "EN 10220"),
        PipeSize("DN80", 88.9, 7.1, 74.7, "EN 10220"),
        PipeSize("DN100", 114.3, 3.6, 107.1, "EN 10220"),
    ]
    result = calculator.recommend_dn(result, sizes)
    assert result.minimum_matching_dn == "DN50"
    assert result.recommended_dn == "DN50"
    assert result.recommended_wall_thickness_mm == 2.9


def test_dn_recommendation_uses_first_suitable_dn_for_reference_flow() -> None:
    """The approved 680 m³/h, 5 m/s case selects DN250, not DN300."""
    calculator = PipeDesignCalculator()
    result = calculator.calculate_diameter(PipeDiameterInput(680, 5))
    sizes = [
        PipeSize("DN200", 219.1, 5.0, 209.1, "EN 10220"),
        PipeSize("DN200", 219.1, 12.5, 194.1, "EN 10220"),
        PipeSize("DN250", 273.0, 5.6, 261.8, "EN 10220"),
        PipeSize("DN250", 273.0, 14.2, 244.6, "EN 10220"),
        PipeSize("DN300", 323.9, 5.6, 312.7, "EN 10220"),
    ]
    result = calculator.recommend_dn(result, sizes)
    assert result.diameter_mm == approx(219.3, abs=0.1)
    assert result.recommended_dn == "DN250"
    assert result.recommended_dn != "DN300"


def test_dn_recommendation_does_not_clamp_beyond_the_largest_nominal_size() -> None:
    """Oversized calculated diameters retain their value without a false DN."""
    calculator = PipeDesignCalculator()
    result = calculator.calculate_diameter(PipeDiameterInput(360000, 1))
    result = calculator.recommend_dn(
        result, [PipeSize("DN500", 508.0, 6.3, 495.4, "EN 10220")]
    )
    assert result.diameter_mm > 495.4
    assert result.recommended_dn is None
    assert result.warnings == ["no_suitable_dn"]


def test_empty_pipe_size_library_returns_a_semantic_warning_code() -> None:
    """An empty library does not leak rendered UI text from engineering code."""
    calculator = PipeDesignCalculator()
    result = calculator.recommend_dn(
        calculator.calculate_diameter(PipeDiameterInput(100, 2)), []
    )

    assert result.recommended_dn is None
    assert result.warnings == ["pipe_size_library_empty"]
def test_wall_formula_with_bend_allowance() -> None:
    """Wall output follows each approved formula term."""
    result=PipeDesignCalculator().calculate_wall_thickness(WallThicknessInput(100,16,200,2,1,1,True,300))
    assert result.allowable_stress_mpa==approx(100);assert result.base_wall_thickness_mm==approx(1600/((20*100*1)+16));assert result.final_wall_thickness_mm==approx(result.base_wall_thickness_mm+1+result.bend_allowance_mm)

def test_reference_diameter_case() -> None:
    """The specified 100 m³/h, 2 m/s reference result is exact to tolerance."""
    result = PipeDesignCalculator().calculate_diameter(PipeDiameterInput(100, 2))
    expected_m = math.sqrt((4 * (100 / 3600)) / (2 * math.pi))
    assert result.diameter_m == approx(expected_m)
    assert result.diameter_mm == approx(expected_m * 1000)

def test_reference_wall_case_without_bend() -> None:
    """The approved 195 MPa reference wall calculation retains precision."""
    result = PipeDesignCalculator().calculate_wall_thickness(
        WallThicknessInput(100, 16, 195, 1.8, 1, 1)
    )
    stress = 195 / 1.8
    base = (100 * 16) / ((20 * stress * 1) + 16)
    assert result.allowable_stress_mpa == approx(stress)
    assert result.base_wall_thickness_mm == approx(base)
    assert result.final_wall_thickness_mm == approx(base + 1)

def test_reference_wall_case_with_bend() -> None:
    """The approved bend allowance adds only the calculated bend term."""
    result = PipeDesignCalculator().calculate_wall_thickness(
        WallThicknessInput(100, 16, 195, 1.8, 1, 1, True, 300)
    )
    base = (100 * 16) / ((20 * (195 / 1.8) * 1) + 16)
    bend = 0.4 * (100 / 300) * base
    assert result.bend_allowance_mm == approx(bend)
    assert result.final_wall_thickness_mm == approx(base + 1 + bend)
