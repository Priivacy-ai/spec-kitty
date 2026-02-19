"""Core decision engine for ``spec-kitty next``.

Delegates planning to ``spec-kitty-runtime`` via :mod:`runtime_bridge`.

The :class:`Decision` dataclass and :class:`DecisionKind` constants are the
public JSON contract.  WP helpers (``_compute_wp_progress``,
``_find_first_wp_by_lane``) and ``_state_to_action`` are kept for use by the
bridge layer.

Legacy functions ``derive_mission_state`` and ``evaluate_guards`` are
preserved for backward compatibility and tests but are no longer called by
``decide_next``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from specify_cli.mission_v1.events import read_events
from specify_cli.mission_v1.guards import _read_lane_from_frontmatter


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class DecisionKind:
    """String constants for decision kinds (avoids Enum import overhead)."""
    step = "step"
    decision_required = "decision_required"
    blocked = "blocked"
    terminal = "terminal"


@dataclass
class Decision:
    kind: str  # one of DecisionKind.*
    agent: str
    feature_slug: str
    mission: str
    mission_state: str
    timestamp: str
    action: str | None = None
    wp_id: str | None = None
    workspace_path: str | None = None
    prompt_file: str | None = None
    reason: str | None = None
    guard_failures: list[str] = field(default_factory=list)
    progress: dict[str, Any] | None = None
    origin: dict[str, Any] = field(default_factory=dict)
    # Runtime fields (added in v2.0.0)
    run_id: str | None = None
    step_id: str | None = None
    decision_id: str | None = None
    input_key: str | None = None
    question: str | None = None
    options: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "agent": self.agent,
            "feature_slug": self.feature_slug,
            "mission": self.mission,
            "mission_state": self.mission_state,
            "timestamp": self.timestamp,
            "action": self.action,
            "wp_id": self.wp_id,
            "workspace_path": self.workspace_path,
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
        No longer used by ``decide_next``.  Runtime state is now managed by
        ``spec-kitty-runtime`` via ``state.json`` in the run directory.
    """
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


def _compute_wp_progress(feature_dir: Path) -> dict[str, int] | None:
    """Compute WP lane counts for the progress field."""
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.is_dir():
        return None

    wp_files = sorted(tasks_dir.glob("WP*.md"))
    if not wp_files:
        return None

    counts = {
        "total_wps": 0,
        "done_wps": 0,
        "in_progress_wps": 0,
        "planned_wps": 0,
        "for_review_wps": 0,
    }

    for wp_file in wp_files:
        counts["total_wps"] += 1
        lane = _read_lane_from_frontmatter(wp_file) or "planned"
        if lane == "done":
            counts["done_wps"] += 1
        elif lane in ("doing", "in_progress"):
            counts["in_progress_wps"] += 1
        elif lane == "for_review":
            counts["for_review_wps"] += 1
        elif lane == "planned":
            counts["planned_wps"] += 1

    return counts


def _find_first_wp_by_lane(feature_dir: Path, lane: str) -> str | None:
    """Find the first WP file with the given lane value."""
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.is_dir():
        return None

    wp_files = sorted(tasks_dir.glob("WP*.md"))
    for wp_file in wp_files:
        wp_lane = _read_lane_from_frontmatter(wp_file)
        if wp_lane == lane:
            match = re.match(r"(WP\d+)", wp_file.stem)
            if match:
                return match.group(1)
    return None


# ---------------------------------------------------------------------------
# Main decision function
# ---------------------------------------------------------------------------


def decide_next(
    agent: str,
    feature_slug: str,
    result: str,
    repo_root: Path,
) -> Decision:
    """Decide the next action for an agent in the mission loop.

    Delegates to :func:`runtime_bridge.decide_next_via_runtime` which uses
    the ``spec-kitty-runtime`` DAG planner for step resolution and manages
    run state locally under ``.kittify/runtime/runs/``.

    The canonical agent loop is::

        while True:
            decision = spec-kitty next --agent X --json
            if decision.kind == "terminal": break
            execute(decision.prompt_file)
    """
    from specify_cli.next.runtime_bridge import decide_next_via_runtime

    return decide_next_via_runtime(agent, feature_slug, result, repo_root)


# ---------------------------------------------------------------------------
# State-to-action mapping
# ---------------------------------------------------------------------------


def _state_to_action(
    state: str,
    feature_slug: str,
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
            # Check for for_review WPs -- switch to review sub-action
            review_wp = _find_first_wp_by_lane(feature_dir, "for_review")
            if review_wp:
                workspace_name = f"{feature_slug}-{review_wp}"
                workspace_path = str(repo_root / ".worktrees" / workspace_name)
                return "review", review_wp, workspace_path
            return None, None, None

        workspace_name = f"{feature_slug}-{wp_id}"
        workspace_path = str(repo_root / ".worktrees" / workspace_name)
        return "implement", wp_id, workspace_path

    # "review" state: WP-level if for_review WP exists, else template-level
    if state == "review":
        wp_id = _find_first_wp_by_lane(feature_dir, "for_review")
        if wp_id is not None:
            workspace_name = f"{feature_slug}-{wp_id}"
            workspace_path = str(repo_root / ".worktrees" / workspace_name)
            return "review", wp_id, workspace_path
        # Fall through to generic template resolution below

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
        try:
            resolve_command(f"{alias}.md", repo_root, mission=mission_name)
            return alias, None, None
        except FileNotFoundError:
            pass

    return None, None, None


def _build_prompt_safe(
    action: str,
    feature_dir: Path,
    feature_slug: str,
    wp_id: str | None,
    agent: str,
    repo_root: Path,
    mission_key: str,
) -> str | None:
    """Build prompt, returning None on failure instead of raising."""
    try:
        from specify_cli.next.prompt_builder import build_prompt

        _, prompt_path = build_prompt(
            action=action,
            feature_dir=feature_dir,
            feature_slug=feature_slug,
            wp_id=wp_id,
            agent=agent,
            repo_root=repo_root,
            mission_key=mission_key,
        )
        return str(prompt_path)
    except Exception:
        return None
