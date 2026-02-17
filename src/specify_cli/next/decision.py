"""Core decision engine for ``spec-kitty next``.

Pure logic, no CLI concerns.  Given a feature directory and mission config,
derive the current mission state from the event log, evaluate guards, and
return a deterministic :class:`Decision`.

**State advancement**: when guards pass, ``decide_next`` emits a
``phase_entered`` event so the canonical agent loop advances on each call.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from specify_cli.mission_v1.events import emit_event, read_events
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
    progress: dict | None = None
    origin: dict = field(default_factory=dict)

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
        }


# ---------------------------------------------------------------------------
# State derivation from event log
# ---------------------------------------------------------------------------


def derive_mission_state(feature_dir: Path, initial_state: str) -> str:
    """Derive current mission state by replaying the event log.

    Scans ``mission-events.jsonl`` for the last ``phase_entered`` event and
    returns its state.  Falls back to *initial_state* when the log is empty
    or contains no ``phase_entered`` events.
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
# Guard evaluation (standalone, without firing transitions)
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

    **State advancement**: when guards pass and the machine advances, a
    ``phase_entered`` event is emitted so the next call sees the new state.
    This is the only place state is persisted — the canonical loop is::

        while True:
            decision = spec-kitty next --agent X --json
            if decision.kind == "terminal": break
            execute(decision.prompt_file)

    Algorithm:
    1. Resolve feature_dir and mission config
    2. Derive current state from event log
    3. Handle ``--result`` flags (failed, blocked)
    4. Check terminal state
    5. Evaluate guards for ``advance`` from current state
    6. If guards fail → stay in current state, map to action
    7. If guards pass → advance, persist ``phase_entered``, map dest to action
    8. Build prompt via prompt_builder
    """
    feature_dir = repo_root / "kitty-specs" / feature_slug
    now = datetime.now(timezone.utc).isoformat()

    if not feature_dir.is_dir():
        return Decision(
            kind=DecisionKind.blocked,
            agent=agent,
            feature_slug=feature_slug,
            mission="unknown",
            mission_state="unknown",
            timestamp=now,
            reason=f"Feature directory not found: {feature_dir}",
        )

    # --- Resolve mission ---
    from specify_cli.mission import get_feature_mission_key

    mission_key = get_feature_mission_key(feature_dir)

    try:
        from specify_cli.runtime.resolver import resolve_mission as resolve_mission_path

        mission_result = resolve_mission_path(mission_key, repo_root)
        mission_path = mission_result.path.parent
    except FileNotFoundError:
        return Decision(
            kind=DecisionKind.blocked,
            agent=agent,
            feature_slug=feature_slug,
            mission=mission_key,
            mission_state="unknown",
            timestamp=now,
            reason=f"Mission '{mission_key}' not found in any resolution tier",
        )

    from specify_cli.mission_v1 import load_mission

    try:
        mission = load_mission(mission_path, feature_dir=feature_dir)
    except Exception as exc:
        return Decision(
            kind=DecisionKind.blocked,
            agent=agent,
            feature_slug=feature_slug,
            mission=mission_key,
            mission_state="unknown",
            timestamp=now,
            reason=f"Failed to load mission: {exc}",
        )

    origin = {
        "mission_tier": getattr(mission_result, "tier", "unknown"),
        "mission_path": str(mission_path),
    }
    if hasattr(origin["mission_tier"], "value"):
        origin["mission_tier"] = origin["mission_tier"].value

    # --- Derive current state ---
    config = mission._config if hasattr(mission, "_config") else {}
    initial_state = config.get("initial", "discovery")
    current_state = derive_mission_state(feature_dir, initial_state)
    progress = _compute_wp_progress(feature_dir)
    mission_name = config.get("mission", {}).get("name", mission_key)

    # --- Handle --result flags ---
    if result == "failed":
        return Decision(
            kind=DecisionKind.decision_required,
            agent=agent,
            feature_slug=feature_slug,
            mission=mission_key,
            mission_state=current_state,
            timestamp=now,
            reason="Previous step reported failure; agent decision required",
            progress=progress,
            origin=origin,
        )

    if result == "blocked":
        return Decision(
            kind=DecisionKind.blocked,
            agent=agent,
            feature_slug=feature_slug,
            mission=mission_key,
            mission_state=current_state,
            timestamp=now,
            reason="Previous step reported blocked",
            progress=progress,
            origin=origin,
        )

    # --- Terminal check ---
    if current_state == "done":
        return Decision(
            kind=DecisionKind.terminal,
            agent=agent,
            feature_slug=feature_slug,
            mission=mission_key,
            mission_state=current_state,
            timestamp=now,
            reason="Mission complete",
            progress=progress,
            origin=origin,
        )

    # --- Evaluate guards for advance from current state ---
    guards_passed, guard_failures = evaluate_guards(config, feature_dir, current_state)

    if not guards_passed:
        # Guards haven't passed -- stay in current state and map it to an action
        action, wp_id, workspace_path = _state_to_action(
            current_state, feature_slug, feature_dir, repo_root, mission_name,
        )

        if action is None:
            return Decision(
                kind=DecisionKind.blocked,
                agent=agent,
                feature_slug=feature_slug,
                mission=mission_key,
                mission_state=current_state,
                timestamp=now,
                reason=f"No action mapped for state '{current_state}'",
                guard_failures=guard_failures,
                progress=progress,
                origin=origin,
            )

        prompt_file = _build_prompt_safe(
            action, feature_dir, feature_slug, wp_id, agent, repo_root, mission_key,
        )

        return Decision(
            kind=DecisionKind.step,
            agent=agent,
            feature_slug=feature_slug,
            mission=mission_key,
            mission_state=current_state,
            timestamp=now,
            action=action,
            wp_id=wp_id,
            workspace_path=workspace_path,
            prompt_file=prompt_file,
            guard_failures=guard_failures,
            progress=progress,
            origin=origin,
        )

    # --- Guards passed: advance state ---
    transitions = config.get("transitions", [])
    dest_state = None
    for t in transitions:
        if t.get("trigger") == "advance" and t.get("source") == current_state:
            dest_state = t.get("dest")
            break

    if dest_state is None:
        return Decision(
            kind=DecisionKind.terminal,
            agent=agent,
            feature_slug=feature_slug,
            mission=mission_key,
            mission_state=current_state,
            timestamp=now,
            reason=f"No advance transition from state '{current_state}'",
            progress=progress,
            origin=origin,
        )

    # *** P0 FIX: persist state advancement ***
    emit_event(
        "phase_entered",
        {"state": dest_state, "from_state": current_state, "agent": agent},
        mission_name=mission_name,
        feature_dir=feature_dir,
    )

    # Terminal check on destination
    if dest_state == "done":
        return Decision(
            kind=DecisionKind.terminal,
            agent=agent,
            feature_slug=feature_slug,
            mission=mission_key,
            mission_state=dest_state,
            timestamp=now,
            reason="Mission complete",
            progress=progress,
            origin=origin,
        )

    # Map destination state to action
    action, wp_id, workspace_path = _state_to_action(
        dest_state, feature_slug, feature_dir, repo_root, mission_name,
    )

    if action is None:
        return Decision(
            kind=DecisionKind.blocked,
            agent=agent,
            feature_slug=feature_slug,
            mission=mission_key,
            mission_state=dest_state,
            timestamp=now,
            reason=f"No action mapped for state '{dest_state}'",
            progress=progress,
            origin=origin,
        )

    prompt_file = _build_prompt_safe(
        action, feature_dir, feature_slug, wp_id, agent, repo_root, mission_key,
    )

    return Decision(
        kind=DecisionKind.step,
        agent=agent,
        feature_slug=feature_slug,
        mission=mission_key,
        mission_state=dest_state,
        timestamp=now,
        action=action,
        wp_id=wp_id,
        workspace_path=workspace_path,
        prompt_file=prompt_file,
        progress=progress,
        origin=origin,
    )


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
