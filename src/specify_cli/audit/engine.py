"""Audit engine: scan loop, classifier dispatch, repo-level findings, report assembly.

This module is the integration point for the read-only mission-state audit.  It:

1. Discovers mission directories under ``scan_root`` in lexicographic order.
2. Dispatches the 7 per-artifact classifiers for each mission.
3. Calls ``audit_repo()`` once and indexes ``IdentityState`` results by slug.
4. Calls ``find_duplicate_prefixes()`` and ``find_ambiguous_selectors()`` for
   repo-level findings.
5. Sorts findings by ``(artifact_path, code)`` within each mission.
6. Assembles ``RepoAuditReport`` with sorted missions and shape counters.

Determinism contract (D4):
- Missions processed in ``sorted(..., key=lambda p: p.name)`` order.
- Findings sorted by ``(artifact_path, code)`` before constructing ``MissionAuditResult``.
- ``json.dumps(sort_keys=True, indent=2)`` — enforced by ``serializer.py``.
- No timestamps, PIDs, or wall-clock values in output.
- ``shape_counters`` built with ``collections.Counter``, serialised with sorted keys.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from specify_cli.context.mission_resolver import (
    AmbiguousHandleError,  # noqa: F401  (re-exported for CLI callers via engine)
    MissionNotFoundError,  # noqa: F401
    resolve_mission,
)
from specify_cli.status.identity_audit import (
    IdentityState,
    audit_repo,
    find_ambiguous_selectors,
    find_duplicate_prefixes,
)

from .classifiers.decisions_events import classify_decisions_events_jsonl
from .classifiers.handoff_events import classify_handoff_events_jsonl
from .classifiers.meta import classify_meta_json
from .classifiers.mission_events import classify_mission_events_jsonl
from .classifiers.status_events import classify_status_events_jsonl
from .classifiers.status_json import classify_status_json
from .classifiers.wp_files import classify_wp_files
from .identity_adapter import (
    identity_state_to_findings,
)
from .models import AuditOptions, MissionAuditResult, MissionFinding, RepoAuditReport


# ---------------------------------------------------------------------------
# Private: mission filter resolution
# ---------------------------------------------------------------------------


def _resolve_mission_filter(
    handle: str | None,
    repo_root: Path,
    scan_root: Path,
) -> frozenset[Path] | None:
    """Return the set of allowed directories for ``--mission`` scoping, or None for all.

    If *handle* is None, returns None — meaning all missions are scanned.

    If *handle* is provided, ``resolve_mission()`` is called against *repo_root*
    (which expects ``kitty-specs/`` to live there).  If the resolved slug
    corresponds to an existing directory under *scan_root*, a singleton
    ``frozenset`` is returned.  If the candidate directory is absent under
    *scan_root* (e.g. fixture-dir mode with a missing mission), an empty
    ``frozenset`` is returned so the scan yields an empty report.

    Raises:
        AmbiguousHandleError: The handle matches more than one mission.
        MissionNotFoundError: The handle matches no mission.

    Note: these exceptions propagate up to the CLI layer, which formats them
    as structured errors.
    """
    if handle is None:
        return None  # no filter: scan everything

    resolved = resolve_mission(handle, repo_root)
    candidate = scan_root / resolved.mission_slug
    if candidate.is_dir():
        return frozenset({candidate})
    # Candidate not found under scan_root (fixture-dir mismatch).
    return frozenset()


# ---------------------------------------------------------------------------
# Private: per-mission scan loop
# ---------------------------------------------------------------------------


def _scan_missions(
    scan_root: Path,
    allowed_dirs: frozenset[Path] | None,
    identity_index: dict[str, Any],
) -> list[MissionAuditResult]:
    """Walk *scan_root* and classify each mission directory.

    Args:
        scan_root: Directory to walk (usually ``repo_root / "kitty-specs"``).
        allowed_dirs: When not None, only directories in this set are processed.
            Pass ``frozenset()`` to produce an empty scan result.
        identity_index: Mapping of ``{mission_slug: IdentityState}`` built from
            ``audit_repo()``.  Used to call ``identity_state_to_findings()``
            without re-reading ``meta.json`` for each mission.

    Returns:
        List of :class:`~specify_cli.audit.models.MissionAuditResult`, one per
        directory, in lexicographic order of directory name.  Each result's
        findings are sorted by ``(artifact_path, code)``.
    """
    if not scan_root.exists():
        return []

    try:
        candidates = sorted(scan_root.iterdir(), key=lambda p: p.name)
    except OSError:
        return []

    results: list[MissionAuditResult] = []

    for candidate in candidates:
        if not candidate.is_dir():
            continue

        if allowed_dirs is not None and candidate not in allowed_dirs:
            continue

        identity_state = identity_index.get(candidate.name)

        # Collect findings from all 7 classifiers in the documented order.
        all_findings: list[MissionFinding] = []

        # 1. meta.json
        all_findings.extend(classify_meta_json(candidate))

        # 2. status.events.jsonl — returns (findings, has_corrupt_jsonl)
        findings_events, has_corrupt = classify_status_events_jsonl(candidate)
        all_findings.extend(findings_events)

        # 3. status.json — skip drift check if events are corrupt
        all_findings.extend(classify_status_json(candidate, skip_drift=has_corrupt))

        # 4. mission-events.jsonl
        all_findings.extend(classify_mission_events_jsonl(candidate))

        # 5. decisions/events.jsonl
        all_findings.extend(classify_decisions_events_jsonl(candidate))

        # 6. handoff/events.jsonl
        all_findings.extend(classify_handoff_events_jsonl(candidate))

        # 7. WP*.md frontmatter
        all_findings.extend(classify_wp_files(candidate))

        # 8. Identity-state adapter (only when identity data is available)
        if identity_state is not None:
            all_findings.extend(identity_state_to_findings(identity_state, candidate))

        # Sort by (artifact_path, code) for determinism before constructing the result.
        sorted_findings = sorted(all_findings, key=lambda f: (f.artifact_path, f.code))

        results.append(
            MissionAuditResult(
                mission_slug=candidate.name,
                mission_dir=candidate,
                findings=sorted_findings,
            )
        )

    return results


# ---------------------------------------------------------------------------
# Private: repo-level finding computation (slug-attributed)
# ---------------------------------------------------------------------------


def _compute_repo_findings_by_slug(
    repo_root: Path,
    identity_states: list[IdentityState],
    mission_results: list[MissionAuditResult],
) -> dict[str, list[MissionFinding]]:
    """Compute cross-mission (repo-level) findings, attributed by slug.

    Calls the three repo-level identity functions and returns a dict mapping
    each mission slug to any findings that belong to that mission.

    Three sources:
    - Duplicate 3-digit numeric prefixes (``DUPLICATE_PREFIX`` warning)
    - Ambiguous selector handles (``AMBIGUOUS_SELECTOR`` warning)
    - Duplicate ``mission_id`` values (``DUPLICATE_MISSION_ID`` error)

    All three identity functions use *repo_root* (not ``scan_root``) because
    they internally append ``/kitty-specs``.

    The adapter functions each emit one finding *per member* of a duplicate
    group. We attribute each finding to the correct mission by re-running the
    adapters and tracking which state generated which finding.

    Args:
        repo_root: Repository root.
        identity_states: All ``IdentityState`` objects from ``audit_repo()``.
        mission_results: Per-mission results (used to build ``slug_to_dir``).

    Returns:
        Dict mapping ``{mission_slug: [MissionFinding, ...]}`` for all
        missions that have any repo-level findings.
    """
    prefix_groups = find_duplicate_prefixes(repo_root)
    selector_groups = find_ambiguous_selectors(identity_states)
    slug_to_dir = {r.mission_slug: r.mission_dir for r in mission_results}

    attributed: dict[str, list[MissionFinding]] = {}

    # --- DUPLICATE_PREFIX: one finding per state in each prefix group -----------
    for prefix, states in prefix_groups.items():
        if len(states) < 2:
            continue
        all_slugs = sorted(s.slug for s in states)
        for state in states:
            other_slugs = ", ".join(s for s in all_slugs if s != state.slug)
            finding = MissionFinding(
                code="DUPLICATE_PREFIX",
                severity=_slug_to_finding_severity("DUPLICATE_PREFIX"),
                artifact_path="meta.json",
                detail=f"prefix {prefix!r} shared with: {other_slugs}",
            )
            if state.slug in slug_to_dir:
                attributed.setdefault(state.slug, []).append(finding)

    # --- AMBIGUOUS_SELECTOR: one finding per state in each selector group -------
    for handle, states in selector_groups.items():
        if len(states) < 2:
            continue
        all_slugs = sorted(s.slug for s in states)
        for state in states:
            other_slugs = ", ".join(s for s in all_slugs if s != state.slug)
            finding = MissionFinding(
                code="AMBIGUOUS_SELECTOR",
                severity=_slug_to_finding_severity("AMBIGUOUS_SELECTOR"),
                artifact_path="meta.json",
                detail=f"handle {handle!r} also matches: {other_slugs}",
            )
            if state.slug in slug_to_dir:
                attributed.setdefault(state.slug, []).append(finding)

    # --- DUPLICATE_MISSION_ID: one finding per mission sharing the same ID ------
    from collections import defaultdict

    by_id: dict[str, list[IdentityState]] = defaultdict(list)
    for state in identity_states:
        if state.mission_id is not None:
            by_id[state.mission_id].append(state)

    for mission_id, group in by_id.items():
        if len(group) < 2:
            continue
        all_slugs = sorted(s.slug for s in group)
        for state in group:
            other_slugs = ", ".join(s for s in all_slugs if s != state.slug)
            finding = MissionFinding(
                code="DUPLICATE_MISSION_ID",
                severity=_slug_to_finding_severity("DUPLICATE_MISSION_ID"),
                artifact_path="meta.json",
                detail=f"mission_id {mission_id!r} also used by: {other_slugs}",
            )
            if state.slug in slug_to_dir:
                attributed.setdefault(state.slug, []).append(finding)

    return attributed


def _slug_to_finding_severity(code: str) -> Any:
    """Return the severity for a repo-level finding code."""
    from .models import Severity

    _MAP = {
        "DUPLICATE_PREFIX": Severity.WARNING,
        "AMBIGUOUS_SELECTOR": Severity.WARNING,
        "DUPLICATE_MISSION_ID": Severity.ERROR,
    }
    return _MAP.get(code, Severity.WARNING)


def _compute_repo_findings(
    repo_root: Path,
    identity_states: list[IdentityState],
    mission_results: list[MissionAuditResult],
) -> list[MissionFinding]:
    """Compute cross-mission (repo-level) findings as a flat list.

    This thin wrapper calls ``_compute_repo_findings_by_slug`` and flattens
    the result.  Used in the public API signature described in the WP spec.
    """
    by_slug = _compute_repo_findings_by_slug(repo_root, identity_states, mission_results)
    return [f for findings in by_slug.values() for f in findings]


def _merge_repo_findings(
    mission_results: list[MissionAuditResult],
    repo_findings: list[MissionFinding],
) -> list[MissionAuditResult]:
    """Attach repo-level findings to the appropriate per-mission result.

    NOTE: This function exists to satisfy the WP spec API contract.  The
    actual attribution is performed inside ``run_audit()`` via
    ``_compute_repo_findings_by_slug()``, which returns slug-keyed findings.
    When called from ``run_audit()`` the ``repo_findings`` list passed here
    will be empty (findings are merged directly).  When called externally
    with a non-empty list, findings are distributed using a slug-match
    heuristic against the finding ``detail`` field.

    Args:
        mission_results: Per-mission results.
        repo_findings: Flat list of repo-level findings to distribute.

    Returns:
        The same list of ``MissionAuditResult`` objects, modified in place.
    """
    # When called from run_audit(), repo_findings is always empty because
    # attribution is already handled by _compute_repo_findings_by_slug().
    # This function is kept for API contract compliance and external use.
    if not repo_findings:
        return mission_results

    by_slug = {r.mission_slug: r for r in mission_results}
    for finding in repo_findings:
        detail = finding.detail or ""
        matched = False
        for slug, result in by_slug.items():
            if slug in detail:
                result.findings.append(finding)
                result.findings.sort(key=lambda f: (f.artifact_path, f.code))
                matched = True
                break
        if not matched:
            for result in by_slug.values():
                result.findings.append(finding)
                result.findings.sort(key=lambda f: (f.artifact_path, f.code))

    return mission_results


# ---------------------------------------------------------------------------
# Private: report assembly
# ---------------------------------------------------------------------------


def _build_report(mission_results: list[MissionAuditResult]) -> RepoAuditReport:
    """Assemble the final ``RepoAuditReport`` from per-mission results.

    Args:
        mission_results: Per-mission results, already merged with repo-level
            findings and individually sorted.

    Returns:
        :class:`~specify_cli.audit.models.RepoAuditReport` with:
        - ``missions`` sorted by ``mission_slug``
        - ``shape_counters`` built via ``Counter`` (serialised with sorted keys
          by ``RepoAuditReport.to_dict()``)
        - ``repo_summary`` with counts and severity breakdown
    """
    counter: Counter[str] = Counter(
        f.code for r in mission_results for f in r.findings
    )

    severity_counts: dict[str, int] = {"error": 0, "warning": 0, "info": 0}
    for r in mission_results:
        for f in r.findings:
            severity_counts[f.severity.value] += 1

    repo_summary: dict[str, Any] = {
        "total_missions": len(mission_results),
        "missions_with_errors": sum(1 for r in mission_results if r.has_errors),
        "missions_with_warnings": sum(1 for r in mission_results if r.has_warnings),
        "total_findings": sum(len(r.findings) for r in mission_results),
        "findings_by_severity": severity_counts,
    }

    return RepoAuditReport(
        missions=sorted(mission_results, key=lambda r: r.mission_slug),
        shape_counters=dict(counter),
        repo_summary=repo_summary,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_audit(options: AuditOptions) -> RepoAuditReport:
    """Run the full mission-state audit and return a ``RepoAuditReport``.

    This function is the sole public entry point for the audit engine.  It
    is completely read-only: no files are written, no processes are spawned,
    and no network calls are made.

    Args:
        options: Engine configuration.  ``scan_root`` defaults to
            ``options.repo_root / "kitty-specs"`` when None.

    Returns:
        :class:`~specify_cli.audit.models.RepoAuditReport` with all findings.

    Raises:
        AmbiguousHandleError: ``options.mission_filter`` matches > 1 mission.
        MissionNotFoundError: ``options.mission_filter`` matches 0 missions.
    """
    scan_root = options.scan_root or (options.repo_root / "kitty-specs")

    # CRITICAL: identity functions (audit_repo, find_duplicate_prefixes) take
    # repo_root and internally append /kitty-specs.  They must NOT receive
    # scan_root, which would cause them to look for scan_root/kitty-specs —
    # a path that does not exist — and silently return zero identity states.
    identity_states = audit_repo(options.repo_root)
    identity_index: dict[str, Any] = {s.slug: s for s in identity_states}

    # Mission filter: resolve handle → allowed_dirs set (may raise on bad handle)
    allowed_dirs = _resolve_mission_filter(
        options.mission_filter, options.repo_root, scan_root
    )

    # Per-mission classification
    mission_results = _scan_missions(scan_root, allowed_dirs, identity_index)

    # Repo-level findings with explicit slug attribution
    attributed = _compute_repo_findings_by_slug(
        options.repo_root, identity_states, mission_results
    )

    # Merge attributed repo-level findings into per-mission results
    if attributed:
        by_slug = {r.mission_slug: r for r in mission_results}
        for slug, findings in attributed.items():
            if slug in by_slug:
                by_slug[slug].findings.extend(findings)
                by_slug[slug].findings.sort(key=lambda f: (f.artifact_path, f.code))

    # Build and return the final report
    return _build_report(mission_results)
