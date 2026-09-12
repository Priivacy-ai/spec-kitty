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

from specify_cli.charter_runtime.lint.findings import LintFinding


def _content_hash(text: str | None) -> str:
    """Return a short SHA-256 hex digest for *text*, or '' when None."""
    if text is None:
        return ""
    return hashlib.sha256(text.encode()).hexdigest()[:16]  # noqa: TID251 - production raw SHA-256 owner


def _adr_topic_and_decision_hash(node: Any) -> tuple[str, str] | None:
    """Return ``(topic, decision_hash)`` for an ADR *node*, or ``None``.

    Returns ``None`` when *node* is not an ``adr`` node, or when it has no
    ``topic`` metadata (both cases are skipped by the caller).
    """
    kind = getattr(node, "kind", None)
    kind_val = getattr(kind, "value", str(kind) if kind else "")
    if kind_val != "adr":
        return None

    # ``topic`` may live in a ``metadata`` dict or as a direct attribute
    metadata = getattr(node, "metadata", None) or {}
    topic: str = (
        getattr(node, "topic", None)
        or (metadata.get("topic") if isinstance(metadata, dict) else None)
        or ""
    )
    if not topic:
        return None

    decision: str = (
        getattr(node, "decision", None)
        or (metadata.get("decision") if isinstance(metadata, dict) else None)
        or getattr(node, "label", None)
        or ""
    )
    return topic, _content_hash(decision)


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

    def _check_adr_topic_clash(
        self, drg: Any, feature_scope: str | None
    ) -> list[LintFinding]:
        """Find ADR nodes with the same topic but different decision hashes."""
        by_topic = self._group_adr_decisions_by_topic(drg)

        findings: list[LintFinding] = []
        for topic, entries in by_topic.items():
            hashes = {h for _, h in entries}
            if len(hashes) > 1:
                findings.append(
                    self._build_topic_clash_finding(topic, entries, feature_scope)
                )

        return findings

    @staticmethod
    def _group_adr_decisions_by_topic(
        drg: Any,
    ) -> dict[str, list[tuple[str, str]]]:
        """Group ``(urn, decision_hash)`` pairs by ADR topic."""
        by_topic: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for node in getattr(drg, "nodes", []):
            result = _adr_topic_and_decision_hash(node)
            if result is None:
                continue
            topic, decision_hash = result
            urn: str = getattr(node, "urn", "") or ""
            by_topic[topic].append((urn, decision_hash))
        return by_topic

    @staticmethod
    def _build_topic_clash_finding(
        topic: str,
        entries: list[tuple[str, str]],
        feature_scope: str | None,
    ) -> LintFinding:
        urns = [u for u, _ in entries]
        return LintFinding(
            category="contradiction",
            type="adr_topic_clash",
            id=f"topic:{topic}",
            severity="high",
            message=(
                f"ADR topic '{topic}' has {len(urns)} nodes with "
                f"conflicting decision content: {', '.join(urns)}"
            ),
            feature_id=feature_scope,
            remediation_hint=(
                "Review the conflicting ADRs and supersede the older ones."
            ),
        )

    # ------------------------------------------------------------------
    # Duplicate glossary senses
    # ------------------------------------------------------------------

    def _check_duplicate_glossary_senses(
        self, drg: Any, feature_scope: str | None
    ) -> list[LintFinding]:
        """Find glossary_scope nodes with duplicate labels within the same scope."""
        # normalised_label -> list of urn
        by_label: dict[str, list[str]] = defaultdict(list)

        for node in getattr(drg, "nodes", []):
            kind = getattr(node, "kind", None)
            kind_val = getattr(kind, "value", str(kind) if kind else "")
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
                        message=(
                            f"Glossary label '{normalised}' is defined by "
                            f"{len(urns)} nodes: {', '.join(urns)}"
                        ),
                        feature_id=feature_scope,
                        remediation_hint=(
                            "Merge the duplicate definitions or make them distinct terms."
                        ),
                    )
                )

        return findings
