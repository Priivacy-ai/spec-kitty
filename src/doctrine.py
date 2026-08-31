"""Deprecated compatibility shim for the top-level ``doctrine`` package (CR-06).

Mission ``charter-code-topology-01M152G1`` relocated the top-level
``src/doctrine/`` package (the offer catalogue: agent profiles, directives,
paradigms, procedures, styleguides, tactics, missions, glossary packs, DRG,
skills, etc.) to ``src/charter/offering/`` (MAP-000 / CR-06 in
``kitty-specs/charter-code-topology-01M152G1/contracts/canonical-operator-surface-map.md``).
The ``src/doctrine/`` *directory* no longer exists — this is a single MODULE
file, not a package, kept only so pre-existing external/legacy callers that
still spell the import as ``import doctrine`` or ``from doctrine import X``
keep working during the deprecation window.

Canonical replacement
----------------------
Replace every ``doctrine.<name>`` reference with ``charter.offering.<name>``:

- ``import doctrine`` -> ``import charter.offering``
- ``from doctrine import X`` -> ``from charter.offering import X``
- ``from doctrine.missions.repository import Y`` -> ``from charter.offering.missions.repository import Y``

Mechanics
---------
A module-level ``__getattr__`` (PEP 562, the same lazy-re-export shape as
``src/runtime/next/__init__.py``) resolves any attribute access against the
real ``charter.offering`` package: first as an already-bound attribute of
``charter.offering`` (covers top-level re-exports like ``ArtifactKind``, and
any submodule ``charter/offering/__init__.py`` itself imports), then as a
``charter.offering.<name>`` submodule import (covers ``from doctrine import
resolver``-style module-form access to a submodule the package ``__init__``
does not eagerly import). Every resolved attribute is cached on this shim
module's ``globals()`` so repeat access after the first does not re-run the
lookup.

Deprecation signal (warn-once discipline, mirrors
``src/specify_cli/retrospective/deprecation.py``): the first import or
attribute access in a process emits a ``DeprecationWarning`` naming the
canonical replacement;
subsequent accesses in the same process are silent (NFR-006-style one-warning-
per-process budget) so normal test/CI runs are not flooded.

Registered in ``docs/migrations/shim-registry.yaml`` per the compatibility
shim lifecycle rulebook (``docs/migrations/migration-and-shim-rules.md``).
"""

from __future__ import annotations

import warnings
from importlib import import_module
from typing import Any

__all__: list[str] = []

_CANONICAL_MODULE = "charter.offering"

_warned = False


def _warn_once() -> None:
    """Emit the CR-06 deprecation notice at most once per process."""
    global _warned
    if _warned:
        return
    _warned = True
    warnings.warn(
        "The top-level 'doctrine' package has moved to 'charter.offering' "
        "(mission charter-code-topology-01M152G1, CR-06). Replace "
        "'import doctrine' / 'from doctrine import X' with "
        "'import charter.offering' / 'from charter.offering import X'. "
        "This compatibility shim (src/doctrine.py) is tracked for removal "
        "in docs/migrations/shim-registry.yaml.",
        DeprecationWarning,
        stacklevel=3,
    )


def __getattr__(name: str) -> Any:
    """Lazily resolve ``doctrine.<name>`` against the real ``charter.offering`` package.

    Dunder names (``__path__``, ``__spec__``, ``__wrapped__``, ...) are
    refused outright rather than delegated. ``charter.offering`` is a real
    package with its own ``__path__``; if this shim ever cached that list
    under its own ``__path__`` attribute, Python's import machinery would
    start treating the *shim* as a package too (``hasattr(sys.modules["doctrine"],
    "__path__")`` becomes true), and a subsequent ``import doctrine.<sub>``
    would silently succeed by re-executing the target source file under the
    ``doctrine.<sub>`` name -- a second, distinct module object from
    ``charter.offering.<sub>``, breaking object identity for anything that
    compares or mutates one and expects the other to see it. Dotted
    submodule imports are intentionally NOT served by this shim (see module
    docstring); this guard is what keeps that true even after ``__path__``
    (or any other dunder) is probed once, e.g. by ``hasattr``.
    """
    if name.startswith("__") and name.endswith("__"):
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    _warn_once()
    offering = import_module(_CANONICAL_MODULE)
    try:
        value = getattr(offering, name)
    except AttributeError:
        try:
            value = import_module(f"{_CANONICAL_MODULE}.{name}")
        except ModuleNotFoundError as exc:
            raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    globals()[name] = value
    return value


_warn_once()
