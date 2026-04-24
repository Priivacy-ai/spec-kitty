"""Bridge between CLI ``decide_next()`` and ``spec-kitty-runtime`` engine.

Maps the CLI's Decision dataclass to the runtime's NextDecision by:

1. Starting or loading a mission run (persisted under .kittify/runtime/)
2. Delegating step planning to the runtime DAG planner
3. Handling WP-level iteration within "implement" and "review" steps
4. Enforcing CLI-level guards (artifact checks, WP status)
5. Preserving the existing JSON output contract

Run state is stored locally under ``.kittify/runtime/runs/<run_id>/``.
A tracked-mission-to-run compatibility index currently lives at
``.kittify/runtime/feature-runs.json``.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from datetime import datetime, timezone, UTC
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Module-level string constants (S1192)
# ---------------------------------------------------------------------------

_KITTIFY_DIR = ".kittify"
_WP_GLOB = "WP*.md"
_MISSION_RUNTIME_YAML = "mission-runtime.yaml"
_MISSION_YAML = "mission.yaml"

import yaml
from spec_kitty_runtime import (
    DiscoveryContext,
    MissionPolicySnapshot,
    MissionRunRef,
    NextDecision,
    NullEmitter,
    next_step as runtime_next_step,
    provide_decision_answer as runtime_provide_decision_answer,
    start_mission_run,
)
from spec_kitty_runtime.schema import ActorIdentity, load_mission_template_file

from specify_cli.core.atomic import atomic_write
from specify_cli.mission import get_mission_type
from specify_cli.status.lane_reader import CanonicalStatusNotFoundError
from specify_cli.status.models import Lane
from specify_cli.status.wp_state import wp_state_for
from runtime.decisioning.decision import (
    Decision,
    DecisionKind,
    _build_prompt_safe,
    _compute_wp_progress,
    _state_to_action,
)
from specify_cli.sync.runtime_event_emitter import SyncRuntimeEventEmitter

logger = logging.getLogger(__name__)


class QueryModeValidationError(ValueError):
    """Raised when query mode cannot produce a truthful read-only preview."""


# ---------------------------------------------------------------------------
# Feature → Run index
# ---------------------------------------------------------------------------

_FEATURE_RUNS_FILE = "feature-runs.json"


def _feature_runs_path(repo_root: Path) -> Path:
    return repo_root / _KITTIFY_DIR / "runtime" / _FEATURE_RUNS_FILE


def _load_feature_runs(repo_root: Path) -> dict[str, dict[str, str]]:
    path = _feature_runs_path(repo_root)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_feature_runs(repo_root: Path, index: dict[str, dict[str, str]]) -> None:
    path = _feature_runs_path(repo_root)
    content = json.dumps(index, indent=2, sort_keys=True)
    atomic_write(path, content, mkdir=True)


def _mission_key_for_run_ref(run_ref: MissionRunRef, default: str) -> str:
    """Read the mission key from either runtime field name."""
    mission_key = getattr(run_ref, "mission_key", None)
    if isinstance(mission_key, str) and mission_key.strip():
        return mission_key
    mission_type = getattr(run_ref, "mission_type", None)
    if isinstance(mission_type, str) and mission_type.strip():
        return mission_type
    return default


def _build_run_ref(*, run_id: str, run_dir: str, mission_type: str) -> MissionRunRef:
    """Construct MissionRunRef across runtime versions."""
    try:
        return MissionRunRef(
            run_id=run_id,
            run_dir=run_dir,
            mission_key=mission_type,
        )
    except TypeError:
        return MissionRunRef(
            run_id=run_id,
            run_dir=run_dir,
            mission_type=mission_type,
        )


# ---------------------------------------------------------------------------
# WP iteration helpers
# ---------------------------------------------------------------------------

_WP_ITERATION_STEPS = frozenset({"implement", "review"})


def _is_wp_iteration_step(step_id: str) -> bool:
    """Check if a step is a WP-iteration step (implement, review)."""
    return step_id in _WP_ITERATION_STEPS


def _wp_blocks_implement(state: Any, lane: Any) -> bool:
    """Return True if a WP in the given state/lane blocks implement advancement."""
    # Advance past implement only when the WP has been handed off
    # (for_review or approved) or completed (done/canceled).
    # is_run_affecting is True for all active lanes; we further restrict
    # to only allow advancement for the "handed off" active lanes.
    if state.is_run_affecting and lane not in (Lane.FOR_REVIEW, Lane.APPROVED):
        return True
    # A blocked WP is not run_affecting but also not handed off — blocks advancement.
    return bool(state.is_blocked)


def _should_advance_wp_step(step_id: str, feature_dir: Path) -> bool:
    """Check if all WPs are done for this phase, meaning we should advance.

    For implement: all WPs must be handed off or complete
    (for_review, approved, or done).
    For review: all WPs must be approved or done.
    """
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.is_dir():
        return True  # no WPs to iterate over

    wp_files = sorted(tasks_dir.glob(_WP_GLOB))
    if not wp_files:
        return True

    # Get canonical lane state from event log (hard-fail if absent)
    import re as _re
    from specify_cli.status.lane_reader import get_wp_lane

    for wp_file in wp_files:
        wp_match = _re.match(r"(WP\d+)", wp_file.stem)
        wp_id = wp_match.group(1) if wp_match else wp_file.stem
        raw_lane = get_wp_lane(feature_dir, wp_id)
        try:
            state = wp_state_for(raw_lane)
        except ValueError:
            # Unknown lane (e.g. "uninitialized" before status bootstrap) — treat as
            # not-yet-handed-off, so this WP blocks advancement.
            return False
        lane = state.lane
        if step_id == "implement" and _wp_blocks_implement(state, lane):
            return False
        elif step_id == "review" and lane not in (Lane.DONE, Lane.APPROVED):
            return False

    return True


# ---------------------------------------------------------------------------
# Guard evaluation (CLI-level, not runtime-level)
# ---------------------------------------------------------------------------


def _guard_artifact_exists(feature_dir: Path, filename: str) -> list[str]:
    """Return a failure list if the given artifact file is missing."""
    if not (feature_dir / filename).exists():
        return [f"Required artifact missing: {filename}"]
    return []


def _guard_tasks_packages(feature_dir: Path) -> list[str]:
    """Return failures if no tasks/WP*.md files exist."""
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.is_dir() or not list(tasks_dir.glob(_WP_GLOB)):
        return ["Required: at least one tasks/WP*.md file"]
    return []


def _guard_tasks_finalize(feature_dir: Path) -> list[str]:
    """Return failures if tasks/ is missing, empty, or WP files lack 'dependencies'."""
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.is_dir():
        return ["Required: tasks/ directory with finalized WP files"]
    wp_files = sorted(tasks_dir.glob(_WP_GLOB))
    if not wp_files:
        return ["Required: at least one tasks/WP*.md file"]
    for wp_file in wp_files:
        if not _has_raw_dependencies_field(wp_file):
            return [
                f"WP {wp_file.stem} missing 'dependencies' in frontmatter"
                " (run 'spec-kitty agent mission finalize-tasks')"
            ]
    return []


def _check_cli_guards(step_id: str, feature_dir: Path) -> list[str]:
    """Check CLI-level guard conditions before completing a step.

    Returns list of failure descriptions. Empty list means all guards pass.
    """
    if step_id == "specify":
        return _guard_artifact_exists(feature_dir, "spec.md")
    if step_id == "plan":
        return _guard_artifact_exists(feature_dir, "plan.md")
    if step_id == "tasks_outline":
        return _guard_artifact_exists(feature_dir, "tasks.md")
    if step_id == "tasks_packages":
        return _guard_tasks_packages(feature_dir)
    if step_id == "tasks_finalize":
        return _guard_tasks_finalize(feature_dir)
    if step_id == "implement":
        if not _should_advance_wp_step("implement", feature_dir):
            return ["Not all work packages have required status (for_review, approved, or done)"]
    elif step_id == "review":
        if not _should_advance_wp_step("review", feature_dir):
            return ["Not all work packages are approved or done"]
    return []


def _has_raw_dependencies_field(wp_file: Path) -> bool:
    """Check if WP file has an explicit 'dependencies' field in raw frontmatter.

    Reads raw text to avoid auto-injection by read_frontmatter().
    """
    try:
        text = wp_file.read_text(encoding="utf-8")
    except OSError:
        return False
    if not text.startswith("---"):
        return False
    end = text.find("---", 3)
    if end == -1:
        return False
    for line in text[3:end].splitlines():
        stripped = line.strip()
        if stripped.startswith("dependencies:"):
            return True
    return False


# ---------------------------------------------------------------------------
# Run management
# ---------------------------------------------------------------------------


def _build_discovery_context(repo_root: Path) -> DiscoveryContext:
    """Build a DiscoveryContext that finds the runtime mission template."""
    # Point at the missions directory so the runtime can discover mission-runtime.yaml
    package_root = Path(__file__).resolve().parent.parent.parent / "specify_cli" / "missions"
    return DiscoveryContext(
        project_dir=repo_root,
        builtin_roots=[package_root],
    )


def _split_env_paths(value: str) -> list[Path]:
    if not value.strip():
        return []
    return [Path(chunk) for chunk in value.split(os.pathsep) if chunk.strip()]


def _project_config_pack_paths(repo_root: Path) -> list[Path]:
    config_file = repo_root / _KITTIFY_DIR / "config.yaml"
    if not config_file.exists():
        return []
    try:
        raw = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    mission_packs = raw.get("mission_packs", [])
    if not isinstance(mission_packs, list):
        return []
    return [repo_root / pack for pack in mission_packs if isinstance(pack, str)]


def _candidate_templates_for_root(root: Path, mission_type: str) -> list[Path]:
    candidates: list[Path] = []

    if root.is_file():
        if root.name in {_MISSION_RUNTIME_YAML, _MISSION_YAML}:
            candidates.append(root)
    elif root.exists() and root.is_dir():
        candidates.extend(
            [
                root / mission_type / _MISSION_RUNTIME_YAML,
                root / mission_type / _MISSION_YAML,
                root / "missions" / mission_type / _MISSION_RUNTIME_YAML,
                root / "missions" / mission_type / _MISSION_YAML,
                root / _MISSION_RUNTIME_YAML,
                root / _MISSION_YAML,
            ]
        )

    # De-duplicate while preserving order.
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def _template_key_for_file(path: Path) -> str | None:
    try:
        template = load_mission_template_file(path)
        return template.mission.key
    except Exception:
        return None


def _resolve_runtime_template_in_root(root: Path, mission_type: str) -> Path | None:
    for candidate in _candidate_templates_for_root(root, mission_type):
        if not candidate.exists() or not candidate.is_file():
            continue

        paths_to_try = [candidate]
        # Prefer mission-runtime.yaml sidecar when candidate is mission.yaml.
        if candidate.name == _MISSION_YAML:
            runtime_sidecar = candidate.with_name(_MISSION_RUNTIME_YAML)
            if runtime_sidecar.exists() and runtime_sidecar.is_file():
                paths_to_try = [runtime_sidecar, candidate]

        for path in paths_to_try:
            template_key = _template_key_for_file(path)
            if template_key == mission_type:
                return path.resolve()

    return None


def _runtime_template_key(mission_type: str, repo_root: Path) -> str:
    """Resolve the runtime template path for a mission key.

    Uses deterministic runtime discovery precedence for mission-runtime YAML:
    explicit -> env -> project override -> project legacy -> user global
    -> project config -> built-in.
    """
    context = _build_discovery_context(repo_root)
    env_value = os.environ.get(context.env_var_name, "")
    tiers: list[list[Path]] = [
        list(context.explicit_paths),
        _split_env_paths(env_value),
        [repo_root / _KITTIFY_DIR / "overrides" / "missions"],
        [repo_root / _KITTIFY_DIR / "missions"],
        [context.user_home / _KITTIFY_DIR / "missions"],
        _project_config_pack_paths(repo_root),
        list(context.builtin_roots),
    ]

    for roots in tiers:
        for root in roots:
            resolved = _resolve_runtime_template_in_root(root, mission_type)
            if resolved is not None:
                return str(resolved)

    # Fallback: let runtime resolve mission key via mission.yaml discovery.
    return mission_type


def _existing_run_ref(
    mission_slug: str,
    repo_root: Path,
    mission_type: str,
) -> MissionRunRef | None:
    """Return an existing run without creating a new one."""
    index = _load_feature_runs(repo_root)

    if mission_slug not in index:
        return None

    entry = index[mission_slug]
    run_dir = Path(entry["run_dir"])
    if not (run_dir / "state.json").exists():
        return None

    stored_mission_type = entry.get("mission_type") or entry.get("mission_key") or mission_type
    return _build_run_ref(
        run_id=entry["run_id"],
        run_dir=entry["run_dir"],
        mission_type=stored_mission_type,
    )


def _start_ephemeral_query_run(
    mission_slug: str,
    mission_type: str,
    repo_root: Path,
) -> tuple[MissionRunRef, Path]:
    """Start a fresh query-only run outside the repository.

    This keeps fresh query mode non-mutating for the project working tree and
    `.kittify/runtime/feature-runs.json` while still using the runtime's own
    snapshot/bootstrap behavior. The temp run store is cleaned up if any
    bootstrap step raises so we never leak directories on failure paths.
    """
    run_store = Path(tempfile.mkdtemp(prefix="spec-kitty-query-run-"))
    try:
        template_key = _runtime_template_key(mission_type, repo_root)
        context = _build_discovery_context(repo_root)

        run_ref = start_mission_run(
            template_key=template_key,
            inputs={"mission_slug": mission_slug},
            policy_snapshot=MissionPolicySnapshot(),
            context=context,
            run_store=run_store,
            emitter=NullEmitter(),
        )
    except Exception:
        shutil.rmtree(run_store, ignore_errors=True)
        raise
    return run_ref, run_store


def get_or_start_run(
    mission_slug: str,
    repo_root: Path,
    mission_type: str,
    *,
    emitter: Any | None = None,
) -> MissionRunRef:
    """Load existing run or start a new one.

    Run mapping stored in .kittify/runtime/feature-runs.json:
    { "042-test-feature": { "run_id": "abc", "run_dir": "..." } }
    """
    index = _load_feature_runs(repo_root)

    if mission_slug in index:
        entry = index[mission_slug]
        run_dir = Path(entry["run_dir"])
        if (run_dir / "state.json").exists():
            stored_mission_type = entry.get("mission_type") or entry.get("mission_key") or mission_type
            return _build_run_ref(
                run_id=entry["run_id"],
                run_dir=entry["run_dir"],
                mission_type=stored_mission_type,
            )

    # Start a new run
    run_store = repo_root / _KITTIFY_DIR / "runtime" / "runs"
    template_key = _runtime_template_key(mission_type, repo_root)
    context = _build_discovery_context(repo_root)

    run_ref = start_mission_run(
        template_key=template_key,
        inputs={"mission_slug": mission_slug},
        policy_snapshot=MissionPolicySnapshot(),
        context=context,
        run_store=run_store,
        emitter=emitter or NullEmitter(),
    )

    # Persist to index
    resolved_mission_type = _mission_key_for_run_ref(run_ref, mission_type)
    index[mission_slug] = {
        "run_id": run_ref.run_id,
        "run_dir": run_ref.run_dir,
        "mission_type": resolved_mission_type,
        "mission_key": resolved_mission_type,
    }
    _save_feature_runs(repo_root, index)

    return run_ref


# ---------------------------------------------------------------------------
# Main bridge functions
# ---------------------------------------------------------------------------


def _resolve_mission_origin(mission_type: str, repo_root: Path) -> dict[str, Any]:
    """Resolve the mission tier/path origin dict for a Decision."""
    try:
        from runtime.discovery.resolver import resolve_mission as resolve_mission_path

        mission_result = resolve_mission_path(mission_type, repo_root)
        return {
            "mission_tier": getattr(mission_result.tier, "value", str(mission_result.tier)),
            "mission_path": str(mission_result.path.parent),
        }
    except FileNotFoundError:
        return {"mission_tier": "unknown", "mission_path": "unknown"}


def _build_non_wp_guard_decision(
    step_id: str,
    guard_failures: list[str],
    agent: str,
    mission_slug: str,
    mission_type: str,
    feature_dir: Path,
    repo_root: Path,
    now: str,
    progress: dict | None,
    origin: dict,
    run_ref: Any,
) -> Decision:
    """Build a guard-blocked Decision for a non-WP step."""
    action, wp_id, workspace_path = _state_to_action(
        step_id,
        mission_slug,
        feature_dir,
        repo_root,
        mission_type,
    )
    prompt_file = (
        _build_prompt_safe(
            action or step_id,
            feature_dir,
            mission_slug,
            wp_id,
            agent,
            repo_root,
            mission_type,
        )
        if action
        else None
    )
    return Decision(
        kind=DecisionKind.step,
        agent=agent,
        mission_slug=mission_slug,
        mission=mission_type,
        mission_state=step_id,
        timestamp=now,
        action=action,
        wp_id=wp_id,
        workspace_path=workspace_path,
        prompt_file=prompt_file,
        guard_failures=guard_failures,
        progress=progress,
        origin=origin,
        run_id=run_ref.run_id,
        step_id=step_id,
    )


def _check_advance_gates(
    step_id: str,
    feature_dir: Path,
    agent: str,
    mission_slug: str,
    mission_type: str,
    repo_root: Path,
    now: str,
    progress: dict | None,
    origin: dict,
    run_ref: MissionRunRef,
) -> Decision | None:
    """Return an early Decision if WP iteration or guards block advance; else None."""
    if _is_wp_iteration_step(step_id):
        try:
            should_advance = _should_advance_wp_step(step_id, feature_dir)
        except CanonicalStatusNotFoundError as exc:
            return Decision(
                kind=DecisionKind.blocked,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state=step_id,
                timestamp=now,
                reason=str(exc),
                guard_failures=[str(exc)],
                progress=progress,
                origin=origin,
                run_id=run_ref.run_id,
                step_id=step_id,
            )
        if not should_advance:
            return _build_wp_iteration_decision(
                step_id, agent, mission_slug, mission_type,
                feature_dir, repo_root, now, progress, origin, run_ref,
            )
        # All WPs done — guards must still pass before advancing.
        guard_failures = _check_cli_guards(step_id, feature_dir)
        if guard_failures:
            return _build_wp_iteration_decision(
                step_id, agent, mission_slug, mission_type,
                feature_dir, repo_root, now, progress, origin, run_ref,
                guard_failures=guard_failures,
            )
        return None

    guard_failures = _check_cli_guards(step_id, feature_dir)
    if guard_failures:
        return _build_non_wp_guard_decision(
            step_id, guard_failures, agent, mission_slug, mission_type,
            feature_dir, repo_root, now, progress, origin, run_ref,
        )
    return None


def decide_next_via_runtime(
    agent: str,
    mission_slug: str,
    result: str,
    repo_root: Path,
) -> Decision:
    """Main entry point replacing old decide_next().

    Flow:
    1. Resolve mission_type from meta.json
    2. get_or_start_run() to obtain MissionRunRef
    3. Check if current step is a WP-iteration step
       a. If yes and WPs remain: skip runtime advance, build WP prompt, return step
       b. If yes and all WPs done: call next_step(result="success") to advance
    4. For non-WP steps: call next_step(run_ref, agent, result) directly
    5. Map NextDecision -> Decision (preserving JSON contract)
    """
    feature_dir = repo_root / "kitty-specs" / mission_slug
    now = datetime.now(UTC).isoformat()

    if not feature_dir.is_dir():
        return Decision(
            kind=DecisionKind.blocked,
            agent=agent,
            mission_slug=mission_slug,
            mission="unknown",
            mission_state="unknown",
            timestamp=now,
            reason=f"Feature directory not found: {feature_dir}",
        )

    mission_type = get_mission_type(feature_dir)
    sync_emitter = SyncRuntimeEventEmitter.for_feature(
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        mission_type=mission_type,
    )

    origin = _resolve_mission_origin(mission_type, repo_root)
    progress = _compute_wp_progress(feature_dir)

    # Get or start runtime run (before result handling so failed/blocked
    # decisions include canonical run_id, step_id, and mission_state)
    try:
        run_ref = get_or_start_run(
            mission_slug,
            repo_root,
            mission_type,
            emitter=sync_emitter,
        )
    except Exception as exc:
        return Decision(
            kind=DecisionKind.blocked,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state="unknown",
            timestamp=now,
            reason=f"Failed to start/load runtime run: {exc}",
            progress=progress,
            origin=origin,
        )

    # Read current run state
    try:
        from spec_kitty_runtime.engine import _read_snapshot

        snapshot = _read_snapshot(Path(run_ref.run_dir))
        current_step_id = snapshot.issued_step_id
        sync_emitter.seed_from_snapshot(snapshot)
    except Exception:
        current_step_id = None

    # WP iteration and guard checks before advancing the runtime DAG.
    if result == "success" and current_step_id:
        early = _check_advance_gates(
            current_step_id, feature_dir, agent, mission_slug, mission_type,
            repo_root, now, progress, origin, run_ref,
        )
        if early is not None:
            return early

    # Advance via runtime
    try:
        runtime_decision = runtime_next_step(
            run_ref,
            agent_id=agent,
            result=result,
            emitter=sync_emitter,
        )
    except Exception as exc:
        return Decision(
            kind=DecisionKind.blocked,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=current_step_id or "unknown",
            timestamp=now,
            reason=f"Runtime engine error: {exc}",
            progress=progress,
            origin=origin,
        )

    return _map_runtime_decision(
        runtime_decision,
        agent,
        mission_slug,
        mission_type,
        repo_root,
        feature_dir,
        now,
        progress,
        origin,
    )


def _load_query_run_and_plan(
    mission_slug: str,
    mission_type: str,
    repo_root: Path,
    run_ref: Any | None,
) -> tuple[Any, Any, Any, Path | None]:
    """Load snapshot and plan_next for query mode.

    Returns (run_ref, snapshot, runtime_decision, ephemeral_run_store).
    ephemeral_run_store is non-None when a temporary run was created.
    Raises QueryModeValidationError on failure.
    """
    from spec_kitty_runtime import engine
    from spec_kitty_runtime.planner import plan_next

    ephemeral_run_store: Path | None = None
    try:
        if run_ref is None:
            run_ref, ephemeral_run_store = _start_ephemeral_query_run(
                mission_slug,
                mission_type,
                repo_root,
            )
            snapshot = engine._read_snapshot(Path(run_ref.run_dir))
            template_path = Path(run_ref.run_dir) / "mission_template_frozen.yaml"
        else:
            snapshot = engine._read_snapshot(Path(run_ref.run_dir))
            template_path = Path(snapshot.template_path)
        template = load_mission_template_file(template_path)
        runtime_decision = plan_next(
            snapshot,
            template,
            snapshot.policy_snapshot,
            live_template_path=template_path,
        )
    except QueryModeValidationError:
        raise
    except Exception as exc:
        raise QueryModeValidationError(
            f"Could not read query state for mission '{mission_slug}': {exc}"
        ) from exc

    return run_ref, snapshot, runtime_decision, ephemeral_run_store


def _map_query_runtime_decision(
    agent: str | None,
    mission_slug: str,
    mission_type: str,
    snapshot: Any,
    runtime_decision: Any,
    emitted_run_id: str | None,
    now: str,
    progress: dict | None,
) -> Decision:
    """Map a plan_next result to a query-mode Decision."""
    if not snapshot.completed_steps and not snapshot.pending_decisions and not snapshot.decisions:
        if runtime_decision.kind in {"step", "decision_required"} and runtime_decision.step_id:
            return Decision(
                kind=DecisionKind.query,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state="not_started",
                timestamp=now,
                is_query=True,
                reason=None,
                progress=progress,
                run_id=emitted_run_id,
                preview_step=runtime_decision.step_id,
            )
        raise QueryModeValidationError(
            f"Mission '{mission_type}' has no issuable first step for run '{mission_slug}'"
        )

    if runtime_decision.kind == DecisionKind.decision_required:
        return Decision(
            kind=DecisionKind.query,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=snapshot.issued_step_id or runtime_decision.step_id or "unknown",
            timestamp=now,
            is_query=True,
            reason=None,
            progress=progress,
            run_id=emitted_run_id,
            step_id=snapshot.issued_step_id or runtime_decision.step_id,
            decision_id=runtime_decision.decision_id,
            input_key=runtime_decision.input_key,
            question=runtime_decision.question,
            options=runtime_decision.options,
        )

    mission_state = runtime_decision.step_id or "unknown"
    blocked_reason: str | None = None
    if runtime_decision.kind == "terminal":
        mission_state = "done"
    elif runtime_decision.kind == "blocked":
        mission_state = snapshot.issued_step_id or runtime_decision.step_id or "blocked"
        blocked_reason = snapshot.blocked_reason or getattr(runtime_decision, "reason", None)

    return Decision(
        kind=DecisionKind.query,
        agent=agent,
        mission_slug=mission_slug,
        mission=mission_type,
        mission_state=mission_state,
        timestamp=now,
        is_query=True,
        reason=blocked_reason,
        progress=progress,
        run_id=emitted_run_id,
        step_id=snapshot.issued_step_id or runtime_decision.step_id,
    )


def query_current_state(
    agent: str | None,
    mission_slug: str,
    repo_root: Path,
) -> Decision:
    """Return current mission state without advancing the DAG.

    Reads the run snapshot idempotently. Does NOT call next_step().
    Returns a Decision with kind=DecisionKind.query and is_query=True.

    Args:
        agent: Agent name (for Decision construction only).
        mission_slug: Mission slug (e.g. '069-planning-pipeline-integrity').
        repo_root: Repository root path.
    """
    feature_dir = repo_root / "kitty-specs" / mission_slug
    now = datetime.now(UTC).isoformat()

    if not feature_dir.is_dir():
        return Decision(
            kind=DecisionKind.query,
            agent=agent,
            mission_slug=mission_slug,
            mission="unknown",
            mission_state="unknown",
            timestamp=now,
            is_query=True,
            reason=None,
        )

    mission_type = get_mission_type(feature_dir)
    progress = _compute_wp_progress(feature_dir)

    run_ref = _existing_run_ref(mission_slug, repo_root, mission_type)

    # Read current step WITHOUT calling next_step(). When no step has been
    # issued yet, use the planner read-only to compute a truthful preview.
    # The try/finally below guarantees the ephemeral run store is cleaned up
    # on every return path (success, raise, or early exit).
    ephemeral_run_store: Path | None = None
    try:
        run_ref, snapshot, runtime_decision, ephemeral_run_store = _load_query_run_and_plan(
            mission_slug, mission_type, repo_root, run_ref
        )

        # Query mode never persists the ephemeral run it bootstraps for a
        # not-yet-started mission. Returning that run's id in the JSON would
        # mislead callers into thinking they can issue ``spec-kitty next
        # --mission <slug> --result …`` against it; in reality the run state
        # is wiped in the finally block before the function returns. Only
        # emit ``run_id`` when the run is a real, persisted one.
        emitted_run_id: str | None = None if ephemeral_run_store is not None else getattr(run_ref, "run_id", None)

        return _map_query_runtime_decision(
            agent, mission_slug, mission_type, snapshot, runtime_decision,
            emitted_run_id, now, progress,
        )
    finally:
        if ephemeral_run_store is not None:
            shutil.rmtree(ephemeral_run_store, ignore_errors=True)


def answer_decision_via_runtime(
    mission_slug: str,
    decision_id: str,
    answer: str,
    agent: str,
    repo_root: Path,
    *,
    actor_type: str = "human",
) -> None:
    """Answer a pending decision.

    CLI answers are human-authored by default even though the command still
    carries an ``--agent`` identity for the surrounding mission loop.
    """
    mission_type = get_mission_type(repo_root / "kitty-specs" / mission_slug)
    feature_dir = repo_root / "kitty-specs" / mission_slug
    run_ref = get_or_start_run(mission_slug, repo_root, mission_type)
    sync_emitter = SyncRuntimeEventEmitter.for_feature(
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        mission_type=mission_type,
    )
    try:
        from spec_kitty_runtime.engine import _read_snapshot

        sync_emitter.seed_from_snapshot(_read_snapshot(Path(run_ref.run_dir)))
    except Exception:
        pass
    actor = ActorIdentity(actor_id=agent, actor_type=actor_type)
    runtime_provide_decision_answer(
        run_ref,
        decision_id,
        answer,
        actor,
        emitter=sync_emitter,
    )


# ---------------------------------------------------------------------------
# Internal mapping helpers
# ---------------------------------------------------------------------------


def _build_wp_iteration_decision(
    step_id: str,
    agent: str,
    mission_slug: str,
    mission_type: str,
    feature_dir: Path,
    repo_root: Path,
    timestamp: str,
    progress: dict | None,
    origin: dict,
    run_ref: MissionRunRef,
    guard_failures: list[str] | None = None,
) -> Decision:
    """Build a Decision for WP iteration within a step."""
    action, wp_id, workspace_path = _state_to_action(
        step_id,
        mission_slug,
        feature_dir,
        repo_root,
        mission_type,
    )

    if action is None:
        return Decision(
            kind=DecisionKind.blocked,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=step_id,
            timestamp=timestamp,
            reason=f"No action mapped for step '{step_id}'",
            guard_failures=guard_failures or [],
            progress=progress,
            origin=origin,
            run_id=run_ref.run_id,
            step_id=step_id,
        )

    prompt_file = _build_prompt_safe(
        action,
        feature_dir,
        mission_slug,
        wp_id,
        agent,
        repo_root,
        mission_type,
    )

    return Decision(
        kind=DecisionKind.step,
        agent=agent,
        mission_slug=mission_slug,
        mission=mission_type,
        mission_state=step_id,
        timestamp=timestamp,
        action=action,
        wp_id=wp_id,
        workspace_path=workspace_path,
        prompt_file=prompt_file,
        guard_failures=guard_failures or [],
        progress=progress,
        origin=origin,
        run_id=run_ref.run_id,
        step_id=step_id,
    )


def _resolve_decision_prompt_file(
    decision: Any,
    mission_slug: str,
    agent: str,
) -> str | None:
    """Build a prompt file for a decision_required runtime decision."""
    if not decision.question:
        return None
    from runtime.prompts.builder import build_decision_prompt

    try:
        _, prompt_path = build_decision_prompt(
            question=decision.question,
            options=decision.options,
            decision_id=decision.decision_id or "unknown",
            mission_slug=mission_slug,
            agent=agent,
        )
        return str(prompt_path)
    except Exception:
        return None


def _map_wp_step_to_decision(
    step_id: str,
    run_id: str | None,
    agent: str,
    mission_slug: str,
    mission_type: str,
    feature_dir: Path,
    repo_root: Path,
    timestamp: str,
    progress: dict | None,
    origin: dict,
) -> Decision:
    """Map a WP-iteration step to the appropriate Decision."""
    action, wp_id, workspace_path = _state_to_action(
        step_id, mission_slug, feature_dir, repo_root, mission_type,
    )
    if action is None:
        return Decision(
            kind=DecisionKind.blocked,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=step_id,
            timestamp=timestamp,
            reason=f"No action mapped for WP step '{step_id}'",
            progress=progress,
            origin=origin,
            run_id=run_id,
            step_id=step_id,
        )
    prompt_file = _build_prompt_safe(
        action, feature_dir, mission_slug, wp_id, agent, repo_root, mission_type,
    )
    return Decision(
        kind=DecisionKind.step,
        agent=agent,
        mission_slug=mission_slug,
        mission=mission_type,
        mission_state=step_id,
        timestamp=timestamp,
        action=action,
        wp_id=wp_id,
        workspace_path=workspace_path,
        prompt_file=prompt_file,
        progress=progress,
        origin=origin,
        run_id=run_id,
        step_id=step_id,
    )


def _map_non_wp_step_to_decision(
    step_id: str | None,
    run_id: str | None,
    agent: str,
    mission_slug: str,
    mission_type: str,
    feature_dir: Path,
    repo_root: Path,
    timestamp: str,
    progress: dict | None,
    origin: dict,
) -> Decision:
    """Map a non-WP step to a Decision via template resolution."""
    action, wp_id, workspace_path = _state_to_action(
        step_id or "unknown", mission_slug, feature_dir, repo_root, mission_type,
    )
    prompt_file = (
        _build_prompt_safe(
            action or step_id or "unknown",
            feature_dir, mission_slug, wp_id, agent, repo_root, mission_type,
        )
        if action or step_id
        else None
    )
    return Decision(
        kind=DecisionKind.step,
        agent=agent,
        mission_slug=mission_slug,
        mission=mission_type,
        mission_state=step_id or "unknown",
        timestamp=timestamp,
        action=action or step_id,
        wp_id=wp_id,
        workspace_path=workspace_path,
        prompt_file=prompt_file,
        progress=progress,
        origin=origin,
        run_id=run_id,
        step_id=step_id,
    )


def _map_runtime_decision(
    decision: NextDecision,
    agent: str,
    mission_slug: str,
    mission_type: str,
    repo_root: Path,
    feature_dir: Path,
    timestamp: str,
    progress: dict | None,
    origin: dict,
) -> Decision:
    """Convert runtime NextDecision to CLI Decision dataclass."""
    step_id = decision.step_id
    run_id = decision.run_id

    if decision.kind == "terminal":
        return Decision(
            kind=DecisionKind.terminal,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state="done",
            timestamp=timestamp,
            reason=decision.reason or "Mission complete",
            progress=progress,
            origin=origin,
            run_id=run_id,
            step_id=step_id,
        )

    if decision.kind == "blocked":
        return Decision(
            kind=DecisionKind.blocked,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=step_id or "unknown",
            timestamp=timestamp,
            reason=decision.reason,
            progress=progress,
            origin=origin,
            run_id=run_id,
            step_id=step_id,
        )

    if decision.kind == "decision_required":
        prompt_file = _resolve_decision_prompt_file(decision, mission_slug, agent)
        return Decision(
            kind=DecisionKind.decision_required,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=step_id or "unknown",
            timestamp=timestamp,
            reason=decision.reason or "Decision required",
            progress=progress,
            origin=origin,
            run_id=run_id,
            step_id=step_id,
            decision_id=decision.decision_id,
            input_key=decision.input_key,
            question=decision.question,
            options=decision.options,
            prompt_file=prompt_file,
        )

    # kind == "step"
    if step_id and _is_wp_iteration_step(step_id):
        return _map_wp_step_to_decision(
            step_id, run_id, agent, mission_slug, mission_type,
            feature_dir, repo_root, timestamp, progress, origin,
        )

    return _map_non_wp_step_to_decision(
        step_id, run_id, agent, mission_slug, mission_type,
        feature_dir, repo_root, timestamp, progress, origin,
    )
