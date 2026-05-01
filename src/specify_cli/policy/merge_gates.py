"""Evidence-based merge gate evaluation engine.

Three gates that must pass before a merge proceeds:
1. Evidence gate — all WPs have reviewer approval in the event log.
2. Risk gate — parallelization risk score is below threshold.
3. Dependency gate — all WP dependencies are in done lane.

Gates are configurable via MergeGateConfig. Each gate returns
pass/fail/skip. The overall evaluation passes if no blocking
failures exist.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import StrEnum
from pathlib import Path
from typing import Any

from specify_cli.mission_metadata import mission_identity_fields, resolve_mission_identity
from specify_cli.policy.config import MergeGateConfig
from specify_cli.status.models import Lane


class GateVerdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


@dataclass(frozen=True)
class GateResult:
    """Result of a single gate evaluation."""

    gate_name: str
    verdict: GateVerdict
    details: str
    blocking: bool  # True if mode=="block" and verdict=="fail"


@dataclass
class MergeGateEvaluation:
    """Combined result of all gate evaluations."""

    mission_slug: str
    evaluated_at: str
    gates: list[GateResult] = field(default_factory=list)
    mission_number: str | None = None
    mission_type: str | None = None

    @property
    def overall_pass(self) -> bool:
        return not any(g.blocking for g in self.gates)

    @property
    def warnings(self) -> list[str]:
        return [f"{g.gate_name}: {g.details}" for g in self.gates if g.verdict == GateVerdict.FAIL and not g.blocking]

    def to_dict(self) -> dict[str, Any]:
        return {
            **mission_identity_fields(
                self.mission_slug,
                self.mission_number,
                self.mission_type,
            ),
            "evaluated_at": self.evaluated_at,
            "overall_pass": self.overall_pass,
            "gates": [
                {
                    "gate_name": g.gate_name,
                    "verdict": g.verdict,
                    "details": g.details,
                    "blocking": g.blocking,
                }
                for g in self.gates
            ],
            "warnings": self.warnings,
        }


def evaluate_merge_gates(
    feature_dir: Path,
    mission_slug: str,
    wp_ids: list[str],
    policy: MergeGateConfig,
    repo_root: Path,
) -> MergeGateEvaluation:
    """Evaluate all merge gates for a feature.

    Args:
        feature_dir: Path to kitty-specs/{mission_slug}/.
        mission_slug: Feature identifier.
        wp_ids: WP IDs being merged.
        policy: Merge gate configuration.
        repo_root: Repository root.

    Returns:
        MergeGateEvaluation with per-gate results.
    """
    evaluation = MergeGateEvaluation(
        mission_slug=mission_slug,
        evaluated_at=datetime.now(UTC).isoformat(),
    )
    identity = resolve_mission_identity(feature_dir)
    evaluation.mission_slug = identity.mission_slug
    evaluation.mission_number = identity.mission_number
    evaluation.mission_type = identity.mission_type

    if not policy.enabled or policy.mode == "off":
        return evaluation

    is_blocking = policy.mode == "block"

    if policy.require_review_approval:
        evaluation.gates.append(_evaluate_evidence_gate(feature_dir, wp_ids, is_blocking))

    if policy.require_risk_check:
        evaluation.gates.append(_evaluate_risk_gate(feature_dir, is_blocking))

    if policy.require_deps_complete:
        evaluation.gates.append(_evaluate_dependency_gate(feature_dir, wp_ids, is_blocking))

    return evaluation


def _evaluate_evidence_gate(
    feature_dir: Path,
    wp_ids: list[str],
    is_blocking: bool,
) -> GateResult:
    """Check that all WPs have reviewer approval in the event log."""
    try:
        from specify_cli.status.store import read_events

        events = read_events(feature_dir)
        # Find WPs that reached 'approved' lane.
        approved_wps: set[str] = set()
        for event in events:
            data = event if isinstance(event, dict) else event.__dict__
            if data.get("to_lane") in (Lane.APPROVED, Lane.DONE):
                wp = data.get("wp_id")
                if wp:
                    approved_wps.add(wp)

        missing = sorted(set(wp_ids) - approved_wps)
        if missing:
            return GateResult(
                gate_name="evidence",
                verdict=GateVerdict.FAIL,
                details=f"WPs missing review approval: {', '.join(missing)}",
                blocking=is_blocking,
            )
        return GateResult(
            gate_name="evidence",
            verdict=GateVerdict.PASS,
            details=f"All {len(wp_ids)} WPs have review approval",
            blocking=False,
        )
    except Exception as exc:
        return GateResult(
            gate_name="evidence",
            verdict=GateVerdict.FAIL,
            details=f"Could not read event log: {exc}",
            blocking=is_blocking,
        )


def _evaluate_risk_gate(
    feature_dir: Path,
    is_blocking: bool,
) -> GateResult:
    """Check that parallelization risk score is below threshold."""
    try:
        from specify_cli.lanes.persistence import read_lanes_json
        from specify_cli.policy.config import load_policy_config
        from specify_cli.policy.risk_scorer import compute_risk_report

        lanes_manifest = read_lanes_json(feature_dir)
        if lanes_manifest is None:
            return GateResult(
                gate_name="risk",
                verdict=GateVerdict.SKIP,
                details="No lanes.json — risk gate skipped",
                blocking=False,
            )

        # Load risk policy from repo root (navigate up from feature_dir).
        repo_root = feature_dir.parent.parent
        policy = load_policy_config(repo_root)
        report = compute_risk_report(lanes_manifest, policy=policy.risk)

        if report.exceeds_threshold:
            return GateResult(
                gate_name="risk",
                verdict=GateVerdict.FAIL,
                details=(f"Risk score {report.overall_score:.2f} exceeds threshold {report.threshold:.2f}"),
                blocking=is_blocking,
            )
        return GateResult(
            gate_name="risk",
            verdict=GateVerdict.PASS,
            details=f"Risk score {report.overall_score:.2f} within threshold",
            blocking=False,
        )
    except Exception as exc:
        return GateResult(
            gate_name="risk",
            verdict=GateVerdict.SKIP,
            details=f"Risk assessment unavailable: {exc}",
            blocking=False,
        )


def _evaluate_dependency_gate(
    feature_dir: Path,
    wp_ids: list[str],
    is_blocking: bool,
) -> GateResult:
    """Check that all WP dependencies are in done lane."""
    try:
        from specify_cli.core.dependency_graph import build_dependency_graph
        from specify_cli.status.reducer import reduce
        from specify_cli.status.store import read_events

        graph = build_dependency_graph(feature_dir)
        # Merge gate evaluation must remain read-only. Writing status.json here
        # dirties the repo and can block repeated merge attempts.
        snapshot = reduce(read_events(feature_dir))

        wp_lanes: dict[str, str] = {}
        if snapshot and hasattr(snapshot, "work_packages"):
            for wp_id_key, wp_data in snapshot.work_packages.items():
                lane_val = wp_data.get("lane") if isinstance(wp_data, dict) else getattr(wp_data, "lane", None)
                if lane_val:
                    wp_lanes[wp_id_key] = str(lane_val)

        incomplete_deps: list[str] = []
        for wp_id in wp_ids:
            for dep_id in graph.get(wp_id, []):
                dep_lane = wp_lanes.get(dep_id, "unknown")
                if dep_lane not in (Lane.DONE, Lane.APPROVED):
                    incomplete_deps.append(f"{dep_id} (lane={dep_lane})")

        if incomplete_deps:
            return GateResult(
                gate_name="dependency",
                verdict=GateVerdict.FAIL,
                details=f"Incomplete dependencies: {', '.join(incomplete_deps)}",
                blocking=is_blocking,
            )
        return GateResult(
            gate_name="dependency",
            verdict=GateVerdict.PASS,
            details="All dependencies complete",
            blocking=False,
        )
    except Exception as exc:
        return GateResult(
            gate_name="dependency",
            verdict=GateVerdict.SKIP,
            details=f"Dependency check unavailable: {exc}",
            blocking=False,
        )
