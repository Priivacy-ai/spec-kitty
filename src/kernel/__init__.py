"""Kernel — zero-dependency shared utilities and primitive types.

This package contains primitives shared by ``specify_cli``, ``constitution``,
and ``doctrine``.  It has **no imports from any of those packages**, keeping
the dependency direction clean:

    kernel  <-  constitution
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
"""
