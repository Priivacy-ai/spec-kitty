"""Machine-contract API commands for external orchestrators.

All commands emit exactly one JSON object using the canonical envelope.
Non-zero exit is used for any failure.
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

from specify_cli.core.dependency_graph import build_dependency_graph
from specify_cli.core.paths import get_main_repo_root, locate_project_root
from specify_cli.git.commit_helpers import safe_commit
from specify_cli.merge import get_merge_order, run_preflight
from specify_cli.tasks_support import (
    activity_entries,
    append_activity_log,
    build_document,
    extract_scalar,
    set_scalar,
    split_frontmatter,
)

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

# API lanes that require policy metadata.
_RUN_AFFECTING_LANES = frozenset(["claimed", "in_progress", "for_review"])
_TERMINAL_LANES = frozenset(["blocked", "canceled"])
_WP_ID_RE = re.compile(r"^(WP\d+)")


def _emit(envelope: dict[str, Any]) -> None:
    print(json.dumps(envelope))


def _fail(command: str, error_code: str, message: str, data: dict[str, Any] | None = None) -> None:
    envelope = make_envelope(
        command=command,
        success=False,
        data=data or {"message": message},
        error_code=error_code,
    )
    _emit(envelope)
    raise typer.Exit(1)


def _get_main_repo_root() -> Path:
    cwd = Path.cwd()
    root = locate_project_root(cwd)
    if root is None:
        return get_main_repo_root(cwd)
    return root


def _resolve_feature_dir(main_repo_root: Path, feature_slug: str) -> Path | None:
    feature_dir = main_repo_root / "kitty-specs" / feature_slug
    if not feature_dir.is_dir():
        return None
    return feature_dir


def _extract_wp_id(stem: str) -> str | None:
    match = _WP_ID_RE.match(stem)
    return match.group(1) if match else None


def _normalize_internal_lane(lane: str | None) -> str:
    value = (lane or "planned").strip().lower()
    if value in {"doing", "planned", "for_review", "done", "blocked", "canceled"}:
        return value
    if value in {"in_progress", "claimed"}:
        return "doing"
    return value


def _api_lane_from_internal(lane: str | None) -> str:
    value = (lane or "planned").strip().lower()
    if value in {"doing", "in_progress", "claimed"}:
        return "in_progress"
    return value


def _api_lane_from_requested(lane: str) -> str:
    value = lane.strip().lower()
    if value in {"doing", "in_progress", "claimed"}:
        return "in_progress"
    return value


def _internal_lane_for_api(api_lane: str) -> str:
    if api_lane == "in_progress":
        return "doing"
    return api_lane


def _resolve_wp_file(tasks_dir: Path, wp_id: str) -> Path | None:
    exact = tasks_dir / f"{wp_id}.md"
    if exact.exists():
        return exact
    for path in sorted(tasks_dir.glob(f"{wp_id}-*.md")):
        return path
    return None


def _last_actor_from_document(frontmatter: str, body: str) -> str | None:
    entries = activity_entries(body)
    if entries:
        actor = (entries[-1].get("agent") or "").strip()
        if actor:
            return actor

    actor = extract_scalar(frontmatter, "agent")
    if actor:
        actor = actor.strip()
    return actor or None


def _load_feature_wps(feature_dir: Path) -> dict[str, dict[str, Any]]:
    tasks_dir = feature_dir / "tasks"
    states: dict[str, dict[str, Any]] = {}
    if not tasks_dir.exists():
        return states

    for path in sorted(tasks_dir.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        wp_id = _extract_wp_id(path.stem)
        if wp_id is None or wp_id in states:
            continue

        raw = path.read_text(encoding="utf-8")
        frontmatter, body, padding = split_frontmatter(raw)
        lane_internal = _normalize_internal_lane(extract_scalar(frontmatter, "lane"))
        states[wp_id] = {
            "wp_id": wp_id,
            "path": path,
            "frontmatter": frontmatter,
            "body": body,
            "padding": padding,
            "lane_internal": lane_internal,
            "lane_api": _api_lane_from_internal(lane_internal),
            "last_actor": _last_actor_from_document(frontmatter, body),
        }

    return states


def _write_wp_transition(
    main_repo_root: Path,
    feature_slug: str,
    wp_state: dict[str, Any],
    to_api_lane: str,
    actor: str,
    note: str | None = None,
    review_ref: str | None = None,
) -> None:
    to_internal_lane = _internal_lane_for_api(to_api_lane)

    updated_front = set_scalar(wp_state["frontmatter"], "lane", to_internal_lane)
    updated_front = set_scalar(updated_front, "agent", actor)

    if review_ref:
        updated_front = set_scalar(updated_front, "review_ref", review_ref)

    if to_api_lane == "done":
        updated_front = set_scalar(updated_front, "reviewed_by", actor)
        updated_front = set_scalar(updated_front, "review_status", "approved")

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    note_text = (note or f"Moved to {to_api_lane}").strip()
    if review_ref:
        note_text = f"{note_text} (review_ref={review_ref})"

    history_entry = (
        f"- {timestamp} \u2013 {actor} \u2013 lane={to_internal_lane} \u2013 {note_text}"
    )
    updated_body = append_activity_log(wp_state["body"], history_entry)

    wp_path = wp_state["path"]
    wp_path.write_text(
        build_document(updated_front, updated_body, wp_state["padding"]),
        encoding="utf-8",
    )

    safe_commit(
        repo_path=main_repo_root,
        files_to_commit=[wp_path],
        commit_message=(
            f"chore: orchestrator-api transition {feature_slug}/{wp_state['wp_id']} "
            f"to {to_api_lane}"
        ),
        allow_empty=True,
    )


def _validate_transition(
    from_api_lane: str,
    to_api_lane: str,
    review_ref: str | None,
    force: bool,
) -> str | None:
    if force:
        return None

    if from_api_lane == to_api_lane:
        return None

    if to_api_lane in _TERMINAL_LANES:
        return None

    allowed = {
        ("planned", "in_progress"),
        ("in_progress", "for_review"),
        ("for_review", "in_progress"),
        ("for_review", "planned"),
        ("for_review", "done"),
    }

    if (from_api_lane, to_api_lane) not in allowed:
        return (
            f"Transition {from_api_lane} -> {to_api_lane} is not allowed "
            "without --force"
        )

    if from_api_lane == "for_review" and to_api_lane == "in_progress" and not review_ref:
        return "--review-ref is required for for_review -> in_progress"

    if from_api_lane == "for_review" and to_api_lane == "planned" and not review_ref:
        return "--review-ref is required for for_review -> planned (review rejection)"

    return None


# ── Command 1: contract-version ────────────────────────────────────────────


@app.command(name="contract-version")
def contract_version(
    provider_version: str = typer.Option(
        None,
        "--provider-version",
        help="Caller provider version; checked against min supported provider version",
    ),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Output as JSON"),
) -> None:
    cmd = "contract-version"

    if provider_version is not None:
        from packaging.version import InvalidVersion, Version

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

    _emit(
        make_envelope(
            command=cmd,
            success=True,
            data={
                "api_version": CONTRACT_VERSION,
                "min_supported_provider_version": MIN_PROVIDER_VERSION,
            },
        )
    )


# ── Command 2: feature-state ───────────────────────────────────────────────


@app.command(name="feature-state")
def feature_state(
    feature: str = typer.Option(..., "--feature", help="Feature slug (e.g. 034-my-feature)"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Output as JSON"),
) -> None:
    cmd = "feature-state"
    main_repo_root = _get_main_repo_root()
    feature_dir = _resolve_feature_dir(main_repo_root, feature)
    if feature_dir is None:
        _fail(cmd, "FEATURE_NOT_FOUND", f"Feature '{feature}' not found in kitty-specs/")
        return

    wp_states = _load_feature_wps(feature_dir)
    dep_graph = build_dependency_graph(feature_dir)
    all_wp_ids = sorted(set(dep_graph.keys()) | set(wp_states.keys()))

    work_packages: list[dict[str, Any]] = []
    lane_counts: dict[str, int] = {
        "planned": 0,
        "in_progress": 0,
        "for_review": 0,
        "done": 0,
    }

    for wp_id in all_wp_ids:
        state = wp_states.get(wp_id)
        lane = state["lane_api"] if state else "planned"
        lane_counts[lane] = lane_counts.get(lane, 0) + 1
        work_packages.append(
            {
                "wp_id": wp_id,
                "lane": lane,
                "dependencies": dep_graph.get(wp_id, []),
                "last_actor": state["last_actor"] if state else None,
            }
        )

    _emit(
        make_envelope(
            command=cmd,
            success=True,
            data={
                "feature_slug": feature,
                "summary": {
                    "total_work_packages": len(all_wp_ids),
                    **lane_counts,
                },
                "work_packages": work_packages,
            },
        )
    )


# ── Command 3: list-ready ──────────────────────────────────────────────────


@app.command(name="list-ready")
def list_ready(
    feature: str = typer.Option(..., "--feature", help="Feature slug"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Output as JSON"),
) -> None:
    cmd = "list-ready"
    main_repo_root = _get_main_repo_root()
    feature_dir = _resolve_feature_dir(main_repo_root, feature)
    if feature_dir is None:
        _fail(cmd, "FEATURE_NOT_FOUND", f"Feature '{feature}' not found in kitty-specs/")
        return

    wp_states = _load_feature_wps(feature_dir)
    dep_graph = build_dependency_graph(feature_dir)
    all_wp_ids = sorted(set(dep_graph.keys()) | set(wp_states.keys()))

    ready: list[dict[str, Any]] = []
    for wp_id in all_wp_ids:
        state = wp_states.get(wp_id)
        lane = state["lane_api"] if state else "planned"
        deps = dep_graph.get(wp_id, [])
        deps_done = all((wp_states.get(dep, {}).get("lane_api") == "done") for dep in deps)

        if lane == "planned" and deps_done:
            ready.append(
                {
                    "wp_id": wp_id,
                    "lane": "planned",
                    "dependencies_satisfied": True,
                    "recommended_base": deps[-1] if deps else None,
                }
            )

    _emit(
        make_envelope(
            command=cmd,
            success=True,
            data={
                "feature_slug": feature,
                "ready_work_packages": ready,
            },
        )
    )


# ── Command 4: start-implementation ────────────────────────────────────────


@app.command(name="start-implementation")
def start_implementation(
    feature: str = typer.Option(..., "--feature", help="Feature slug"),
    wp: str = typer.Option(..., "--wp", help="Work package ID (e.g. WP01)"),
    actor: str = typer.Option(..., "--actor", help="Actor identity"),
    policy: str = typer.Option(None, "--policy", help="Policy metadata JSON (required)"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Output as JSON"),
) -> None:
    cmd = "start-implementation"

    if not policy:
        _fail(cmd, "POLICY_METADATA_REQUIRED", "--policy is required for start-implementation")
        return

    try:
        policy_obj = parse_and_validate_policy(policy)
    except ValueError as exc:
        _fail(cmd, "POLICY_VALIDATION_FAILED", str(exc))
        return

    main_repo_root = _get_main_repo_root()
    feature_dir = _resolve_feature_dir(main_repo_root, feature)
    if feature_dir is None:
        _fail(cmd, "FEATURE_NOT_FOUND", f"Feature '{feature}' not found in kitty-specs/")
        return

    wp_states = _load_feature_wps(feature_dir)
    wp_state = wp_states.get(wp)
    if wp_state is None:
        _fail(cmd, "WP_NOT_FOUND", f"Work package '{wp}' not found in {feature}")
        return

    current_lane = wp_state["lane_api"]
    last_actor = wp_state["last_actor"]

    workspace_path = str(main_repo_root / ".worktrees" / f"{feature}-{wp}")
    prompt_path = str(wp_state["path"])

    if current_lane == "planned":
        _write_wp_transition(
            main_repo_root=main_repo_root,
            feature_slug=feature,
            wp_state=wp_state,
            to_api_lane="in_progress",
            actor=actor,
            note="Implementation started",
        )
        from_lane = "planned"
        no_op = False
    elif current_lane == "in_progress":
        if last_actor and last_actor != actor:
            _fail(
                cmd,
                "WP_ALREADY_CLAIMED",
                f"WP {wp} is already in_progress by '{last_actor}'",
                {"claimed_by": last_actor, "requesting_actor": actor},
            )
            return
        from_lane = "in_progress"
        no_op = True
    else:
        _fail(
            cmd,
            "TRANSITION_REJECTED",
            f"WP {wp} is in '{current_lane}', cannot start implementation",
        )
        return

    _emit(
        make_envelope(
            command=cmd,
            success=True,
            data={
                "feature_slug": feature,
                "wp_id": wp,
                "from_lane": from_lane,
                "to_lane": "in_progress",
                "workspace_path": workspace_path,
                "prompt_path": prompt_path,
                "policy_metadata_recorded": policy_to_dict(policy_obj) is not None,
                "no_op": no_op,
            },
        )
    )


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
    cmd = "start-review"

    if not policy:
        _fail(cmd, "POLICY_METADATA_REQUIRED", "--policy is required for start-review")
        return

    if not review_ref:
        _fail(
            cmd,
            "TRANSITION_REJECTED",
            "--review-ref is required for start-review (for_review -> in_progress)",
        )
        return

    try:
        policy_obj = parse_and_validate_policy(policy)
    except ValueError as exc:
        _fail(cmd, "POLICY_VALIDATION_FAILED", str(exc))
        return

    main_repo_root = _get_main_repo_root()
    feature_dir = _resolve_feature_dir(main_repo_root, feature)
    if feature_dir is None:
        _fail(cmd, "FEATURE_NOT_FOUND", f"Feature '{feature}' not found in kitty-specs/")
        return

    wp_state = _load_feature_wps(feature_dir).get(wp)
    if wp_state is None:
        _fail(cmd, "WP_NOT_FOUND", f"Work package '{wp}' not found in {feature}")
        return

    from_lane = wp_state["lane_api"]
    if from_lane != "for_review":
        _fail(
            cmd,
            "TRANSITION_REJECTED",
            f"WP {wp} must be in 'for_review' for start-review (current: '{from_lane}')",
        )
        return

    _write_wp_transition(
        main_repo_root=main_repo_root,
        feature_slug=feature,
        wp_state=wp_state,
        to_api_lane="in_progress",
        actor=actor,
        note="Review requested changes",
        review_ref=review_ref,
    )

    _emit(
        make_envelope(
            command=cmd,
            success=True,
            data={
                "feature_slug": feature,
                "wp_id": wp,
                "from_lane": from_lane,
                "to_lane": "in_progress",
                "prompt_path": str(wp_state["path"]),
                "policy_metadata_recorded": policy_to_dict(policy_obj) is not None,
            },
        )
    )


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
    cmd = "transition"

    requested_lane = to.strip().lower()
    to_api_lane = _api_lane_from_requested(requested_lane)

    policy_dict: dict[str, Any] | None = None
    needs_policy = requested_lane in _RUN_AFFECTING_LANES or to_api_lane in _RUN_AFFECTING_LANES
    if needs_policy:
        if not policy:
            _fail(
                cmd,
                "POLICY_METADATA_REQUIRED",
                f"--policy is required when transitioning to '{requested_lane}'",
            )
            return
        try:
            policy_dict = policy_to_dict(parse_and_validate_policy(policy))
        except ValueError as exc:
            _fail(cmd, "POLICY_VALIDATION_FAILED", str(exc))
            return
    elif policy:
        try:
            policy_dict = policy_to_dict(parse_and_validate_policy(policy))
        except ValueError as exc:
            _fail(cmd, "POLICY_VALIDATION_FAILED", str(exc))
            return

    main_repo_root = _get_main_repo_root()
    feature_dir = _resolve_feature_dir(main_repo_root, feature)
    if feature_dir is None:
        _fail(cmd, "FEATURE_NOT_FOUND", f"Feature '{feature}' not found in kitty-specs/")
        return

    wp_state = _load_feature_wps(feature_dir).get(wp)
    if wp_state is None:
        _fail(cmd, "WP_NOT_FOUND", f"Work package '{wp}' not found in {feature}")
        return

    from_lane = wp_state["lane_api"]

    supported = {
        "planned",
        "claimed",
        "in_progress",
        "doing",
        "for_review",
        "done",
        "blocked",
        "canceled",
    }
    if requested_lane not in supported and to_api_lane not in supported:
        _fail(
            cmd,
            "TRANSITION_REJECTED",
            f"Unsupported target lane '{to}'",
        )
        return

    validation_error = _validate_transition(from_lane, to_api_lane, review_ref, force)
    if validation_error:
        _fail(cmd, "TRANSITION_REJECTED", validation_error)
        return

    if from_lane != to_api_lane:
        _write_wp_transition(
            main_repo_root=main_repo_root,
            feature_slug=feature,
            wp_state=wp_state,
            to_api_lane=to_api_lane,
            actor=actor,
            note=note,
            review_ref=review_ref,
        )

    _emit(
        make_envelope(
            command=cmd,
            success=True,
            data={
                "feature_slug": feature,
                "wp_id": wp,
                "from_lane": from_lane,
                "to_lane": to_api_lane,
                "policy_metadata_recorded": policy_dict is not None,
            },
        )
    )


# ── Command 7: append-history ──────────────────────────────────────────────


@app.command(name="append-history")
def append_history(
    feature: str = typer.Option(..., "--feature", help="Feature slug"),
    wp: str = typer.Option(..., "--wp", help="Work package ID"),
    actor: str = typer.Option(..., "--actor", help="Actor identity"),
    note: str = typer.Option(..., "--note", help="History note to append"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Output as JSON"),
) -> None:
    cmd = "append-history"

    main_repo_root = _get_main_repo_root()
    feature_dir = _resolve_feature_dir(main_repo_root, feature)
    if feature_dir is None:
        _fail(cmd, "FEATURE_NOT_FOUND", f"Feature '{feature}' not found in kitty-specs/")
        return

    wp_file = _resolve_wp_file(feature_dir / "tasks", wp)
    if wp_file is None:
        _fail(cmd, "WP_NOT_FOUND", f"Work package '{wp}' not found in {feature}")
        return

    raw = wp_file.read_text(encoding="utf-8")
    frontmatter, body, padding = split_frontmatter(raw)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry_text = f"- [{timestamp}] {actor}: {note}"
    new_body = append_activity_log(body, entry_text)

    wp_file.write_text(build_document(frontmatter, new_body, padding), encoding="utf-8")

    safe_commit(
        repo_path=main_repo_root,
        files_to_commit=[wp_file],
        commit_message=f"hist: append activity log entry for {feature}/{wp}",
        allow_empty=True,
    )

    _emit(
        make_envelope(
            command=cmd,
            success=True,
            data={
                "feature_slug": feature,
                "wp_id": wp,
                "history_entry_id": "hist-" + uuid.uuid4().hex,
            },
        )
    )


# ── Command 8: accept-feature ──────────────────────────────────────────────


@app.command(name="accept-feature")
def accept_feature(
    feature: str = typer.Option(..., "--feature", help="Feature slug"),
    actor: str = typer.Option(..., "--actor", help="Actor identity"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Output as JSON"),
) -> None:
    cmd = "accept-feature"

    main_repo_root = _get_main_repo_root()
    feature_dir = _resolve_feature_dir(main_repo_root, feature)
    if feature_dir is None:
        _fail(cmd, "FEATURE_NOT_FOUND", f"Feature '{feature}' not found in kitty-specs/")
        return

    wp_states = _load_feature_wps(feature_dir)
    dep_graph = build_dependency_graph(feature_dir)
    all_wp_ids = sorted(set(dep_graph.keys()) | set(wp_states.keys()))

    incomplete = [
        wp_id
        for wp_id in all_wp_ids
        if (wp_states.get(wp_id, {}).get("lane_api") or "planned") != "done"
    ]
    if incomplete:
        _fail(
            cmd,
            "FEATURE_NOT_READY",
            f"Feature has {len(incomplete)} incomplete WP(s)",
            {"incomplete_wps": incomplete},
        )
        return

    meta_path = feature_dir / "meta.json"
    meta: dict[str, Any] = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            meta = {}

    accepted_at = datetime.now(timezone.utc).isoformat()
    meta["accepted_at"] = accepted_at
    meta["accepted_by"] = actor
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")

    _emit(
        make_envelope(
            command=cmd,
            success=True,
            data={
                "feature_slug": feature,
                "accepted": True,
                "mode": "auto",
                "accepted_at": accepted_at,
            },
        )
    )


# ── Command 9: merge-feature ───────────────────────────────────────────────


@app.command(name="merge-feature")
def merge_feature(
    feature: str = typer.Option(..., "--feature", help="Feature slug"),
    target: str = typer.Option(None, "--target", help="Target branch to merge into (auto-detected from meta.json)"),
    strategy: str = typer.Option("merge", "--strategy", help="Merge strategy: merge or squash"),
    push: bool = typer.Option(False, "--push", help="Push target branch after merge"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Output as JSON"),
) -> None:
    cmd = "merge-feature"

    supported_strategies = frozenset(["merge", "squash"])
    if strategy not in supported_strategies:
        _fail(
            cmd,
            "UNSUPPORTED_STRATEGY",
            f"Strategy '{strategy}' is not supported. Supported strategies: {sorted(supported_strategies)}",
            {"strategy": strategy, "supported": sorted(supported_strategies)},
        )
        return

    main_repo_root = _get_main_repo_root()

    if target is None:
        from specify_cli.core.feature_detection import get_feature_target_branch
        target = get_feature_target_branch(main_repo_root, feature)

    feature_dir = _resolve_feature_dir(main_repo_root, feature)
    if feature_dir is None:
        _fail(cmd, "FEATURE_NOT_FOUND", f"Feature '{feature}' not found in kitty-specs/")
        return

    worktrees_root = main_repo_root / ".worktrees"
    wp_workspaces: list[tuple[Path, str, str]] = []
    if worktrees_root.exists():
        for wt_path in sorted(worktrees_root.iterdir()):
            if wt_path.name.startswith(f"{feature}-") and wt_path.is_dir():
                suffix = wt_path.name[len(feature) + 1 :]
                if suffix.startswith("WP"):
                    wp_workspaces.append((wt_path, suffix, wt_path.name))

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

    ordered_workspaces = get_merge_order(wp_workspaces, feature_dir)

    merged_wps: list[str] = []
    for _wt_path, wp_id, branch_name in ordered_workspaces:
        try:
            subprocess.run(
                ["git", "-C", str(main_repo_root), "checkout", target],
                check=True,
                capture_output=True,
                text=True,
            )
            if strategy == "merge":
                merge_cmd = [
                    "git",
                    "-C",
                    str(main_repo_root),
                    "merge",
                    "--no-ff",
                    branch_name,
                    "-m",
                    f"merge: {feature}/{wp_id} into {target}",
                ]
            else:
                merge_cmd = [
                    "git",
                    "-C",
                    str(main_repo_root),
                    "merge",
                    "--squash",
                    branch_name,
                ]
            subprocess.run(merge_cmd, check=True, capture_output=True, text=True)
            merged_wps.append(wp_id)
        except subprocess.CalledProcessError as exc:
            _fail(
                cmd,
                "MERGE_FAILED",
                f"Failed to merge {wp_id}: {(exc.stderr or '').strip() or str(exc)}",
                {"merged_so_far": merged_wps, "failed_wp": wp_id},
            )
            return

    if push:
        try:
            subprocess.run(
                ["git", "-C", str(main_repo_root), "push", "origin", target],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            _fail(
                cmd,
                "PUSH_FAILED",
                f"Merge succeeded but push failed: {(exc.stderr or '').strip() or str(exc)}",
                {"merged_wps": merged_wps},
            )
            return

    _emit(
        make_envelope(
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
    )


__all__ = ["app"]
