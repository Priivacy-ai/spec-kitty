"""CLI command for ``spec-kitty next``."""

from __future__ import annotations

import json
import sys
from typing import Optional

import typer
from typing_extensions import Annotated

from specify_cli.core.context_validation import require_main_repo
from specify_cli.core.feature_detection import (
    FeatureDetectionError,
    detect_feature_slug,
)
from specify_cli.core.paths import locate_project_root
from specify_cli.mission_v1.events import emit_event
from specify_cli.next.decision import DecisionKind, decide_next


_VALID_RESULTS = ("success", "failed", "blocked")


@require_main_repo
def next_step(
    agent: Annotated[str, typer.Option("--agent", help="Agent name (required)")],
    result: Annotated[str, typer.Option("--result", help="Result of previous step: success|failed|blocked")] = "success",
    feature: Annotated[Optional[str], typer.Option("--feature", help="Feature slug (auto-detected if omitted)")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON decision only")] = False,
) -> None:
    """Decide and emit the next agent action for the current mission.

    Agents call this command repeatedly in a loop.  The system inspects the
    mission state machine, evaluates guards, and returns a deterministic
    decision with an action and prompt file.

    Examples:
        spec-kitty next --agent claude --json
        spec-kitty next --agent codex --feature 034-my-feature
        spec-kitty next --agent gemini --result failed --json
    """
    # Validate --result
    if result not in _VALID_RESULTS:
        print(f"Error: --result must be one of {_VALID_RESULTS}, got '{result}'", file=sys.stderr)
        raise typer.Exit(1)

    # Resolve repo root
    repo_root = locate_project_root()
    if repo_root is None:
        print("Error: Could not locate project root", file=sys.stderr)
        raise typer.Exit(1)

    # Resolve feature slug
    try:
        feature_slug = detect_feature_slug(repo_root, explicit_feature=feature)
    except FeatureDetectionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise typer.Exit(1)

    # Core decision
    decision = decide_next(agent, feature_slug, result, repo_root)

    # Emit MissionNextInvoked event
    feature_dir = repo_root / "kitty-specs" / feature_slug
    emit_event(
        "MissionNextInvoked",
        {
            "agent": agent,
            "result_input": result,
            "decision_kind": decision.kind,
            "action": decision.action,
            "wp_id": decision.wp_id,
            "mission_state": decision.mission_state,
        },
        mission_name=decision.mission,
        feature_dir=feature_dir if feature_dir.is_dir() else None,
    )

    # Output
    if json_output:
        print(json.dumps(decision.to_dict(), indent=2))
    else:
        _print_human(decision)

    # Exit code
    if decision.kind == DecisionKind.blocked:
        raise typer.Exit(1)


def _print_human(decision) -> None:
    """Print a human-readable summary."""
    kind = decision.kind.upper()
    print(f"[{kind}] {decision.mission} @ {decision.mission_state}")

    if decision.action:
        if decision.wp_id:
            print(f"  Action: {decision.action} {decision.wp_id}")
        else:
            print(f"  Action: {decision.action}")

    if decision.workspace_path:
        print(f"  Workspace: {decision.workspace_path}")

    if decision.guard_failures:
        print(f"  Guards pending: {', '.join(decision.guard_failures)}")

    if decision.reason:
        print(f"  Reason: {decision.reason}")

    if decision.progress:
        p = decision.progress
        total = p.get("total_wps", 0)
        done = p.get("done_wps", 0)
        if total > 0:
            pct = int(100 * done / total)
            print(f"  Progress: {done}/{total} WPs done ({pct}%)")

    if decision.prompt_file:
        print()
        print(f"  Next step: read the prompt file:")
        print(f"    cat {decision.prompt_file}")
