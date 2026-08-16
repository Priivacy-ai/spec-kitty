"""ReferenceIntegrityChecker: detect broken and misleading DRG references.

Two integrity rules are applied:

1. **Dangling edges**: An edge whose ``target`` URN is not present in the
   DRG node set.  This indicates a broken reference — the target was deleted
   or renamed without updating the edge.  Severity: ``high``.

2. **Superseded ADR references**: A ``wp`` node has an edge pointing to an
   ``adr`` node, but that ADR node itself has an outgoing ``"replaces"``
   edge (i.e. it has been superseded by a newer ADR).  The WP should be
   updated to reference the current ADR instead.  Severity: ``medium``.

All checks are pure graph traversal using ``edge.relation``.
"""

from __future__ import annotations

from typing import Any

from specify_cli.charter_runtime.lint.findings import LintFinding


def _edge_relation_value(edge: Any) -> str:
    """Return the string value of an edge's ``relation``, or '' when unset."""
    relation = getattr(edge, "relation", None)
    return getattr(relation, "value", str(relation) if relation else "")


class ReferenceIntegrityChecker:
    """Detect dangling edges and superseded ADR references."""

    def run(self, drg: Any, feature_scope: str | None = None) -> list[LintFinding]:
        """Return integrity findings for *drg*.

        Returns ``[]`` when *drg* is ``None``.
        """
        if drg is None:
            return []

        # Build node-urn set for O(1) membership tests
        node_urns: set[str] = {
            getattr(n, "urn", None) or "" for n in getattr(drg, "nodes", [])
        }
        node_urns.discard("")

        findings: list[LintFinding] = []
        findings.extend(self._check_dangling_edges(drg, node_urns, feature_scope))
        findings.extend(
            self._check_superseded_adr_references(drg, node_urns, feature_scope)
        )
        return findings

    # ------------------------------------------------------------------
    # Rule 1 — dangling edges
    # ------------------------------------------------------------------

    def _check_dangling_edges(
        self, drg: Any, node_urns: set[str], feature_scope: str | None
    ) -> list[LintFinding]:
        findings: list[LintFinding] = []
        for edge in getattr(drg, "edges", []):
            target: str = getattr(edge, "target", None) or ""
            if not target:
                continue
            if target not in node_urns:
                source: str = getattr(edge, "source", None) or ""
                relation_val = _edge_relation_value(edge)
                findings.append(
                    LintFinding(
                        category="reference_integrity",
                        type="dangling_edge",
                        id=f"edge:{source}->{target}",
                        severity="high",
                        message=(
                            f"Edge from '{source}' to '{target}' via '{relation_val}' "
                            f"is dangling — target URN '{target}' does not exist in the DRG."
                        ),
                        feature_id=feature_scope,
                        remediation_hint=(
                            f"Remove the edge or add the missing node '{target}'."
                        ),
                    )
                )
        return findings

    # ------------------------------------------------------------------
    # Rule 2 — WP references a superseded ADR
    # ------------------------------------------------------------------

    def _check_superseded_adr_references(
        self, drg: Any, _node_urns: set[str], feature_scope: str | None
    ) -> list[LintFinding]:
        """Flag WP->ADR edges where the referenced ADR has been superseded."""
        superseded_adrs = self._collect_superseded_adrs(drg)
        if not superseded_adrs:
            return []

        findings: list[LintFinding] = []
        for source, target in self._iter_wp_to_superseded_edges(drg, superseded_adrs):
            findings.append(
                self._build_superseded_finding(source, target, feature_scope)
            )
        return findings

    @staticmethod
    def _collect_superseded_adrs(drg: Any) -> set[str]:
        """Return ADR URNs that have outgoing ``"replaces"`` edges.

        The *source* of a "replaces" edge is the newer ADR; the *target* is
        the older (superseded) ADR.
        """
        superseded_adrs: set[str] = set()
        for edge in getattr(drg, "edges", []):
            if _edge_relation_value(edge) != "replaces":
                continue
            target: str = getattr(edge, "target", None) or ""
            if target:
                superseded_adrs.add(target)
        return superseded_adrs

    @staticmethod
    def _iter_wp_to_superseded_edges(
        drg: Any, superseded_adrs: set[str]
    ) -> list[tuple[str, str]]:
        """Return ``(source, target)`` pairs for WP edges into a superseded ADR."""
        pairs: list[tuple[str, str]] = []
        for edge in getattr(drg, "edges", []):
            source: str = getattr(edge, "source", None) or ""
            target: str = getattr(edge, "target", None) or ""

            # Source must be a WP node
            if not source.startswith("wp:"):
                continue

            # Target must be a superseded ADR
            if target not in superseded_adrs:
                continue

            pairs.append((source, target))
        return pairs

    @staticmethod
    def _build_superseded_finding(
        source: str, target: str, feature_scope: str | None
    ) -> LintFinding:
        return LintFinding(
            category="reference_integrity",
            type="superseded_adr_reference",
            id=f"edge:{source}->{target}",
            severity="medium",
            message=(
                f"Work package '{source}' references ADR '{target}' "
                f"which has been superseded by a newer ADR."
            ),
            feature_id=feature_scope,
            remediation_hint=(
                "Update the WP to reference the superseding ADR instead."
            ),
        )
