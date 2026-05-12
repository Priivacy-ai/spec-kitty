"""Canonical exception hierarchy for Spec Kitty internal-consistency errors.

Lives in ``kernel`` because every other package (``charter``, ``doctrine``,
``specify_cli``) is allowed to depend on ``kernel`` but ``kernel`` depends on
nothing else. This breaks the import cycle that would otherwise prevent
``charter`` from referencing the base error type when ``specify_cli``'s
package init eagerly registers commands that touch ``charter`` back.

``KittyInternalConsistencyError`` is the canonical base for any error that
indicates the system detected a violated internal invariant — content that
cannot be safely processed under the project's contract (e.g. a charter file
in an ambiguous encoding), state that contradicts a declared schema, or an
artifact that cannot be reconciled with its origin.

These errors are **never** silently swallowed by ``except Exception`` in
production code. Subsystems raise specific subclasses (e.g.
``CharterEncodingError``); CLI / TUI / UI layers catch the base and render
the diagnostic uniformly so the operator sees the actual failure mode rather
than an empty result.

Attributes carried by every subclass:

- ``code``: JSON-stable diagnostic string (e.g. ``"CHARTER_ENCODING_AMBIGUOUS"``).
  Suitable for machine consumers (CI harnesses, dashboards, the cross-surface
  fixture harness in epic #992 Phase 0).
- ``body``: human-readable detail with remediation steps. Suitable for stderr,
  TUI dialogs, or a web error panel.
"""

from __future__ import annotations


class KittyInternalConsistencyError(Exception):
    """Base for errors indicating a violated internal invariant.

    Subsystems raise more specific subclasses; CLI/TUI/UI layers catch this
    base type to render the diagnostic uniformly. Do **not** catch in bare
    ``except Exception`` blocks in production code.
    """

    def __init__(self, code: str, body: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.body = body
