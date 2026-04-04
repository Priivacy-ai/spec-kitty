"""Parallelization conflict risk scoring.

Scores the risk of integration conflicts between parallel execution lanes.
Lane computation already groups WPs with overlapping owned_files globs into
the same lane, so distinct parallel lanes have non-overlapping globs by
construction. This scorer adds three orthogonal heuristics that detect
risk beyond glob-level overlap:

1. **Shared parent directory proximity** — lanes touching files in the same
   parent directory (e.g., both under src/views/) have integration risk from
   shared imports, utilities, or template coupling.

2. **Import/dependency coupling** — cross-lane references in WP body text
   (e.g., "from core.models import Foo" when another lane owns core/models.py).

3. **Shared test surface** — both lanes reference the same test files or
   test modules, predicting merge conflicts in test code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import PurePosixPath

from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.policy.config import RiskPolicyConfig


@dataclass(frozen=True)
class LanePairRisk:
    """Risk assessment for a pair of parallel lanes."""

    lane_a: str
    lane_b: str
    shared_parent_dirs: tuple[str, ...]
    import_coupling: tuple[str, ...]
    shared_test_surfaces: tuple[str, ...]
    score: float


@dataclass(frozen=True)
class RiskReport:
    """Complete risk report for a feature's lane parallelization."""

    feature_slug: str
    lane_pair_risks: list[LanePairRisk]
    overall_score: float
    threshold: float
    exceeds_threshold: bool


def compute_risk_report(
    lanes_manifest: LanesManifest,
    wp_bodies: dict[str, str] | None = None,
    policy: RiskPolicyConfig | None = None,
) -> RiskReport:
    """Compute conflict risk for parallel lanes.

    Args:
        lanes_manifest: Computed lane assignments.
        wp_bodies: WP ID → body text for import coupling analysis.
        policy: Risk policy config (for threshold). Defaults if None.

    Returns:
        RiskReport with per-pair and overall scores.
    """
    if policy is None:
        policy = RiskPolicyConfig()

    # Group lanes by parallel_group — only lanes in the same group can conflict.
    groups: dict[int, list[ExecutionLane]] = {}
    for lane in lanes_manifest.lanes:
        groups.setdefault(lane.parallel_group, []).append(lane)

    pair_risks: list[LanePairRisk] = []
    for group_lanes in groups.values():
        if len(group_lanes) < 2:
            continue
        for lane_a, lane_b in combinations(group_lanes, 2):
            risk = _score_lane_pair(lane_a, lane_b, wp_bodies or {})
            pair_risks.append(risk)

    overall = max((r.score for r in pair_risks), default=0.0)

    return RiskReport(
        feature_slug=lanes_manifest.feature_slug,
        lane_pair_risks=pair_risks,
        overall_score=overall,
        threshold=policy.threshold,
        exceeds_threshold=overall > policy.threshold,
    )


def _score_lane_pair(
    lane_a: ExecutionLane,
    lane_b: ExecutionLane,
    wp_bodies: dict[str, str],
) -> LanePairRisk:
    """Score a single pair of parallel lanes."""
    shared_parents = _find_shared_parent_dirs(lane_a.write_scope, lane_b.write_scope)
    imports = _find_import_coupling(lane_a, lane_b, wp_bodies)
    shared_tests = _find_shared_test_surfaces(lane_a, lane_b, wp_bodies)

    # Weighted score: parent proximity is strongest signal, then imports, then tests.
    raw = (
        min(len(shared_parents), 5) * 0.12
        + min(len(imports), 5) * 0.10
        + min(len(shared_tests), 3) * 0.08
    )
    score = min(1.0, raw)

    return LanePairRisk(
        lane_a=lane_a.lane_id,
        lane_b=lane_b.lane_id,
        shared_parent_dirs=tuple(shared_parents),
        import_coupling=tuple(imports),
        shared_test_surfaces=tuple(shared_tests),
        score=round(score, 3),
    )


def _find_shared_parent_dirs(
    scope_a: tuple[str, ...], scope_b: tuple[str, ...],
) -> list[str]:
    """Find parent directories (depth 2+) shared between two write scopes.

    E.g., src/views/dashboard.py and src/views/workspace.py share src/views/.
    """
    parents_a = _extract_parent_dirs(scope_a)
    parents_b = _extract_parent_dirs(scope_b)
    return sorted(parents_a & parents_b)


def _extract_parent_dirs(scope: tuple[str, ...]) -> set[str]:
    """Extract parent directories at depth 2+ from glob patterns."""
    parents: set[str] = set()
    for pattern in scope:
        # Strip glob wildcards to get the path prefix.
        clean = pattern.replace("/**", "").replace("/*", "").replace("**", "").rstrip("/")
        if not clean:
            continue
        path = PurePosixPath(clean)
        # Add parent at depth 2+ (e.g., src/views from src/views/dashboard.py)
        for parent in path.parents:
            parts = parent.parts
            if len(parts) >= 2:
                parents.add(str(parent))
    return parents


def _find_import_coupling(
    lane_a: ExecutionLane, lane_b: ExecutionLane,
    wp_bodies: dict[str, str],
) -> list[str]:
    """Find cross-lane import references in WP body text.

    If lane-a's WP body mentions a module path owned by lane-b, that's coupling.
    """
    coupling: list[str] = []

    # Build module paths from write scopes.
    modules_a = _scope_to_module_paths(lane_a.write_scope)
    modules_b = _scope_to_module_paths(lane_b.write_scope)

    # Check if lane-a's WP bodies reference lane-b's modules.
    bodies_a = " ".join(wp_bodies.get(wp, "") for wp in lane_a.wp_ids)
    bodies_b = " ".join(wp_bodies.get(wp, "") for wp in lane_b.wp_ids)

    for mod in modules_b:
        if mod in bodies_a:
            coupling.append(f"{lane_a.lane_id} references {mod} (owned by {lane_b.lane_id})")

    for mod in modules_a:
        if mod in bodies_b:
            coupling.append(f"{lane_b.lane_id} references {mod} (owned by {lane_a.lane_id})")

    return coupling


def _scope_to_module_paths(scope: tuple[str, ...]) -> set[str]:
    """Convert write scope globs to Python-style module paths for text matching."""
    modules: set[str] = set()
    for pattern in scope:
        clean = pattern.replace("/**", "").replace("/*", "").replace("**", "").rstrip("/")
        if not clean:
            continue
        # Convert path to dotted module: src/specify_cli/core -> specify_cli.core
        if clean.startswith("src/"):
            clean = clean[4:]
        if clean.endswith(".py"):
            clean = clean[:-3]
        modules.add(clean.replace("/", "."))
    return modules


_TEST_FILE_RE = re.compile(r"tests?/[\w/]*test_\w+", re.IGNORECASE)


def _find_shared_test_surfaces(
    lane_a: ExecutionLane, lane_b: ExecutionLane,
    wp_bodies: dict[str, str],
) -> list[str]:
    """Find test files referenced by both lanes' WP bodies."""
    tests_a = _extract_test_refs(lane_a, wp_bodies)
    tests_b = _extract_test_refs(lane_b, wp_bodies)
    return sorted(tests_a & tests_b)


def _extract_test_refs(lane: ExecutionLane, wp_bodies: dict[str, str]) -> set[str]:
    """Extract test file references from WP body text and write scope."""
    refs: set[str] = set()
    # From write scope.
    for pattern in lane.write_scope:
        if "test" in pattern.lower():
            clean = pattern.replace("/**", "").replace("/*", "").rstrip("/")
            if clean:
                refs.add(clean)
    # From WP body text.
    for wp_id in lane.wp_ids:
        body = wp_bodies.get(wp_id, "")
        for match in _TEST_FILE_RE.finditer(body):
            refs.add(match.group(0))
    return refs
