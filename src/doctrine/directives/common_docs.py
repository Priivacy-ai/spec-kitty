"""Shared binding constant for the Common Docs documentation directive.

This module is the **single source of truth** for the Common Docs directive id
(C-003 binding-must-resolve). Both the authored directive artifact
(``src/doctrine/directives/built-in/042-common-docs.directive.yaml``) and the
Common Docs anti-sprawl structure ratchet (WP05) reference this constant so the
binding is a resolvable contract, not a copy-pasted string.

WP05's ratchet self-test MUST assert that :data:`COMMON_DOCS_DIRECTIVE_ID`
resolves to a *loaded* directive — a node in ``src/doctrine/graph.yaml`` / a
directive that loads via ``DoctrineService`` — not merely that the literal string
appears somewhere. A directive nothing consults is the fakeable failure mode this
constant exists to prevent.
"""

from __future__ import annotations

#: Canonical directive id for the Common Docs documentation standard.
#: Matches the ``id`` field of
#: ``src/doctrine/directives/built-in/042-common-docs.directive.yaml`` and
#: normalises to the same value via ``directive_to_urn`` (the ``042-`` filename
#: prefix and this ``DIRECTIVE_042`` id resolve to the identical URN).
COMMON_DOCS_DIRECTIVE_ID: str = "DIRECTIVE_042"

__all__ = [
    "COMMON_DOCS_DIRECTIVE_ID",
]
