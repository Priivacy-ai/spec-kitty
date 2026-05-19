"""Charter facade for mission primitive execution.

This module is the charter-layer proxy for runtime callers that historically
imported from ``doctrine.missions`` directly. The runtime → charter →
doctrine boundary (ADR 2026-03-27-1, tightened by mission
``charter-mediated-doctrine-selection-01KRTZCA``) requires runtime modules
under ``src/specify_cli/`` to reach doctrine artifacts only through such
charter facades.

This file is a **pure re-export** module — no behaviour, no wrappers, no
type aliases.
"""

from doctrine.missions import PrimitiveExecutionContext, execute_with_glossary

__all__ = [
    "PrimitiveExecutionContext",
    "execute_with_glossary",
]
