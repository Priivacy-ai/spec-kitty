"""Deprecated path; re-exports from charter_runtime.preflight for one cycle (C-008).

Eagerly registers the canonical submodules in ``sys.modules`` under the
legacy dotted names so BOTH access patterns resolve to the SAME canonical
module instance:

- ``from specify_cli.charter_preflight import hook``
- ``import specify_cli.charter_preflight.hook``
- ``mock.patch("specify_cli.charter_preflight.hook.X", ...)``

Module-object identity is critical for the third pattern — a test that
patches ``specify_cli.charter_preflight.hook.run_charter_preflight`` must
see the patch take effect inside production code that imports via the
same dotted path. Earlier ``__path__``-sharing approach caused Python to
create a SECOND module instance under the legacy name, defeating the
patch contract (CI run 26440330590).

NFR-003 latency: eager submodule loading here is bounded. The biggest
latency saver (lazy LD-3 chokepoint import in
``charter_runtime/freshness/computer.py``) remains in place.
"""

from __future__ import annotations

import importlib
import sys

from specify_cli.charter_runtime.preflight import *  # noqa: F401,F403
from specify_cli.charter_runtime.preflight import __all__  # noqa: F401

_CANONICAL = "specify_cli.charter_runtime.preflight"

for _sub in ("cli", "config", "dashboard_warning", "hook", "result", "runner"):
    _module = importlib.import_module(f"{_CANONICAL}.{_sub}")
    sys.modules[f"{__name__}.{_sub}"] = _module
    setattr(sys.modules[__name__], _sub, _module)
