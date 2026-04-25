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
from datetime import UTC, datetime
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
from specify_cli.status.lane_reader import CanonicalStatusNotFoundError
from specify_cli.status.models import Lane
from specify_cli.status.wp_state import wp_state_for
from specify_cli.next.decision import (
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
        raw_lane = get_wp_lane(feature_dir, wp_id)
        try:
            state = wp_state_for(raw_lane)
        except ValueError:
            # Unknown lane (e.g. "uninitialized" before status bootstrap) — treat as
            # not-yet-handed-off, so this WP blocks advancement.
            return False
        lane = state.lane
        if step_id == "implement":
            # Advance past implement only when the WP has been handed off
            # (for_review or approved) or completed (done/canceled).
            # is_run_affecting is True for all active lanes; we further restrict
            # to only allow advancement for the "handed off" active lanes.
            if state.is_run_affecting and lane not in (Lane.FOR_REVIEW, Lane.APPROVED):
                return False
            # A blocked WP is not run_affecting but also not handed off — blocks advancement.
            if state.is_blocked:
                return False
        elif step_id == "review":
            if lane not in (Lane.DONE, Lane.APPROVED):
                return False

    return True


# ---------------------------------------------------------------------------
# Guard evaluation (CLI-level, not runtime-level)
# ---------------------------------------------------------------------------


def _check_cli_guards(step_id: str, feature_dir: Path) -> list[str]:  # noqa: C901
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
                        failures.append(f"WP {wp_file.stem} missing 'dependencies' in frontmatter (run 'spec-kitty agent mission finalize-tasks')")
                        break  # One failure message is enough

    elif step_id == "implement":
        if not _should_advance_wp_step("implement", feature_dir):
            failures.append("Not all work packages have required status (for_review, approved, or done)")

    elif step_id == "review" and not _should_advance_wp_step("review", feature_dir):
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
# Composition dispatch (WP02 / mission software-dev-composition-rewrite-01KQ26CY)
# ---------------------------------------------------------------------------
#
# These helpers route the live runtime path for the built-in ``software-dev``
# mission's five public actions (``specify``, ``plan``, ``tasks``,
# ``implement``, ``review``) through ``StepContractExecutor.execute`` instead
# of the legacy mission-runtime.yaml DAG step handlers. All other missions and
# step IDs continue to fall through to the runtime planner path unchanged
# (constraint C-008).
#
# Constraints active here:
#   - C-001: the composition path MUST go through ``StepContractExecutor``;
#     never call ``ProfileInvocationExecutor`` directly.
#   - C-002: composition produces invocation payloads; this bridge does NOT
#     generate text or call models.
#   - C-003 / FR-007: any lane-state writes inside composed steps go through
#     ``emit_status_transition`` -- this bridge writes no raw lane strings.
#   - C-008: dispatch is hard-guarded on ``mission == "software-dev"``.

_COMPOSED_ACTIONS_BY_MISSION: dict[str, frozenset[str]] = {
    "software-dev": frozenset({"specify", "plan", "tasks", "implement", "review"}),
}

# Legacy run snapshots and project-local templates may still contain the old
# tasks substep IDs. Normalize them into the single public ``tasks`` action so
# existing in-flight missions can advance through the composition path.
_LEGACY_TASKS_STEP_IDS: frozenset[str] = frozenset(
    {"tasks_outline", "tasks_packages", "tasks_finalize"}
)


def _normalize_action_for_composition(step_id: str) -> str:
    """Map a legacy DAG step ID to its composed action ID.

    The legacy ``mission-runtime.yaml`` splits ``tasks`` into three steps;
    the composition layer exposes a single ``tasks`` action whose contract
    holds the substructure internally. All other step IDs pass through
    unchanged.
    """
    if step_id in _LEGACY_TASKS_STEP_IDS:
        return "tasks"
    return step_id


def _should_dispatch_via_composition(mission: str, step_id: str) -> bool:
    """Return True iff ``(mission, step_id)`` routes through composition.

    Hard-guarded on ``mission == "software-dev"`` (C-008). For any other
    mission, returns False unconditionally so the bridge falls through to the
    legacy DAG handler.
    """
    composed = _COMPOSED_ACTIONS_BY_MISSION.get(mission)
    if composed is None:
        return False
    return _normalize_action_for_composition(step_id) in composed


def _check_composed_action_guard(  # noqa: C901
    action: str,
    feature_dir: Path,
    *,
    legacy_step_id: str | None = None,
) -> list[str]:
    """CLI-level guards that fire AFTER a composed action completes.

    Mirrors ``_check_cli_guards`` semantics for the five composed actions.

    For ``tasks``, the assertion shape depends on which surface invoked us:

    * **Legacy DAG path** (``legacy_step_id`` is ``"tasks_outline"`` /
      ``"tasks_packages"`` / ``"tasks_finalize"``): the runtime engine fires
      the bridge **once per substep**, so the guard must reflect the artifact
      state the user is **expected** to have produced **at that substep**, not
      the terminal post-finalize state. Demanding the terminal state on
      ``tasks_outline`` blocks the user with "Required: at least one
      tasks/WP*.md file" while the surfaced retry action is still
      ``tasks-outline`` — an unsatisfiable loop. (Mission-review follow-up to
      the original WP02 collapsed guard, which conflated dispatch
      normalization with guard semantics.)

    * **Composition-only path** (``legacy_step_id`` is ``None``): a direct
      ``action="tasks"`` invocation represents the terminal state of the
      whole composed action; the guard demands the **union** of all three
      legacy substep checks (no weakening).

    Returns a list of failure descriptions; an empty list means all guards
    pass.
    """
    failures: list[str] = []

    if action == "specify":
        if not (feature_dir / "spec.md").exists():
            failures.append("Required artifact missing: spec.md")

    elif action == "plan":
        if not (feature_dir / "plan.md").exists():
            failures.append("Required artifact missing: plan.md")

    elif action == "tasks":
        if legacy_step_id == "tasks_outline":
            # After tasks_outline the user is expected to have produced
            # tasks.md. WP files and dependencies come in later substeps.
            if not (feature_dir / "tasks.md").exists():
                failures.append("Required artifact missing: tasks.md")
        elif legacy_step_id == "tasks_packages":
            # After tasks_packages: tasks.md AND >=1 WP file. Dependencies
            # are not yet expected — finalize-tasks adds them in the next
            # substep.
            if not (feature_dir / "tasks.md").exists():
                failures.append("Required artifact missing: tasks.md")
            tasks_dir = feature_dir / "tasks"
            if not tasks_dir.is_dir() or not list(tasks_dir.glob("WP*.md")):
                failures.append("Required: at least one tasks/WP*.md file")
        else:
            # legacy_step_id == "tasks_finalize" OR composition-only
            # (legacy_step_id is None): demand the full terminal state.
            # Union of legacy tasks_outline + tasks_packages + tasks_finalize
            # checks; no weakening of assertions.
            if not (feature_dir / "tasks.md").exists():
                failures.append("Required artifact missing: tasks.md")
            tasks_dir = feature_dir / "tasks"
            if not tasks_dir.is_dir() or not list(tasks_dir.glob("WP*.md")):
                failures.append("Required: at least one tasks/WP*.md file")
            else:
                for wp_file in sorted(tasks_dir.glob("WP*.md")):
                    if not _has_raw_dependencies_field(wp_file):
                        failures.append(
                            f"WP {wp_file.stem} missing 'dependencies' in frontmatter "
                            "(run 'spec-kitty agent mission finalize-tasks')"
                        )
                        break  # One failure message is enough

    elif action == "implement":
        if not _should_advance_wp_step("implement", feature_dir):
            failures.append(
                "Not all work packages have required status (for_review, approved, or done)"
            )

    elif action == "review" and not _should_advance_wp_step("review", feature_dir):
        failures.append("Not all work packages are approved or done")

    return failures


def _dispatch_via_composition(
    *,
    repo_root: Path,
    mission: str,
    action: str,
    actor: str,
    profile_hint: str | None,
    request_text: str | None,
    mode_of_work: Any | None,
    feature_dir: Path,
    legacy_step_id: str | None = None,
) -> list[str] | None:
    """Run a composed action via ``StepContractExecutor``; then guard.

    Returns:
      - ``None`` on success (composition succeeded AND post-action guard
        passed). The caller should continue to the runtime planner advance call
        so run state progresses to the next step.
      - A non-empty list of failure descriptions if the executor raised
        ``StepContractExecutionError`` (FR-009: structured CLI surface, not a
        Python traceback) or the post-action guard failed. The caller turns
        this into a ``Decision`` with ``guard_failures`` populated.

    Constraint C-001 is preserved: this function only ever invokes
    ``StepContractExecutor.execute``; it never touches
    ``ProfileInvocationExecutor`` directly.

    The follow-up ``runtime_next_step`` call is only run-state planning. The
    action dispatch for the five public ``software-dev`` actions happens here,
    through composition, before the planner advances.
    """
    # Local import keeps module load lean and avoids circular import risk.
    from specify_cli.mission_step_contracts.executor import (
        StepContractExecutionContext,
        StepContractExecutionError,
        StepContractExecutor,
    )

    context = StepContractExecutionContext(
        repo_root=repo_root,
        mission=mission,
        action=action,
        actor=actor or "unknown",
        profile_hint=profile_hint,
        request_text=request_text,
        mode_of_work=mode_of_work,
    )
    try:
        result = StepContractExecutor(repo_root=repo_root).execute(context)
    except StepContractExecutionError as exc:
        # Structured CLI failure surface (FR-009) — caller turns this into a
        # Decision; no Python traceback escapes.
        return [f"composition failed for {mission}/{action}: {exc}"]
    except Exception as exc:  # noqa: BLE001 — FR-009 contract: any executor
        # exception class must surface as a structured CLI failure rather than
        # a Python traceback. The narrow ``StepContractExecutionError`` catch
        # above handles the documented executor failure mode; this widened
        # catch defends against contract drift (e.g., a future executor change
        # that raises ``ValueError`` from a malformed YAML, or a transient
        # ``OSError`` reading a contract file). The exception detail is logged
        # for operator triage; the structured surface preserves the FR-009 UX.
        logger.exception(
            "unexpected exception in composition for %s/%s", mission, action
        )
        return [
            f"composition crashed for {mission}/{action}: "
            f"{type(exc).__name__}: {exc}"
        ]

    # FR-008: forward the invocation_id chain produced by the executor to the
    # bridge log so downstream event/trail writers and operators can correlate
    # the composed action with its underlying ProfileInvocationExecutor calls.
    # Defensive ``getattr`` + duck-typed length so test mocks (MagicMock) and
    # real ``StepContractExecutionResult`` instances both flow through cleanly.
    invocation_ids = getattr(result, "invocation_ids", ()) or ()
    try:
        invocation_count = len(invocation_ids)
    except TypeError:
        invocation_count = 0
    logger.info(
        "composed %s/%s emitted %d invocation(s): %s",
        mission,
        action,
        invocation_count,
        invocation_ids,
    )

    failures = _check_composed_action_guard(
        action, feature_dir, legacy_step_id=legacy_step_id
    )
    if failures:
        return failures
    return None


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
        candidates.extend(
            [
                root / mission_type / "mission-runtime.yaml",
                root / mission_type / "mission.yaml",
                root / "missions" / mission_type / "mission-runtime.yaml",
                root / "missions" / mission_type / "mission.yaml",
                root / "mission-runtime.yaml",
                root / "mission.yaml",
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
    explicit -> env -> project override -> project legacy -> project config
    -> user global -> built-in.

    For the built-in ``software-dev`` mission, the packaged runtime template is
    canonical after this composition rewrite. Stale user-global mission packs
    from earlier installs must not reintroduce the legacy tasks_* DAG, while
    explicit, env, and project-scoped overrides remain honored.
    """
    context = _build_discovery_context(repo_root)
    env_value = os.environ.get(context.env_var_name, "")
    project_tiers: list[list[Path]] = [
        list(context.explicit_paths),
        _split_env_paths(env_value),
        [repo_root / ".kittify" / "overrides" / "missions"],
        [repo_root / ".kittify" / "missions"],
        _project_config_pack_paths(repo_root),
    ]
    global_tier = [context.user_home / ".kittify" / "missions"]
    builtin_tier = list(context.builtin_roots)
    tiers = (
        project_tiers + [builtin_tier, global_tier]
        if mission_type == "software-dev"
        else project_tiers + [global_tier, builtin_tier]
    )

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
    run_store = repo_root / ".kittify" / "runtime" / "runs"
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

    # WP iteration check: if we're on a WP step and WPs remain, don't advance runtime
    if result == "success" and current_step_id and _is_wp_iteration_step(current_step_id):
        try:
            should_advance = _should_advance_wp_step(current_step_id, feature_dir)
        except CanonicalStatusNotFoundError as exc:
            return Decision(
                kind=DecisionKind.blocked,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state=current_step_id,
                timestamp=now,
                reason=str(exc),
                guard_failures=[str(exc)],
                progress=progress,
                origin=origin,
                run_id=run_ref.run_id,
                step_id=current_step_id,
            )
        if not should_advance:
            # Stay in current step, return WP-level action
            return _build_wp_iteration_decision(
                current_step_id,
                agent,
                mission_slug,
                mission_type,
                feature_dir,
                repo_root,
                now,
                progress,
                origin,
                run_ref,
            )
        # All WPs done for this step — check guards before advancing
        guard_failures = _check_cli_guards(current_step_id, feature_dir)
        if guard_failures:
            return _build_wp_iteration_decision(
                current_step_id,
                agent,
                mission_slug,
                mission_type,
                feature_dir,
                repo_root,
                now,
                progress,
                origin,
                run_ref,
                guard_failures=guard_failures,
            )

    # Check guards for non-WP steps before advancing
    if result == "success" and current_step_id and not _is_wp_iteration_step(current_step_id):
        guard_failures = _check_cli_guards(current_step_id, feature_dir)
        if guard_failures:
            action, wp_id, workspace_path = _state_to_action(
                current_step_id,
                mission_slug,
                feature_dir,
                repo_root,
                mission_type,
            )
            prompt_file = (
                _build_prompt_safe(
                    action or current_step_id,
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

    # Composition dispatch (mission `software-dev-composition-rewrite-01KQ26CY`).
    #
    # For the built-in `software-dev` mission's five public actions, route the
    # just-completed step through `StepContractExecutor.execute` BEFORE we let
    # the runtime planner advance run state. The composition produces the
    # invocation_id chain (host harness interprets it); a structured guard
    # failure surface (Decision.kind=blocked, guard_failures populated) is
    # used in lieu of a Python traceback when the executor raises
    # `StepContractExecutionError`. C-008 hard-guards this on
    # `mission == "software-dev"`; every other mission falls through to the
    # runtime planner unchanged.
    if (
        result == "success"
        and current_step_id
        and _should_dispatch_via_composition(mission_type, current_step_id)
    ):
        composed_action = _normalize_action_for_composition(current_step_id)
        composition_failures = _dispatch_via_composition(
            repo_root=repo_root,
            mission=mission_type,
            action=composed_action,
            actor=agent,
            profile_hint=None,
            request_text=None,
            mode_of_work=None,
            feature_dir=feature_dir,
            # Thread the original step_id so the post-action guard can branch
            # on substep semantics for legacy tasks_outline/tasks_packages/
            # tasks_finalize. Without this, the collapsed guard demands the
            # terminal post-finalize state on every substep and blocks the
            # live tasks_outline → tasks_packages → tasks_finalize flow.
            legacy_step_id=current_step_id,
        )
        if composition_failures:
            action, wp_id, workspace_path = _state_to_action(
                current_step_id,
                mission_slug,
                feature_dir,
                repo_root,
                mission_type,
            )
            prompt_file = (
                _build_prompt_safe(
                    action or current_step_id,
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
                kind=DecisionKind.blocked,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state=current_step_id,
                timestamp=now,
                reason=composition_failures[0],
                action=action,
                wp_id=wp_id,
                workspace_path=workspace_path,
                prompt_file=prompt_file,
                guard_failures=composition_failures,
                progress=progress,
                origin=origin,
                run_id=run_ref.run_id,
                step_id=current_step_id,
            )
        # Composition succeeded; fall through to the runtime planner advance so
        # run state progresses to the next step.

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
    ephemeral_run_store: Path | None = None

    # Read current step WITHOUT calling next_step(). When no step has been
    # issued yet, use the planner read-only to compute a truthful preview.
    # The try/finally below guarantees the ephemeral run store is cleaned up
    # on every return path (success, raise, or early exit).
    try:
        try:
            from spec_kitty_runtime import engine
            from spec_kitty_runtime.planner import plan_next

            if run_ref is None:
                run_ref, ephemeral_run_store = _start_ephemeral_query_run(
                    mission_slug,
                    mission_type,
                    repo_root,
                )
                snapshot = engine._read_snapshot(Path(run_ref.run_dir))
                template_path = Path(run_ref.run_dir) / "mission_template_frozen.yaml"
                template = load_mission_template_file(template_path)
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
            raise QueryModeValidationError(f"Could not read query state for mission '{mission_slug}': {exc}") from exc

        # Query mode never persists the ephemeral run it bootstraps for a
        # not-yet-started mission. Returning that run's id in the JSON would
        # mislead callers into thinking they can issue ``spec-kitty next
        # --mission <slug> --result …`` against it; in reality the run state
        # is wiped in the finally block before the function returns. Only
        # emit ``run_id`` when the run is a real, persisted one.
        emitted_run_id: str | None = None
        if ephemeral_run_store is None:
            emitted_run_id = getattr(run_ref, "run_id", None)

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
            raise QueryModeValidationError(f"Mission '{mission_type}' has no issuable first step for run '{mission_slug}'")

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
                reason=f"No action mapped for WP step '{step_id}'",
                progress=progress,
                origin=origin,
                run_id=run_id,
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
            progress=progress,
            origin=origin,
            run_id=run_id,
            step_id=step_id,
        )

    # Non-WP step: map step_id to action via template resolution
    action, wp_id, workspace_path = _state_to_action(
        step_id or "unknown",
        mission_slug,
        feature_dir,
        repo_root,
        mission_type,
    )
    prompt_file = (
        _build_prompt_safe(
            action or step_id or "unknown",
            feature_dir,
            mission_slug,
            wp_id,
            agent,
            repo_root,
            mission_type,
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
