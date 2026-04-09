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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
from specify_cli.status.transitions import resolve_lane_alias
from specify_cli.next.decision import (
    Decision,
    DecisionKind,
    _build_prompt_safe,
    _compute_wp_progress,
    _find_first_wp_by_lane,
    _state_to_action,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Feature → Run index
# ---------------------------------------------------------------------------

_FEATURE_RUNS_FILE = "feature-runs.json"


def _feature_runs_path(repo_root: Path) -> Path:
    return repo_root / ".kittify" / "runtime" / _FEATURE_RUNS_FILE


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


def _should_advance_wp_step(step_id: str, feature_dir: Path) -> bool:
    """Check if all WPs are done for this phase, meaning we should advance.

    For implement: all WPs must be handed off or complete
    (for_review, approved, or done).
    For review: all WPs must be approved or done.
    """
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.is_dir():
        return True  # no WPs to iterate over

    wp_files = sorted(tasks_dir.glob("WP*.md"))
    if not wp_files:
        return True

    # Get canonical lane state from event log (hard-fail if absent)
    import re as _re
    from specify_cli.status.lane_reader import get_wp_lane

    for wp_file in wp_files:
        wp_match = _re.match(r"(WP\d+)", wp_file.stem)
        wp_id = wp_match.group(1) if wp_match else wp_file.stem
        lane = resolve_lane_alias(get_wp_lane(feature_dir, wp_id))
        if step_id == "implement":
            if lane not in ("done", "approved", "for_review"):
                return False
        elif step_id == "review":
            if lane not in ("done", "approved"):
                return False

    return True


# ---------------------------------------------------------------------------
# Guard evaluation (CLI-level, not runtime-level)
# ---------------------------------------------------------------------------


def _check_cli_guards(step_id: str, feature_dir: Path) -> list[str]:
    """Check CLI-level guard conditions before completing a step.

    Returns list of failure descriptions. Empty list means all guards pass.
    """
    failures: list[str] = []

    if step_id == "specify":
        if not (feature_dir / "spec.md").exists():
            failures.append("Required artifact missing: spec.md")

    elif step_id == "plan":
        if not (feature_dir / "plan.md").exists():
            failures.append("Required artifact missing: plan.md")

    elif step_id == "tasks_outline":
        if not (feature_dir / "tasks.md").exists():
            failures.append("Required artifact missing: tasks.md")

    elif step_id == "tasks_packages":
        tasks_dir = feature_dir / "tasks"
        if not tasks_dir.is_dir() or not list(tasks_dir.glob("WP*.md")):
            failures.append("Required: at least one tasks/WP*.md file")

    elif step_id == "tasks_finalize":
        tasks_dir = feature_dir / "tasks"
        if not tasks_dir.is_dir():
            failures.append("Required: tasks/ directory with finalized WP files")
        else:
            wp_files = sorted(tasks_dir.glob("WP*.md"))
            if not wp_files:
                failures.append("Required: at least one tasks/WP*.md file")
            else:
                for wp_file in wp_files:
                    if not _has_raw_dependencies_field(wp_file):
                        failures.append(
                            f"WP {wp_file.stem} missing 'dependencies' in frontmatter "
                            f"(run 'spec-kitty agent mission finalize-tasks')"
                        )
                        break  # One failure message is enough

    elif step_id == "implement":
        if not _should_advance_wp_step("implement", feature_dir):
            failures.append(
                "Not all work packages have required status (for_review, approved, or done)"
            )

    elif step_id == "review":
        if not _should_advance_wp_step("review", feature_dir):
            failures.append("Not all work packages are approved or done")

    return failures


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
    package_root = Path(__file__).resolve().parent.parent / "missions"
    return DiscoveryContext(
        project_dir=repo_root,
        builtin_roots=[package_root],
    )


def _split_env_paths(value: str) -> list[Path]:
    if not value.strip():
        return []
    return [Path(chunk) for chunk in value.split(os.pathsep) if chunk.strip()]


def _project_config_pack_paths(repo_root: Path) -> list[Path]:
    config_file = repo_root / ".kittify" / "config.yaml"
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
        if root.name in {"mission-runtime.yaml", "mission.yaml"}:
            candidates.append(root)
    elif root.exists() and root.is_dir():
        candidates.extend([
            root / mission_type / "mission-runtime.yaml",
            root / mission_type / "mission.yaml",
            root / "missions" / mission_type / "mission-runtime.yaml",
            root / "missions" / mission_type / "mission.yaml",
            root / "mission-runtime.yaml",
            root / "mission.yaml",
        ])

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
        if candidate.name == "mission.yaml":
            runtime_sidecar = candidate.with_name("mission-runtime.yaml")
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
        [repo_root / ".kittify" / "overrides" / "missions"],
        [repo_root / ".kittify" / "missions"],
        [context.user_home / ".kittify" / "missions"],
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


def get_or_start_run(
    mission_slug: str,
    repo_root: Path,
    mission_type: str,
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
            stored_mission_type = (
                entry.get("mission_type")
                or entry.get("mission_key")
                or mission_type
            )
            return _build_run_ref(
                run_id=entry["run_id"],
                run_dir=entry["run_dir"],
                mission_type=stored_mission_type,
            )

    # Start a new run
    run_store = repo_root / ".kittify" / "runtime" / "runs"
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
    now = datetime.now(timezone.utc).isoformat()

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

    # Resolve origin info
    origin: dict[str, Any] = {}
    try:
        from specify_cli.runtime.resolver import resolve_mission as resolve_mission_path
        mission_result = resolve_mission_path(mission_type, repo_root)
        origin = {
            "mission_tier": getattr(mission_result.tier, "value", str(mission_result.tier)),
            "mission_path": str(mission_result.path.parent),
        }
    except FileNotFoundError:
        origin = {"mission_tier": "unknown", "mission_path": "unknown"}

    progress = _compute_wp_progress(feature_dir)

    # Get or start runtime run (before result handling so failed/blocked
    # decisions include canonical run_id, step_id, and mission_state)
    try:
        run_ref = get_or_start_run(mission_slug, repo_root, mission_type)
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
    except Exception:
        current_step_id = None

    # WP iteration check: if we're on a WP step and WPs remain, don't advance runtime
    if result == "success" and current_step_id and _is_wp_iteration_step(current_step_id):
        if not _should_advance_wp_step(current_step_id, feature_dir):
            # Stay in current step, return WP-level action
            return _build_wp_iteration_decision(
                current_step_id, agent, mission_slug, mission_type,
                feature_dir, repo_root, now, progress, origin, run_ref,
            )
        # All WPs done for this step — check guards before advancing
        guard_failures = _check_cli_guards(current_step_id, feature_dir)
        if guard_failures:
            return _build_wp_iteration_decision(
                current_step_id, agent, mission_slug, mission_type,
                feature_dir, repo_root, now, progress, origin, run_ref,
                guard_failures=guard_failures,
            )

    # Check guards for non-WP steps before advancing
    if result == "success" and current_step_id and not _is_wp_iteration_step(current_step_id):
        guard_failures = _check_cli_guards(current_step_id, feature_dir)
        if guard_failures:
            action, wp_id, workspace_path = _state_to_action(
                current_step_id, mission_slug, feature_dir, repo_root, mission_type,
            )
            prompt_file = _build_prompt_safe(
                action or current_step_id, feature_dir, mission_slug,
                wp_id, agent, repo_root, mission_type,
            ) if action else None
            return Decision(
                kind=DecisionKind.step,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state=current_step_id,
                timestamp=now,
                action=action,
                wp_id=wp_id,
                workspace_path=workspace_path,
                prompt_file=prompt_file,
                guard_failures=guard_failures,
                progress=progress,
                origin=origin,
                run_id=run_ref.run_id,
                step_id=current_step_id,
            )

    # Advance via runtime
    try:
        runtime_decision = runtime_next_step(
            run_ref,
            agent_id=agent,
            result=result,
            emitter=NullEmitter(),
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
        runtime_decision, agent, mission_slug, mission_type,
        repo_root, feature_dir, now, progress, origin,
    )


def query_current_state(
    agent: str,
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
    now = datetime.now(timezone.utc).isoformat()

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

    try:
        run_ref = get_or_start_run(mission_slug, repo_root, mission_type)
    except Exception:
        return Decision(
            kind=DecisionKind.query,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state="unknown",
            timestamp=now,
            is_query=True,
            reason=None,
            progress=progress,
        )

    # Read current step WITHOUT calling next_step()
    current_step_id = "unknown"
    try:
        from spec_kitty_runtime.engine import _read_snapshot  # private API — see note
        snapshot = _read_snapshot(Path(run_ref.run_dir))
        current_step_id = snapshot.issued_step_id or "unknown"
    except Exception:
        pass  # Unknown step is safe — query mode still returns useful output

    return Decision(
        kind=DecisionKind.query,
        agent=agent,
        mission_slug=mission_slug,
        mission=mission_type,
        mission_state=current_step_id,
        timestamp=now,
        is_query=True,
        reason=None,   # label printed by _print_human(); not in reason field
        progress=progress,
        run_id=getattr(run_ref, "run_id", None),
    )


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
    run_ref = get_or_start_run(mission_slug, repo_root, mission_type)
    actor = ActorIdentity(actor_id=agent, actor_type=actor_type)
    runtime_provide_decision_answer(
        run_ref, decision_id, answer, actor,
        emitter=NullEmitter(),
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
            reason=f"No action mapped for step '{step_id}'",
            guard_failures=guard_failures or [],
            progress=progress,
            origin=origin,
            run_id=run_ref.run_id,
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
        guard_failures=guard_failures or [],
        progress=progress,
        origin=origin,
        run_id=run_ref.run_id,
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
        prompt_file = None
        if decision.question:
            from specify_cli.next.prompt_builder import build_decision_prompt
            try:
                _, prompt_path = build_decision_prompt(
                    question=decision.question,
                    options=decision.options,
                    decision_id=decision.decision_id or "unknown",
                    mission_slug=mission_slug,
                    agent=agent,
                )
                prompt_file = str(prompt_path)
            except Exception:
                pass

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
        # WP step: map to implement/review action with WP selection
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

    # Non-WP step: map step_id to action via template resolution
    action, wp_id, workspace_path = _state_to_action(
        step_id or "unknown", mission_slug, feature_dir, repo_root, mission_type,
    )
    prompt_file = _build_prompt_safe(
        action or step_id or "unknown", feature_dir, mission_slug,
        wp_id, agent, repo_root, mission_type,
    ) if action or step_id else None

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
