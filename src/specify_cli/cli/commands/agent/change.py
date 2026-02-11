"""Agent change commands - programmatic endpoints for mid-stream change requests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from specify_cli.core.change_stack import (
    ChangeStackError,
    ValidationState,
    _build_implementation_hint,
    _next_wp_id,
    _render_wp_body,
    build_closed_reference_links,
    compute_merge_coordination_jobs,
    extract_dependency_candidates,
    generate_change_work_packages,
    persist_merge_coordination_jobs,
    reconcile_change_stack,
    resolve_next_change_wp,
    synthesize_change_plan,
    validate_change_request,
    validate_dependency_graph_integrity,
    validate_dependency_policy,
    write_change_work_packages,
)
from specify_cli.core.feature_detection import (
    FeatureDetectionError,
    detect_feature_slug,
)
from specify_cli.core.paths import locate_project_root

app = typer.Typer(
    name="change",
    help="Mid-stream change request commands for AI agents",
    no_args_is_help=True,
)


def _output_result(data: dict[str, object], as_json: bool) -> None:
    """Output result as JSON or human-readable text."""
    if as_json:
        print(json.dumps(data, indent=2, default=str))
    else:
        for key, value in data.items():
            print(f"  {key}: {value}")


def _output_error(error: str, message: str, as_json: bool) -> None:
    """Output error as JSON or human-readable text."""
    if as_json:
        print(json.dumps({"error": error, "message": message}))
    else:
        print(f"Error: {error} - {message}")


def _resolve_repo() -> Path:
    """Resolve project root (requires initialized Spec Kitty project).

    Returns:
        Project root path (with .kittify directory)

    Raises:
        typer.Exit: If not inside an initialized Spec Kitty project
    """
    repo_root = locate_project_root()
    if repo_root is None:
        print(
            "Error: Not inside an initialized Spec Kitty project (.kittify not found)"
        )
        raise typer.Exit(1)
    return repo_root


def _resolve_feature(feature: Optional[str]) -> tuple[Path, str]:
    """Resolve repo root and feature slug.

    Returns:
        Tuple of (repo_root, feature_slug)

    Raises:
        typer.Exit: If resolution fails
    """
    repo_root = _resolve_repo()

    try:
        feature_slug = (
            feature or detect_feature_slug(repo_root, cwd=Path.cwd())
        ).strip()
    except (FeatureDetectionError, Exception) as exc:
        print(f"Error: Could not detect feature - {exc}")
        raise typer.Exit(1)

    return repo_root, feature_slug


@app.command(name="preview")
def preview(
    request_text: Annotated[
        str, typer.Argument(help="Natural-language change request")
    ],
    feature: Annotated[
        Optional[str], typer.Option("--feature", help="Feature slug (auto-detected)")
    ] = None,
    submitted_by: Annotated[
        str, typer.Option("--submitted-by", help="Who submitted the request")
    ] = "agent",
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Validate and classify a change request before creating work packages.

    Performs branch stash routing, complexity assessment, and ambiguity
    detection without writing any files. Returns a preview of the planned
    changes for confirmation.

    Examples:
        spec-kitty agent change preview "use SQLAlchemy instead of raw SQL"
        spec-kitty agent change preview "add caching" --json
    """
    repo_root = _resolve_repo()

    # Validate and route the change request
    try:
        change_req = validate_change_request(
            request_text=request_text,
            repo_root=repo_root,
            feature=feature,
        )
    except ChangeStackError as exc:
        _output_error("stash_resolution_failed", str(exc), json_output)
        raise typer.Exit(1)

    # Build preview response
    requires_clarification = change_req.validation_state == ValidationState.AMBIGUOUS
    score = change_req.complexity_score

    # Determine warning state (FR-010)
    warning_required = score is not None and score.recommend_specify
    warning_message: str | None = None
    if warning_required:
        warning_message = (
            "This change request exceeds the complexity threshold. "
            "Consider using /spec-kitty.specify for full planning. "
            "Use --continue flag on apply to proceed anyway."
        )

    result: dict[str, object] = {
        "requestId": change_req.request_id,
        "stashKey": change_req.stash.stash_key,
        "stashScope": change_req.stash.scope.value,
        "stashPath": str(change_req.stash.stash_path),
        "validationState": change_req.validation_state.value,
        "complexity": score.to_dict() if score is not None else {},
        "proposedMode": score.proposed_mode.value if score is not None else "single_wp",
        "warningRequired": warning_required,
        "warningMessage": warning_message,
        "requiresClarification": requires_clarification,
        "clarificationPrompt": change_req.ambiguity.clarification_prompt,
    }

    # Include closed reference info if present
    if change_req.closed_references.has_closed_references:
        result["closedReferences"] = {
            "wpIds": change_req.closed_references.closed_wp_ids,
            "linkOnly": True,
        }

    _output_result(result, json_output)


@app.command(name="apply")
def apply(
    request_id: Annotated[str, typer.Argument(help="Request ID from preview step")],
    request_text: Annotated[
        str,
        typer.Option(
            "--request-text",
            help="Original request text (required for complexity gating)",
        ),
    ] = ...,
    feature: Annotated[
        Optional[str], typer.Option("--feature", help="Feature slug (auto-detected)")
    ] = None,
    continue_after_warning: Annotated[
        bool, typer.Option("--continue", help="Continue despite complexity warning")
    ] = False,
    confirm_unambiguous: Annotated[
        bool, typer.Option("--confirm", help="Confirm request is unambiguous")
    ] = False,
    scope_breadth: Annotated[
        int, typer.Option("--scope-breadth", help="AI-assessed scope breadth (0-3)")
    ] = 0,
    coupling: Annotated[
        int, typer.Option("--coupling", help="AI-assessed coupling impact (0-2)")
    ] = 0,
    dependency_churn: Annotated[
        int,
        typer.Option("--dependency-churn", help="AI-assessed dependency churn (0-2)"),
    ] = 0,
    ambiguity: Annotated[
        int, typer.Option("--ambiguity", help="AI-assessed ambiguity level (0-2)")
    ] = 0,
    integration_risk: Annotated[
        int,
        typer.Option("--integration-risk", help="AI-assessed integration risk (0-1)"),
    ] = 0,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Apply a validated change request and create change work packages.

    Takes a request ID from the preview step and creates the actual work
    package files with dependencies, documentation links, and merge
    coordination jobs.

    The AI agent assesses complexity via --scope-breadth, --coupling,
    --dependency-churn, --ambiguity, and --integration-risk parameters.
    When the total exceeds the high-complexity threshold, the --continue
    flag is required (FR-010, SC-003). Without it, apply is blocked.

    Examples:
        spec-kitty agent change apply "id-123" --request-text "use SQLAlchemy" --scope-breadth 1 --coupling 1
        spec-kitty agent change apply "id-123" --request-text "replace ORM" --scope-breadth 3 --coupling 2 --continue --json
    """
    repo_root, feature_slug = _resolve_feature(feature)

    # FR-010/FR-011: Build complexity score from AI-assessed factors
    from specify_cli.core.change_classifier import classify_from_scores

    score = classify_from_scores(
        scope_breadth=scope_breadth,
        coupling=coupling,
        dependency_churn=dependency_churn,
        ambiguity=ambiguity,
        integration_risk=integration_risk,
        continued_after_warning=continue_after_warning,
    )
    if score.recommend_specify and not continue_after_warning:
        _output_error(
            "high_complexity_blocked",
            "Request exceeds complexity threshold (score {}/10, classification: {}). "
            "Use --continue to proceed or use /spec-kitty.specify for full planning.".format(
                score.total_score, score.classification.value
            ),
            json_output,
        )
        raise typer.Exit(1)

    # Re-validate request to get full ChangeRequest if text provided
    change_req = None
    if request_text:
        try:
            change_req = validate_change_request(
                request_text=request_text,
                repo_root=repo_root,
                feature=feature,
            )
            # Override the request_id with the one from preview
            change_req.request_id = request_id
            # Propagate the score with correct continued_after_warning state
            # (validate_change_request recomputes without it)
            change_req.complexity_score = score
        except ChangeStackError as exc:
            _output_error("validation_failed", str(exc), json_output)
            raise typer.Exit(1)

    if change_req is not None:
        # Synthesize plan
        plan = synthesize_change_plan(change_req)
        tasks_dir = change_req.stash.stash_path

        # --- Dependency policy enforcement (T024-T026) ---
        import re as _re

        wp_refs = _re.findall(r"\bWP(\d{2})\b", request_text)
        affected_wp_ids = sorted(set(f"WP{num}" for num in wp_refs))

        # Build closed reference links (T027)
        closed_refs = build_closed_reference_links(
            request_text,
            tasks_dir,
            feature_slug,
            repo_root,
        )
        plan.closed_reference_wp_ids = closed_refs

        # Allocate a provisional change WP ID for dependency validation
        provisional_wp_id = _next_wp_id(tasks_dir)

        # Extract candidate dependency edges (T024)
        candidates = extract_dependency_candidates(
            affected_wp_ids,
            provisional_wp_id,
            tasks_dir,
        )

        # Validate dependency policy (T025)
        policy_result = validate_dependency_policy(candidates, tasks_dir)
        validated_dep_ids = [e.target for e in policy_result.valid_edges]

        # Validate full graph integrity (T026) - abort atomically on failure
        dep_issues: list[str] = []
        if validated_dep_ids:
            graph_valid, graph_errors = validate_dependency_graph_integrity(
                provisional_wp_id,
                validated_dep_ids,
                tasks_dir,
            )
            if not graph_valid:
                dep_issues.extend(graph_errors)
                _output_error(
                    "dependency_validation_failed",
                    "; ".join(graph_errors),
                    json_output,
                )
                raise typer.Exit(1)

        # Propagate validated dependencies into the plan
        plan.affected_open_wp_ids = validated_dep_ids

        # Generate WPs with dependency information
        wps = generate_change_work_packages(change_req, plan, tasks_dir)

        # Inject validated dependencies into generated WPs and re-render bodies
        for wp in wps:
            if not wp.dependencies and validated_dep_ids:
                wp.dependencies = validated_dep_ids
                hint = _build_implementation_hint(wp.work_package_id, wp.dependencies)
                wp.body = _render_wp_body(
                    wp,
                    change_req.raw_text,
                    plan.guardrails,
                    wp.closed_reference_links,
                    hint,
                )

        # Write WP files to disk
        written_paths = write_change_work_packages(wps, tasks_dir)

        # Build rejected edge diagnostics
        rejected_diagnostics = [
            {"edge": f"{e.source} -> {e.target}", "reason": reason}
            for e, reason in policy_result.rejected_edges
        ]

        # Reconcile tasks.md and validate dependencies (WP06)
        feature_dir = change_req.stash.stash_path.parent
        consistency = reconcile_change_stack(
            change_req.stash.stash_path,
            feature_dir,
            wps,
        )

        # Compute merge coordination jobs (WP06)
        merge_jobs = compute_merge_coordination_jobs(
            wps,
            change_req.stash.stash_path,
            plan,
        )
        if merge_jobs:
            persist_merge_coordination_jobs(merge_jobs, feature_dir)

        result: dict[str, object] = {
            "requestId": request_id,
            "createdWorkPackages": [wp.to_dict() for wp in wps],
            "writtenFiles": [str(p) for p in written_paths],
            "closedReferenceLinks": plan.closed_reference_wp_ids,
            "mergeCoordinationJobs": [j.to_dict() for j in merge_jobs],
            "consistency": consistency.to_dict(),
            "mode": plan.mode.value,
        }
        if rejected_diagnostics:
            result["rejectedEdges"] = rejected_diagnostics
        if score is not None:
            result["complexity"] = score.to_dict()
    else:
        # No request text: legacy/minimal apply (preview-only flow)
        result = {
            "requestId": request_id,
            "createdWorkPackages": [],
            "closedReferenceLinks": [],
            "mergeCoordinationJobs": [],
            "consistency": {
                "updatedTasksDoc": False,
                "dependencyValidationPassed": True,
                "brokenLinksFixed": 0,
                "issues": [],
            },
            "status": "no_request_text",
            "message": "No --request-text provided. Pass request text for WP synthesis.",
        }

    _output_result(result, json_output)


@app.command(name="next")
def next_doable(
    feature: Annotated[
        Optional[str], typer.Option("--feature", help="Feature slug (auto-detected)")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Resolve the next doable work package with change-stack priority.

    Implements stack-first selection: ready change-stack items take priority
    over normal backlog items. Checks both the main change-stack and the
    feature-local stash. If change-stack items exist but none are ready,
    normal progression is blocked and blockers are reported.

    Examples:
        spec-kitty agent change next
        spec-kitty agent change next --json
    """
    repo_root, feature_slug = _resolve_feature(feature)

    from specify_cli.core.change_stack import MAIN_STASH_RELATIVE
    from specify_cli.core.feature_detection import _get_main_repo_root

    # Check main change-stack first (cross-feature priority)
    main_repo = _get_main_repo_root(repo_root)
    main_stash_dir = main_repo / MAIN_STASH_RELATIVE

    if main_stash_dir.exists() and any(main_stash_dir.glob("WP*.md")):
        main_selection = resolve_next_change_wp(main_stash_dir, "main")

        if (
            main_selection.selected_source == "change_stack"
            and main_selection.next_wp_id
        ):
            result: dict[str, object] = {
                "stashKey": "main",
                "selectedSource": main_selection.selected_source,
                "nextWorkPackageId": main_selection.next_wp_id,
                "normalProgressionBlocked": main_selection.normal_progression_blocked,
                "blockers": main_selection.blockers,
            }
            if main_selection.pending_change_wps:
                result["pendingChangeWPs"] = main_selection.pending_change_wps
            _output_result(result, json_output)
            return

        if main_selection.selected_source == "blocked":
            result = {
                "stashKey": "main",
                "selectedSource": main_selection.selected_source,
                "nextWorkPackageId": None,
                "normalProgressionBlocked": True,
                "blockers": main_selection.blockers,
            }
            if main_selection.pending_change_wps:
                result["pendingChangeWPs"] = main_selection.pending_change_wps
            _output_result(result, json_output)
            return

    # Check feature-local tasks directory
    tasks_dir = repo_root / "kitty-specs" / feature_slug / "tasks"

    # Run stack-first selection on feature stash (FR-017)
    selection = resolve_next_change_wp(tasks_dir, feature_slug)

    result = {
        "stashKey": feature_slug,
        "selectedSource": selection.selected_source,
        "nextWorkPackageId": selection.next_wp_id,
        "normalProgressionBlocked": selection.normal_progression_blocked,
        "blockers": selection.blockers,
    }

    if selection.pending_change_wps:
        result["pendingChangeWPs"] = selection.pending_change_wps

    _output_result(result, json_output)


@app.command(name="reconcile")
def reconcile(
    feature: Annotated[
        Optional[str], typer.Option("--feature", help="Feature slug (auto-detected)")
    ] = None,
    recompute_merge_jobs: Annotated[
        bool,
        typer.Option(
            "--recompute-merge-jobs", help="Recompute merge coordination jobs"
        ),
    ] = True,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Recompute links, dependencies, and merge coordination jobs.

    Validates all change-stack references, repairs broken links, and
    regenerates merge coordination jobs where integration risk exists.

    Examples:
        spec-kitty agent change reconcile
        spec-kitty agent change reconcile --json
    """
    repo_root, feature_slug = _resolve_feature(feature)

    # Resolve paths
    feature_dir = repo_root / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"

    # Run reconciliation (no new WPs - reconcile existing state)

    consistency = reconcile_change_stack(tasks_dir, feature_dir, [])

    # Recompute merge jobs if requested
    merge_jobs_data: list[dict[str, object]] = []
    if recompute_merge_jobs:
        import json as _json

        jobs_path = feature_dir / "change-merge-jobs.json"
        if jobs_path.exists():
            try:
                jobs_data = _json.loads(jobs_path.read_text(encoding="utf-8"))
                merge_jobs_data = jobs_data.get("jobs", [])
            except (ValueError, KeyError):
                consistency.issues.append("Failed to parse change-merge-jobs.json")

    result: dict[str, object] = {
        "stashKey": feature_slug,
        "consistency": consistency.to_dict(),
        "mergeCoordinationJobs": merge_jobs_data,
    }

    _output_result(result, json_output)


__all__ = ["app"]
