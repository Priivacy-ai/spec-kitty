"""Kernel — zero-dependency shared utilities and primitive types.

This package contains primitives shared by ``specify_cli``, ``charter``,
and ``doctrine``.  It has **no imports from any of those packages**, keeping
the dependency direction clean:

    kernel  <-  charter
    kernel  <-  doctrine
    kernel  <-  specify_cli

Modules
-------
atomic
    Atomic file-write utility (write-to-temp-then-rename).
glossary_types
    Glossary primitive value types: ``Strictness``, ``ExtractedTerm``,
    ``SemanticConflict``, ``ScopeRef``, ``GlossaryScope``, and related
    supporting types. Canonical definitions; consumed as re-exports by
    ``specify_cli.glossary`` and ``doctrine.shared``.
paths
    Path resolution utilities: ``get_kittify_home()`` and
    ``get_package_asset_root()``. Canonical implementations; re-exported
    by ``specify_cli.runtime.home`` for backward compatibility.
glossary_runner
    Plugin registry for the glossary runner. Defines
    ``GlossaryRunnerProtocol``, ``register()``, ``get_runner()``, and
    ``clear_registry()`` (test-only). ``specify_cli.glossary`` registers
    the concrete ``GlossaryAwarePrimitiveRunner`` at import time; doctrine
    calls ``get_runner()`` without importing ``specify_cli``.
"""
