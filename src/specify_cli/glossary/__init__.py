"""Compatibility shim for the extracted glossary package.

Deprecated: import from ``glossary`` instead. Scheduled for removal in 3.3.0.
"""

from __future__ import annotations

import importlib
import sys
import warnings

from glossary import *  # noqa: F401,F403
from glossary import __all__ as __all__

__deprecated__ = True
__canonical_import__ = "glossary"
__removal_release__ = "3.3.0"
__deprecation_message__ = (
    "specify_cli.glossary is deprecated; import from glossary. "
    "Scheduled for removal in 3.3.0."
)

warnings.warn(__deprecation_message__, DeprecationWarning, stacklevel=2)

_SUBMODULES = (
    "attachment",
    "checkpoint",
    "chokepoint",
    "clarification",
    "conflict",
    "drg_builder",
    "entity_pages",
    "events",
    "exceptions",
    "extraction",
    "middleware",
    "models",
    "observation",
    "pipeline",
    "resolution",
    "scope",
    "seed_schema",
    "seed_validation",
    "semantic_events",
    "store",
    "strictness",
)

for _name in _SUBMODULES:
    _module = importlib.import_module(f"glossary.{_name}")
    sys.modules[f"{__name__}.{_name}"] = _module
    globals()[_name] = _module

del _module
del _name
