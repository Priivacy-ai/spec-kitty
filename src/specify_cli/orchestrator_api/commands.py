"""Machine-contract API commands for external orchestrators.

All commands emit a single JSON object to stdout via the canonical envelope.
Non-zero exit on any failure. The --json flag is always available (and
orchestrator-api is JSON-first by design; prose output is secondary).

Error codes used:
  POLICY_METADATA_REQUIRED    -- --policy missing on a run-affecting command
  POLICY_VALIDATION_FAILED    -- policy JSON invalid or contains secrets
  FEATURE_NOT_FOUND           -- feature slug does not resolve to a kitty-specs dir
  WP_NOT_FOUND                -- WP ID does not exist in feature
  TRANSITION_REJECTED         -- transition not allowed by state machine
  WP_ALREADY_CLAIMED          -- WP claimed by a different actor
  FEATURE_NOT_READY           -- not all WPs done (for accept-feature)
  PREFLIGHT_FAILED            -- preflight checks failed (for merge-feature)
  CONTRACT_VERSION_MISMATCH   -- provider version is below MIN_PROVIDER_VERSION
  UNSUPPORTED_STRATEGY        -- merge strategy not implemented
"""

from __future__ import annotations

import json
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import typer

from specify_cli.git.commit_helpers import safe_commit
from specify_cli.merge import run_preflight, get_merge_order

from .envelope import (
    CONTRACT_VERSION,
    MIN_PROVIDER_VERSION,
    make_envelope,
    parse_and_validate_policy,
    policy_to_dict,
)

app = typer.Typer(
    name="orchestrator-api",
    help="Machine-contract API for external orchestrators (JSON-first)",
    no_args_is_help=True,
)

# Lanes that require --policy (run-affecting)
_RUN_AFFECTING_LANES = frozenset(["claimed", "in_progress", "for_review"])


def _emit(envelope: dict[str, Any]) -> None:
    """Print canonical JSON envelope to stdout."""
    print(json.dumps(envelope))


def _fail(command: str, error_code: str, message: str, data: dict[str, Any] | None = None) -> None:
    """Print failure envelope and exit non-zero."""
    envelope = make_envelope(
        command=command,
        success=False,
        data=data or {"message": message},
        error_code=error_code,
    )
    _emit(envelope)
    raise typer.Exit(1)


def _get_main_repo_root() -> Path:
    """Resolve main repository root from current working directory."""
    from specify_cli.core.paths import locate_project_root

    root = locate_project_root()
    if root is None:
        # Fall back to cwd
        return Path.cwd()
    return root


def _resolve_feature_dir(main_repo_root: Path, feature_slug: str) -> Path | None:
    """Return the feature directory if it exists, else None."""
    feature_dir = main_repo_root / "kitty-specs" / feature_slug
    if not feature_dir.exists():
        return None
    return feature_dir


def _get_last_actor(feature_dir: Path, wp_id: str) -> str | None:
    """Get the actor of the most recent event for this WP."""
    from specify_cli.status.store import read_events

    events = read_events(feature_dir)
    for event in reversed(events):
        if event.wp_id == wp_id:
            return event.actor
    return None


_WP_ID_RE = re.compile(r"^(WP\d+)")


def _extract_wp_id(stem: str) -> str | None:
    """Extract canonical WP ID from a task filename stem.

    Examples:
        "WP07"                         -> "WP07"
        "WP07-adapter-implementations" -> "WP07"
        "README"                       -> None
    """
    m = _WP_ID_RE.match(stem)
    return m.group(1) if m else None


def _resolve_wp_file(tasks_dir: Path, wp_id: str) -> Path | None:
    """Locate the task file for a WP, accepting suffixed filenames.

    Checks for an exact match first (WP07.md), then falls back to any
    file whose name starts with '<wp_id>-' (e.g. WP07-adapter-implementations.md).
    Returns the first match found, or None if no file exists.
    """
    exact = tasks_dir / f"{wp_id}.md"
    if exact.exists():
        return exact
    for p in sorted(tasks_dir.glob(f"{wp_id}-*.md")):
        return p
    return None


# ── Command 1: contract-version ────────────────────────────────────────────


@app.command(name="contract-version")
def contract_version(
    provider_version: str = typer.Option(
        None,
        "--provider-version",
        help="Caller's provider version; returns CONTRACT_VERSION_MISMATCH if below minimum",
    ),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Output as JSON"),
) -> None:
    """Return the current API contract version.

    Pass --provider-version to check compatibility before running state-mutating commands.
    """
    cmd = "contract-version"

    if provider_version is not None:
        from packaging.version import Version, InvalidVersion

        try:
            if Version(provider_version) < Version(MIN_PROVIDER_VERSION):
                _fail(
                    cmd,
                    "CONTRACT_VERSION_MISMATCH",
                    f"Provider version {provider_version!r} is below minimum {MIN_PROVIDER_VERSION!r}",
                    {
                        "provider_version": provider_version,
                        "min_supported_provider_version": MIN_PROVIDER_VERSION,
                        "api_version": CONTRACT_VERSION,
                    },
                )
                return
        except InvalidVersion:
            _fail(
                cmd,
                "CONTRACT_VERSION_MISMATCH",
                f"Provider version {provider_version!r} is not a valid version string",
                {"provider_version": provider_version},
            )
            return

    envelope = make_envelope(
        command=cmd,
        success=True,
        data={
            "api_version": CONTRACT_VERSION,
            "min_supported_provider_version": MIN_PROVIDER_VERSION,
        },
    )
    _emit(envelope)


# ── Command 2: feature-state ────────────────────────────────────────────────


@app.command(name="feature-state")
def feature_state(
    feature: str = typer.Option(..., "--feature", help="Feature slug (e.g. 034-my-feature)"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Output as JSON"),
) -> None:
    """Return the full state of a feature (all WPs, lanes, dependencies)."""
    main_repo_root = _get_main_repo_root()
    feature_dir = _resolve_feature_dir(main_repo_root, feature)
    if feature_dir is None:
        _fail(
            "feature-state",
            "FEATURE_NOT_FOUND",
            f"Feature '{feature}' not found in kitty-specs/",
        )
        return

    from specify_cli.status.reducer import materialize
    from specify_cli.core.dependency_graph import build_dependency_graph

    snapshot = materialize(feature_dir)
    dep_graph = build_dependency_graph(feature_dir)

    # Build the full WP set from task files + dep graph + snapshot
    # so that untouched WPs (no events yet) still appear as "planned"
    tasks_dir = feature_dir / "tasks"
    task_file_wp_ids: set[str] = set()
    if tasks_dir.exists():
        for p in tasks_dir.iterdir():
            if p.suffix == ".md":
                wp_id = _extract_wp_id(p.stem)
                if wp_id is not None:
                    task_file_wp_ids.add(wp_id)

    all_wp_ids = task_file_wp_ids | set(dep_graph.keys()) | set(snapshot.work_packages.keys())

    work_packages = []
    for wp_id in sorted(all_wp_ids):
        wp_state = snapshot.work_packages.get(wp_id, {})
        work_packages.append(
            {
                "wp_id": wp_id,
                "lane": wp_state.get("lane", "planned"),
                "dependencies": dep_graph.get(wp_id, []),
                "last_actor": wp_state.get("last_actor"),
            }
        )

    envelope = make_envelope(
        command="feature-state",
        success=True,
        data={
            "feature_slug": feature,
            "summary": snapshot.summary,
            "work_packages": work_packages,
        },
    )
    _emit(envelope)


# ── Command 3: list-ready ──────────────────────────────────────────────────


@app.command(name="list-ready")
def list_ready(
    feature: str = typer.Option(..., "--feature", help="Feature slug"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Output as JSON"),
) -> None:
    """List WPs that are ready to start (planned and all deps done)."""
    main_repo_root = _get_main_repo_root()
    feature_dir = _resolve_feature_dir(main_repo_root, feature)
    if feature_dir is None:
        _fail(
            "list-ready",
            "FEATURE_NOT_FOUND",
            f"Feature '{feature}' not found in kitty-specs/",
        )
        return

    from specify_cli.status.reducer import materialize
    from specify_cli.core.dependency_graph import build_dependency_graph

    snapshot = materialize(feature_dir)
    dep_graph = build_dependency_graph(feature_dir)
    wp_states = snapshot.work_packages

    ready_wps = []
    for wp_id, deps in dep_graph.items():
        wp_state = wp_states.get(wp_id, {})
        lane = wp_state.get("lane", "planned")
        if lane != "planned":
            continue

        # Check all dependencies are done
        all_deps_done = all(wp_states.get(dep, {}).get("lane") == "done" for dep in deps)

        recommended_base = deps[-1] if deps else None

        ready_wps.append(
            {
                "wp_id": wp_id,
                "lane": lane,
                "dependencies_satisfied": all_deps_done,
                "recommended_base": recommended_base,
            }
        )

    # Filter to only truly ready ones
    ready_wps = [wp for wp in ready_wps if wp["dependencies_satisfied"]]

    envelope = make_envelope(
        command="list-ready",
        success=True,
        data={
            "feature_slug": feature,
            "ready_work_packages": ready_wps,
        },
    )
    _emit(envelope)


# ── Command 4: start-implementation ────────────────────────────────────────


@app.command(name="start-implementation")
def start_implementation(
    feature: str = typer.Option(..., "--feature", help="Feature slug"),
    wp: str = typer.Option(..., "--wp", help="Work package ID (e.g. WP01)"),
    actor: str = typer.Option(..., "--actor", help="Actor identity"),
    policy: str = typer.Option(None, "--policy", help="Policy metadata JSON (required)"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Output as JSON"),
) -> None:
    """Composite transition: planned→claimed→in_progress (idempotent)."""
    cmd = "start-implementation"

    # Policy required
    if not policy:
        _fail(cmd, "POLICY_METADATA_REQUIRED", "--policy is required for start-implementation")
        return

    try:
        policy_obj = parse_and_validate_policy(policy)
    except ValueError as exc:
        _fail(cmd, "POLICY_VALIDATION_FAILED", str(exc))
        return

    policy_dict = policy_to_dict(policy_obj)

    main_repo_root = _get_main_repo_root()
    feature_dir = _resolve_feature_dir(main_repo_root, feature)
    if feature_dir is None:
        _fail(cmd, "FEATURE_NOT_FOUND", f"Feature '{feature}' not found in kitty-specs/")
        return

    wp_path = _resolve_wp_file(feature_dir / "tasks", wp)
    if wp_path is None:
        _fail(cmd, "WP_NOT_FOUND", f"Work package '{wp}' not found in {feature}")
        return

    from specify_cli.status.reducer import materialize
    from specify_cli.status.emit import emit_status_transition, TransitionError

    snapshot = materialize(feature_dir)
    wp_state = snapshot.work_packages.get(wp, {})
    current_lane = wp_state.get("lane", "planned")
    last_actor = _get_last_actor(feature_dir, wp)

    workspace_path = str(main_repo_root / ".worktrees" / f"{feature}-{wp}")
    prompt_path = str(wp_path)

    try:
        if current_lane == "planned":
            # Composite: planned → claimed → in_progress
            emit_status_transition(
                feature_dir,
                feature,
                wp,
                "claimed",
                actor,
                policy_metadata=policy_dict,
            )
            emit_status_transition(
                feature_dir,
                feature,
                wp,
                "in_progress",
                actor,
                workspace_context=workspace_path,
                execution_mode="worktree",
                policy_metadata=policy_dict,
            )
            from_lane_reported = "planned"
            no_op = False

        elif current_lane == "claimed":
            if last_actor is not None and last_actor != actor:
                _fail(
                    cmd,
                    "WP_ALREADY_CLAIMED",
                    f"WP {wp} is already claimed by '{last_actor}'",
                    {"claimed_by": last_actor, "requesting_actor": actor},
                )
                return
            emit_status_transition(
                feature_dir,
                feature,
                wp,
                "in_progress",
                actor,
                workspace_context=workspace_path,
                execution_mode="worktree",
                policy_metadata=policy_dict,
            )
            from_lane_reported = "claimed"
            no_op = False

        elif current_lane == "in_progress":
            if last_actor is not None and last_actor != actor:
                _fail(
                    cmd,
                    "WP_ALREADY_CLAIMED",
                    f"WP {wp} is already in_progress by '{last_actor}'",
                    {"claimed_by": last_actor, "requesting_actor": actor},
                )
                return
            # Idempotent success
            from_lane_reported = "in_progress"
            no_op = True

        else:
            _fail(
                cmd,
                "TRANSITION_REJECTED",
                f"WP {wp} is in '{current_lane}', cannot start implementation",
            )
            return

    except TransitionError as exc:
        _fail(cmd, "TRANSITION_REJECTED", str(exc))
        return

    envelope = make_envelope(
        command=cmd,
        success=True,
        data={
            "feature_slug": feature,
            "wp_id": wp,
            "from_lane": from_lane_reported,
            "to_lane": "in_progress",
            "workspace_path": workspace_path,
            "prompt_path": prompt_path,
            "policy_metadata_recorded": True,
            "no_op": no_op,
        },
    )
    _emit(envelope)


# ── Command 5: start-review ────────────────────────────────────────────────


@app.command(name="start-review")
def start_review(
    feature: str = typer.Option(..., "--feature", help="Feature slug"),
    wp: str = typer.Option(..., "--wp", help="Work package ID"),
    actor: str = typer.Option(..., "--actor", help="Actor identity"),
    policy: str = typer.Option(None, "--policy", help="Policy metadata JSON (required)"),
    review_ref: str = typer.Option(None, "--review-ref", help="Review feedback reference (required)"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Output as JSON"),
) -> None:
    """Transition a WP from for_review back to in_progress (reviewer rollback)."""
    cmd = "start-review"

    if not policy:
        _fail(cmd, "POLICY_METADATA_REQUIRED", "--policy is required for start-review")
        return

    if not review_ref:
        _fail(cmd, "TRANSITION_REJECTED", "--review-ref is required for start-review (for_review→in_progress guard)")
        return

    try:
        policy_obj = parse_and_validate_policy(policy)
    except ValueError as exc:
        _fail(cmd, "POLICY_VALIDATION_FAILED", str(exc))
        return

    policy_dict = policy_to_dict(policy_obj)

    main_repo_root = _get_main_repo_root()
    feature_dir = _resolve_feature_dir(main_repo_root, feature)
    if feature_dir is None:
        _fail(cmd, "FEATURE_NOT_FOUND", f"Feature '{feature}' not found in kitty-specs/")
        return

    wp_path = _resolve_wp_file(feature_dir / "tasks", wp)
    if wp_path is None:
        _fail(cmd, "WP_NOT_FOUND", f"Work package '{wp}' not found in {feature}")
        return

    from specify_cli.status.reducer import materialize
    from specify_cli.status.emit import emit_status_transition, TransitionError

    snapshot = materialize(feature_dir)
    wp_state = snapshot.work_packages.get(wp, {})
    from_lane = wp_state.get("lane", "planned")

    prompt_path = str(wp_path)

    try:
        emit_status_transition(
            feature_dir,
            feature,
            wp,
            "in_progress",
            actor,
            review_ref=review_ref,
            execution_mode="worktree",
            policy_metadata=policy_dict,
        )
    except TransitionError as exc:
        _fail(cmd, "TRANSITION_REJECTED", str(exc))
        return

    envelope = make_envelope(
        command=cmd,
        success=True,
        data={
            "feature_slug": feature,
            "wp_id": wp,
            "from_lane": from_lane,
            "to_lane": "in_progress",
            "prompt_path": prompt_path,
            "policy_metadata_recorded": True,
        },
    )
    _emit(envelope)


# ── Command 6: transition ──────────────────────────────────────────────────


@app.command(name="transition")
def transition(
    feature: str = typer.Option(..., "--feature", help="Feature slug"),
    wp: str = typer.Option(..., "--wp", help="Work package ID"),
    to: str = typer.Option(..., "--to", help="Target lane"),
    actor: str = typer.Option(..., "--actor", help="Actor identity"),
    note: str = typer.Option(None, "--note", help="Reason/note for the transition"),
    policy: str = typer.Option(None, "--policy", help="Policy metadata JSON (required for run-affecting lanes)"),
    force: bool = typer.Option(False, "--force", help="Force the transition"),
    review_ref: str = typer.Option(None, "--review-ref", help="Review reference"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Output as JSON"),
) -> None:
    """Emit a single lane transition for a WP."""
    cmd = "transition"

    from specify_cli.status.transitions import resolve_lane_alias

    to_lane = resolve_lane_alias(to)

    # Policy required for run-affecting lanes
    policy_dict: dict[str, Any] | None = None
    if to_lane in _RUN_AFFECTING_LANES:
        if not policy:
            _fail(
                cmd,
                "POLICY_METADATA_REQUIRED",
                f"--policy is required when transitioning to '{to_lane}'",
            )
            return
        try:
            policy_obj = parse_and_validate_policy(policy)
            policy_dict = policy_to_dict(policy_obj)
        except ValueError as exc:
            _fail(cmd, "POLICY_VALIDATION_FAILED", str(exc))
            return
    elif policy:
        # Optional policy for non-run-affecting lanes
        try:
            policy_obj = parse_and_validate_policy(policy)
            policy_dict = policy_to_dict(policy_obj)
        except ValueError as exc:
            _fail(cmd, "POLICY_VALIDATION_FAILED", str(exc))
            return

    main_repo_root = _get_main_repo_root()
    feature_dir = _resolve_feature_dir(main_repo_root, feature)
    if feature_dir is None:
        _fail(cmd, "FEATURE_NOT_FOUND", f"Feature '{feature}' not found in kitty-specs/")
        return

    wp_path = _resolve_wp_file(feature_dir / "tasks", wp)
    if wp_path is None:
        _fail(cmd, "WP_NOT_FOUND", f"Work package '{wp}' not found in {feature}")
        return

    from specify_cli.status.reducer import materialize
    from specify_cli.status.emit import emit_status_transition, TransitionError

    snapshot = materialize(feature_dir)
    wp_state = snapshot.work_packages.get(wp, {})
    from_lane = wp_state.get("lane", "planned")

    try:
        emit_status_transition(
            feature_dir,
            feature,
            wp,
            to_lane,
            actor,
            reason=note,
            force=force,
            review_ref=review_ref,
            execution_mode="worktree",
            policy_metadata=policy_dict,
        )
    except TransitionError as exc:
        _fail(cmd, "TRANSITION_REJECTED", str(exc))
        return

    envelope = make_envelope(
        command=cmd,
        success=True,
        data={
            "feature_slug": feature,
            "wp_id": wp,
            "from_lane": from_lane,
            "to_lane": to_lane,
            "policy_metadata_recorded": policy_dict is not None,
        },
    )
    _emit(envelope)


# ── Command 7: append-history ──────────────────────────────────────────────


@app.command(name="append-history")
def append_history(
    feature: str = typer.Option(..., "--feature", help="Feature slug"),
    wp: str = typer.Option(..., "--wp", help="Work package ID"),
    actor: str = typer.Option(..., "--actor", help="Actor identity"),
    note: str = typer.Option(..., "--note", help="History note to append"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Output as JSON"),
) -> None:
    """Append a history entry to a WP prompt file."""
    cmd = "append-history"

    main_repo_root = _get_main_repo_root()
    feature_dir = _resolve_feature_dir(main_repo_root, feature)
    if feature_dir is None:
        _fail(cmd, "FEATURE_NOT_FOUND", f"Feature '{feature}' not found in kitty-specs/")
        return

    wp_path = _resolve_wp_file(feature_dir / "tasks", wp)
    if wp_path is None:
        _fail(cmd, "WP_NOT_FOUND", f"Work package '{wp}' not found in {feature}")
        return

    from specify_cli.tasks_support import (
        split_frontmatter,
        build_document,
        append_activity_log,
    )

    raw = wp_path.read_text(encoding="utf-8")
    fm, body, padding = split_frontmatter(raw)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry_text = f"- [{timestamp}] {actor}: {note}"
    new_body = append_activity_log(body, entry_text)

    wp_path.write_text(build_document(fm, new_body, padding), encoding="utf-8")

    safe_commit(
        repo_path=main_repo_root,
        files_to_commit=[wp_path],
        commit_message=f"hist: append activity log entry for {feature}/{wp}",
        allow_empty=True,
    )

    entry_id = "hist-" + uuid.uuid4().hex

    envelope = make_envelope(
        command=cmd,
        success=True,
        data={
            "feature_slug": feature,
            "wp_id": wp,
            "history_entry_id": entry_id,
        },
    )
    _emit(envelope)


# ── Command 8: accept-feature ──────────────────────────────────────────────


@app.command(name="accept-feature")
def accept_feature(
    feature: str = typer.Option(..., "--feature", help="Feature slug"),
    actor: str = typer.Option(..., "--actor", help="Actor identity"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Output as JSON"),
) -> None:
    """Accept a feature after all WPs are done."""
    cmd = "accept-feature"

    main_repo_root = _get_main_repo_root()
    feature_dir = _resolve_feature_dir(main_repo_root, feature)
    if feature_dir is None:
        _fail(cmd, "FEATURE_NOT_FOUND", f"Feature '{feature}' not found in kitty-specs/")
        return

    from specify_cli.status.reducer import materialize
    from specify_cli.core.dependency_graph import build_dependency_graph

    snapshot = materialize(feature_dir)
    dep_graph = build_dependency_graph(feature_dir)

    # Check all WPs (from dep_graph) are done — include WPs with no events (implicitly planned)
    all_wp_ids = set(dep_graph.keys()) | set(snapshot.work_packages.keys())
    incomplete = [wp_id for wp_id in sorted(all_wp_ids) if snapshot.work_packages.get(wp_id, {}).get("lane") != "done"]
    if incomplete:
        _fail(
            cmd,
            "FEATURE_NOT_READY",
            f"Feature has {len(incomplete)} incomplete WP(s)",
            {"incomplete_wps": sorted(incomplete)},
        )
        return

    # Write acceptance record to meta.json
    import json as _json

    meta_path = feature_dir / "meta.json"
    meta: dict[str, Any] = {}
    if meta_path.exists():
        try:
            meta = _json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            meta = {}

    accepted_at = datetime.now(timezone.utc).isoformat()
    meta["accepted_at"] = accepted_at
    meta["accepted_by"] = actor
    meta_path.write_text(_json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")

    envelope = make_envelope(
        command=cmd,
        success=True,
        data={
            "feature_slug": feature,
            "accepted": True,
            "mode": "auto",
            "accepted_at": accepted_at,
        },
    )
    _emit(envelope)


# ── Command 9: merge-feature ───────────────────────────────────────────────


@app.command(name="merge-feature")
def merge_feature(
    feature: str = typer.Option(..., "--feature", help="Feature slug"),
    target: str = typer.Option("main", "--target", help="Target branch to merge into"),
    strategy: str = typer.Option("merge", "--strategy", help="Merge strategy: merge, squash, or rebase"),
    push: bool = typer.Option(False, "--push", help="Push target branch after merge"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Output as JSON"),
) -> None:
    """Run preflight checks then merge all WP branches into target."""
    cmd = "merge-feature"

    _SUPPORTED_STRATEGIES = frozenset(["merge", "squash", "rebase"])
    if strategy not in _SUPPORTED_STRATEGIES:
        _fail(
            cmd,
            "UNSUPPORTED_STRATEGY",
            f"Strategy '{strategy}' is not supported. Supported strategies: {sorted(_SUPPORTED_STRATEGIES)}",
            {"strategy": strategy, "supported": sorted(_SUPPORTED_STRATEGIES)},
        )
        return

    main_repo_root = _get_main_repo_root()
    feature_dir = _resolve_feature_dir(main_repo_root, feature)
    if feature_dir is None:
        _fail(cmd, "FEATURE_NOT_FOUND", f"Feature '{feature}' not found in kitty-specs/")
        return

    # Discover worktrees for this feature
    worktrees_root = main_repo_root / ".worktrees"
    wp_workspaces: list[tuple[Path, str, str]] = []
    if worktrees_root.exists():
        for wt_path in sorted(worktrees_root.iterdir()):
            if wt_path.name.startswith(f"{feature}-") and wt_path.is_dir():
                # Extract WP ID from directory name: e.g. "034-feature-WP01" → "WP01"
                suffix = wt_path.name[len(feature) + 1 :]
                if suffix.startswith("WP"):
                    wp_id = suffix
                    branch_name = wt_path.name
                    wp_workspaces.append((wt_path, wp_id, branch_name))

    # Run preflight
    preflight_result = run_preflight(
        feature_slug=feature,
        target_branch=target,
        repo_root=main_repo_root,
        wp_workspaces=wp_workspaces,
    )

    if not preflight_result.passed:
        _fail(
            cmd,
            "PREFLIGHT_FAILED",
            "Preflight checks failed",
            {"errors": preflight_result.errors},
        )
        return

    # Determine merge order
    ordered_workspaces = get_merge_order(wp_workspaces, feature_dir)

    # Execute merges using git directly (simplified)
    merged_wps = []
    for wt_path, wp_id, branch_name in ordered_workspaces:
        try:
            # Checkout target branch and merge
            subprocess.run(
                ["git", "-C", str(main_repo_root), "checkout", target],
                check=True,
                capture_output=True,
            )
            if strategy == "squash":
                subprocess.run(
                    ["git", "-C", str(main_repo_root), "merge", "--squash", branch_name],
                    check=True,
                    capture_output=True,
                )
                # squash leaves staged changes; commit them
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(main_repo_root),
                        "commit",
                        "-m",
                        f"squash merge: {feature}/{wp_id} into {target}",
                    ],
                    check=True,
                    capture_output=True,
                )
            elif strategy == "rebase":
                # Rebase WP branch onto target, then fast-forward target.
                subprocess.run(
                    ["git", "-C", str(main_repo_root), "checkout", branch_name],
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "-C", str(main_repo_root), "rebase", target],
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "-C", str(main_repo_root), "checkout", target],
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "-C", str(main_repo_root), "merge", "--ff-only", branch_name],
                    check=True,
                    capture_output=True,
                )
            else:
                # Default: --no-ff merge
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(main_repo_root),
                        "merge",
                        "--no-ff",
                        branch_name,
                        "-m",
                        f"merge: {feature}/{wp_id} into {target}",
                    ],
                    check=True,
                    capture_output=True,
                )
            merged_wps.append(wp_id)
        except subprocess.CalledProcessError as exc:
            _fail(
                cmd,
                "MERGE_FAILED",
                f"Failed to merge {wp_id}: {exc.stderr.decode() if exc.stderr else str(exc)}",
                {"merged_so_far": merged_wps, "failed_wp": wp_id},
            )
            return

    if push:
        try:
            subprocess.run(
                ["git", "-C", str(main_repo_root), "push", "origin", target],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as exc:
            _fail(
                cmd,
                "PUSH_FAILED",
                f"Merge succeeded but push failed: {exc.stderr.decode() if exc.stderr else str(exc)}",
                {"merged_wps": merged_wps},
            )
            return

    envelope = make_envelope(
        command=cmd,
        success=True,
        data={
            "feature_slug": feature,
            "merged": True,
            "target_branch": target,
            "strategy": strategy,
            "merged_wps": merged_wps,
            "worktree_removed": False,
        },
    )
    _emit(envelope)


__all__ = ["app"]
