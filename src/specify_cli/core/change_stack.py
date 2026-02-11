"""Change stack management - stash routing, request validation, and policy enforcement.

Implements branch-aware stash routing (FR-003), ambiguity fail-fast validation
(FR-002A), closed/done link-only policy (FR-016), dependency policy enforcement
(FR-005, FR-005A, FR-006), and stack-first selection with blocker output (FR-017)
for the /spec-kitty.change command.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from specify_cli.core.change_classifier import (
    ComplexityScore,
    PackagingMode,
    classify_change_request,
)
from specify_cli.core.dependency_graph import (
    build_dependency_graph,
    detect_cycles,
    validate_dependencies,
)
from specify_cli.core.feature_detection import _get_main_repo_root
from specify_cli.core.git_ops import get_current_branch

# ============================================================================
# Types
# ============================================================================


class StashScope(str, Enum):
    """Scope type for branch stash routing."""

    MAIN = "main"
    FEATURE = "feature"


class ValidationState(str, Enum):
    """Validation state for change requests."""

    VALID = "valid"
    AMBIGUOUS = "ambiguous"
    BLOCKED = "blocked"


# Embedded main stash path (not a pseudo-feature directory).
# Per plan.md: "On main or master: route to embedded main stash path
# kitty-specs/change-stack/main/"
MAIN_STASH_RELATIVE = Path("kitty-specs") / "change-stack" / "main"

# Primary branch names that route to the main stash.
PRIMARY_BRANCHES = frozenset({"main", "master"})

# Patterns indicating ambiguous change requests (FR-002A).
# These are requests that reference targets without specifying them.
_AMBIGUOUS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bthis\s+block\b", re.IGNORECASE),
    re.compile(r"\bthat\s+block\b", re.IGNORECASE),
    re.compile(r"\bthis\s+section\b", re.IGNORECASE),
    re.compile(r"\bthat\s+section\b", re.IGNORECASE),
    re.compile(r"\bthis\s+part\b", re.IGNORECASE),
    re.compile(r"\bthat\s+part\b", re.IGNORECASE),
    re.compile(r"\bhere\b", re.IGNORECASE),
    re.compile(r"\bthere\b", re.IGNORECASE),
]

# Patterns that disambiguate - if present alongside an ambiguous pattern,
# the request is considered clear enough to proceed.
_DISAMBIGUATING_PATTERNS: list[re.Pattern[str]] = [
    # Explicit file/path references
    re.compile(r"[a-zA-Z_/]+\.(py|ts|js|md|yaml|yml|json|toml|rs|go|java|rb)\b"),
    # Explicit function/class references
    re.compile(r"\b(function|class|method|module|file|directory)\s+\w+", re.IGNORECASE),
    # Explicit WP references
    re.compile(r"\bWP\d{2}\b"),
    # Quoted identifiers
    re.compile(r'["`\'][\w.]+["`\']'),
]

# Closed/done lanes that must not be reopened (FR-016).
CLOSED_LANES = frozenset({"done"})


# ============================================================================
# Data Classes
# ============================================================================


@dataclass(frozen=True)
class BranchStash:
    """Scope-aware destination for generated change work.

    Attributes:
        stash_key: 'main' or feature slug (e.g., '029-mid-stream-change-command')
        scope: Whether this targets main or a feature branch
        stash_path: Absolute path to the stash directory
        tasks_doc_path: Absolute path to tasks.md (if applicable)
    """

    stash_key: str
    scope: StashScope
    stash_path: Path
    tasks_doc_path: Optional[Path] = None


@dataclass
class AmbiguityResult:
    """Result of ambiguity analysis for a change request.

    Attributes:
        is_ambiguous: True if the request lacks sufficient target specificity
        matched_patterns: List of ambiguous pattern descriptions that triggered
        clarification_prompt: Suggested prompt to resolve ambiguity
    """

    is_ambiguous: bool
    matched_patterns: list[str] = field(default_factory=list)
    clarification_prompt: Optional[str] = None


@dataclass
class ClosedReferenceCheck:
    """Result of checking references to closed/done work packages.

    Attributes:
        has_closed_references: True if request references closed/done WPs
        closed_wp_ids: List of referenced closed/done WP IDs
        linkable: True if the references can be used as link-only context
    """

    has_closed_references: bool
    closed_wp_ids: list[str] = field(default_factory=list)
    linkable: bool = True


@dataclass
class ChangeRequest:
    """Parsed and validated change request.

    Attributes:
        request_id: Unique identifier for this request
        raw_text: Original request text
        submitted_branch: Branch the request was submitted from
        stash: Resolved branch stash
        validation_state: Current validation state
        ambiguity: Ambiguity analysis result
        closed_references: Closed WP reference check result
        complexity_score: Deterministic complexity scoring result (FR-009)
    """

    request_id: str
    raw_text: str
    submitted_branch: str
    stash: BranchStash
    validation_state: ValidationState
    ambiguity: AmbiguityResult
    closed_references: ClosedReferenceCheck
    complexity_score: Optional[ComplexityScore] = None


@dataclass(frozen=True)
class DependencyEdge:
    """A candidate dependency edge between work packages.

    Attributes:
        source: The WP that has the dependency (e.g., a change WP)
        target: The WP being depended on
        edge_type: Description of edge kind ('change_to_normal', 'change_to_change')
    """

    source: str
    target: str
    edge_type: str


@dataclass
class DependencyPolicyResult:
    """Result of dependency policy validation.

    Attributes:
        valid_edges: Edges that passed policy checks
        rejected_edges: Edges rejected with reasons
        errors: Critical errors that block the operation
    """

    valid_edges: list[DependencyEdge] = field(default_factory=list)
    rejected_edges: list[tuple[DependencyEdge, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


@dataclass
class StackSelectionResult:
    """Result of stack-first WP selection (FR-017).

    Attributes:
        selected_source: 'change_stack', 'normal_backlog', or 'blocked'
        next_wp_id: The WP ID to implement next, or None if blocked
        normal_progression_blocked: True if change stack blocks normal WPs
        blockers: List of blocking dependency descriptions
        pending_change_wps: Change WPs that exist but aren't ready
    """

    selected_source: str
    next_wp_id: Optional[str] = None
    normal_progression_blocked: bool = False
    blockers: list[str] = field(default_factory=list)
    pending_change_wps: list[str] = field(default_factory=list)


# ============================================================================
# Stash Resolution (T007)
# ============================================================================


def resolve_stash(repo_root: Path, branch: Optional[str] = None) -> BranchStash:
    """Resolve the branch stash from the active branch context.

    Routes to the correct stash based on the current branch:
    - main/master -> kitty-specs/change-stack/main/
    - feature branch (###-name) -> kitty-specs/<feature>/tasks/
    - worktree branch (###-name-WP##) -> kitty-specs/<feature>/tasks/

    Args:
        repo_root: Repository root path (may be worktree)
        branch: Override branch name (auto-detected if None)

    Returns:
        BranchStash with resolved scope and paths

    Raises:
        ChangeStackError: If branch context cannot be resolved
    """
    main_repo = _get_main_repo_root(repo_root)

    if branch is None:
        branch = get_current_branch(repo_root)
        if branch is None:
            raise ChangeStackError(
                "Could not determine current branch. "
                "Ensure you are in a git repository with a checked-out branch."
            )

    # Check for primary branches (main/master)
    if branch in PRIMARY_BRANCHES:
        stash_path = main_repo / MAIN_STASH_RELATIVE
        tasks_doc = stash_path / "tasks.md"
        return BranchStash(
            stash_key="main",
            scope=StashScope.MAIN,
            stash_path=stash_path,
            tasks_doc_path=tasks_doc if tasks_doc.exists() else None,
        )

    # Check for feature branch pattern (###-feature-name or ###-feature-name-WP##)
    # Strip -WP## suffix if present (worktree branch)
    feature_slug = _extract_feature_slug(branch)
    if feature_slug is not None:
        feature_dir = main_repo / "kitty-specs" / feature_slug
        stash_path = feature_dir / "tasks"
        tasks_doc = feature_dir / "tasks.md"
        return BranchStash(
            stash_key=feature_slug,
            scope=StashScope.FEATURE,
            stash_path=stash_path,
            tasks_doc_path=tasks_doc if tasks_doc.exists() else None,
        )

    # Detached HEAD or unrecognized branch pattern
    raise ChangeStackError(
        f"Cannot resolve stash for branch '{branch}'. "
        f"Expected 'main', 'master', or a feature branch (###-feature-name). "
        f"If you are in detached HEAD state, checkout a branch first."
    )


def _extract_feature_slug(branch: str) -> Optional[str]:
    """Extract feature slug from a branch name.

    Handles both direct feature branches and worktree WP branches:
    - '029-mid-stream-change' -> '029-mid-stream-change'
    - '029-mid-stream-change-WP01' -> '029-mid-stream-change'

    Args:
        branch: Git branch name

    Returns:
        Feature slug or None if branch doesn't match feature pattern
    """
    # Try worktree WP branch first (more specific pattern)
    wp_match = re.match(r"^((\d{3})-.+)-WP\d{2}$", branch)
    if wp_match:
        return wp_match.group(1)

    # Try direct feature branch
    feature_match = re.match(r"^(\d{3}-.+)$", branch)
    if feature_match:
        return feature_match.group(1)

    return None


# ============================================================================
# Ambiguity Detection (T010)
# ============================================================================


def check_ambiguity(request_text: str) -> AmbiguityResult:
    """Check if a change request is ambiguous about its target.

    A request is ambiguous if it contains vague references ("this block",
    "that section") without any disambiguating context (file names, function
    names, WP IDs, or quoted identifiers).

    Per FR-002A: The system MUST fail fast and request clarification before
    creating any change work package when the target scope is ambiguous.

    Args:
        request_text: The natural-language change request

    Returns:
        AmbiguityResult indicating whether clarification is needed
    """
    if not request_text or not request_text.strip():
        return AmbiguityResult(
            is_ambiguous=True,
            matched_patterns=["empty request"],
            clarification_prompt="Please provide a change request description.",
        )

    # Check for disambiguating patterns first - if present, request is clear
    for pattern in _DISAMBIGUATING_PATTERNS:
        if pattern.search(request_text):
            return AmbiguityResult(is_ambiguous=False)

    # Check for ambiguous patterns
    matched: list[str] = []
    for pattern in _AMBIGUOUS_PATTERNS:
        match = pattern.search(request_text)
        if match:
            matched.append(match.group())

    if matched:
        prompt_parts = [
            "Your change request contains vague references that could apply "
            "to multiple locations:",
            "",
        ]
        for m in matched:
            prompt_parts.append(f"  - '{m}'")
        prompt_parts.extend(
            [
                "",
                "Please clarify by specifying:",
                "  - File path(s) affected",
                "  - Function or class name(s)",
                "  - Work package ID(s) (e.g., WP01)",
            ]
        )

        return AmbiguityResult(
            is_ambiguous=True,
            matched_patterns=matched,
            clarification_prompt="\n".join(prompt_parts),
        )

    return AmbiguityResult(is_ambiguous=False)


# ============================================================================
# Closed/Done Policy Enforcement (T011)
# ============================================================================


def check_closed_references(
    request_text: str,
    repo_root: Path,
    feature_slug: str,
) -> ClosedReferenceCheck:
    """Check if a change request references closed/done work packages.

    Per FR-016: When a request references a closed/done WP, create a new
    change WP linked to it as historical context. Never reopen.

    Args:
        request_text: The change request text
        repo_root: Repository root path
        feature_slug: Feature slug for WP lookup

    Returns:
        ClosedReferenceCheck with identified closed WP references
    """
    # Find WP references in request text
    wp_pattern = re.compile(r"\bWP(\d{2})\b")
    wp_matches = wp_pattern.findall(request_text)

    if not wp_matches:
        return ClosedReferenceCheck(has_closed_references=False)

    main_repo = _get_main_repo_root(repo_root)
    tasks_dir = main_repo / "kitty-specs" / feature_slug / "tasks"

    closed_ids: list[str] = []

    for wp_num in wp_matches:
        wp_id = f"WP{wp_num}"
        lane = _get_wp_lane(tasks_dir, wp_id)
        if lane in CLOSED_LANES:
            closed_ids.append(wp_id)

    return ClosedReferenceCheck(
        has_closed_references=bool(closed_ids),
        closed_wp_ids=closed_ids,
        linkable=True,  # Always linkable, never reopenable
    )


def _get_wp_lane(tasks_dir: Path, wp_id: str) -> Optional[str]:
    """Get the lane status of a work package from its frontmatter.

    Args:
        tasks_dir: Path to the tasks directory
        wp_id: Work package ID (e.g., "WP01")

    Returns:
        Lane string or None if WP not found
    """
    if not tasks_dir.exists():
        return None

    wp_files = list(tasks_dir.glob(f"{wp_id}-*.md"))
    if not wp_files:
        return None

    # Read frontmatter to get lane
    content = wp_files[0].read_text(encoding="utf-8")
    lane_match = re.search(r'^lane:\s*["\']?(\w+)["\']?\s*$', content, re.MULTILINE)
    if lane_match:
        return lane_match.group(1)

    return None


def validate_no_closed_mutation(
    wp_ids: list[str],
    tasks_dir: Path,
) -> list[str]:
    """Validate that no closed/done WPs would be mutated.

    Per FR-016: The system MUST NOT reopen closed/done WPs.

    Args:
        wp_ids: WP IDs to check
        tasks_dir: Path to the tasks directory

    Returns:
        List of WP IDs that are closed/done and must not be mutated.
        Empty list means all WPs are safe to modify.
    """
    blocked: list[str] = []
    for wp_id in wp_ids:
        lane = _get_wp_lane(tasks_dir, wp_id)
        if lane in CLOSED_LANES:
            blocked.append(wp_id)
    return blocked


# ============================================================================
# Dependency Policy Enforcement (T024, T025, T026, T027, T028)
# ============================================================================


def extract_dependency_candidates(
    affected_wp_ids: list[str],
    change_wp_id: str,
    tasks_dir: Path,
) -> list[DependencyEdge]:
    """Build candidate dependency edges from change request impact and open WPs (T024).

    Parses affected open WPs and builds a deterministic candidate edge list
    for the generated change WP. Edges point from the change WP to affected
    open WPs that impose ordering constraints.

    Args:
        affected_wp_ids: WP IDs identified as impacted by the change request
        change_wp_id: The new change WP being created
        tasks_dir: Path to the tasks directory for lane lookups

    Returns:
        List of candidate DependencyEdge objects in deterministic order
    """
    candidates: list[DependencyEdge] = []

    for wp_id in sorted(affected_wp_ids):
        if wp_id == change_wp_id:
            continue

        lane = _get_wp_lane(tasks_dir, wp_id)
        if lane is None:
            continue

        if lane in CLOSED_LANES:
            # Closed WPs become closed_reference_links, not dependencies
            continue

        # Determine if target is a change WP
        is_change_wp = _is_change_wp(tasks_dir, wp_id)
        edge_type = "change_to_change" if is_change_wp else "change_to_normal"

        candidates.append(
            DependencyEdge(
                source=change_wp_id,
                target=wp_id,
                edge_type=edge_type,
            )
        )

    return candidates


def _is_change_wp(tasks_dir: Path, wp_id: str) -> bool:
    """Check if a WP is a change-stack WP by reading its frontmatter."""
    if not tasks_dir.exists():
        return False

    wp_files = list(tasks_dir.glob(f"{wp_id}-*.md"))
    if not wp_files:
        return False

    content = wp_files[0].read_text(encoding="utf-8")
    match = re.search(r"^change_stack:\s*(true|True)\s*$", content, re.MULTILINE)
    return match is not None


def validate_dependency_policy(
    candidates: list[DependencyEdge],
    tasks_dir: Path,
) -> DependencyPolicyResult:
    """Enforce dependency policy rules on candidate edges (T025).

    Policy rules (FR-005, FR-005A):
    - ALLOW: change WP -> normal open WP (ordering constraint)
    - ALLOW: change WP -> change WP (change-to-change ordering)
    - REJECT: any edge targeting a closed/done WP as a dependency

    Args:
        candidates: Candidate dependency edges to validate
        tasks_dir: Path to tasks directory for lane lookups

    Returns:
        DependencyPolicyResult with valid/rejected edges and diagnostics
    """
    result = DependencyPolicyResult()

    for edge in candidates:
        target_lane = _get_wp_lane(tasks_dir, edge.target)

        if target_lane is None:
            result.rejected_edges.append(
                (edge, f"Target {edge.target} not found in tasks directory")
            )
            continue

        if target_lane in CLOSED_LANES:
            result.rejected_edges.append(
                (
                    edge,
                    f"Target {edge.target} is closed/done (lane: {target_lane}). "
                    f"Use closed_reference_links instead of dependencies.",
                )
            )
            continue

        # Edge targets an open WP - allowed by policy
        result.valid_edges.append(edge)

    return result


def validate_dependency_graph_integrity(
    change_wp_id: str,
    dependency_ids: list[str],
    tasks_dir: Path,
) -> tuple[bool, list[str]]:
    """Validate full graph integrity after adding change WP dependencies (T026).

    Runs existing validators for missing refs, self-edges, and cycles.
    Aborts atomically on any validation failure.

    Args:
        change_wp_id: The new change WP ID
        dependency_ids: Proposed dependency WP IDs for the change WP
        tasks_dir: Path to tasks directory

    Returns:
        Tuple of (is_valid, error_messages). Empty errors means valid.
    """
    # Build the current graph from existing WPs
    graph = build_dependency_graph(tasks_dir)

    # Add the proposed change WP with its dependencies
    graph[change_wp_id] = dependency_ids

    # Validate the proposed dependencies using existing validators
    is_valid, errors = validate_dependencies(change_wp_id, dependency_ids, graph)

    # Also run full cycle detection on the complete graph
    cycles = detect_cycles(graph)
    if cycles:
        for cycle in cycles:
            cycle_str = " → ".join(cycle)
            error = f"Circular dependency detected: {cycle_str}"
            if error not in errors:
                errors.append(error)
        is_valid = False

    return is_valid, errors


def build_closed_reference_links(
    request_text: str,
    tasks_dir: Path,
    feature_slug: str,
    repo_root: Path,
) -> list[str]:
    """Build closed_reference_links metadata for a change WP (T027).

    Identifies closed/done WPs referenced in the request text and returns
    them as link-only references. These are stored in the change WP's
    frontmatter as historical context without reopening the closed WPs.

    Per FR-016: No lane transition is attempted on closed/done targets.

    Args:
        request_text: The change request text
        tasks_dir: Path to tasks directory
        feature_slug: Feature slug for context
        repo_root: Repository root path

    Returns:
        List of closed WP IDs to include in closed_reference_links metadata
    """
    closed_check = check_closed_references(request_text, repo_root, feature_slug)

    if not closed_check.has_closed_references:
        return []

    # Validate that no mutation would occur on these WPs
    blocked = validate_no_closed_mutation(closed_check.closed_wp_ids, tasks_dir)
    if blocked:
        # These are expected to be closed - they become link-only references
        # No lane transition, no reopening, just historical context
        pass

    return sorted(closed_check.closed_wp_ids)


def resolve_next_change_wp(
    tasks_dir: Path,
    feature_slug: str,
) -> StackSelectionResult:
    """Resolve next doable WP with change-stack priority (T028, FR-017).

    Implements stack-first selection:
    1. If ready change-stack WPs exist, select the highest-priority one
    2. If change-stack WPs exist but none are ready, block normal progression
       and report blocking dependencies
    3. If no change-stack WPs exist, allow normal backlog selection

    Args:
        tasks_dir: Path to tasks directory
        feature_slug: Feature slug for context

    Returns:
        StackSelectionResult with selection decision and blocker details
    """
    if not tasks_dir.exists():
        return StackSelectionResult(
            selected_source="normal_backlog",
        )

    # Collect all change-stack WPs and their states
    change_wps: list[tuple[str, str, int]] = []  # (wp_id, lane, stack_rank)
    normal_planned: list[str] = []  # Normal WPs in planned lane

    graph = build_dependency_graph(tasks_dir)

    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        content = wp_file.read_text(encoding="utf-8")

        # Extract WP ID
        wp_id_match = re.search(
            r'^work_package_id:\s*["\']?(WP\d{2})["\']?\s*$', content, re.MULTILINE
        )
        if not wp_id_match:
            continue
        wp_id = wp_id_match.group(1)

        # Check if it's a change-stack WP
        is_change = re.search(
            r"^change_stack:\s*(true|True)\s*$", content, re.MULTILINE
        )

        # Get lane
        lane_match = re.search(r'^lane:\s*["\']?(\w+)["\']?\s*$', content, re.MULTILINE)
        lane = lane_match.group(1) if lane_match else "planned"

        if is_change:
            # Get stack_rank (default 0)
            rank_match = re.search(r"^stack_rank:\s*(\d+)\s*$", content, re.MULTILINE)
            rank = int(rank_match.group(1)) if rank_match else 0
            change_wps.append((wp_id, lane, rank))
        elif lane == "planned":
            normal_planned.append(wp_id)

    # No change-stack WPs at all -> normal backlog selection
    if not change_wps:
        return StackSelectionResult(
            selected_source="normal_backlog",
            next_wp_id=normal_planned[0] if normal_planned else None,
        )

    # Find change WPs in "planned" lane (candidates for doing)
    planned_change_wps = [
        (wp_id, rank) for wp_id, lane, rank in change_wps if lane == "planned"
    ]

    # Check which planned change WPs have all dependencies satisfied
    ready_change_wps: list[tuple[str, int]] = []
    blocked_change_wps: list[tuple[str, list[str]]] = []

    for wp_id, rank in planned_change_wps:
        deps = graph.get(wp_id, [])
        unsatisfied: list[str] = []

        for dep in deps:
            dep_lane = _get_wp_lane(tasks_dir, dep)
            if dep_lane != "done":
                unsatisfied.append(dep)

        if unsatisfied:
            blocked_change_wps.append((wp_id, unsatisfied))
        else:
            ready_change_wps.append((wp_id, rank))

    # If any change WPs are still in progress (doing/for_review), report that
    active_change_wps = [
        wp_id for wp_id, lane, _ in change_wps if lane in ("doing", "for_review")
    ]

    # Ready change WPs available -> select highest priority (lowest rank)
    if ready_change_wps:
        ready_change_wps.sort(key=lambda x: x[1])
        selected_wp_id = ready_change_wps[0][0]
        return StackSelectionResult(
            selected_source="change_stack",
            next_wp_id=selected_wp_id,
        )

    # Pending change WPs exist but none ready -> block normal progression
    pending_ids = [wp_id for wp_id, _ in planned_change_wps] + active_change_wps

    if pending_ids:
        blockers: list[str] = []
        for wp_id, unsatisfied in blocked_change_wps:
            blockers.append(f"{wp_id} blocked by: {', '.join(sorted(unsatisfied))}")
        for wp_id in active_change_wps:
            active_lane = next(
                (lane for wid, lane, _ in change_wps if wid == wp_id), "doing"
            )
            blockers.append(f"{wp_id} is in {active_lane} lane")

        return StackSelectionResult(
            selected_source="blocked",
            normal_progression_blocked=True,
            blockers=blockers,
            pending_change_wps=sorted(pending_ids),
        )

    # All change WPs are done -> allow normal backlog
    return StackSelectionResult(
        selected_source="normal_backlog",
        next_wp_id=normal_planned[0] if normal_planned else None,
    )


# ============================================================================
# Request Validation (T009, T010)
# ============================================================================


def validate_change_request(
    request_text: str,
    repo_root: Path,
    branch: Optional[str] = None,
    feature: Optional[str] = None,
) -> ChangeRequest:
    """Validate and prepare a change request for processing.

    Performs all pre-write validation:
    1. Resolves branch stash (FR-003)
    2. Checks for ambiguity (FR-002A)
    3. Checks for closed WP references (FR-016)

    Args:
        request_text: Natural-language change request
        repo_root: Repository root path
        branch: Override branch name (auto-detected if None)
        feature: Override feature slug (auto-detected from stash if None)

    Returns:
        ChangeRequest with validation results

    Raises:
        ChangeStackError: If stash cannot be resolved
    """
    # Step 1: Resolve stash
    stash = resolve_stash(repo_root, branch=branch)

    # Step 2: Check ambiguity
    ambiguity = check_ambiguity(request_text)

    # Step 3: Check closed references
    feature_slug = feature or stash.stash_key
    closed_refs = check_closed_references(request_text, repo_root, feature_slug)

    # Step 4: Classify complexity (FR-009) - runs even for ambiguous requests
    # so preview can show the score breakdown
    complexity = classify_change_request(request_text)

    # Determine overall validation state
    if ambiguity.is_ambiguous:
        state = ValidationState.AMBIGUOUS
    else:
        state = ValidationState.VALID

    request_id = str(uuid.uuid4())[:8]

    return ChangeRequest(
        request_id=request_id,
        raw_text=request_text,
        submitted_branch=branch or get_current_branch(repo_root) or "unknown",
        stash=stash,
        validation_state=state,
        ambiguity=ambiguity,
        closed_references=closed_refs,
        complexity_score=complexity,
    )


# ============================================================================
# Change Plan and WP Synthesis (T018-T022)
# ============================================================================


@dataclass
class ChangePlan:
    """Planner decision layer for decomposition and guardrails.

    Attributes:
        request_id: Trace ID linking to the ChangeRequest
        mode: Packaging mode selected deterministically
        affected_open_wp_ids: Open WPs referenced in the request
        closed_reference_wp_ids: Closed WPs for link-only context
        guardrails: User-specified constraints to include in generated WPs
        requires_merge_coordination: Whether merge coordination jobs are needed
    """

    request_id: str
    mode: PackagingMode
    affected_open_wp_ids: list[str] = field(default_factory=list)
    closed_reference_wp_ids: list[str] = field(default_factory=list)
    guardrails: list[str] = field(default_factory=list)
    requires_merge_coordination: bool = False


@dataclass
class ChangeWorkPackage:
    """Generated change WP entry ready to write to the tasks directory.

    Attributes:
        work_package_id: e.g., "WP09"
        title: Derived from request text
        filename: Slugged filename, e.g., "WP09-use-sqlalchemy.md"
        lane: Always "planned" for generated WPs
        dependencies: WP IDs this WP depends on
        change_stack: Always True for change WPs
        change_request_id: Trace ID to originating request
        change_mode: Packaging mode label
        stack_rank: Ordering rank within the change set
        review_attention: Normal or elevated
        closed_reference_links: Link-only references to closed WPs
        body: Full markdown body including frontmatter
    """

    work_package_id: str
    title: str
    filename: str
    lane: str = "planned"
    dependencies: list[str] = field(default_factory=list)
    change_stack: bool = True
    change_request_id: str = ""
    change_mode: str = ""
    stack_rank: int = 1
    review_attention: str = "normal"
    closed_reference_links: list[str] = field(default_factory=list)
    body: str = ""

    def to_dict(self) -> dict[str, object]:
        """Serialize to JSON-friendly dictionary."""
        return {
            "workPackageId": self.work_package_id,
            "title": self.title,
            "filename": self.filename,
            "lane": self.lane,
            "dependencies": self.dependencies,
            "changeStack": self.change_stack,
            "changeRequestId": self.change_request_id,
            "changeMode": self.change_mode,
            "stackRank": self.stack_rank,
            "reviewAttention": self.review_attention,
            "closedReferenceLinks": self.closed_reference_links,
        }


def _next_wp_id(tasks_dir: Path) -> str:
    """Allocate the next available WP ID deterministically (T019).

    Scans existing WP files in the tasks directory (and virtual registry
    for in-flight batch generation) and returns the next sequential ID.
    IDs are zero-padded to two digits: WP01, WP02, ..., WP99.

    Args:
        tasks_dir: Path to the flat tasks directory

    Returns:
        Next WP ID string, e.g., "WP09"
    """
    existing_ids: set[int] = set()
    if tasks_dir.exists():
        for f in tasks_dir.glob("WP[0-9][0-9]-*.md"):
            try:
                num = int(f.name[2:4])
                existing_ids.add(num)
            except ValueError:
                continue

    # Also check virtual registry for in-flight allocations
    key = str(tasks_dir)
    if key in _virtual_wp_registry:
        for fname in _virtual_wp_registry[key]:
            try:
                num = int(fname[2:4])
                existing_ids.add(num)
            except (ValueError, IndexError):
                continue

    next_num = 1
    while next_num in existing_ids:
        next_num += 1

    return f"WP{next_num:02d}"


def _slugify(text: str, max_length: int = 40) -> str:
    """Create a URL-safe slug from text for filenames.

    Args:
        text: Raw text to slugify
        max_length: Maximum slug length

    Returns:
        Lowercased, hyphenated slug
    """
    slug = re.sub(r"[^a-zA-Z0-9\s-]", "", text.lower())
    slug = re.sub(r"[\s_]+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    if len(slug) > max_length:
        slug = slug[:max_length].rsplit("-", 1)[0]
    return slug or "change"


def _derive_title(request_text: str, max_length: int = 60) -> str:
    """Derive a concise WP title from the request text.

    Args:
        request_text: Original change request
        max_length: Maximum title length

    Returns:
        A clean title string
    """
    # Take first sentence or first N chars
    text = request_text.strip()
    # Cut at first period/newline if reasonable
    for sep in (".", "\n", ";"):
        idx = text.find(sep)
        if 10 < idx < max_length:
            text = text[:idx]
            break

    if len(text) > max_length:
        text = text[:max_length].rsplit(" ", 1)[0] + "..."

    return text.strip()


def _render_wp_body(
    wp: ChangeWorkPackage,
    request_text: str,
    guardrails: list[str],
    closed_refs: list[str],
    implementation_hint: str,
) -> str:
    """Render full WP markdown including frontmatter and body (T020-T022).

    Args:
        wp: The change work package being rendered
        request_text: Original request text
        guardrails: Acceptance constraints
        closed_refs: Closed WP references for link-only context
        implementation_hint: The spec-kitty implement command hint

    Returns:
        Complete markdown file content
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Build frontmatter
    deps_yaml = (
        "\n".join(f'  - "{d}"' for d in wp.dependencies) if wp.dependencies else ""
    )
    closed_refs_yaml = (
        "\n".join(f'  - "{c}"' for c in wp.closed_reference_links)
        if wp.closed_reference_links
        else ""
    )

    frontmatter_lines = [
        "---",
        f'work_package_id: "{wp.work_package_id}"',
        f'title: "{wp.title}"',
        f'lane: "{wp.lane}"',
    ]

    if deps_yaml:
        frontmatter_lines.append("dependencies:")
        frontmatter_lines.append(deps_yaml)
    else:
        frontmatter_lines.append("dependencies: []")

    frontmatter_lines.extend(
        [
            "change_stack: true",
            f'change_request_id: "{wp.change_request_id}"',
            f'change_mode: "{wp.change_mode}"',
            f"stack_rank: {wp.stack_rank}",
            f'review_attention: "{wp.review_attention}"',
        ]
    )

    if closed_refs_yaml:
        frontmatter_lines.append("closed_reference_links:")
        frontmatter_lines.append(closed_refs_yaml)

    frontmatter_lines.extend(
        [
            'assignee: ""',
            'agent: ""',
            'review_status: ""',
            'reviewed_by: ""',
            "history:",
            f'  - timestamp: "{now}"',
            '    lane: "planned"',
            '    agent: "change-command"',
            '    action: "Generated by /spec-kitty.change"',
            "---",
        ]
    )

    # Build body
    body_parts = [
        f"# {wp.work_package_id}: {wp.title}",
        "",
        "**Implementation command:**",
        "```bash",
        implementation_hint,
        "```",
        "",
        "## Change Request",
        "",
        f"> {request_text}",
        "",
    ]

    # Guardrails (T021)
    if guardrails:
        body_parts.extend(
            [
                "## Acceptance Constraints",
                "",
            ]
        )
        for i, g in enumerate(guardrails, 1):
            body_parts.append(f"{i}. {g}")
        body_parts.append("")

    # Closed references
    if closed_refs:
        body_parts.extend(
            [
                "## Historical Context (Closed References)",
                "",
                "The following closed work packages are referenced for context only (not reopened):",
                "",
            ]
        )
        for ref in closed_refs:
            body_parts.append(f"- {ref}")
        body_parts.append("")

    # Implementation guidance
    body_parts.extend(
        [
            "## Implementation Guidance",
            "",
            "Implement the change described above. Follow the existing codebase patterns.",
            "",
        ]
    )

    # Final testing task (T021 - always present)
    body_parts.extend(
        [
            "## Final Testing Task",
            "",
            "**REQUIRED**: Before marking this WP as done:",
            "",
            "1. Run existing tests to verify no regressions: `pytest tests/`",
            "2. Add tests covering the changes made in this WP",
            "3. Verify all tests pass before moving to `for_review`",
            "",
        ]
    )

    # Activity log
    body_parts.extend(
        [
            "## Activity Log",
            "",
            f"- {now} - change-command - lane=planned - Generated by /spec-kitty.change",
            "",
        ]
    )

    frontmatter = "\n".join(frontmatter_lines)
    body = "\n".join(body_parts)

    return f"{frontmatter}\n\n{body}"


def _build_implementation_hint(wp_id: str, dependencies: list[str]) -> str:
    """Build the spec-kitty implement command hint (T022).

    Args:
        wp_id: Work package ID
        dependencies: List of dependency WP IDs

    Returns:
        The implementation command string
    """
    if dependencies:
        # Use the last dependency as --base (most recent in chain)
        base = dependencies[-1]
        return f"spec-kitty implement {wp_id} --base {base}"
    return f"spec-kitty implement {wp_id}"


def _extract_guardrails(request_text: str) -> list[str]:
    """Extract guardrails/constraints from request text.

    Looks for explicit constraint language in the request. Returns
    a default guardrail if none are found.

    Args:
        request_text: The change request text

    Returns:
        List of guardrail strings
    """
    guardrails: list[str] = []

    # Check for "must" / "must not" / "do not" / "never" / "always" patterns
    constraint_patterns = [
        re.compile(r"(?:must|should)\s+(?:not\s+)?(.{10,80}?)(?:\.|$)", re.IGNORECASE),
        re.compile(r"(?:do not|don\'t|never)\s+(.{10,60}?)(?:\.|$)", re.IGNORECASE),
        re.compile(r"(?:always)\s+(.{10,60}?)(?:\.|$)", re.IGNORECASE),
        re.compile(r"(?:without)\s+(.{10,60}?)(?:\.|$)", re.IGNORECASE),
    ]

    for pattern in constraint_patterns:
        for match in pattern.finditer(request_text):
            guardrails.append(match.group(0).strip().rstrip("."))

    if not guardrails:
        guardrails.append("Ensure existing tests continue to pass")

    return guardrails


def synthesize_change_plan(
    change_req: ChangeRequest,
) -> ChangePlan:
    """Create a change plan from a validated change request (T018).

    Deterministically selects the packaging mode and extracts
    guardrails from the request text.

    Args:
        change_req: Validated change request

    Returns:
        ChangePlan with mode selection and guardrails
    """
    score = change_req.complexity_score
    mode = score.proposed_mode if score is not None else PackagingMode.SINGLE_WP

    # Extract closed references
    closed_refs = (
        change_req.closed_references.closed_wp_ids
        if change_req.closed_references.has_closed_references
        else []
    )

    # Extract guardrails from request text
    guardrails = _extract_guardrails(change_req.raw_text)

    # Determine if merge coordination is needed (integration risk > 0)
    requires_merge = score is not None and score.integration_risk_score > 0

    return ChangePlan(
        request_id=change_req.request_id,
        mode=mode,
        affected_open_wp_ids=[],  # Populated by apply command in WP05
        closed_reference_wp_ids=closed_refs,
        guardrails=guardrails,
        requires_merge_coordination=requires_merge,
    )


def generate_change_work_packages(
    change_req: ChangeRequest,
    plan: ChangePlan,
    tasks_dir: Path,
) -> list[ChangeWorkPackage]:
    """Generate change work packages from a plan (T019-T022).

    Creates one or more WP files based on the packaging mode:
    - single_wp: One WP with all tasks
    - orchestration: One coordinating WP
    - targeted_multi: Multiple focused WPs (2-3 based on scope)

    Args:
        change_req: The validated change request
        plan: The change plan with mode and guardrails
        tasks_dir: Path to the tasks directory for ID allocation

    Returns:
        List of ChangeWorkPackage ready to be written
    """
    score = change_req.complexity_score
    review_att = score.review_attention.value if score is not None else "normal"
    mode_label = _mode_to_frontmatter_label(plan.mode)

    if plan.mode == PackagingMode.TARGETED_MULTI:
        return _generate_targeted_multi(
            change_req,
            plan,
            tasks_dir,
            review_att,
            mode_label,
        )

    # single_wp and orchestration both produce one WP
    # (orchestration gets a different title prefix)
    wp_id = _next_wp_id(tasks_dir)
    title = _derive_title(change_req.raw_text)
    if plan.mode == PackagingMode.ORCHESTRATION:
        title = f"Orchestrate: {title}"

    slug = _slugify(title)
    filename = f"{wp_id}-{slug}.md"

    hint = _build_implementation_hint(wp_id, [])
    wp = ChangeWorkPackage(
        work_package_id=wp_id,
        title=title,
        filename=filename,
        lane="planned",
        dependencies=[],
        change_stack=True,
        change_request_id=change_req.request_id,
        change_mode=mode_label,
        stack_rank=1,
        review_attention=review_att,
        closed_reference_links=plan.closed_reference_wp_ids,
    )
    wp.body = _render_wp_body(
        wp,
        change_req.raw_text,
        plan.guardrails,
        plan.closed_reference_wp_ids,
        hint,
    )
    return [wp]


def _generate_targeted_multi(
    change_req: ChangeRequest,
    plan: ChangePlan,
    tasks_dir: Path,
    review_att: str,
    mode_label: str,
) -> list[ChangeWorkPackage]:
    """Generate multiple targeted WPs for parallelizable changes.

    Splits the request into 2-3 WPs based on scope breadth score.

    Args:
        change_req: The validated request
        plan: The change plan
        tasks_dir: Path to tasks directory
        review_att: Review attention level
        mode_label: Frontmatter mode label

    Returns:
        List of 2-3 ChangeWorkPackage entries
    """
    score = change_req.complexity_score
    # Determine WP count: 2 for moderate scope, 3 for wide scope
    wp_count = 3 if (score and score.scope_breadth_score >= 3) else 2

    wps: list[ChangeWorkPackage] = []
    base_title = _derive_title(change_req.raw_text, max_length=45)

    for i in range(wp_count):
        wp_id = _next_wp_id(tasks_dir)
        rank = i + 1
        suffix = f"(part {rank}/{wp_count})"
        title = f"{base_title} {suffix}"
        slug = _slugify(title)
        filename = f"{wp_id}-{slug}.md"

        # First WP has no deps, subsequent depend on predecessor
        deps = [wps[i - 1].work_package_id] if i > 0 else []
        hint = _build_implementation_hint(wp_id, deps)

        wp = ChangeWorkPackage(
            work_package_id=wp_id,
            title=title,
            filename=filename,
            lane="planned",
            dependencies=deps,
            change_stack=True,
            change_request_id=change_req.request_id,
            change_mode=mode_label,
            stack_rank=rank,
            review_attention=review_att,
            closed_reference_links=plan.closed_reference_wp_ids if i == 0 else [],
        )
        wp.body = _render_wp_body(
            wp,
            change_req.raw_text,
            plan.guardrails,
            plan.closed_reference_wp_ids if i == 0 else [],
            hint,
        )

        # "Create" the file virtually so next _next_wp_id sees it
        # We do this by writing a placeholder (the caller writes the real files)
        # For ID allocation, we track in-memory
        _register_virtual_wp(tasks_dir, wp_id, filename)
        wps.append(wp)

    return wps


# Track virtually allocated WP IDs during multi-WP generation
_virtual_wp_registry: dict[str, set[str]] = {}


def _register_virtual_wp(tasks_dir: Path, wp_id: str, filename: str) -> None:
    """Register a virtual WP file for ID collision avoidance during batch generation."""
    key = str(tasks_dir)
    if key not in _virtual_wp_registry:
        _virtual_wp_registry[key] = set()
    _virtual_wp_registry[key].add(filename)


def _clear_virtual_registry() -> None:
    """Clear the virtual WP registry (call after write is complete)."""
    _virtual_wp_registry.clear()


def _mode_to_frontmatter_label(mode: PackagingMode) -> str:
    """Convert PackagingMode enum to frontmatter label."""
    return {
        PackagingMode.SINGLE_WP: "single",
        PackagingMode.ORCHESTRATION: "orchestration",
        PackagingMode.TARGETED_MULTI: "targeted",
    }[mode]


def write_change_work_packages(
    wps: list[ChangeWorkPackage],
    tasks_dir: Path,
) -> list[Path]:
    """Write generated change work packages to disk.

    Creates the tasks directory if it doesn't exist, then writes
    each WP file.

    Args:
        wps: List of ChangeWorkPackage with rendered bodies
        tasks_dir: Target directory

    Returns:
        List of paths to written files
    """
    tasks_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for wp in wps:
        path = tasks_dir / wp.filename
        path.write_text(wp.body, encoding="utf-8")
        written.append(path)
    _clear_virtual_registry()
    return written


# ============================================================================
# Reconciliation and Consistency (T030, T031)
# ============================================================================


@dataclass
class ConsistencyReport:
    """Machine-readable reconciliation status (FR-007, SC-001).

    Attributes:
        updated_tasks_doc: Whether tasks.md was updated
        dependency_validation_passed: Whether all dependencies are valid
        broken_links_fixed: Number of broken links repaired
        issues: List of issue descriptions found during reconciliation
        wp_sections_added: Number of new WP sections added to tasks.md
        wp_sections_updated: Number of existing WP sections updated
    """

    updated_tasks_doc: bool = False
    dependency_validation_passed: bool = True
    broken_links_fixed: int = 0
    issues: list[str] = field(default_factory=list)
    wp_sections_added: int = 0
    wp_sections_updated: int = 0

    def to_dict(self) -> dict[str, object]:
        """Serialize to JSON-friendly dictionary."""
        return {
            "updatedTasksDoc": self.updated_tasks_doc,
            "dependencyValidationPassed": self.dependency_validation_passed,
            "brokenLinksFixed": self.broken_links_fixed,
            "issues": self.issues,
            "wpSectionsAdded": self.wp_sections_added,
            "wpSectionsUpdated": self.wp_sections_updated,
        }


@dataclass
class MergeCoordinationJob:
    """A merge coordination job triggered by cross-stream risk (FR-013).

    Attributes:
        job_id: Unique identifier for this job
        reason: Why this job was triggered
        source_wp: The change WP that triggered coordination
        target_wps: WPs that need coordination
        risk_indicator: The risk factor that triggered this job
    """

    job_id: str
    reason: str
    source_wp: str
    target_wps: list[str] = field(default_factory=list)
    risk_indicator: str = ""

    def to_dict(self) -> dict[str, object]:
        """Serialize to JSON-friendly dictionary."""
        return {
            "jobId": self.job_id,
            "reason": self.reason,
            "sourceWP": self.source_wp,
            "targetWPs": self.target_wps,
            "riskIndicator": self.risk_indicator,
        }


def reconcile_tasks_doc(
    tasks_dir: Path,
    feature_dir: Path,
    change_wps: list[ChangeWorkPackage],
) -> ConsistencyReport:
    """Reconcile tasks.md with generated change WPs (T030, FR-007).

    Inserts or updates WP sections and prompt links in tasks.md.
    Preserves existing checklist state for unrelated subtasks.
    Ensures deterministic ordering by WP ID.

    Args:
        tasks_dir: Path to the tasks directory
        feature_dir: Path to the feature directory (parent of tasks/)
        change_wps: List of change WPs that were generated

    Returns:
        ConsistencyReport with reconciliation results
    """
    report = ConsistencyReport()

    if not change_wps:
        return report

    tasks_doc_path = feature_dir / "tasks.md"

    # Read existing content or start fresh
    existing_content = ""
    existing_sections: dict[str, str] = {}
    if tasks_doc_path.exists():
        existing_content = tasks_doc_path.read_text(encoding="utf-8")
        existing_sections = _parse_wp_sections(existing_content)

    # Build updated sections for change WPs
    new_sections: list[str] = []
    for wp in change_wps:
        wp_id = wp.work_package_id
        section = _build_tasks_doc_section(wp)

        if wp_id in existing_sections:
            # Update existing section
            existing_sections[wp_id] = section
            report.wp_sections_updated += 1
        else:
            # New section
            new_sections.append(section)
            report.wp_sections_added += 1

    if not new_sections and report.wp_sections_updated == 0:
        return report

    # Rebuild the document preserving non-WP content
    updated_content = _rebuild_tasks_doc(
        existing_content,
        existing_sections,
        new_sections,
        change_wps,
    )

    tasks_doc_path.parent.mkdir(parents=True, exist_ok=True)
    tasks_doc_path.write_text(updated_content, encoding="utf-8")
    report.updated_tasks_doc = True

    return report


def _parse_wp_sections(content: str) -> dict[str, str]:
    """Parse tasks.md into a dict of WP ID -> section content.

    Sections are identified by headers matching '## WP##' or '### WP##'.
    """
    sections: dict[str, str] = {}
    current_wp: Optional[str] = None
    current_lines: list[str] = []

    for line in content.split("\n"):
        wp_header = re.match(r"^#{2,3}\s+(WP\d{2})\b", line)
        if wp_header:
            # Save previous section
            if current_wp is not None:
                sections[current_wp] = "\n".join(current_lines)
            current_wp = wp_header.group(1)
            current_lines = [line]
        elif current_wp is not None:
            # Check if we hit another non-WP heading (section boundary)
            if re.match(r"^#{1,2}\s+(?!WP\d{2})", line):
                sections[current_wp] = "\n".join(current_lines)
                current_wp = None
                current_lines = []
            else:
                current_lines.append(line)

    # Save last section
    if current_wp is not None:
        sections[current_wp] = "\n".join(current_lines)

    return sections


def _build_tasks_doc_section(wp: ChangeWorkPackage) -> str:
    """Build a tasks.md section for a change WP."""
    lines = [
        f"### {wp.work_package_id}: {wp.title}",
        "",
        f"- **Lane**: {wp.lane}",
        "- **Change Stack**: Yes",
        f"- **Mode**: {wp.change_mode}",
    ]
    if wp.dependencies:
        deps_str = ", ".join(wp.dependencies)
        lines.append(f"- **Dependencies**: {deps_str}")
    if wp.closed_reference_links:
        refs_str = ", ".join(wp.closed_reference_links)
        lines.append(f"- **Closed References**: {refs_str} (link-only)")
    lines.extend(
        [
            "",
            f"**Prompt**: `tasks/{wp.filename}`",
            "",
        ]
    )
    return "\n".join(lines)


def _rebuild_tasks_doc(
    existing_content: str,
    existing_sections: dict[str, str],
    new_sections: list[str],
    change_wps: list[ChangeWorkPackage],
) -> str:
    """Rebuild tasks.md with updated and new sections.

    Preserves existing non-WP content and unrelated checklist state.
    Orders WP sections deterministically by WP ID.
    """

    # Sort new sections by WP ID for deterministic ordering
    def _wp_id_from_section(section: str) -> str:
        match = re.search(r"### (WP\d{2}):", section)
        return match.group(1) if match else "WP99"

    new_sections_sorted = sorted(new_sections, key=_wp_id_from_section)

    # If no existing content, build from scratch
    if not existing_content.strip():
        parts = ["# Tasks", "", "## Change Stack Work Packages", ""]
        for section in new_sections_sorted:
            parts.append(section)
        return "\n".join(parts)

    # Find the "Change Stack" section or append at end
    change_header_pattern = re.compile(
        r"^#{1,2}\s+Change\s+Stack", re.MULTILINE | re.IGNORECASE
    )
    match = change_header_pattern.search(existing_content)

    if match:
        # Insert new sections after the change stack header
        insert_pos = existing_content.find("\n", match.end())
        if insert_pos == -1:
            insert_pos = len(existing_content)
        else:
            insert_pos += 1

        # Collect all WP sections that should appear under change stack
        all_change_wp_ids = sorted(
            set(
                list(existing_sections.keys())
                + [wp.work_package_id for wp in change_wps]
            )
        )

        # Build the change stack section content
        change_parts: list[str] = []
        for wp_id in all_change_wp_ids:
            if wp_id in existing_sections:
                change_parts.append(existing_sections[wp_id])
            else:
                # Find in new_sections_sorted
                for ns in new_sections_sorted:
                    if f"### {wp_id}:" in ns:
                        change_parts.append(ns)
                        break

        # Replace change stack section content
        # Find the end of the change stack section (next top-level heading)
        rest_match = re.search(
            r"^#{1,2}\s+(?!Change\s+Stack|WP\d{2})",
            existing_content[insert_pos:],
            re.MULTILINE,
        )
        if rest_match:
            rest_start = insert_pos + rest_match.start()
            before = existing_content[:insert_pos]
            after = existing_content[rest_start:]
        else:
            before = existing_content[:insert_pos]
            after = ""

        change_content = "\n".join(change_parts)
        return f"{before}\n{change_content}\n{after}".rstrip() + "\n"
    else:
        # Append a change stack section
        parts = [
            existing_content.rstrip(),
            "",
            "## Change Stack Work Packages",
            "",
        ]
        for section in new_sections_sorted:
            parts.append(section)
        return "\n".join(parts) + "\n"


def validate_all_dependencies(
    tasks_dir: Path,
) -> tuple[bool, list[str]]:
    """Validate dependency integrity for all WPs in the tasks directory.

    Checks for missing references, self-edges, and cycles across
    the entire WP graph.

    Args:
        tasks_dir: Path to the tasks directory

    Returns:
        Tuple of (all_valid, list of error messages)
    """
    if not tasks_dir.exists():
        return True, []

    graph = build_dependency_graph(tasks_dir)
    all_errors: list[str] = []

    # Check each WP's dependencies
    for wp_id, deps in graph.items():
        is_valid, errors = validate_dependencies(wp_id, deps, graph)
        if not is_valid:
            all_errors.extend(errors)

    # Check for cycles
    cycles = detect_cycles(graph)
    if cycles:
        for cycle in cycles:
            cycle_str = " → ".join(cycle)
            error = f"Circular dependency detected: {cycle_str}"
            if error not in all_errors:
                all_errors.append(error)

    return len(all_errors) == 0, all_errors


def reconcile_change_stack(
    tasks_dir: Path,
    feature_dir: Path,
    change_wps: list[ChangeWorkPackage],
) -> ConsistencyReport:
    """Full reconciliation: tasks.md + dependency validation (T030, T031).

    Orchestrates the complete reconciliation workflow:
    1. Reconcile tasks.md with generated WPs
    2. Validate all dependency integrity
    3. Check for broken links and fix them

    Args:
        tasks_dir: Path to the tasks directory
        feature_dir: Path to the feature directory
        change_wps: List of generated change WPs

    Returns:
        ConsistencyReport with complete reconciliation status
    """
    # Step 1: Reconcile tasks.md
    report = reconcile_tasks_doc(tasks_dir, feature_dir, change_wps)

    # Step 2: Validate dependencies
    is_valid, dep_errors = validate_all_dependencies(tasks_dir)
    report.dependency_validation_passed = is_valid
    if dep_errors:
        report.issues.extend(dep_errors)

    # Step 3: Check for broken prompt links in tasks.md
    broken_count = _fix_broken_prompt_links(tasks_dir, feature_dir)
    report.broken_links_fixed = broken_count

    return report


def _fix_broken_prompt_links(tasks_dir: Path, feature_dir: Path) -> int:
    """Check and fix broken prompt links in tasks.md.

    Removes lines containing broken prompt links (references to WP files
    that no longer exist in the tasks directory).

    Returns the number of links fixed (removed).
    """
    tasks_doc = feature_dir / "tasks.md"
    if not tasks_doc.exists():
        return 0

    content = tasks_doc.read_text(encoding="utf-8")
    fixed_count = 0

    # Find all prompt links: `tasks/WP##-*.md`
    link_pattern = re.compile(r"`tasks/(WP\d{2}-[^`]+\.md)`")
    lines = content.split("\n")
    cleaned_lines: list[str] = []

    for line in lines:
        match = link_pattern.search(line)
        if match:
            filename = match.group(1)
            if not (tasks_dir / filename).exists():
                # Broken link - remove this line
                fixed_count += 1
                continue
        cleaned_lines.append(line)

    if fixed_count > 0:
        tasks_doc.write_text("\n".join(cleaned_lines), encoding="utf-8")

    return fixed_count


# ============================================================================
# Merge Coordination Heuristics (T032, T033)
# ============================================================================


def compute_merge_coordination_jobs(
    change_wps: list[ChangeWorkPackage],
    tasks_dir: Path,
    plan: ChangePlan,
) -> list[MergeCoordinationJob]:
    """Deterministically compute merge coordination jobs (T032, FR-013).

    Creates merge coordination jobs when deterministic risk heuristics trigger:
    1. Cross-dependency risk: change WP depends on an in-progress normal WP
    2. Parallel modification risk: multiple change WPs touch overlapping areas
    3. Integration risk: change plan has integration_risk flagged

    Jobs are only created when conditions are met - no speculative jobs.

    Args:
        change_wps: The generated change WPs
        tasks_dir: Path to tasks directory
        plan: The change plan with risk indicators

    Returns:
        List of MergeCoordinationJob records
    """
    jobs: list[MergeCoordinationJob] = []

    if not change_wps:
        return jobs

    # Heuristic 1: Integration risk from classifier
    if plan.requires_merge_coordination:
        source_wp = change_wps[0].work_package_id
        # Find in-progress WPs that might conflict
        active_wps = _find_active_wps(tasks_dir)

        if active_wps:
            job = MergeCoordinationJob(
                job_id=f"mcj-{source_wp}-integration",
                reason="Integration risk detected: change request involves CI/CD, "
                "deployment, or external API changes that may conflict with "
                "in-progress work",
                source_wp=source_wp,
                target_wps=active_wps,
                risk_indicator="integration_risk",
            )
            jobs.append(job)

    # Heuristic 2: Cross-dependency risk
    for wp in change_wps:
        for dep in wp.dependencies:
            dep_lane = _get_wp_lane(tasks_dir, dep)
            if dep_lane in ("doing", "for_review"):
                job = MergeCoordinationJob(
                    job_id=f"mcj-{wp.work_package_id}-cross-{dep}",
                    reason=f"Cross-dependency risk: {wp.work_package_id} depends on "
                    f"{dep} which is currently in {dep_lane} lane. Coordination "
                    f"needed to avoid merge conflicts.",
                    source_wp=wp.work_package_id,
                    target_wps=[dep],
                    risk_indicator="cross_dependency",
                )
                jobs.append(job)

    # Heuristic 3: Parallel modification risk (targeted_multi only)
    if len(change_wps) > 1:
        # Multiple change WPs from same request could conflict
        wp_ids = [wp.work_package_id for wp in change_wps]
        job = MergeCoordinationJob(
            job_id=f"mcj-parallel-{change_wps[0].change_request_id[:8]}",
            reason="Parallel modification risk: multiple change WPs generated "
            "from the same request. Ensure sequential implementation "
            "respects the dependency chain.",
            source_wp=change_wps[0].work_package_id,
            target_wps=wp_ids[1:],
            risk_indicator="parallel_modification",
        )
        jobs.append(job)

    return jobs


def _find_active_wps(tasks_dir: Path) -> list[str]:
    """Find WPs currently in doing or for_review lanes."""
    active: list[str] = []
    if not tasks_dir.exists():
        return active

    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        content = wp_file.read_text(encoding="utf-8")
        wp_id_match = re.search(
            r'^work_package_id:\s*["\']?(WP\d{2})["\']?\s*$',
            content,
            re.MULTILINE,
        )
        lane_match = re.search(
            r'^lane:\s*["\']?(\w+)["\']?\s*$',
            content,
            re.MULTILINE,
        )

        if wp_id_match and lane_match:
            wp_id = wp_id_match.group(1)
            lane = lane_match.group(1)
            if lane in ("doing", "for_review"):
                active.append(wp_id)

    return active


def persist_merge_coordination_jobs(
    jobs: list[MergeCoordinationJob],
    feature_dir: Path,
) -> Path | None:
    """Persist merge coordination jobs to planning artifacts (T033).

    Writes jobs to a JSON file in the feature directory for downstream
    discovery and command output.

    Args:
        jobs: List of merge coordination jobs to persist
        feature_dir: Path to the feature directory

    Returns:
        Path to the persisted file, or None if no jobs
    """
    if not jobs:
        return None

    import json as _json

    output_path = feature_dir / "change-merge-jobs.json"
    feature_dir.mkdir(parents=True, exist_ok=True)

    # If file exists, merge with existing jobs (idempotent by job_id)
    existing_jobs: dict[str, dict[str, object]] = {}
    if output_path.exists():
        try:
            existing_data = _json.loads(output_path.read_text(encoding="utf-8"))
            for j in existing_data.get("jobs", []):
                existing_jobs[j["jobId"]] = j
        except (ValueError, KeyError):
            pass

    # Add/update new jobs
    for job in jobs:
        existing_jobs[job.job_id] = job.to_dict()

    # Write sorted by job_id for determinism
    sorted_jobs = [existing_jobs[k] for k in sorted(existing_jobs)]
    output_data = {
        "version": 1,
        "featureDir": str(feature_dir),
        "jobCount": len(sorted_jobs),
        "jobs": sorted_jobs,
    }

    output_path.write_text(
        _json.dumps(output_data, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return output_path


# ============================================================================
# Errors
# ============================================================================


class ChangeStackError(Exception):
    """Error during change stack operations."""

    pass
