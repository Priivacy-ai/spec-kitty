"""ContradictionChecker: detect logical contradictions within the DRG.

Two contradiction classes are checked:

1. **ADR topic clash**: Two or more ``adr`` nodes share the same ``topic``
   metadata field but have different ``decision`` content hashes.  This
   signals conflicting decisions on the same architectural question.

2. **Duplicate active glossary scopes**: Two or more ``glossary_scope``
   nodes within the same scope share the same ``label`` (case-insensitive),
   indicating that the same term has been defined more than once.

No LLM calls are made.  All comparisons are string equality / hash
comparison on node metadata.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any

from specify_cli.charter_lint.findings import LintFinding


def _content_hash(text: str | None) -> str:
    """Return a short SHA-256 hex digest for *text*, or '' when None."""
    if text is None:
        return ""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


class ContradictionChecker:
    """Detect contradictory ADR decisions and duplicate glossary senses."""

    def run(self, drg: Any, feature_scope: str | None = None) -> list[LintFinding]:
        """Return findings for all detected contradictions.

        Returns ``[]`` when *drg* is ``None``.
        """
        if drg is None:
            return []

        findings: list[LintFinding] = []
        findings.extend(self._check_adr_topic_clash(drg, feature_scope))
        findings.extend(self._check_duplicate_glossary_senses(drg, feature_scope))
        return findings

    # ------------------------------------------------------------------
    # ADR topic contradictions
    # ------------------------------------------------------------------

    def _check_adr_topic_clash(self, drg: Any, feature_scope: str | None) -> list[LintFinding]:
        """Find ADR nodes with the same topic but different decision hashes."""
        # topic -> list of (urn, decision_hash)
        by_topic: dict[str, list[tuple[str, str]]] = defaultdict(list)

        for node in getattr(drg, "nodes", []):
            kind = getattr(node, "kind", None)
            kind_val = kind.value if hasattr(kind, "value") else str(kind) if kind else ""
            if kind_val != "adr":
                continue

            urn: str = getattr(node, "urn", "") or ""
            # ``topic`` may live in a ``metadata`` dict or as a direct attribute
            metadata = getattr(node, "metadata", None) or {}
            topic: str = getattr(node, "topic", None) or (metadata.get("topic") if isinstance(metadata, dict) else None) or ""
            decision: str = (
                getattr(node, "decision", None) or (metadata.get("decision") if isinstance(metadata, dict) else None) or getattr(node, "label", None) or ""
            )

            if not topic:
                continue

            by_topic[topic].append((urn, _content_hash(decision)))

        findings: list[LintFinding] = []
        for topic, entries in by_topic.items():
            hashes = {h for _, h in entries}
            if len(hashes) > 1:
                urns = [u for u, _ in entries]
                findings.append(
                    LintFinding(
                        category="contradiction",
                        type="adr_topic_clash",
                        id=f"topic:{topic}",
                        severity="high",
                        message=(f"ADR topic '{topic}' has {len(urns)} nodes with conflicting decision content: {', '.join(urns)}"),
                        feature_id=feature_scope,
                        remediation_hint=("Review the conflicting ADRs and supersede the older ones."),
                    )
                )

        return findings

    # ------------------------------------------------------------------
    # Duplicate glossary senses
    # ------------------------------------------------------------------

    def _check_duplicate_glossary_senses(self, drg: Any, feature_scope: str | None) -> list[LintFinding]:
        """Find glossary_scope nodes with duplicate labels within the same scope."""
        # normalised_label -> list of urn
        by_label: dict[str, list[str]] = defaultdict(list)

        for node in getattr(drg, "nodes", []):
            kind = getattr(node, "kind", None)
            kind_val = kind.value if hasattr(kind, "value") else str(kind) if kind else ""
            if kind_val != "glossary_scope":
                continue

            urn: str = getattr(node, "urn", "") or ""
            label: str = getattr(node, "label", None) or ""
            if not label:
                continue

            by_label[label.strip().lower()].append(urn)

        findings: list[LintFinding] = []
        for normalised, urns in by_label.items():
            if len(urns) > 1:
                findings.append(
                    LintFinding(
                        category="contradiction",
                        type="duplicate_glossary_sense",
                        id=f"label:{normalised}",
                        severity="medium",
                        message=(f"Glossary label '{normalised}' is defined by {len(urns)} nodes: {', '.join(urns)}"),
                        feature_id=feature_scope,
                        remediation_hint=("Merge the duplicate definitions or make them distinct terms."),
                    )
                )

        return findings
