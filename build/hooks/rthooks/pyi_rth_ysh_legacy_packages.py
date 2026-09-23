"""Load legacy YSH package roots before the package compatibility bridge."""

from __future__ import annotations

import importlib


for package_name in (
    "core",
    "database",
    "engineering",
    "repositories",
    "services",
    "i18n",
    "ui",
    "paths",
):
    importlib.import_module(package_name)
