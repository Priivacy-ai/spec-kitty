"""OrphanChecker: detect DRG nodes that have no expected incoming edges.

A node is "orphaned" when it belongs to a kind that, by convention, must
be referenced by at least one other node via a specific relation — but no
such edge exists in the graph.

Supported orphan-detection rules
---------------------------------
``directive`` nodes   → expected inbound relation: ``"governs"``
``adr`` nodes         → expected inbound relation: ``"supersedes"`` OR ``"references"``
``glossary_scope``    → expected inbound relation: ``"vocabulary"``

All rules are checked using ``get_incoming_edges()`` from the ``_drg``
helper which uses ``edge.relation`` (not ``edge.type``).
"""

from __future__ import annotations

from typing import Any

from specify_cli.charter_lint._drg import get_incoming_edges
from specify_cli.charter_lint.findings import LintFinding

# Map: node-kind-string -> expected incoming relation names
_ORPHAN_RULES: dict[str, tuple[str, set[str]]] = {
    "directive": ("directive", {"governs"}),
    "adr": ("adr", {"supersedes", "references"}),
    "glossary_scope": ("glossary_scope", {"vocabulary"}),
}


class OrphanChecker:
    """Detect nodes that lack expected inbound edges."""

    def run(self, drg: Any, feature_scope: str | None = None) -> list[LintFinding]:
        """Return a finding for every orphaned node in *drg*.

        Returns ``[]`` when *drg* is ``None`` or when the graph has no nodes.
        """
        if drg is None:
            return []

        findings: list[LintFinding] = []

        for node in getattr(drg, "nodes", []):
            urn: str = getattr(node, "urn", "") or ""
            kind = getattr(node, "kind", None)
            kind_val: str = (
                kind.value if hasattr(kind, "value") else str(kind) if kind else ""
            )

            if kind_val not in _ORPHAN_RULES:
                continue

            type_label, expected_relations = _ORPHAN_RULES[kind_val]
            incoming = get_incoming_edges(drg, urn, expected_relations)

            if not incoming:
                label: str = getattr(node, "label", None) or urn
                findings.append(
                    LintFinding(
                        category="orphan",
                        type=f"orphaned_{type_label}",
                        id=urn,
                        severity="medium",
                        message=(
                            f"Node '{label}' ({urn}) has no incoming edges "
                            f"with relation {sorted(expected_relations)}."
                        ),
                        feature_id=feature_scope,
                        remediation_hint=(
                            f"Link another node to this {kind_val} node via one of: "
                            + ", ".join(f"'{r}'" for r in sorted(expected_relations))
                        ),
                    )
                )

        return findings
