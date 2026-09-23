"""Offline localization infrastructure for YSH."""

import sys

sys.modules.setdefault("i18n", sys.modules[__name__])

from .manager import LocalizationManager
from .translator import Translator

__all__ = ["LocalizationManager", "Translator"]
