"""Central semantic tokens for the D243 naval engineering interface.

The values here deliberately describe roles rather than pages.  Calculation
screens can retain a small module accent, while the shell, typography and
primary actions all speak the same restrained navy / white / gold language.
"""

NAVY = "#102B46"
DEEP_NAVY = "#091B2D"
NAVY_TEXT = "#152B3F"
WHITE = "#FFFFFF"
# Gold is an accent and action cue, never a severity signal.
GOLD = "#B58A2A"
GOLD_DARK = "#7B5A17"
GOLD_SOFT = "#FBF6E9"
GOLD_BORDER = "#D8C18D"

# Pipe is the first D243 master screen, so its visual accent intentionally
# aligns to the product accent rather than creating a competing neon identity.
PIPE = GOLD
PIPE_DARK = GOLD_DARK
PIPE_DEEP = "#5D4311"
PIPE_SOFT = GOLD_SOFT
PIPE_HOVER_SOFT = "#F5EBCF"
PIPE_PRESSED_SOFT = "#E9D9AD"
PIPE_BORDER = GOLD_BORDER
PIPE_DISABLED = "#E2D7BB"
PIPE_ACTION_HOVER = "#C79D3B"
PIPE_ACTION_PRESSED = "#96701F"
# Transfer now follows the shared D243 product accent rather than retaining a
# competing module-orange visual system.
TRANSFER = GOLD
TRANSFER_SOFT = GOLD_SOFT
# Discharge adopts the shared D243 navy-led presentation; gold remains the
# restrained engineering-result accent rather than a competing bright blue.
DISCHARGE = NAVY
DISCHARGE_SOFT = GOLD_SOFT
SUCTION = "#35698F"
SUCTION_SOFT = "#EEF4F8"

APP_BACKGROUND = "#EEF2F5"
HEADER_SURFACE = NAVY
RIBBON_SURFACE = NAVY
SECONDARY_SURFACE = "#F4F6F8"
SIDEBAR_SURFACE = SECONDARY_SURFACE
WORKSPACE_SURFACE = APP_BACKGROUND
CARD_SURFACE = WHITE
RESULT_SURFACE = "#F9FBFC"
FORMULA_SURFACE = "#F8F7F3"
INFO_SURFACE = "#EDF5FF"
TEXT_PRIMARY = NAVY_TEXT
TEXT_SECONDARY = "#5B6B82"
TEXT_MUTED = "#7C8BA1"
BORDER = "#D3DAE1"
STRONG_BORDER = "#A9B7C4"
DIVIDER = "#E3E8EC"
ON_ACCENT = WHITE

# The shell uses a restrained tonal step inside the fixed two-row navy header.
HEADER_GROUP_SURFACE = "#0A2B54"
HEADER_GROUP_BORDER = "#3A5F8C"
HEADER_GROUP_TEXT = "#EAF3FF"
HEADER_MUTED_TEXT = "#C8D7EE"

INFO = "#1677E8"
SUCCESS = "#159A55"
SUCCESS_SURFACE = "#EDF9F2"
WARNING = "#E98600"
WARNING_SURFACE = "#FFF6E8"
ERROR = "#E52B32"
ERROR_SURFACE = "#FFF0F1"
CRITICAL_ENGINEERING = "#8E1028"
CRITICAL_ENGINEERING_SURFACE = "#FCECEF"

# Compatibility aliases used by the current shared presentation components.
BACKGROUND = APP_BACKGROUND
SURFACE = CARD_SURFACE
SURFACE_ALT = WORKSPACE_SURFACE
# Generic application-primary compatibility values remain aligned with the
# navy-led D243 product identity rather than a module-specific accent.
PRIMARY = NAVY
PRIMARY_HOVER = DEEP_NAVY
PRIMARY_SOFT = "#E9EFF4"
SECONDARY = NAVY
SECONDARY_SOFT = INFO_SURFACE
FORMULA = GOLD_DARK
FORMULA_SOFT = GOLD_SOFT
SUCCESS_SOFT = SUCCESS_SURFACE
WARNING_SOFT = WARNING_SURFACE
DANGER = ERROR
DANGER_SOFT = ERROR_SURFACE
