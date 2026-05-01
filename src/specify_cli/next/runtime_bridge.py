"""Bridge between CLI ``decide_next()`` and the CLI-internal ``_internal_runtime`` engine.

The runtime is now internalized as part of mission
``shared-package-boundary-cutover-01KQ22DS``; production code no longer imports
the standalone ``spec-kitty-runtime`` PyPI package.

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
from specify_cli.next._internal_runtime import (
    DiscoveryContext,
    MissionPolicySnapshot,
    MissionRunRef,
    NextDecision,
    NullEmitter,
    next_step as runtime_next_step,
    provide_decision_answer as runtime_provide_decision_answer,
    start_mission_run,
)
from specify_cli.next._internal_runtime.schema import ActorIdentity, load_mission_template_file

from specify_cli.core.atomic import atomic_write
from specify_cli.mission import get_mission_type
from specify_cli.status.lane_reader import CanonicalStatusNotFoundError
from specify_cli.status.models import Lane
from specify_cli.status.wp_state import wp_state_for
from specify_cli.next.decision import (
    Decision,
    DecisionKind,
    InvalidStepDecision,
    _build_prompt_or_error,
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


class _BufferingRuntimeEmitter:
    """Records runtime emit calls in order and replays them on flush.

    Used on the legacy DAG dispatch path when the retrospective gate is
    opted in: the engine's ``next_step()`` synchronously calls the
    emitter's ``emit_mission_run_completed`` (and its sync side-effects:
    remote dispatch, queueing, etc.) the moment a terminal advance lands.
    A naive rollback that only restores local files would leave those
    sync events fired and unretractable.

    The buffer captures every emit call in order. After the engine
    returns, the bridge either flushes the buffer to the real emitter
    (gate allowed) or drops it (gate blocked). The ``flush`` is a single
    one-shot replay; subsequent calls flush nothing.

    Implements the ``RuntimeEventEmitter`` Protocol structurally — every
    emit method records ``(method_name, payload)`` and returns ``None``.
    """

    def __init__(self) -> None:
        self._calls: list[tuple[str, Any]] = []
        self._flushed = False

    def _record(self, method_name: str, payload: Any) -> None:
        self._calls.append((method_name, payload))

    def emit_mission_run_started(self, payload: Any) -> None:
        self._record("emit_mission_run_started", payload)

    def emit_next_step_issued(self, payload: Any) -> None:
        self._record("emit_next_step_issued", payload)

    def emit_next_step_auto_completed(self, payload: Any) -> None:
        self._record("emit_next_step_auto_completed", payload)

    def emit_decision_input_requested(self, payload: Any) -> None:
        self._record("emit_decision_input_requested", payload)

    def emit_decision_input_answered(self, payload: Any) -> None:
        self._record("emit_decision_input_answered", payload)

    def emit_mission_run_completed(self, payload: Any) -> None:
        self._record("emit_mission_run_completed", payload)

    def emit_significance_evaluated(self, payload: Any) -> None:
        self._record("emit_significance_evaluated", payload)

    def emit_decision_timeout_expired(self, payload: Any) -> None:
        self._record("emit_decision_timeout_expired", payload)

    def seed_from_snapshot(self, snapshot: Any) -> None:
        # Pass-through for SyncRuntimeEventEmitter compatibility; not
        # buffered because seed is idempotent and side-effect-free.
        del snapshot

    def call_count(self) -> int:
        return len(self._calls)

    def discard(self) -> None:
        """Drop all buffered calls without replaying them."""
        self._calls.clear()
        self._flushed = True

    def flush(self, target: Any) -> None:
        """Replay all buffered calls into ``target`` and mark as flushed.

        Re-flushing is a no-op so the same buffer can safely be passed
        through multiple paths without double-emitting.
        """
        if self._flushed:
            return
        for method_name, payload in self._calls:
            method = getattr(target, method_name, None)
            if method is None:
                continue
            method(payload)
        # Also seed phase state on the target from any buffered events that
        # imply phase transitions, since the buffered emitter did not run
        # the SyncRuntimeEventEmitter's _enter_phase logic.
        self._calls.clear()
        self._flushed = True


def _rich_hic_prompt() -> tuple[bool, str | None]:
    """Operator-facing Rich prompt for the HiC retrospective lifecycle.

    Lives in the bridge layer so the ``_internal_runtime/`` package keeps a
    rich/typer-free import surface (test_internal_runtime_parity).
    """
    from rich.prompt import Confirm, Prompt

    run_now: bool = Confirm.ask("Run retrospective now?", default=True)
    if run_now:
        return True, None

    skip_reason: str = ""
    while not skip_reason.strip():
        skip_reason = Prompt.ask("Skip reason (required, must be non-empty)")
    return False, skip_reason.strip()


def _resolve_mission_id_for_terminus(feature_dir: Path) -> str:
    """Read the canonical ULID mission_id from ``meta.json`` next to the feature.

    Used by the retrospective terminus wiring to identify the mission for
    event emission and gate consultation. Falls back to the feature_dir name
    when meta.json is missing or malformed (older missions predating the
    ULID identity rollout); the gate handles missing identities defensively.
    """
    meta_path = feature_dir / "meta.json"
    if not meta_path.exists():
        return feature_dir.name
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return feature_dir.name
    mission_id = meta.get("mission_id") if isinstance(meta, dict) else None
    if isinstance(mission_id, str) and mission_id.strip():
        return mission_id
    return feature_dir.name


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


SPEC_ARTIFACT = "spec.md"
PLAN_ARTIFACT = "plan.md"
TASKS_ARTIFACT = "tasks.md"
STATE_FILE = "state.json"
TASKS_GLOB = "WP*.md"
MISSING_ARTIFACT_MESSAGE = "Required artifact missing: {name}"
MISSING_TASK_FILES_MESSAGE = f"Required: at least one tasks/{TASKS_GLOB} file"


def _check_cli_guards(step_id: str, feature_dir: Path) -> list[str]:  # noqa: C901
    """Check CLI-level guard conditions before completing a step.

    Returns list of failure descriptions. Empty list means all guards pass.
    """
    failures: list[str] = []

    if step_id == "specify":
        if not (feature_dir / SPEC_ARTIFACT).exists():
            failures.append(MISSING_ARTIFACT_MESSAGE.format(name=SPEC_ARTIFACT))

    elif step_id == "plan":
        if not (feature_dir / PLAN_ARTIFACT).exists():
            failures.append(MISSING_ARTIFACT_MESSAGE.format(name=PLAN_ARTIFACT))

    elif step_id == "tasks_outline":
        if not (feature_dir / TASKS_ARTIFACT).exists():
            failures.append(MISSING_ARTIFACT_MESSAGE.format(name=TASKS_ARTIFACT))

    elif step_id == "tasks_packages":
        tasks_dir = feature_dir / "tasks"
        if not tasks_dir.is_dir() or not list(tasks_dir.glob(TASKS_GLOB)):
            failures.append(MISSING_TASK_FILES_MESSAGE)

    elif step_id == "tasks_finalize":
        tasks_dir = feature_dir / "tasks"
        if not tasks_dir.is_dir():
            failures.append("Required: tasks/ directory with finalized WP files")
        else:
            wp_files = sorted(tasks_dir.glob(TASKS_GLOB))
            if not wp_files:
                failures.append(MISSING_TASK_FILES_MESSAGE)
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
    "research": frozenset({"scoping", "methodology", "gathering", "synthesis", "output"}),
    "documentation": frozenset({"discover", "audit", "design", "generate", "validate", "publish"}),
}

# Legacy run snapshots and project-local templates may still contain the old
# tasks substep IDs. Normalize them into the single public ``tasks`` action so
# existing in-flight missions can advance through the composition path.
_LEGACY_TASKS_STEP_IDS: frozenset[str] = frozenset({"tasks_outline", "tasks_packages", "tasks_finalize"})


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


def _should_dispatch_via_composition(
    mission: str,
    step_id: str,
    *,
    run_dir: Path | None = None,
) -> bool:
    """Return True iff ``(mission, step_id)`` routes through composition.

    Order is critical and load-bearing:

    1. **Built-in fast path** (PR #797 invariant): the
       ``_COMPOSED_ACTIONS_BY_MISSION`` lookup short-circuits without loading
       the frozen template, so built-in dispatch (e.g., ``software-dev``)
       remains byte-identical to its pre-Phase-6 behavior.
    2. **Custom mission widening** (Phase 6 / R-005): consulted only when
       ``run_dir`` is provided AND the mission is NOT a built-in entry in
       ``_COMPOSED_ACTIONS_BY_MISSION``. The active step's explicit binding is
       read from the frozen template; a non-empty ``agent_profile`` OR
       ``contract_ref`` triggers composition. Empty / missing bindings fall
       through to the legacy DAG handler unchanged.
    """
    # Built-in fast path — short-circuits without touching the frozen template.
    composed = _COMPOSED_ACTIONS_BY_MISSION.get(mission)
    if composed is not None and _normalize_action_for_composition(step_id) in composed:
        return True

    # Custom mission widening (R-005). ``run_dir`` is required to read the
    # frozen template; without it (e.g., on the very first decide_next call
    # before the run is started), fall through to the legacy DAG handler.
    if run_dir is None:
        return False
    profile, contract_ref = _resolve_step_binding(run_dir, step_id)
    return bool(profile or contract_ref)  # treat empty strings as falsy


def _resolve_step_binding(run_dir: Path, step_id: str) -> tuple[str | None, str | None]:
    """Return ``(agent_profile, contract_ref)`` for ``step_id`` in the frozen template.

    Missing templates, missing steps, and empty strings all resolve to
    ``None`` values so callers fail closed through the legacy path or the
    executor's structured error surface.
    """
    try:
        from specify_cli.next._internal_runtime.engine import _load_frozen_template

        template = _load_frozen_template(run_dir)
    except Exception:
        return None, None

    normalized = _normalize_action_for_composition(step_id)
    for step in template.steps:
        if step.id == step_id or step.id == normalized:
            profile = step.agent_profile.strip() if step.agent_profile else None
            contract_ref = step.contract_ref.strip() if step.contract_ref else None
            return profile or None, contract_ref or None
    return None, None


def _resolve_step_agent_profile(run_dir: Path, step_id: str) -> str | None:
    """Return the ``agent_profile`` set on ``step_id`` in the frozen template.

    Returns ``None`` when:

    - ``run_dir`` lacks a frozen template (e.g., the run has not been started
      yet, or template load otherwise raises).
    - The step is not present in the template.
    - The step's ``agent_profile`` is ``None`` or an empty string (treated as
      falsy so the gate widens only for explicit author opt-in).

    The lookup tolerates legacy ``tasks_outline`` / ``tasks_packages`` /
    ``tasks_finalize`` substep IDs by normalizing through
    ``_normalize_action_for_composition``.
    """
    profile, _contract_ref = _resolve_step_binding(run_dir, step_id)
    return profile


def _resolve_runtime_contract_for_step(
    *,
    repo_root: Path,
    run_dir: Path,
    mission: str,
    step_id: str,
) -> Any | None:
    """Resolve a custom step contract from durable frozen-template state.

    ``mission run`` and ``next`` normally execute in separate CLI processes,
    so the process-local registry populated by ``mission run`` cannot be the
    only handoff for synthesized contracts.
    """
    try:
        from doctrine.mission_step_contracts.repository import (
            MissionStepContractRepository,
        )
        from specify_cli.mission_loader.contract_synthesis import synthesize_contracts
        from specify_cli.mission_loader.registry import lookup_contract
        from specify_cli.next._internal_runtime.engine import _load_frozen_template

        template = _load_frozen_template(run_dir)
    except Exception:
        return None

    normalized = _normalize_action_for_composition(step_id)
    for step in template.steps:
        if step.id != step_id and step.id != normalized:
            continue
        contract_ref = step.contract_ref.strip() if step.contract_ref else None
        if contract_ref:
            repository = MissionStepContractRepository(project_dir=repo_root / ".kittify" / "doctrine" / "mission_step_contracts")
            return lookup_contract(contract_ref, repository)
        profile = step.agent_profile.strip() if step.agent_profile else None
        if profile:
            contract_id = f"custom:{mission}:{normalized}"
            for contract in synthesize_contracts(template):
                if contract.id == contract_id:
                    return contract
        return None
    return None


def _composition_dispatch_inputs(
    *,
    repo_root: Path,
    run_dir: Path,
    mission: str,
    step_id: str,
    action: str,
) -> tuple[str | None, Any | None]:
    """Return ``(profile_hint, contract)`` for a composition dispatch."""
    if action in _COMPOSED_ACTIONS_BY_MISSION.get(mission, frozenset()):
        return None, None
    return (
        _resolve_step_agent_profile(run_dir, step_id),
        _resolve_runtime_contract_for_step(
            repo_root=repo_root,
            run_dir=run_dir,
            mission=mission,
            step_id=step_id,
        ),
    )


def _count_source_documented_events(feature_dir: Path) -> int:
    """Return the number of ``source_documented`` events in the mission event log.

    Mirrors the v1 ``event_count`` guard primitive (see
    ``src/specify_cli/mission_v1/guards.py``): reads
    ``feature_dir / "mission-events.jsonl"``, treats each line as a JSON
    record, and counts those whose ``type`` equals ``"source_documented"``.

    Missing or unreadable logs return ``0`` so the guard fails closed at the
    research ``gathering`` branch.
    """
    log_path = feature_dir / "mission-events.jsonl"
    if not log_path.is_file():
        return 0
    count = 0
    try:
        for raw_line in log_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict) and entry.get("type") == "source_documented":
                count += 1
    except OSError:
        return 0
    return count


def _publication_approved(feature_dir: Path) -> bool:
    """Return True iff the mission event log carries a ``publication_approved`` gate event.

    Mirrors the v1 ``gate_passed`` guard primitive: a gate event is recorded
    as ``{"type": "gate_passed", "name": "<gate_name>"}`` in
    ``feature_dir / "mission-events.jsonl"``. Missing or unreadable logs
    return ``False`` so the research ``output`` guard fails closed.

    This signal was chosen because the research mission's existing v1
    ``mission.yaml`` declares the same surface
    (``gate_passed("publication_approved")``) for both the source-side gate
    check and the publication-approval gate. Keeping the runtime bridge's
    guard reading from the same JSONL the v1 guard primitives consume
    avoids forking the gate-event surface during the v2 composition
    rewrite.
    """
    log_path = feature_dir / "mission-events.jsonl"
    if not log_path.is_file():
        return False
    try:
        for raw_line in log_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict) and entry.get("type") == "gate_passed" and entry.get("name") == "publication_approved":
                return True
    except OSError:
        return False
    return False


def _has_generated_docs(feature_dir: Path) -> bool:
    """Return True iff at least one *.md file exists under feature_dir / 'docs'.

    Used by the documentation `generate` guard branch (D6 of plan.md).
    """
    docs_root = feature_dir / "docs"
    if not docs_root.is_dir():
        return False
    return next(docs_root.rglob("*.md"), None) is not None


def _check_composed_action_guard(  # noqa: C901
    action: str,
    feature_dir: Path,
    *,
    mission: str = "software-dev",
    legacy_step_id: str | None = None,
) -> list[str]:
    """CLI-level guards that fire AFTER a composed action completes.

    Mirrors ``_check_cli_guards`` semantics for the composed actions.

    The ``mission`` keyword-only parameter selects the guard branch family:

    * ``mission="software-dev"`` (default) routes through the original
      software-dev guard chain (``specify`` / ``plan`` / ``tasks`` /
      ``implement`` / ``review``).
    * ``mission="research"`` routes through the research guard chain
      (``scoping`` / ``methodology`` / ``gathering`` / ``synthesis`` /
      ``output``) plus a **fail-closed default** for any unknown research
      action — closing the v1 P1 silent-pass finding where unknown actions
      fell through with empty failures.

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

    if mission == "research":
        # Research composition guard chain (D3) + fail-closed default for
        # unknown research actions (T022 — closes the v1 P1 silent-pass
        # finding). Every (mission="research", action=<unknown>) tuple
        # produces a non-empty failures list, which the dispatch surface
        # propagates as a structured error with no run-state advancement.
        if action == "scoping":
            if not (feature_dir / SPEC_ARTIFACT).is_file():
                failures.append(MISSING_ARTIFACT_MESSAGE.format(name=SPEC_ARTIFACT))
        elif action == "methodology":
            if not (feature_dir / PLAN_ARTIFACT).is_file():
                failures.append(MISSING_ARTIFACT_MESSAGE.format(name=PLAN_ARTIFACT))
        elif action == "gathering":
            if not (feature_dir / "source-register.csv").is_file():
                failures.append("Required artifact missing: source-register.csv")
            if _count_source_documented_events(feature_dir) < 3:
                failures.append("Insufficient sources documented (need >=3)")
        elif action == "synthesis":
            if not (feature_dir / "findings.md").is_file():
                failures.append("Required artifact missing: findings.md")
        elif action == "output":
            if not (feature_dir / "report.md").is_file():
                failures.append("Required artifact missing: report.md")
            if not _publication_approved(feature_dir):
                failures.append("Publication approval gate not passed")
        else:
            failures.append(f"No guard registered for research action: {action}")
        return failures

    if mission == "documentation":
        if action == "discover":
            if not (feature_dir / SPEC_ARTIFACT).is_file():
                failures.append(MISSING_ARTIFACT_MESSAGE.format(name=SPEC_ARTIFACT))
        elif action == "audit":
            if not (feature_dir / "gap-analysis.md").is_file():
                failures.append("Required artifact missing: gap-analysis.md")
        elif action == "design":
            if not (feature_dir / PLAN_ARTIFACT).is_file():
                failures.append(MISSING_ARTIFACT_MESSAGE.format(name=PLAN_ARTIFACT))
        elif action == "generate":
            if not _has_generated_docs(feature_dir):
                failures.append("Required artifact missing: docs/**/*.md (no Markdown files found under docs/)")
        elif action == "validate":
            if not (feature_dir / "audit-report.md").is_file():
                failures.append("Required artifact missing: audit-report.md")
        elif action == "publish":
            if not (feature_dir / "release.md").is_file():
                failures.append("Required artifact missing: release.md")
        else:
            failures.append(f"No guard registered for documentation action: {action}")
        return failures

    if action == "specify":
        if not (feature_dir / SPEC_ARTIFACT).exists():
            failures.append(MISSING_ARTIFACT_MESSAGE.format(name=SPEC_ARTIFACT))

    elif action == "plan":
        if not (feature_dir / PLAN_ARTIFACT).exists():
            failures.append(MISSING_ARTIFACT_MESSAGE.format(name=PLAN_ARTIFACT))

    elif action == "tasks":
        if legacy_step_id == "tasks_outline":
            # After tasks_outline the user is expected to have produced
            # tasks.md. WP files and dependencies come in later substeps.
            if not (feature_dir / TASKS_ARTIFACT).exists():
                failures.append(MISSING_ARTIFACT_MESSAGE.format(name=TASKS_ARTIFACT))
        elif legacy_step_id == "tasks_packages":
            # After tasks_packages: tasks.md AND >=1 WP file. Dependencies
            # are not yet expected — finalize-tasks adds them in the next
            # substep.
            if not (feature_dir / TASKS_ARTIFACT).exists():
                failures.append(MISSING_ARTIFACT_MESSAGE.format(name=TASKS_ARTIFACT))
            tasks_dir = feature_dir / "tasks"
            if not tasks_dir.is_dir() or not list(tasks_dir.glob("WP*.md")):
                failures.append("Required: at least one tasks/WP*.md file")
        else:
            # legacy_step_id == "tasks_finalize" OR composition-only
            # (legacy_step_id is None): demand the full terminal state.
            # Union of legacy tasks_outline + tasks_packages + tasks_finalize
            # checks; no weakening of assertions.
            if not (feature_dir / TASKS_ARTIFACT).exists():
                failures.append(MISSING_ARTIFACT_MESSAGE.format(name=TASKS_ARTIFACT))
            tasks_dir = feature_dir / "tasks"
            if not tasks_dir.is_dir() or not list(tasks_dir.glob("WP*.md")):
                failures.append("Required: at least one tasks/WP*.md file")
            else:
                for wp_file in sorted(tasks_dir.glob("WP*.md")):
                    if not _has_raw_dependencies_field(wp_file):
                        failures.append(f"WP {wp_file.stem} missing 'dependencies' in frontmatter (run 'spec-kitty agent mission finalize-tasks')")
                        break  # One failure message is enough

    elif action == "implement":
        if not _should_advance_wp_step("implement", feature_dir):
            failures.append("Not all work packages have required status (for_review, approved, or done)")

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
    contract: Any | None = None,
) -> list[str] | None:
    """Run a composed action via ``StepContractExecutor``; then guard.

    Returns:
      - ``None`` on success (composition succeeded AND post-action guard
        passed). On the live ``decide_next_via_runtime`` path the caller then
        invokes :func:`_advance_run_state_after_composition` to progress run
        state without entering the legacy DAG dispatch handler
        (single-dispatch, FR-001/FR-002).
      - A non-empty list of failure descriptions if the executor raised
        ``StepContractExecutionError`` (FR-009: structured CLI surface, not a
        Python traceback) or the post-action guard failed. The caller turns
        this into a ``Decision`` with ``guard_failures`` populated.

    Constraint C-001 is preserved: this function only ever invokes
    ``StepContractExecutor.execute``; it never touches
    ``ProfileInvocationExecutor`` directly.

    The follow-up advancement is performed by
    :func:`_advance_run_state_after_composition`, which reuses the same
    primitives ``runtime_next_step(...)`` uses internally for state, lane,
    and prompt progression. The legacy ``runtime_next_step`` is **not**
    called for composition-backed actions (FR-001).
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
    # For custom missions, prefer the durable contract resolved from the
    # frozen template during ``next``. Fall back to the process-local registry
    # for in-process tests and callers, and then to the executor's repository
    # lookup for built-in software-dev dispatch.
    from specify_cli.mission_loader.registry import get_runtime_contract_registry

    selected_contract = contract or get_runtime_contract_registry().lookup(f"custom:{mission}:{action}")
    try:
        result = StepContractExecutor(repo_root=repo_root).execute(context, contract=selected_contract)
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
        logger.exception("unexpected exception in composition for %s/%s", mission, action)
        return [f"composition crashed for {mission}/{action}: {type(exc).__name__}: {exc}"]

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

    failures = _check_composed_action_guard(action, feature_dir, mission=mission, legacy_step_id=legacy_step_id)
    if failures:
        return failures
    return None


# Single-dispatch invariant (FR-001 / phase6-composition-stabilization-01KQ2JAS):
# After a composition-backed software-dev action succeeds, run state must still
# advance through the next public step — but the legacy ``runtime_next_step``
# DAG dispatch handler MUST NOT be invoked for the same action attempt. The
# helper below performs the equivalent run-state, event, and prompt
# progression by reusing the same engine primitives ``runtime_next_step`` uses
# internally (``_read_snapshot``, ``_append_event``, ``_load_frozen_template``,
# ``plan_next``, ``_write_snapshot``) plus the same ``SyncRuntimeEventEmitter``
# the legacy path uses, without re-entering the legacy DAG dispatch.
def _advance_run_state_after_composition(
    *,
    run_ref: MissionRunRef,
    agent: str,
    mission_slug: str,
    mission_type: str,
    repo_root: Path,
    feature_dir: Path,
    timestamp: str,
    progress: dict[str, int | float] | None,
    origin: dict[str, Any],
    sync_emitter: SyncRuntimeEventEmitter,
) -> Decision:
    """Advance run state after a successful composed action and return a Decision.

    Reuses the same engine primitives as ``runtime_next_step(...)`` for state,
    lane-event, and prompt progression — but does NOT invoke
    ``runtime_next_step``. This is the single-dispatch enforcement point for
    composition-backed software-dev actions (FR-001, FR-002).

    Behavior mirrors the success branch of
    ``spec_kitty_runtime.engine.next_step``:

    1. Read the current snapshot.
    2. Mark the issued step as completed; emit ``NextStepAutoCompleted``.
    3. Plan the next decision via ``plan_next`` against the frozen template.
    4. On a ``step`` decision, emit ``NextStepIssued`` and stamp
       ``issued_step_id`` so the next bridge call sees fresh state.
    5. On a ``terminal`` decision (a step actually completed), emit
       ``MissionRunCompleted``.
    6. Persist the snapshot.
    7. Return the mapped ``Decision`` via :func:`_map_runtime_decision`.

    Returns the same ``Decision`` shape ``runtime_next_step(...)`` would have
    produced for the same advance (FR-005); only the dispatch path differs.
    """
    # Local imports keep the legacy import block at the top of the module
    # focused and mirror the pattern used by ``_dispatch_via_composition``.
    from datetime import UTC, datetime

    from specify_cli.next._internal_runtime.engine import (
        _append_event,
        _load_frozen_template,
        _read_snapshot,
        _write_snapshot,
    )
    from specify_cli.next._internal_runtime.events import (
        DECISION_INPUT_REQUESTED,
        MISSION_RUN_COMPLETED,
        NEXT_STEP_AUTO_COMPLETED,
        NEXT_STEP_ISSUED,
    )
    from spec_kitty_events.mission_next import (
        DecisionInputRequestedPayload,
        MissionRunCompletedPayload,
        NextStepAutoCompletedPayload,
        NextStepIssuedPayload,
        RuntimeActorIdentity,
    )
    from specify_cli.next._internal_runtime.planner import plan_next
    from specify_cli.next._internal_runtime.schema import DecisionRequest, MissionRunSnapshot

    run_dir = Path(run_ref.run_dir)
    snapshot = _read_snapshot(run_dir)
    sync_emitter.seed_from_snapshot(snapshot)

    did_complete_step = snapshot.issued_step_id is not None

    # Step 1 — mark current step completed (success path only; composition
    # surfaces failures via ``_dispatch_via_composition``'s failure list).
    if snapshot.issued_step_id is not None:
        completed_steps = list(snapshot.completed_steps)
        completed_step_id = snapshot.issued_step_id
        if completed_step_id not in completed_steps:
            completed_steps.append(completed_step_id)

        snapshot = MissionRunSnapshot(
            run_id=snapshot.run_id,
            mission_key=snapshot.mission_key,
            template_path=snapshot.template_path,
            template_hash=snapshot.template_hash,
            policy_snapshot=snapshot.policy_snapshot,
            issued_step_id=None,
            completed_steps=completed_steps,
            inputs=snapshot.inputs,
            decisions=snapshot.decisions,
            pending_decisions=snapshot.pending_decisions,
            blocked_reason=snapshot.blocked_reason,
        )
        ac_actor = RuntimeActorIdentity(actor_id=agent, actor_type="llm")
        ac_payload = NextStepAutoCompletedPayload(
            run_id=snapshot.run_id,
            step_id=completed_step_id,
            agent_id=agent,
            result="success",
            actor=ac_actor,
        )
        _append_event(run_dir, NEXT_STEP_AUTO_COMPLETED, ac_payload.model_dump(mode="json"))
        sync_emitter.emit_next_step_auto_completed(ac_payload)

    # Step 2 — plan the next decision against the frozen template, mirroring
    # ``runtime_next_step``'s drift-detection plumbing.
    template = _load_frozen_template(run_dir)
    live_template_path: Path | None = None
    if snapshot.template_path:
        candidate = Path(snapshot.template_path)
        if candidate.exists():
            live_template_path = candidate

    decision = plan_next(
        snapshot,
        template,
        snapshot.policy_snapshot,
        actor_context={"agent_id": agent},
        live_template_path=live_template_path,
    )

    # Step 3 — record issued step / completion-of-mission / decision-required
    # events as the engine does, so downstream consumers of the run event log
    # see equivalent state. The three branches mirror
    # ``spec_kitty_runtime.engine.next_step``:
    #   - ``step``           → emit ``NextStepIssued``, stamp issued_step_id.
    #   - ``decision_required`` → persist ``pending_decisions[decision_id]``
    #     and emit ``DecisionInputRequested`` so a downstream caller can answer
    #     it. Required for project/runtime overrides and custom missions that
    #     introduce input/audit gates after a composed step (mission-review.md
    #     RISK-2 fix).
    #   - ``terminal``       → emit ``MissionRunCompleted`` if a step actually
    #     just completed (avoid duplicate emit on re-poll).
    issued_step_id = snapshot.issued_step_id
    pending_decisions = dict(snapshot.pending_decisions)
    if decision.kind == "step" and decision.step_id:
        issued_step_id = decision.step_id
        si_actor = RuntimeActorIdentity(actor_id=agent, actor_type="llm")
        si_payload = NextStepIssuedPayload(
            run_id=snapshot.run_id,
            step_id=decision.step_id,
            agent_id=agent,
            actor=si_actor,
        )
        _append_event(run_dir, NEXT_STEP_ISSUED, si_payload.model_dump(mode="json"))
        sync_emitter.emit_next_step_issued(si_payload)
    elif decision.kind == "decision_required" and decision.decision_id:
        # Persist input-keyed decisions in pending_decisions so they're
        # answerable; only emit + persist on first occurrence to avoid
        # duplicates on re-poll. Mirrors engine.next_step's branch verbatim
        # (modulo the runtime emitter passed in, which is the same instance).
        if decision.decision_id not in pending_decisions:
            dr_actor = RuntimeActorIdentity(actor_id=agent, actor_type="llm")
            req = DecisionRequest(
                decision_id=decision.decision_id,
                step_id=decision.step_id or "",
                question=decision.question or "",
                options=decision.options or [],
                requested_by=dr_actor,
                requested_at=datetime.now(UTC),
            )
            pending_decisions[decision.decision_id] = req.model_dump(mode="json")

            dr_payload = DecisionInputRequestedPayload(
                run_id=snapshot.run_id,
                decision_id=decision.decision_id,
                step_id=decision.step_id or "",
                question=decision.question or "",
                options=tuple(decision.options or []),
                input_key=decision.input_key,
                actor=dr_actor,
            )
            _append_event(run_dir, DECISION_INPUT_REQUESTED, dr_payload.model_dump(mode="json"))
            sync_emitter.emit_decision_input_requested(dr_payload)
    elif decision.kind == "terminal" and did_complete_step:
        # Retrospective lifecycle gate (FR-011..FR-014). Opt-in via charter
        # ``mode:`` clause or ``SPEC_KITTY_RETROSPECTIVE`` env var; projects
        # that have not opted in see no behavior change. When opted in,
        # ``run_terminus`` drives mode detection, prompt/skip/run flow, and
        # emits the canonical retrospective.* events; ``before_mark_done``
        # then consults the gate. Any blocking decision propagates as
        # ``MissionCompletionBlocked`` and prevents ``MissionRunCompleted``
        # from being emitted, keeping the audit trail honest.
        from specify_cli.retrospective.config import is_retrospective_enabled

        if is_retrospective_enabled(repo_root):
            from specify_cli.next._internal_runtime.retrospective_terminus import (
                run_terminus,
            )
            from specify_cli.retrospective.schema import ActorRef

            mission_id = _resolve_mission_id_for_terminus(feature_dir)
            operator_actor = ActorRef(kind="agent", id=agent, profile_id=None)
            run_terminus(
                mission_id=mission_id,
                mission_type=mission_type,
                feature_dir=feature_dir,
                repo_root=repo_root,
                operator_actor=operator_actor,
                facilitator_callback=None,  # wiring deferred; gate enforces
                hic_prompt=_rich_hic_prompt,
            )

        mc_actor = RuntimeActorIdentity(actor_id=agent, actor_type="llm")
        mc_payload = MissionRunCompletedPayload(
            run_id=snapshot.run_id,
            mission_type=snapshot.mission_key,
            actor=mc_actor,
        )
        _append_event(run_dir, MISSION_RUN_COMPLETED, mc_payload.model_dump(mode="json"))
        sync_emitter.emit_mission_run_completed(mc_payload)

    # Step 4 — persist the new snapshot so the next ``decide_next_via_runtime``
    # call observes the fresh issued_step_id and any new pending_decisions.
    snapshot = MissionRunSnapshot(
        run_id=snapshot.run_id,
        mission_key=snapshot.mission_key,
        template_path=snapshot.template_path,
        template_hash=snapshot.template_hash,
        policy_snapshot=snapshot.policy_snapshot,
        issued_step_id=issued_step_id,
        completed_steps=snapshot.completed_steps,
        inputs=snapshot.inputs,
        decisions=snapshot.decisions,
        pending_decisions=pending_decisions,
        blocked_reason=snapshot.blocked_reason,
    )
    _write_snapshot(run_dir, snapshot)

    # Step 5 — map the runtime decision to the public ``Decision`` shape using
    # the same mapper the legacy path uses, preserving FR-005.
    return _map_runtime_decision(
        decision,
        agent,
        mission_slug,
        mission_type,
        repo_root,
        feature_dir,
        timestamp,
        progress,
        origin,
    )


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
    tiers = project_tiers + [builtin_tier, global_tier] if mission_type == "software-dev" else project_tiers + [global_tier, builtin_tier]

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
    if not (run_dir / STATE_FILE).exists():
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
        if (run_dir / STATE_FILE).exists():
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


def decide_next_via_runtime(  # noqa: C901
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
        from specify_cli.next._internal_runtime.engine import _read_snapshot

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
            prompt_file: str | None = None
            prompt_error: str | None = None
            if action:
                prompt_file, prompt_error = _build_prompt_or_error(
                    action,
                    feature_dir,
                    mission_slug,
                    wp_id,
                    agent,
                    repo_root,
                    mission_type,
                )
            else:
                prompt_error = f"no action mapped for step '{current_step_id}'; cannot resolve prompt"
            if prompt_file is None:
                # WP06 (FR-006/FR-013): never issue kind=step with prompt_file=None.
                # When a prompt cannot be resolved, surface a structured blocked
                # decision so callers can stop, not partial-execute.
                return Decision(
                    kind=DecisionKind.blocked,
                    agent=agent,
                    mission_slug=mission_slug,
                    mission=mission_type,
                    mission_state=current_step_id,
                    timestamp=now,
                    reason=prompt_error or "prompt_file_not_resolvable",
                    action=action,
                    wp_id=wp_id,
                    workspace_path=workspace_path,
                    guard_failures=guard_failures,
                    progress=progress,
                    origin=origin,
                    run_id=run_ref.run_id,
                    step_id=current_step_id,
                )
            try:
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
            except InvalidStepDecision:
                # C-005: keep the kind=step prompt contract as a hard
                # constructor invariant. If the file disappears between
                # resolution and construction, surface a structured blocker.
                return Decision(
                    kind=DecisionKind.blocked,
                    agent=agent,
                    mission_slug=mission_slug,
                    mission=mission_type,
                    mission_state=current_step_id,
                    timestamp=now,
                    reason=prompt_error or "prompt_file_not_resolvable",
                    action=action,
                    wp_id=wp_id,
                    workspace_path=workspace_path,
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
        and _should_dispatch_via_composition(
            mission_type,
            current_step_id,
            run_dir=Path(run_ref.run_dir),
        )
    ):
        run_dir = Path(run_ref.run_dir)
        composed_action = _normalize_action_for_composition(current_step_id)
        # R-005: for custom missions, the active step's ``agent_profile`` is
        # the source of truth for ``profile_hint``. For built-in missions
        # (e.g., ``software-dev``), built-in templates do NOT set
        # ``agent_profile``, so this resolves to ``None`` and the executor's
        # ``_resolve_profile_hint`` falls back to ``_ACTION_PROFILE_DEFAULTS``
        # — preserving byte-identical built-in dispatch behavior (FR-010).
        resolved_profile, runtime_contract = _composition_dispatch_inputs(
            repo_root=repo_root,
            run_dir=run_dir,
            mission=mission_type,
            step_id=current_step_id,
            action=composed_action,
        )
        composition_failures = _dispatch_via_composition(
            repo_root=repo_root,
            mission=mission_type,
            action=composed_action,
            actor=agent,
            profile_hint=resolved_profile,
            request_text=None,
            mode_of_work=None,
            feature_dir=feature_dir,
            # Thread the original step_id so the post-action guard can branch
            # on substep semantics for legacy tasks_outline/tasks_packages/
            # tasks_finalize. Without this, the collapsed guard demands the
            # terminal post-finalize state on every substep and blocks the
            # live tasks_outline → tasks_packages → tasks_finalize flow.
            legacy_step_id=current_step_id,
            contract=runtime_contract,
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
        # Composition succeeded; advance run state via the
        # composition-specific advancement helper and short-circuit the
        # legacy ``runtime_next_step`` fall-through (FR-001/FR-002). The
        # helper emits the same lane / state events the legacy path emits;
        # any error from it surfaces through the existing ``Decision``
        # ``blocked`` shape (EDGE-003) — the legacy DAG dispatch handler is
        # **not** entered as a fallback.
        try:
            return _advance_run_state_after_composition(
                run_ref=run_ref,
                agent=agent,
                mission_slug=mission_slug,
                mission_type=mission_type,
                repo_root=repo_root,
                feature_dir=feature_dir,
                timestamp=now,
                progress=progress,
                origin=origin,
                sync_emitter=sync_emitter,
            )
        except Exception as exc:  # noqa: BLE001 — EDGE-003 contract: any
            # advancement-helper failure must surface as a structured
            # Decision, not as a Python traceback, and MUST NOT silently
            # fall through to the legacy DAG dispatch handler.
            logger.exception(
                "advancement helper failed after composition for %s/%s",
                mission_type,
                composed_action,
            )
            return Decision(
                kind=DecisionKind.blocked,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state=current_step_id,
                timestamp=now,
                reason=(f"Run-state advancement after composition failed for {mission_type}/{composed_action}: {type(exc).__name__}: {exc}"),
                progress=progress,
                origin=origin,
                run_id=run_ref.run_id,
                step_id=current_step_id,
            )

    # Retrospective lifecycle gate (FR-011..FR-014). The legacy
    # ``runtime_next_step`` path is a black-box engine call that updates
    # state.json and emits ``MissionRunCompleted`` synchronously through
    # the sync emitter (which dispatches to remote queues / SaaS). If we
    # let the engine run with the real emitter and gate-check afterwards,
    # both the snapshot AND the sync events are already out the door by
    # the time the gate blocks — and rolling back local files cannot
    # retract dispatched sync events.
    #
    # Strategy: use a buffering emitter for the speculative engine call.
    # The buffer records every emit_* call in order without firing them.
    # After the engine returns:
    #   * non-terminal → flush buffer to real emitter (normal behavior).
    #   * terminal + opt-in + gate allows → flush buffer (mission really
    #     completed).
    #   * terminal + opt-in + gate blocks → discard buffer (no events
    #     ever leave the bridge) AND restore state.json + truncate
    #     run.events.jsonl to pre-call shape.
    # This mirrors the composition path, which runs the gate before its
    # ``MissionRunCompleted`` emission.
    from specify_cli.retrospective.config import is_retrospective_enabled

    retrospective_enabled = is_retrospective_enabled(repo_root)

    pre_state_bytes: bytes | None = None
    pre_events_size: int | None = None
    engine_emitter: Any = sync_emitter
    buffer: _BufferingRuntimeEmitter | None = None

    if retrospective_enabled:
        run_dir = Path(run_ref.run_dir)
        state_path = run_dir / STATE_FILE
        events_path = run_dir / "run.events.jsonl"
        try:
            pre_state_bytes = state_path.read_bytes() if state_path.exists() else None
            pre_events_size = events_path.stat().st_size if events_path.exists() else 0
        except OSError:
            # If we cannot capture pre-state we cannot guarantee a clean
            # rollback. Surface this as a blocked Decision rather than
            # advancing into a state we cannot retract.
            return Decision(
                kind=DecisionKind.blocked,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state=current_step_id or "unknown",
                timestamp=now,
                reason=("Cannot read run state.json / run.events.jsonl before speculative engine advance; refusing to advance"),
                progress=progress,
                origin=origin,
            )
        buffer = _BufferingRuntimeEmitter()
        engine_emitter = buffer

    # Advance via runtime
    try:
        runtime_decision = runtime_next_step(
            run_ref,
            agent_id=agent,
            result=result,
            emitter=engine_emitter,
        )
    except Exception as exc:
        # Engine raised: discard any buffered events; nothing left to flush.
        if buffer is not None:
            buffer.discard()
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

    if retrospective_enabled and runtime_decision.kind == "terminal":
        from specify_cli.next._internal_runtime.retrospective_terminus import (
            run_terminus,
        )
        from specify_cli.retrospective.schema import ActorRef

        mission_id = _resolve_mission_id_for_terminus(feature_dir)
        operator_actor = ActorRef(kind="agent", id=agent, profile_id=None)
        try:
            run_terminus(
                mission_id=mission_id,
                mission_type=mission_type,
                feature_dir=feature_dir,
                repo_root=repo_root,
                operator_actor=operator_actor,
                facilitator_callback=None,
                hic_prompt=_rich_hic_prompt,
            )
        except Exception as exc:
            # Gate refused. Drop the buffered emit calls (so no
            # MissionRunCompleted ever reaches the real emitter) and
            # restore state.json + truncate run.events.jsonl to pre-call.
            if buffer is not None:
                buffer.discard()
            run_dir = Path(run_ref.run_dir)
            if pre_state_bytes is not None:
                try:
                    (run_dir / STATE_FILE).write_bytes(pre_state_bytes)
                except OSError as restore_exc:
                    logger.error(
                        "rollback of state.json failed after gate block: %s",
                        restore_exc,
                    )
            if pre_events_size is not None:
                events_path = run_dir / "run.events.jsonl"
                try:
                    if events_path.exists():
                        with open(events_path, "r+b") as handle:
                            handle.truncate(pre_events_size)
                except OSError as restore_exc:
                    logger.error(
                        "rollback of run.events.jsonl failed after gate block: %s",
                        restore_exc,
                    )
            return Decision(
                kind=DecisionKind.blocked,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state=current_step_id or "unknown",
                timestamp=now,
                reason=f"Retrospective gate refused completion: {exc}",
                progress=progress,
                origin=origin,
            )

    # Gate either passed (terminal allow) or never ran (non-terminal /
    # not opted in): flush any buffered emit calls into the real sync
    # emitter so observers receive them in original order.
    if buffer is not None:
        buffer.flush(sync_emitter)

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
            from specify_cli.next._internal_runtime import engine
            from specify_cli.next._internal_runtime.planner import plan_next

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
        from specify_cli.next._internal_runtime.engine import _read_snapshot

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

    prompt_file, prompt_error = _build_prompt_or_error(
        action,
        feature_dir,
        mission_slug,
        wp_id,
        agent,
        repo_root,
        mission_type,
    )
    if prompt_file is None:
        # WP06 (FR-006/FR-013): kind=step decisions must always carry a
        # non-empty resolvable prompt_file. When prompt resolution fails,
        # surface a structured blocked decision instead of a partial step.
        return Decision(
            kind=DecisionKind.blocked,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=step_id,
            timestamp=timestamp,
            reason=prompt_error or "no_prompt_template",
            action=action,
            wp_id=wp_id,
            workspace_path=workspace_path,
            guard_failures=guard_failures or [],
            progress=progress,
            origin=origin,
            run_id=run_ref.run_id,
            step_id=step_id,
        )

    try:
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
    except InvalidStepDecision:
        # C-005: prompt_builder failed to produce a usable prompt for this
        # WP iteration. Route to kind=blocked rather than emitting a
        # kind=step with a null/unresolvable prompt_file.
        return Decision(
            kind=DecisionKind.blocked,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=step_id,
            timestamp=timestamp,
            reason=prompt_error or "prompt_file_not_resolvable",
            action=action,
            wp_id=wp_id,
            workspace_path=workspace_path,
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
        prompt_file, prompt_error = _build_prompt_or_error(
            action,
            feature_dir,
            mission_slug,
            wp_id,
            agent,
            repo_root,
            mission_type,
        )
        if prompt_file is None:
            # WP06 (FR-006/FR-013): kind=step requires a resolvable prompt;
            # fall through to blocked when one cannot be built.
            return Decision(
                kind=DecisionKind.blocked,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state=step_id,
                timestamp=timestamp,
                reason=prompt_error or "prompt_file_not_resolvable",
                action=action,
                wp_id=wp_id,
                workspace_path=workspace_path,
                progress=progress,
                origin=origin,
                run_id=run_id,
                step_id=step_id,
            )
        try:
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
        except InvalidStepDecision:
            return Decision(
                kind=DecisionKind.blocked,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state=step_id,
                timestamp=timestamp,
                reason=prompt_error or "prompt_file_not_resolvable",
                action=action,
                wp_id=wp_id,
                workspace_path=workspace_path,
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
    prompt_file: str | None = None
    prompt_error: str | None = None
    if action or step_id:
        prompt_file, prompt_error = _build_prompt_or_error(
            action or step_id or "unknown",
            feature_dir,
            mission_slug,
            wp_id,
            agent,
            repo_root,
            mission_type,
        )
    else:
        prompt_error = "no action and no step_id; cannot resolve prompt"
    if prompt_file is None:
        # WP06 (FR-006/FR-013): emit a structured blocked decision rather than
        # an issued step that has no resolvable prompt.
        return Decision(
            kind=DecisionKind.blocked,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=step_id or "unknown",
            timestamp=timestamp,
            reason=prompt_error or "no_prompt_template",
            action=action or step_id,
            wp_id=wp_id,
            workspace_path=workspace_path,
            progress=progress,
            origin=origin,
            run_id=run_id,
            step_id=step_id,
        )

    try:
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
    except InvalidStepDecision:
        # C-005: non-WP step path — prompt resolution failed (no template,
        # build error, or null step_id with no action). Surface as blocked
        # rather than emit kind=step with a null/unresolvable prompt.
        return Decision(
            kind=DecisionKind.blocked,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=step_id or "unknown",
            timestamp=timestamp,
            reason=prompt_error or "prompt_file_not_resolvable",
            action=action or step_id,
            wp_id=wp_id,
            workspace_path=workspace_path,
            progress=progress,
            origin=origin,
            run_id=run_id,
            step_id=step_id,
        )
