"""Core decision engine for ``spec-kitty next``.

Delegates planning to the CLI-internal runtime
(``runtime.next._internal_runtime``) via :mod:`runtime_bridge`.
Post-mission ``shared-package-boundary-cutover-01KQ22DS`` the standalone
``spec-kitty-runtime`` PyPI package is no longer involved in any
production code path.

The :class:`Decision` dataclass and :class:`DecisionKind` constants are the
public JSON contract.  WP helpers (``_compute_wp_progress``,
``_find_first_wp_by_lane``) and ``_state_to_action`` are kept for use by the
bridge layer.

Legacy functions ``derive_mission_state`` and ``evaluate_guards`` are
preserved for backward compatibility and tests but are no longer called by
``decide_next``.
"""

from __future__ import annotations

import contextlib
import io
import os
import re
import tempfile
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from runtime.next._tmp_namespace import prompt_tmp_dir
from specify_cli.mission_metadata import mission_identity_fields
from specify_cli.status import wp_state_for
from specify_cli.status import Lane
from specify_cli.workspace.context import resolve_workspace_for_wp


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class DecisionKind(StrEnum):
    """Canonical kind values for :class:`Decision` envelopes.

    Declared as a ``StrEnum`` so that:

    * Comparisons against raw strings (e.g. ``decision.kind == "terminal"``)
      continue to work without change — every member *is* its string value.
    * JSON serialisation of ``to_dict()`` is byte-identical to the pre-enum
      form: ``self.kind`` in the dict is the bare string value.
    * Type-checkers can now flag typos such as ``"terminl"`` at analysis time.

    Serialisation note: ``DecisionKind.step.value == "step"``.  With
    ``StrEnum``, ``str(DecisionKind.step) == "step"`` and
    ``json.dumps({"kind": DecisionKind.step}) == '{"kind": "step"}'``.
    The ``to_dict()`` method emits ``self.kind`` directly, which serialises
    as the bare string value — byte-identical to the pre-enum form.
    """

    step = "step"
    decision_required = "decision_required"
    blocked = "blocked"
    terminal = "terminal"
    query = "query"  # bare next call; state not advanced


class InvalidStepDecision(ValueError):
    """Raised when a ``kind="step"`` ``Decision`` is constructed without a
    valid, on-disk-resolvable ``prompt_file``.

    See contracts C1/C2/C3 in
    ``kitty-specs/charter-e2e-827-followups-01KQAJA0/contracts/next-prompt-file-contract.md``:
    a ``kind="step"`` envelope MUST carry a non-null, non-empty ``prompt_file``
    that resolves on disk. ``null`` is legal only for non-step kinds.
    """


@dataclass
class Decision:
    kind: str  # one of DecisionKind.*
    agent: str | None
    mission_slug: str
    mission: str
    mission_state: str
    timestamp: str
    action: str | None = None
    wp_id: str | None = None
    workspace_path: str | None = None
    prompt_file: str | None = None
    reason: str | None = None
    guard_failures: list[str] = field(default_factory=list)
    progress: dict | None = None
    origin: dict = field(default_factory=dict)
    # Runtime fields (added in v2.0.0)
    run_id: str | None = None
    step_id: str | None = None
    decision_id: str | None = None
    input_key: str | None = None
    question: str | None = None
    options: list[str] | None = None
    is_query: bool = False  # New: True when kind == DecisionKind.query
    preview_step: str | None = None
    mission_number: str | None = None
    mission_type: str | None = None

    def __post_init__(self) -> None:
        """Enforce the ``kind="step"`` prompt-file contract at construction time.

        Contract (C1/C2 in
        ``kitty-specs/charter-e2e-827-followups-01KQAJA0/contracts/next-prompt-file-contract.md``):
        a ``kind="step"`` envelope MUST carry a non-null, non-empty
        ``prompt_file`` that resolves on disk. Non-step kinds (``blocked``,
        ``terminal``, ``decision_required``, ``query``) remain permissive —
        ``prompt_file=None`` is legal there.

        Raises :class:`InvalidStepDecision` (a :class:`ValueError`) on
        violation so the call site can ``try/except`` and route to a
        ``kind="blocked"`` envelope (Constraint C-005: do NOT weaken the
        ``kind="step"`` contract).
        """
        if self.kind == DecisionKind.step:
            prompt = self.prompt_file
            if not prompt:
                raise InvalidStepDecision(
                    "kind='step' requires a non-empty prompt_file; got None/empty"
                )
            if not Path(prompt).is_file():
                raise InvalidStepDecision(
                    f"kind='step' prompt_file must resolve on disk: {prompt!r} does not"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "agent": self.agent,
            **mission_identity_fields(
                self.mission_slug,
                self.mission_number,
                self.mission_type or self.mission,
            ),
            "mission": self.mission,
            "mission_state": self.mission_state,
            "timestamp": self.timestamp,
            "action": self.action,
            "wp_id": self.wp_id,
            "workspace_path": self.workspace_path,
            # kind='step' MUST carry a non-null prompt_file that resolves on
            # disk (see C1/C2 in
            # kitty-specs/charter-e2e-827-followups-01KQAJA0/contracts/next-prompt-file-contract.md).
            # null is legal only for non-step kinds.
            "prompt_file": self.prompt_file,
            "reason": self.reason,
            "guard_failures": self.guard_failures,
            "progress": self.progress,
            "origin": self.origin,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "decision_id": self.decision_id,
            "input_key": self.input_key,
            "question": self.question,
            "options": self.options,
            "is_query": self.is_query,
            "preview_step": self.preview_step,
        }


# ---------------------------------------------------------------------------
# State derivation from event log (legacy — kept for backward compat)
# ---------------------------------------------------------------------------


def derive_mission_state(feature_dir: Path, initial_state: str) -> str:
    """Derive current mission state by replaying the event log.

    Scans ``mission-events.jsonl`` for the last ``phase_entered`` event and
    returns its state.  Falls back to *initial_state* when the log is empty
    or contains no ``phase_entered`` events.

    .. deprecated:: 2.0.0
        No longer used by ``decide_next``.  Runtime state is now managed
        by the CLI-internal runtime
        (``runtime.next._internal_runtime``) via ``state.json`` in the
        run directory.
    """
    from specify_cli.mission_v1.events import read_events

    events = read_events(feature_dir)
    last_state = initial_state
    for event in events:
        if event.get("type") == "phase_entered":
            payload = event.get("payload", {})
            state = payload.get("state")
            if state:
                last_state = state
    return last_state


# ---------------------------------------------------------------------------
# Guard evaluation (legacy — kept for backward compat / tests)
# ---------------------------------------------------------------------------


def evaluate_guards(
    mission_config: dict[str, Any],
    feature_dir: Path,
    current_state: str,
) -> tuple[bool, list[str]]:
    """Evaluate guard conditions for the ``advance`` trigger from *current_state*.

    Checks both ``conditions`` (all must return True) and ``unless``
    (all must return False) arrays on the advance transition.

    Returns ``(all_passed, list_of_failure_descriptions)``.  If there is no
    ``advance`` transition from the current state, returns ``(True, [])``.

    .. deprecated:: 2.0.0
        No longer used by ``decide_next``.  CLI-level guards are now
        evaluated in :mod:`runtime_bridge`.
    """
    transitions = mission_config.get("transitions", [])

    # Find the advance transition from current_state
    advance_transition = None
    for t in transitions:
        if t.get("trigger") == "advance" and t.get("source") == current_state:
            advance_transition = t
            break

    if advance_transition is None:
        return True, []

    # Build a minimal event_data with model for guard evaluation
    model = SimpleNamespace(feature_dir=feature_dir, inputs={})
    event_data = SimpleNamespace(model=model)

    failures: list[str] = []

    # Check conditions (all must pass)
    for cond in advance_transition.get("conditions", []):
        if callable(cond):
            try:
                if not cond(event_data):
                    failures.append(_describe_guard(cond, negate=False))
            except Exception as exc:
                failures.append(f"Guard error: {exc}")
        elif isinstance(cond, str):
            failures.append(f"Uncompiled guard: {cond}")

    # Check unless (all must be False; if any is True, guard fails)
    for cond in advance_transition.get("unless", []):
        if callable(cond):
            try:
                if cond(event_data):
                    failures.append(_describe_guard(cond, negate=True))
            except Exception as exc:
                failures.append(f"Guard error: {exc}")
        elif isinstance(cond, str):
            failures.append(f"Uncompiled unless-guard: {cond}")

    return len(failures) == 0, failures


def _describe_guard(guard_callable: Any, *, negate: bool = False) -> str:
    """Best-effort human description of a guard callable."""
    qualname = getattr(guard_callable, "__qualname__", "")
    prefix = "Unless-guard active: " if negate else ""
    if "artifact_exists" in qualname:
        return f"{prefix}Required artifact missing"
    if "all_wp_status" in qualname:
        return f"{prefix}Not all work packages have required status"
    if "any_wp_status" in qualname:
        return f"{prefix}No work package has required status"
    if "gate_passed" in qualname:
        return f"{prefix}Required gate not passed"
    if "event_count" in qualname:
        return f"{prefix}Insufficient events of required type"
    if "input_provided" in qualname:
        return f"{prefix}Required input not provided"
    return f"{prefix}Guard failed: {qualname or repr(guard_callable)}"


# ---------------------------------------------------------------------------
# WP progress helpers
# ---------------------------------------------------------------------------


def _get_wp_lanes(feature_dir: Path) -> dict[str, str]:
    """Return a mapping of wp_id -> canonical lane from the event log.

    Best-effort: routes through the canonical reader and returns ``{}`` when no
    canonical event log exists yet (#1775 Randy-Reducer F5 — this was a verbatim
    duplicate of ``get_all_wp_lanes`` minus the fail-loud guard).
    """
    from specify_cli.status import CanonicalStatusNotFoundError, get_all_wp_lanes

    try:
        return get_all_wp_lanes(feature_dir)
    except CanonicalStatusNotFoundError:
        return {}


def _compute_wp_progress(
    feature_dir: Path,
    *,
    status_dir: Path | None = None,
) -> dict[str, int | float] | None:
    """Compute WP lane counts and weighted progress for the progress field from the event log."""
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.is_dir():
        return None

    wp_files = sorted(tasks_dir.glob("WP*.md"))
    if not wp_files:
        return None

    lane_read_dir = status_dir if status_dir is not None else feature_dir
    wp_lanes = _get_wp_lanes(lane_read_dir)

    counts: dict[str, int | float] = {
        "total_wps": 0,
        "done_wps": 0,
        "approved_wps": 0,
        "in_progress_wps": 0,
        "planned_wps": 0,
        "for_review_wps": 0,
    }

    for wp_file in wp_files:
        counts["total_wps"] += 1
        wp_match = re.match(r"(WP\d+)", wp_file.stem)
        wp_id = wp_match.group(1) if wp_match else wp_file.stem
        # Default to GENESIS for unseeded WPs: they are not displayed in any
        # progress bucket until finalize-tasks seeds them (Contract 3, FR-008).
        lane = wp_lanes.get(wp_id, Lane.GENESIS)
        # Genesis WPs are non-display; they belong in no progress bucket.
        if lane == Lane.GENESIS:
            continue
        state = wp_state_for(lane)
        if state.lane == Lane.DONE:
            counts["done_wps"] += 1
        elif state.lane == Lane.APPROVED:
            counts["approved_wps"] += 1
        elif state.progress_bucket() == "in_flight" and not state.is_blocked:
            counts["in_progress_wps"] += 1
        elif state.progress_bucket() == "review":
            counts["for_review_wps"] += 1
        elif state.progress_bucket() == "not_started":
            counts["planned_wps"] += 1

    # Compute weighted progress from the materialized snapshot
    try:
        from specify_cli.status import compute_weighted_progress
        from specify_cli.status import materialize

        snapshot = materialize(lane_read_dir)
        progress = compute_weighted_progress(snapshot)
        counts["weighted_percentage"] = round(progress.percentage, 1)
    except Exception:
        pass

    return counts


def _find_first_wp_by_lane(
    feature_dir: Path,
    lane: str,
    *,
    status_dir: Path | None = None,
) -> str | None:
    """Find the first WP file with the given lane value (from event log).

    Accepts canonical lane strings (e.g. ``"planned"``) or legacy aliases
    (e.g. ``"doing"``).  Comparison is done via :func:`wp_state_for` so
    that aliases resolve to their canonical ``Lane`` enum member.
    """
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.is_dir():
        return None

    target_lane = wp_state_for(lane).lane

    lane_read_dir = status_dir if status_dir is not None else feature_dir
    wp_lanes = _get_wp_lanes(lane_read_dir)
    wp_files = sorted(tasks_dir.glob("WP*.md"))
    for wp_file in wp_files:
        wp_match = re.match(r"(WP\d+)", wp_file.stem)
        if wp_match is None:
            continue
        wp_id = wp_match.group(1)
        # Default to GENESIS for unseeded WPs: they are not claimable/findable
        # by any lane query until finalize-tasks seeds them (Contract 3, FR-008).
        wp_lane = wp_lanes.get(wp_id, Lane.GENESIS)
        # Genesis WPs cannot be found by lane query — skip them.
        if wp_lane == Lane.GENESIS:
            continue
        if wp_state_for(wp_lane).lane == target_lane:
            return wp_id
    return None


# ---------------------------------------------------------------------------
# Main decision function
# ---------------------------------------------------------------------------


def decide_next(
    agent: str,
    mission_slug: str,
    result: str,
    repo_root: Path,
) -> Decision:
    """Decide the next action for an agent in the mission loop.

    Delegates to :func:`runtime_bridge.decide_next_via_runtime` which uses
    the CLI-internal runtime's DAG planner
    (``runtime.next._internal_runtime.planner``) for step resolution
    and manages run state locally under ``.kittify/runtime/runs/``.

    The canonical agent loop is::

        while True:
            decision = spec-kitty next --agent X --json
            if decision.kind == "terminal": break
            execute(decision.prompt_file)
    """
    from runtime.next.runtime_bridge import decide_next_via_runtime

    return decide_next_via_runtime(agent, mission_slug, result, repo_root)


# ---------------------------------------------------------------------------
# State-to-action mapping
# ---------------------------------------------------------------------------


def _state_to_action(
    state: str,
    mission_slug: str,
    feature_dir: Path,
    repo_root: Path,
    mission_name: str,
) -> tuple[str | None, str | None, str | None]:
    """Map a mission state to a ``(action, wp_id, workspace_path)`` triple.

    Returns ``(None, None, None)`` if the state cannot be mapped to a
    command template.
    """
    # "implement" state: find first planned or in_progress WP
    if state == "implement":
        wp_id = _find_first_wp_by_lane(feature_dir, "planned")
        if wp_id is None:
            wp_id = _find_first_wp_by_lane(feature_dir, "doing")
        if wp_id is None:
            wp_id = _find_first_wp_by_lane(feature_dir, "in_progress")

        if wp_id is None:
            # No implementable WPs — check for reviewable ones.
            # Only for_review WPs are available for pickup; in_review WPs
            # are already claimed by another reviewer and must NOT be
            # reassigned (FR-012a).
            review_wp = _find_first_wp_by_lane(feature_dir, "for_review")
            if review_wp:
                workspace_path = str(resolve_workspace_for_wp(repo_root, mission_slug, review_wp).worktree_path)
                return "review", review_wp, workspace_path
            # in_review WPs exist but are not actionable by this agent —
            # review is already in progress, nothing to pick up.
            in_review_wp = _find_first_wp_by_lane(feature_dir, "in_review")
            if in_review_wp:
                return None, None, None
            return None, None, None

        workspace_path = str(resolve_workspace_for_wp(repo_root, mission_slug, wp_id).worktree_path)
        return "implement", wp_id, workspace_path

    # "review" state: WP-level if for_review WP exists, else template-level.
    # in_review WPs are already being reviewed by another agent and must
    # NOT be reassigned — only for_review WPs are available for pickup.
    if state == "review":
        wp_id = _find_first_wp_by_lane(feature_dir, "for_review")
        if wp_id is not None:
            workspace_path = str(resolve_workspace_for_wp(repo_root, mission_slug, wp_id).worktree_path)
            return "review", wp_id, workspace_path
        # Explicitly skip in_review WPs — they are claimed by another
        # reviewer (FR-012a).  Fall through to generic template resolution.
        # Note: _find_first_wp_by_lane(feature_dir, "in_review") is
        # intentionally not called here because we don't act on it.

    # "done" state -- terminal, no action
    if state == "done":
        return "accept", None, None

    # Generic: try state name as command template, then known aliases
    from specify_cli.runtime.resolver import resolve_command

    try:
        resolve_command(f"{state}.md", repo_root, mission=mission_name)
        return state, None, None
    except FileNotFoundError:
        pass

    # Known aliases (maps mission-specific state names to standard templates)
    _ALIASES: dict[str, str] = {
        "discovery": "research",
        "scoping": "specify",
        "methodology": "plan",
        "tasks_outline": "tasks-outline",
        "tasks_packages": "tasks-packages",
        "tasks_finalize": "tasks-finalize",
        "gathering": "implement",
        "synthesis": "review",
        "output": "accept",
        "goals": "specify",
        "structure": "plan",
        "draft": "plan",
    }
    alias = _ALIASES.get(state)
    if alias:
        # Registered consumer skills (CLI-driven shims or prompt-driven
        # commands) are known to the shim registry and do not require a
        # resolvable template file to be considered valid.
        from specify_cli.shims.registry import is_cli_driven, is_prompt_driven

        if is_cli_driven(alias) or is_prompt_driven(alias):
            return alias, None, None
        try:
            resolve_command(f"{alias}.md", repo_root, mission=mission_name)
            return alias, None, None
        except FileNotFoundError:
            pass

    return None, None, None


def _build_prompt_safe(
    action: str,
    feature_dir: Path,
    mission_slug: str,
    wp_id: str | None,
    agent: str,
    repo_root: Path,
    mission_type: str,
) -> str | None:
    """Build prompt, returning None on failure instead of raising.

    .. deprecated::
        Prefer :func:`_build_prompt_or_error` which surfaces the underlying
        exception text so callers can emit a structured ``blocked`` decision
        with a populated ``reason`` (WP06 / FR-006 / FR-013).
    """
    path, _err = _build_prompt_or_error(
        action=action,
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        wp_id=wp_id,
        agent=agent,
        repo_root=repo_root,
        mission_type=mission_type,
    )
    return path




def _build_prompt_or_error(
    action: str,
    feature_dir: Path,
    mission_slug: str,
    wp_id: str | None,
    agent: str,
    repo_root: Path,
    mission_type: str,
) -> tuple[str | None, str | None]:
    """Build prompt, returning ``(path, None)`` on success or ``(None, error)``.

    The ``error`` message is suitable for embedding in a ``blocked`` decision's
    ``reason`` so callers can avoid emitting a ``kind=step`` decision with a
    null/missing ``prompt_file`` (WP06 / FR-006 / FR-013).

    The path is also verified to exist on disk; if ``build_prompt`` returned a
    path that does not resolve, ``error`` is populated and ``path`` is ``None``.

    For composed actions (documentation ``discover``, ``audit``, … and their
    equivalents in research / software-dev missions), no file-based prompt
    template exists — dispatch happens through the composition layer.  Rather
    than returning ``(None, error)`` and causing ``_map_runtime_decision`` to
    emit a ``blocked`` decision, this function writes a minimal marker file so
    the ``kind=step`` invariant is satisfied (FR-007 / T019).
    """
    # Fast path: composed actions do not use file-based templates.  Write a
    # lightweight marker file and return its path so callers can emit a
    # ``kind=step`` Decision without hitting the ``if prompt_file is None``
    # blocked branch in ``_map_runtime_decision``.
    _is_composed_action = False
    try:
        from charter.mission_type_profiles import (  # noqa: PLC0415
            resolve_action_sequence as _charter_resolve_action_sequence,
        )

        action_sequence = _charter_resolve_action_sequence(mission_type, repo_root)
        _is_composed_action = wp_id is None and action in action_sequence
    except Exception:
        pass
    if _is_composed_action:
        composed_prompt = (
            f"# {mission_type} — {action}\n\n"
            f"This step is dispatched via composition.\n"
            f"Run `spec-kitty next --agent <name>` to advance.\n"
        )
        marker_fd, marker_path = tempfile.mkstemp(
            prefix=f"spec-kitty-composed-{action}-",
            suffix=".md",
            dir=prompt_tmp_dir(repo_root),
        )
        os.write(marker_fd, composed_prompt.encode("utf-8"))
        os.close(marker_fd)
        return marker_path, None

    try:
        from runtime.next.prompt_builder import build_prompt

        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            _, prompt_path = build_prompt(
                action=action,
                feature_dir=feature_dir,
                mission_slug=mission_slug,
                wp_id=wp_id,
                agent=agent,
                repo_root=repo_root,
                mission_type=mission_type,
            )
        path_str = str(prompt_path)
        try:
            if not Path(path_str).exists():
                return None, (
                    f"prompt template did not materialize on disk for action "
                    f"'{action}' (path={path_str})"
                )
        except OSError as exc:
            return None, (
                f"prompt template path is not stat-able for action '{action}': {exc}"
            )
        return path_str, None
    except FileNotFoundError:
        # No file-based template for this non-WP step (e.g. workflow-inserted
        # steps like ``design-review``, or global-runtime steps like
        # ``discovery`` that have no mission-step prompt file).  Rather than
        # returning an error and causing ``_map_runtime_decision`` to emit a
        # ``kind=blocked`` decision, write a minimal composition marker so the
        # ``kind=step`` invariant is satisfied (FR-007 / T019).
        if wp_id is None:
            composed_prompt = (
                f"# {mission_type} — {action}\n\n"
                f"This step is dispatched via composition.\n"
                f"Run `spec-kitty next --agent <name>` to advance.\n"
            )
            marker_fd, marker_path = tempfile.mkstemp(
                prefix=f"spec-kitty-composed-{action}-",
                suffix=".md",
                dir=prompt_tmp_dir(repo_root),
            )
            os.write(marker_fd, composed_prompt.encode("utf-8"))
            os.close(marker_fd)
            return marker_path, None
        return None, (
            f"prompt resolution failed for action '{action}': "
            f"FileNotFoundError: no template found"
        )
    except Exception as exc:
        return None, (
            f"prompt resolution failed for action '{action}': "
            f"{type(exc).__name__}: {exc}"
        )
