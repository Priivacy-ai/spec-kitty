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
    answer: Annotated[Optional[str], typer.Option("--answer", help="Answer to a pending decision")] = None,
    decision_id: Annotated[Optional[str], typer.Option("--decision-id", help="Decision ID (required if multiple pending)")] = None,
) -> None:
    """Decide and emit the next agent action for the current mission.

    Agents call this command repeatedly in a loop.  The system inspects the
    mission state machine, evaluates guards, and returns a deterministic
    decision with an action and prompt file.

    Examples:
        spec-kitty next --agent claude --json
        spec-kitty next --agent codex --feature 034-my-feature
        spec-kitty next --agent gemini --result failed --json
        spec-kitty next --agent claude --answer "yes" --json
        spec-kitty next --agent claude --answer "approve" --decision-id "input:review" --json
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

    # Handle --answer flow
    answered_id = None
    if answer is not None:
        answered_id = _handle_answer(agent, feature_slug, answer, decision_id, repo_root)

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

    # Output — always exactly one JSON document
    if json_output:
        d = decision.to_dict()
        if answered_id is not None:
            d["answered"] = answered_id
            d["answer"] = answer
        print(json.dumps(d, indent=2))
    else:
        if answered_id is not None:
            print(f"  Answered decision: {answered_id}")
        _print_human(decision)

    # Exit code
    if decision.kind == DecisionKind.blocked:
        raise typer.Exit(1)


def _handle_answer(
    agent: str,
    feature_slug: str,
    answer: str,
    decision_id: str | None,
    repo_root: object,
) -> str:
    """Handle the --answer flow for pending decisions.

    Returns the resolved decision_id.
    """
    from pathlib import Path

    repo_root_path = Path(str(repo_root)) if not isinstance(repo_root, Path) else repo_root

    try:
        from specify_cli.next.runtime_bridge import answer_decision_via_runtime, get_or_start_run
        from specify_cli.mission import get_feature_mission_key

        feature_dir = repo_root_path / "kitty-specs" / feature_slug
        mission_key = get_feature_mission_key(feature_dir)
        run_ref = get_or_start_run(feature_slug, repo_root_path, mission_key)

        # If no decision_id provided, try to auto-resolve
        if decision_id is None:
            from spec_kitty_runtime.engine import _read_snapshot

            snapshot = _read_snapshot(Path(run_ref.run_dir))
            pending = snapshot.pending_decisions

            if len(pending) == 0:
                print("Error: No pending decisions to answer", file=sys.stderr)
                raise typer.Exit(1)
            elif len(pending) == 1:
                decision_id = next(iter(pending.keys()))
            else:
                pending_ids = sorted(pending.keys())
                print(
                    f"Error: Multiple pending decisions ({', '.join(pending_ids)}). "
                    f"Use --decision-id to specify which one.",
                    file=sys.stderr,
                )
                raise typer.Exit(1)

        answer_decision_via_runtime(
            feature_slug, decision_id, answer, agent, repo_root_path,
        )

        return decision_id

    except typer.Exit:
        raise
    except Exception as exc:
        print(f"Error answering decision: {exc}", file=sys.stderr)
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

    if getattr(decision, "question", None):
        print(f"  Question: {decision.question}")
    if getattr(decision, "options", None):
        for i, opt in enumerate(decision.options, 1):
            print(f"    {i}. {opt}")
    if decision.decision_id:
        print(f"  Decision ID: {decision.decision_id}")

    if decision.progress:
        p = decision.progress
        total = p.get("total_wps", 0)
        done = p.get("done_wps", 0)
        if total > 0:
            pct = int(100 * done / total)
            print(f"  Progress: {done}/{total} WPs done ({pct}%)")

    if decision.run_id:
        print(f"  Run ID: {decision.run_id}")

    if decision.prompt_file:
        print()
        print("  Next step: read the prompt file:")
        print(f"    cat {decision.prompt_file}")
