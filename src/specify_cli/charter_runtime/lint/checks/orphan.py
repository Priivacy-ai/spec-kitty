"""OrphanChecker: detect DRG nodes that have no expected incoming edges.

A node is "orphaned" when it belongs to a kind that, by convention, must
be referenced by at least one other node via a specific relation — but no
such edge exists in the graph.

Supported orphan-detection rules
---------------------------------
``directive`` nodes   → expected inbound relation: one of ``"scope"``,
                        ``"requires"``, ``"suggests"``, ``"applies"``, or
                        ``"refines"`` (the relations the built-in doctrine
                        layer actually emits toward directives) — OR an
                        *outgoing* ``"reconciles_tension"`` edge, since an
                        active reconciliation directive is by design the
                        *source* of its reconciliation edges, never their
                        target, and would otherwise misfire as orphaned.
``glossary_scope``    → expected inbound relation: ``"vocabulary"``

Prior to this fix, ``directive`` nodes required an inbound ``"governs"``
edge and ``adr`` nodes required inbound ``"supersedes"`` or ``"references"``.
None of ``governs``, ``supersedes``, or ``references`` is a member of the
``Relation`` enum (``src/doctrine/drg/models.py``), so those edges could
never be authored — the rules misfired on every built-in directive/adr node
regardless of how well-connected it actually was (issue #2737). The
``directive`` rule now checks the relations the graph actually emits; the
``adr`` rule is retired outright since no real relation ever backed it and
no ``adr`` node kind exists in the built-in layer today.

Incoming-edge rules are checked using ``get_incoming_edges()`` from the
``_drg`` helper which uses ``edge.relation`` (not ``edge.type``). The
outgoing-edge reconciliation exemption is checked directly against
``drg.edges`` (see ``_has_exempting_outgoing_edge``).
"""

from __future__ import annotations

from typing import Any

from specify_cli.charter_runtime.lint._drg import get_incoming_edges
from specify_cli.charter_runtime.lint.findings import LintFinding

# Map: node-kind-string -> (finding type label, expected incoming relation names)
_ORPHAN_RULES: dict[str, tuple[str, set[str]]] = {
    "directive": ("directive", {"scope", "requires", "suggests", "applies", "refines"}),
    "glossary_scope": ("glossary_scope", {"vocabulary"}),
}

# Node kinds whose orphan check is also satisfied by an *outgoing* edge of one
# of these relations -- i.e. the node is expected to be a reference *source*,
# never a *target*, for that relation. A ``reconciles_tension`` edge always
# points FROM the active reconciliation artefact TO the tension pair it
# resolves (never the reverse), so a reconciliation directive would otherwise
# be flagged as orphaned even when it is doing exactly its intended job.
_SELF_EXEMPTING_OUTGOING_RELATIONS: dict[str, set[str]] = {
    "directive": {"reconciles_tension"},
}


def _has_exempting_outgoing_edge(drg: Any, urn: str, kind_val: str) -> bool:
    """Return True if *urn* has an outgoing edge that exempts it from orphan status.

    Returns ``False`` when *kind_val* has no self-exempting relations configured,
    or when no matching outgoing edge exists.
    """
    exempt_relations = _SELF_EXEMPTING_OUTGOING_RELATIONS.get(kind_val)
    if not exempt_relations:
        return False

    for edge in getattr(drg, "edges", []):
        if getattr(edge, "source", None) != urn:
            continue
        relation = getattr(edge, "relation", None)
        relation_val = getattr(relation, "value", str(relation) if relation else "")
        if relation_val in exempt_relations:
            return True
    return False


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
            kind_val: str = getattr(kind, "value", str(kind) if kind else "")

            if kind_val not in _ORPHAN_RULES:
                continue

            type_label, expected_relations = _ORPHAN_RULES[kind_val]
            incoming = get_incoming_edges(drg, urn, expected_relations)

            if not incoming and not _has_exempting_outgoing_edge(drg, urn, kind_val):
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
