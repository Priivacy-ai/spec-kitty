"""StalenessChecker: detect DRG nodes that have grown stale over time.

Two staleness rules are applied:

1. **Synthesized artifact staleness**: Any node whose metadata contains a
   ``synthesized_at`` (or ``created_at`` / ``updated_at``) timestamp that
   is older than ``staleness_threshold_days`` is flagged.

2. **Dangling context-source references**: ``agent_profile`` nodes may carry
   a list of ``context_sources`` (URNs of other nodes they reference).  If
   any of those URNs is absent from the DRG node set, the profile is flagged
   as stale.

All comparisons are pure datetime arithmetic.  No LLM calls.
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
from typing import Any

from specify_cli.charter_lint.findings import LintFinding

# Timestamp metadata keys searched in order of preference
_TIMESTAMP_KEYS = ("synthesized_at", "updated_at", "created_at")


def _parse_ts(value: Any) -> datetime | None:
    """Try to parse *value* as an ISO-8601 datetime.  Returns None on failure."""
    if value is None:
        return None
    try:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        s = str(value).strip()
        # Python 3.11+ fromisoformat handles 'Z' suffix; earlier versions need replacement
        s = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except (ValueError, TypeError):
        return None


def _get_metadata_ts(node: Any) -> datetime | None:
    """Return the best available timestamp from *node* metadata."""
    metadata = getattr(node, "metadata", None) or {}
    for key in _TIMESTAMP_KEYS:
        # Try direct attribute first, then metadata dict
        raw = getattr(node, key, None)
        if raw is None and isinstance(metadata, dict):
            raw = metadata.get(key)
        ts = _parse_ts(raw)
        if ts is not None:
            return ts
    return None


class StalenessChecker:
    """Detect stale synthesized artifacts and dangling profile context-sources."""

    def __init__(self, staleness_threshold_days: int = 90) -> None:
        self._threshold = timedelta(days=staleness_threshold_days)

    def run(self, drg: Any, feature_scope: str | None = None) -> list[LintFinding]:
        """Return a finding for every stale node detected in *drg*.

        Returns ``[]`` when *drg* is ``None``.
        """
        if drg is None:
            return []

        now = datetime.now(tz=UTC)
        node_urns: set[str] = {
            getattr(n, "urn", None) or "" for n in getattr(drg, "nodes", [])
        }

        findings: list[LintFinding] = []
        for node in getattr(drg, "nodes", []):
            findings.extend(
                self._check_artifact_staleness(node, now, feature_scope)
            )
            findings.extend(
                self._check_dangling_context_sources(node, node_urns, feature_scope)
            )

        return findings

    # ------------------------------------------------------------------
    # Rule 1 — synthesized-artifact staleness
    # ------------------------------------------------------------------

    def _check_artifact_staleness(
        self, node: Any, now: datetime, feature_scope: str | None
    ) -> list[LintFinding]:
        """Flag synthesized nodes whose timestamp is beyond the threshold."""
        urn: str = getattr(node, "urn", "") or ""
        kind = getattr(node, "kind", None)
        kind_val: str = getattr(kind, "value", str(kind) if kind else "")

        # Only check node kinds that are likely synthesized artifacts
        if kind_val not in {
            "synthesized_artifact",
            "synthesis",
            "retro_finding",
            "charter_section",
            "mission_brief",
        }:
            return []

        ts = _get_metadata_ts(node)
        if ts is None:
            return []

        age = now - ts
        if age <= self._threshold:
            return []

        label: str = getattr(node, "label", None) or urn
        days_old = age.days
        return [
            LintFinding(
                category="staleness",
                type="stale_synthesized_artifact",
                id=urn,
                severity="medium",
                message=(
                    f"Node '{label}' ({urn}) is a synthesized {kind_val} that "
                    f"is {days_old} days old (threshold: {self._threshold.days} days)."
                ),
                feature_id=feature_scope,
                remediation_hint="Re-synthesize or archive this artifact.",
            )
        ]

    # ------------------------------------------------------------------
    # Rule 2 — dangling context-source references on profile nodes
    # ------------------------------------------------------------------

    def _check_dangling_context_sources(
        self, node: Any, node_urns: set[str], feature_scope: str | None
    ) -> list[LintFinding]:
        """Flag agent_profile nodes that reference non-existent context-source URNs."""
        kind = getattr(node, "kind", None)
        kind_val: str = getattr(kind, "value", str(kind) if kind else "")
        if kind_val != "agent_profile":
            return []

        urn: str = getattr(node, "urn", "") or ""
        metadata = getattr(node, "metadata", None) or {}
        # ``context_sources`` may be a direct attribute or nested in metadata
        context_sources: list[str] = (
            getattr(node, "context_sources", None)
            or (metadata.get("context_sources") if isinstance(metadata, dict) else None)
            or []
        )

        findings: list[LintFinding] = []
        for src_urn in context_sources:
            if src_urn not in node_urns:
                label: str = getattr(node, "label", None) or urn
                findings.append(
                    LintFinding(
                        category="staleness",
                        type="dangling_context_source",
                        id=urn,
                        severity="low",
                        message=(
                            f"Agent profile '{label}' ({urn}) references "
                            f"context source '{src_urn}' which no longer exists in the DRG."
                        ),
                        feature_id=feature_scope,
                        remediation_hint=(
                            f"Remove or update the context_sources reference to '{src_urn}'."
                        ),
                    )
                )

        return findings
