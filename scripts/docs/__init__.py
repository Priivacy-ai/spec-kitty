"""Docs maintenance tooling for the Spec Kitty 3.2 documentation refresh.

This package houses read-only checks used by the documentation mission
(``spec-kitty-3-2-docs-01KS4KSZ``). The modules here never mutate ``docs/``
or the inventory manifests they consume; they only inspect, classify, and
report.

Public modules:

- :mod:`scripts.docs.version_leakage_check` – CLI entry point that enforces
  ``FR-005`` / ``NFR-002`` (version-tier leakage detection).
- :mod:`scripts.docs._inventory` – ruamel.yaml-based loader for
  ``PageInventoryEntry`` rows.
- :mod:`scripts.docs._render` – deterministic rich/plain table renderers
  for ``FreshnessFinding`` rows.
"""

from __future__ import annotations

__all__: list[str] = []
