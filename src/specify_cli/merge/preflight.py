"""Merge preflight checks for target branch safety.

Mission #2057 (decompose ``cli/commands/merge.py``) — IC-05 / WP05 relocated the
git / target-branch / mission-branch / canonical-status / review-artifact /
hollow-review preflights here (the historical home of the target-sync
remediation). One-way import: this module never imports the command shim.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import typer

from specify_cli import __version__ as SPEC_KITTY_VERSION
from specify_cli.cli.helpers import console
from specify_cli.core.git_ops import run_command
from specify_cli.core.git_preflight import (
    build_git_preflight_failure_payload,
    run_git_preflight,
)
from specify_cli.merge._constants import (
    HollowReviewWarnings,
    MissionBranchBlocker,
    _STATUS_EVENTS_FILENAME,
    _STATUS_FILENAME,
)
from specify_cli.merge.git_probes import _has_branch_ref
from specify_cli.merge.state import load_state
from specify_cli.post_merge.review_artifact_consistency import (
    format_review_artifact_finding,
    review_artifact_finding_diagnostic,
    run_review_artifact_consistency_preflight,
)
from specify_cli.status import REVIEWER_SELF_APPROVAL

if TYPE_CHECKING:
    from specify_cli.merge.push_preflight import TargetBranchSyncStatus

_PUSH_PREFLIGHT_EXPORTS = {
    "TargetBranchRefreshStatus",
    "TargetBranchSyncState",
    "TargetBranchSyncStatus",
    "inspect_target_branch_sync",
    "refresh_target_branch_tracking_ref",
}


def __getattr__(name: str) -> Any:
    """Lazily expose moved publish-layer symbols for transition compatibility."""
    if name in _PUSH_PREFLIGHT_EXPORTS:
        from specify_cli.merge import push_preflight

        return getattr(push_preflight, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def focused_pr_branch_name(mission_slug: str, target_branch: str) -> str:
    """Return a deterministic branch name for non-destructive recovery."""
    safe_target = target_branch.replace("/", "-")
    return f"kitty/pr/{mission_slug}-to-{safe_target}"


def target_branch_sync_remediation(
    status: TargetBranchSyncStatus,
    *,
    mission_slug: str | None,
    mission_branch: str | None = None,
    mission_id: str | None = None,
) -> list[str]:
    """Build actionable, non-destructive remediation diagnostics.

    The focused-PR recovery source branch prefers the recorded
    ``mission_branch`` (``lanes.json.mission_branch``) verbatim. When it is
    absent the canonical branch is composed via the fail-closed WP01 seam
    :func:`mission_branch_name_required`, NOT a bare ``kitty/mission-<slug>``
    f-string that drops the ``-<mid8>`` disambiguator / keeps a stale ``NNN-``
    prefix and so names a never-created branch (#1978).
    """
    tracking_branch = status.tracking_branch or f"origin/{status.target_branch}"
    lines = [
        (
            f"Local target branch '{status.target_branch}' is {status.state} "
            f"relative to '{tracking_branch}' "
            f"({status.ahead_count} ahead, {status.behind_count} behind)."
        ),
        "Spec Kitty stopped before mutating merge state or reconstructing branches.",
        f"Refresh remote refs: git fetch origin {status.target_branch}",
        (
            "Inspect differences: "
            f"git log --oneline --left-right --cherry-pick {status.target_branch}...{tracking_branch}"
        ),
        (
            "Inspect changed paths: "
            f"git diff --name-only {tracking_branch}...{status.target_branch}"
        ),
    ]

    if status.state in {"ahead", "diverged"}:
        lines.extend(
            [
                (
                    "Recommended: use the focused PR path unless you verified every ahead "
                    f"commit belongs on '{status.target_branch}' now."
                ),
                (
                    f"Do not run 'git push origin {status.target_branch}' just to satisfy "
                    "this preflight; local target commits may include orchestration history "
                    "or unrelated missions."
                ),
                (
                    f"Only direct-push '{status.target_branch}' after reviewing the ahead "
                    "commits and changed paths."
                ),
            ]
        )
    elif status.state == "behind":
        lines.append(
            f"Recommended: update local '{status.target_branch}' from '{tracking_branch}' "
            "after reviewing remote-only commits; do not push the local target branch."
        )

    if mission_slug:
        from specify_cli.lanes.branch_naming import mission_branch_name_required

        focused_branch = focused_pr_branch_name(mission_slug, status.target_branch)
        source_branch = mission_branch or mission_branch_name_required(
            mission_slug, mission_id
        )
        lines.extend(
            [
                (
                    "Focused PR path: "
                    f"git switch -c {focused_branch} {source_branch}"
                ),
                f"Then push it: git push -u origin {focused_branch}",
                f"Open a PR from {focused_branch} into {status.target_branch}.",
            ]
        )
    else:
        lines.append(
            "If local-only commits are intentional, preserve them on a new PR branch before retrying."
        )

    lines.append("Do not use reset, rebase, or force-push as part of this preflight remediation.")
    return lines


def _check_mission_branch(
    mission_slug: str,
    repo_root: Path,
    *,
    expected_branch: str | None = None,
    mission_id: str | None = None,
) -> tuple[bool, MissionBranchBlocker | None]:
    """Check whether the expected mission branch exists locally.

    Dry-run and real merge both use this as a read-only preflight. Missing
    branches are reported as structured blockers; this function never creates
    the branch.

    When ``expected_branch`` is not supplied (no recorded
    ``lanes.json.mission_branch``), the branch to CHECK is RESOLVED via the WP01
    seam :func:`resolve_branch_name` — the canonical-first / legacy-failover
    resolver (FR-004) — rather than a bare ``kitty/mission-<slug>`` f-string. The
    f-string drops the ``-<mid8>`` disambiguator and never strips a stale ``NNN-``
    prefix, so it mis-targeted the never-created branch and falsely reported it
    missing (#1978). ``resolve_branch_name`` keeps that #1978 fix intact for
    canonical/embedded slugs (no warning), failovers to the legacy ``NNN-`` branch
    with a one-shot deprecation warning, and still raises
    :class:`BranchIdentityUnresolved` for a genuinely-unresolvable modern slug
    (fail-closed preserved).
    """
    from specify_cli.lanes.branch_naming import resolve_branch_name

    expected_branch = expected_branch or resolve_branch_name(
        mission_slug, mission_id=mission_id
    )
    if _has_branch_ref(repo_root, expected_branch):
        return True, None

    retcode, stdout, _stderr = run_command(
        ["git", "rev-parse", "HEAD"],
        capture=True,
        check_return=False,
        cwd=repo_root,
    )
    base_sha = stdout.strip()[:12] if retcode == 0 else "<base-commit>"

    blocker_payload: MissionBranchBlocker = {
        "ready": False,
        "blocker": "missing_mission_branch",
        "expected_branch": expected_branch,
        "remediation": f"git branch {expected_branch} {base_sha}",
    }
    return False, blocker_payload


def _enforce_planning_artifact_target_branch(repo_root: Path, target_branch: str) -> None:
    """Planning-only closeout writes directly to the target branch."""

    retcode, stdout, _stderr = run_command(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture=True,
        check_return=False,
        cwd=repo_root,
    )
    current_branch = stdout.strip() if retcode == 0 else ""
    if current_branch == target_branch:
        return

    current_label = current_branch or "detached HEAD"
    console.print(
        "[red]Error:[/red] Planning-artifact-only merge must run on "
        f"target branch {target_branch}, not {current_label}."
    )
    raise typer.Exit(1)


def _enforce_git_preflight(repo_root: Path, *, json_output: bool) -> None:
    """Run git preflight checks and stop early with deterministic remediation."""
    if not (repo_root / ".git").exists():
        return

    preflight = run_git_preflight(repo_root, check_worktree_list=True)
    if preflight.passed:
        return

    payload = build_git_preflight_failure_payload(preflight, command_name="spec-kitty merge")
    if json_output:
        enriched = dict(payload)
        enriched["spec_kitty_version"] = SPEC_KITTY_VERSION
        print(json.dumps(enriched))
    else:
        console.print(f"[red]Error:[/red] {payload['error']}")
        for cmd in payload.get("remediation", []):
            console.print(f"  - Run: {cmd}")
    raise typer.Exit(1)


def _validate_target_branch(
    repo_root: Path,
    mission_slug: str | None,
    target_branch: str,
    target_source: str | None,
    *,
    json_output: bool,
) -> None:
    ret_local, _, _ = run_command(
        ["git", "rev-parse", "--verify", f"refs/heads/{target_branch}"],
        capture=True,
        check_return=False,
        cwd=repo_root,
    )
    if ret_local == 0:
        return

    ret_remote, _, _ = run_command(
        ["git", "rev-parse", "--verify", f"refs/remotes/origin/{target_branch}"],
        capture=True,
        check_return=False,
        cwd=repo_root,
    )
    if ret_remote == 0:
        return

    if target_source == "meta.json" and mission_slug:
        error_msg = f"Target branch '{target_branch}' (from meta.json) does not exist locally or on origin. Check kitty-specs/{mission_slug}/meta.json."
    elif target_source == "primary_branch" and mission_slug:
        error_msg = f"Target branch '{target_branch}' (resolved as primary branch) does not exist locally or on origin. Check kitty-specs/{mission_slug}/meta.json."
    else:
        error_msg = f"Target branch '{target_branch}' does not exist locally or on origin."

    if json_output:
        print(json.dumps({"spec_kitty_version": SPEC_KITTY_VERSION, "error": error_msg}))
    else:
        console.print(f"[red]Error:[/red] {error_msg}")
    raise typer.Exit(1)


def _print_remediation_lines(remediation: object) -> None:
    """Print remediation lines from a ``dict[str, object]`` payload value.

    The payload is typed ``dict[str, object]`` so the ``remediation`` value is
    ``object`` at the call site; normalize to a list of strings before printing
    (behavior-preserving — the value is always a ``list[str]``).
    """
    lines = remediation if isinstance(remediation, list) else [str(remediation)]
    for line in lines:
        console.print(f"  - {line}")


def _effective_push_requested(
    repo_root: Path,
    mission_id: str,
    requested_push: bool,
) -> bool:
    """Return persisted push intent for resumptions, otherwise current CLI intent."""
    state = load_state(repo_root, mission_id)
    if state is not None:
        return bool(state.push_requested)
    return requested_push


def _enforce_canonical_status_history(
    *,
    feature_dir: Path,
    mission_slug: str,
    wp_ids: list[str],
) -> None:
    """Refuse to merge missions whose canonical status log is bootstrap-only.

    A bootstrap-only log is a ``status.events.jsonl`` that contains
    nothing but forced ``planned -> planned`` entries emitted by
    ``finalize-tasks``. When the mission carries work packages that
    must have advanced past planned for merge to make sense, the log
    is an unreliable source of truth and downstream replay (TeamSpace
    rebuild, dashboard refresh) will reset every WP to planned. We
    fail loudly with a remediation hint rather than ship in that
    state. See https://github.com/Priivacy-ai/spec-kitty/issues/1069.
    """
    from specify_cli.status import has_non_bootstrap_status_history

    if not wp_ids:
        return

    log_path = feature_dir / _STATUS_EVENTS_FILENAME
    if not log_path.exists():
        return

    if has_non_bootstrap_status_history(feature_dir):
        return

    console.print(
        "[red]Error:[/red] Canonical status history is bootstrap-only — the local "
        "event log cannot prove that WPs advanced past planned, so a merge would "
        "ship a mission whose downstream replay would regress every WP."
    )
    console.print(f"  Mission: {mission_slug}")
    console.print(f"  Event log: {log_path}")
    console.print(f"  Work packages requiring history: {', '.join(wp_ids)}")
    console.print(
        "  Remediation: re-run the per-WP `spec-kitty agent action review` and "
        "`spec-kitty agent action implement` flows so the canonical event log "
        "captures the real lane transitions before merging, or run the "
        "repair/replay tooling for this mission."
    )
    raise typer.Exit(1)


def _enforce_review_artifact_consistency(
    *,
    repo_root: Path,
    feature_dir: Path,
    mission_slug: str,
    wp_ids: list[str],
) -> None:
    """Block terminal signoff when the latest review artifact is rejected."""
    preflight = run_review_artifact_consistency_preflight(feature_dir, wp_ids=wp_ids)
    if preflight.passed:
        return
    findings = list(preflight.findings)

    console.print("[red]Error:[/red] Review artifact consistency gate failed.")
    for finding in findings:
        diagnostic = review_artifact_finding_diagnostic(
            finding,
            repo_root=repo_root,
        )
        console.print(
            f"  - {format_review_artifact_finding(finding, repo_root=repo_root)}"
        )
        console.print(f"    diagnostic_code: {diagnostic['diagnostic_code']}")
        console.print(
            f"    branch_or_work_package: {diagnostic['branch_or_work_package']}"
        )
        console.print(
            f"    violated_invariant: {diagnostic['violated_invariant']}"
        )
        console.print(
            f"    latest_review_cycle_path: {diagnostic['latest_review_cycle_path']}"
        )
        if "latest_review_cycle_verdict" in diagnostic:
            console.print(
                f"    latest_review_cycle_verdict: {diagnostic['latest_review_cycle_verdict']}"
            )
        if "schema_error" in diagnostic:
            console.print(f"    schema_error: {diagnostic['schema_error']}")
        remediation = diagnostic.get("remediation", [])
        if not isinstance(remediation, list):
            remediation = [str(remediation)]
        for line in remediation:
            console.print(f"    remediation: {line}")
    console.print(
        f"  Mission: {mission_slug}"
    )
    raise typer.Exit(1)


def _collect_force_count_warnings(
    feature_dir: Path,
    wp_set: set[str],
    warnings: HollowReviewWarnings,
) -> None:
    """Append force_count>=2 warnings from ``status.json`` (WP05 split helper).

    Behavior-preserving extraction of the status-snapshot scan formerly inlined
    in ``_collect_hollow_review_warnings`` (FR-005, keeps CC <= 15).
    """
    status_path = feature_dir / _STATUS_FILENAME
    if not status_path.exists():
        return
    try:
        status = json.loads(status_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        status = {}
    work_packages = status.get("work_packages", {}) if isinstance(status, dict) else {}
    if not isinstance(work_packages, dict):
        return
    for wp_id in sorted(wp_set):
        wp_state = work_packages.get(wp_id, {})
        if not isinstance(wp_state, dict):
            continue
        try:
            force_count = int(wp_state.get("force_count", 0))
        except (TypeError, ValueError):
            force_count = 0
        if force_count >= 2:
            warnings.setdefault(wp_id, []).append(f"force_count={force_count}")


def _collect_self_approval_warnings(
    feature_dir: Path,
    wp_set: set[str],
    warnings: HollowReviewWarnings,
) -> None:
    """Append ReviewerSelfApproval warnings from the event log (WP05 split helper).

    Behavior-preserving extraction of the event-log scan formerly inlined in
    ``_collect_hollow_review_warnings`` (FR-005, keeps CC <= 15).
    """
    events_path = feature_dir / _STATUS_EVENTS_FILENAME
    if not events_path.exists():
        return
    try:
        raw_lines = events_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        raw_lines = []
    for raw_line in raw_lines:
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or event.get("event_type") != REVIEWER_SELF_APPROVAL:
            continue
        payload = event.get("payload", {})
        if not isinstance(payload, dict):
            continue
        wp_id = str(payload.get("wp_id") or "")
        if wp_id not in wp_set:
            continue
        intended = str(payload.get("intended_reviewer") or "unknown")
        actor = str(payload.get("implementing_actor") or "unknown")
        reason = str(payload.get("failure_reason") or "reviewer_failed")
        warnings.setdefault(wp_id, []).append(
            f"ReviewerSelfApproval ({intended} failed: {reason}; {actor} self-reviewed)"
        )


def _collect_hollow_review_warnings(feature_dir: Path, wp_ids: list[str]) -> HollowReviewWarnings:
    """Return WPs whose approval history indicates missing independent review.

    Delegates to two focused scans (status-snapshot force_count + event-log
    ReviewerSelfApproval). The split keeps each helper <= 15 CC (FR-005) while
    preserving the exact warning buckets and emission order.
    """
    warnings: HollowReviewWarnings = {}
    wp_set = set(wp_ids)
    _collect_force_count_warnings(feature_dir, wp_set, warnings)
    _collect_self_approval_warnings(feature_dir, wp_set, warnings)
    return warnings


def _warn_or_confirm_hollow_reviews(
    *,
    feature_dir: Path,
    wp_ids: list[str],
    assume_yes: bool,
) -> None:
    warnings = _collect_hollow_review_warnings(feature_dir, wp_ids)
    if not warnings:
        return

    console.print("\n[bold yellow]MERGE WARNING: Hollow reviews detected[/bold yellow]\n")
    console.print("The following WPs were approved without clear independent review:")
    for wp_id in sorted(warnings):
        console.print(f"  {wp_id}: {' + '.join(warnings[wp_id])}")
    console.print()
    console.print("These WPs may have been approved by the implementing agent, not an independent reviewer.")
    console.print("Consider re-reviewing before merge.\n")

    if assume_yes or not sys.stdin.isatty():
        console.print("[yellow]Proceeding without interactive confirmation.[/yellow]")
        return

    if not typer.confirm("Proceed?", default=False):
        raise typer.Exit(1)
