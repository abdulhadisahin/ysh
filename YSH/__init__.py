"""YSH application package and compatibility bridge for legacy internal imports."""

from __future__ import annotations

import sys

from . import core as _core
from . import paths as _paths
from . import database as _database
from . import engineering as _engineering
from . import repositories as _repositories
from . import services as _services
from . import i18n as _i18n
from . import ui as _ui

# Internal modules historically used top-level imports (``core``, ``database``
# and similar). Register package-owned aliases so existing local callers and
# package execution share the same modules without modifying ``sys.path``.
sys.modules.setdefault("core", _core)
sys.modules.setdefault("paths", _paths)
sys.modules.setdefault("database", _database)
sys.modules.setdefault("engineering", _engineering)
sys.modules.setdefault("repositories", _repositories)
sys.modules.setdefault("services", _services)
sys.modules.setdefault("i18n", _i18n)
sys.modules.setdefault("ui", _ui)
