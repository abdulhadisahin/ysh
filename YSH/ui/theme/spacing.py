"""Shared spacing tokens that avoid page-specific visual magic numbers."""

XS = 4
SM = 8
MD = 12
LG = 16
XL = 24

CARD_PADDING = (MD, SM)
CONTROL_PADDING = (SM, XS)

# Character width for numerical engineering inputs; free text stays independent.
NUMERIC_INPUT_WIDTH = 12

# Medium source selectors stay independent of free-text/applicability fields.
SOURCE_FIELD_WIDTH = 28
PANEL_TRANSMISSION_FACTOR = 1.20
