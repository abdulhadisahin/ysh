"""Verified local EN 10220 DN10–DN500 pipe-size reference dataset."""

from __future__ import annotations

from collections.abc import Iterator


EN_10220_STANDARD_CODE = "EN_10220"
EN_10220_STANDARD = "EN 10220"
EN_10220_DESCRIPTION = (
    "EN 10220 DN10–DN500 — Seamless and welded steel tubes – "
    "Dimensions and masses per unit length."
)

# The supplied dataset is deliberately local and contains no runtime network use.
_DIMENSIONS: tuple[tuple[str, float, tuple[float, ...]], ...] = (
    ("DN10", 17.2, (2.0, 2.3, 2.6, 2.9)),
    ("DN15", 21.3, (2.0, 2.3, 2.6, 2.9, 3.2)),
    ("DN20", 26.9, (2.0, 2.3, 2.6, 2.9, 3.2, 3.6)),
    ("DN25", 33.7, (2.6, 2.9, 3.2, 3.6, 4.0)),
    ("DN32", 42.4, (2.6, 2.9, 3.2, 3.6, 4.0, 4.5)),
    ("DN40", 48.3, (2.6, 2.9, 3.2, 3.6, 4.0, 4.5, 5.0)),
    ("DN50", 60.3, (2.9, 3.2, 3.6, 4.0, 4.5, 5.0, 5.6)),
    ("DN65", 76.1, (2.9, 3.2, 3.6, 4.0, 4.5, 5.0, 5.6, 6.3)),
    ("DN80", 88.9, (3.2, 3.6, 4.0, 4.5, 5.0, 5.6, 6.3, 7.1)),
    ("DN100", 114.3, (3.6, 4.0, 4.5, 5.0, 5.6, 6.3, 7.1, 8.0, 8.8)),
    ("DN125", 139.7, (4.0, 4.5, 5.0, 5.6, 6.3, 7.1, 8.0, 8.8, 10.0)),
    ("DN150", 168.3, (4.5, 5.0, 5.6, 6.3, 7.1, 8.0, 8.8, 10.0, 11.0)),
    ("DN200", 219.1, (5.0, 5.6, 6.3, 7.1, 8.0, 8.8, 10.0, 11.0, 12.5)),
    ("DN250", 273.0, (5.6, 6.3, 7.1, 8.0, 8.8, 10.0, 11.0, 12.5, 14.2)),
    ("DN300", 323.9, (5.6, 6.3, 7.1, 8.0, 8.8, 10.0, 11.0, 12.5, 14.2, 16.0)),
    ("DN350", 355.6, (5.6, 6.3, 7.1, 8.0, 8.8, 10.0, 11.0, 12.5, 14.2, 16.0)),
    ("DN400", 406.4, (6.3, 7.1, 8.0, 8.8, 10.0, 11.0, 12.5, 14.2, 16.0)),
    ("DN450", 457.0, (6.3, 7.1, 8.0, 8.8, 10.0, 11.0, 12.5, 14.2, 16.0)),
    ("DN500", 508.0, (6.3, 7.1, 8.0, 8.8, 10.0, 11.0, 12.5, 14.2, 16.0)),
)


def iter_en_10220_pipe_sizes() -> Iterator[tuple[str, float, float, float]]:
    """Yield supplied DN, OD, wall-thickness, and derived-ID values in order."""
    for nominal_diameter, outside_diameter_mm, wall_thicknesses in _DIMENSIONS:
        for wall_thickness_mm in wall_thicknesses:
            yield (
                nominal_diameter,
                outside_diameter_mm,
                wall_thickness_mm,
                outside_diameter_mm - (2 * wall_thickness_mm),
            )
