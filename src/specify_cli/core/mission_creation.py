"""Reusable mission-creation logic extracted from the CLI command.

This module provides ``create_mission_core()`` -- the programmatic API
for creating a new mission directory with all scaffolding. The CLI
command ``create()`` is a thin wrapper around this function.
"""

from __future__ import annotations

import contextlib
import logging
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ulid import ULID

from specify_cli.core.constants import KITTY_SPECS_DIR
from mission_runtime import (
    CommitTarget,
    MissionArtifactKind,
    MissionTopology,
    placement_seam,
    resolve_create_time_write_target,
)
from specify_cli.core.checkout_ownership import (
    OwnershipClaim,
    OwnershipValidationResult,
    error_for_claim,
    resolve_ownership_claim,
)
from specify_cli.core.commit_guard import GuardCapability
from specify_cli.core.git_ops import get_current_branch, is_git_repo
from specify_cli.core.mission_payload import (
    build_mission_created_payload,
    default_mission_display_name,
    default_mission_purpose_context,
)
from specify_cli.core.paths import is_worktree_context, locate_project_root
from kernel.clock import now_utc_iso
from specify_cli.git import safe_commit
from specify_cli.git.commit_helpers import (
    ProtectedBranchRefused,
    SafeCommitDestinationNotFound,
    SafeCommitHeadMismatch,
)
from specify_cli.git.ref_advance import RefRestoreError, restore_branch_ref
from specify_cli.lanes.branch_naming import mission_dir_name, resolve_mid8
from specify_cli.mission_metadata import load_meta_or_empty, validate_purpose_summary

logger = logging.getLogger(__name__)

# coord-primary-partition-lock WP02 (T009 / S1192): the ``meta`` field names
# repeated across the metadata-assembly block below (default + event-emission
# reads) hoisted to named constants rather than restated as literals.
_META_KEY_MISSION_TYPE = "mission_type"
_META_KEY_CREATED_AT = "created_at"

# WP12 (FR-011 / #3339): coordination branches are the only branch refs a
# mission-create mints, and their names are all ``kitty/mission-<slug>-<mid8>``.
# The glob lets the failure-atomic rollback diff pre- vs post-create refs so it
# deletes exactly the orphan branch an aborted create left behind.
_COORDINATION_BRANCH_GLOB = "kitty/mission-*"
_BOOTSTRAP_META_COMMIT_SKIPS = (
    ProtectedBranchRefused,
    SafeCommitDestinationNotFound,
    SafeCommitHeadMismatch,
)


class MissionCreationError(RuntimeError):
    """Raised when mission creation fails."""


@dataclass(slots=True)
class MissionCreationResult:
    """Structured result from ``create_mission_core()``."""

    feature_dir: Path
    mission_slug: str
    mission_number: int | None  # None for pre-merge missions (FR-044)
    meta: dict[str, Any]
    target_branch: str
    current_branch: str
    created_files: list[Path] = field(default_factory=list)
    origin_binding_attempted: bool = False
    origin_binding_succeeded: bool = False
    origin_binding_error: str | None = None
    # Coordination-branch outcome (WP03 / issue #1348).  ``coordination_branch``
    # is the canonical per-mission ref ``kitty/mission-<slug>-<mid8>`` parented
    # off ``target_branch``; ``coordination_branch_created`` distinguishes a
    # freshly-minted branch from an idempotent reuse on re-run.
    coordination_branch: str | None = None
    coordination_branch_created: bool = False
    owned_checkout: Path | None = None
    canonical_repo_root: Path | None = None


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KEBAB_CASE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9]*(-[a-z0-9]+)*$")
# Note: Intentionally permissive — bare-digit slugs like "069" are accepted.
# create_mission_core() always prefixes the mission number, so "069" becomes "070-069" in practice.

TASKS_README_TEMPLATE = """\
# Tasks Directory

This directory contains work package (WP) prompt files.

## Directory Structure (v0.9.0+)

```
tasks/
\u251c\u2500\u2500 WP01-setup-infrastructure.md
\u251c\u2500\u2500 WP02-user-authentication.md
\u251c\u2500\u2500 WP03-api-endpoints.md
\u2514\u2500\u2500 README.md
```

All WP files are stored flat in `tasks/`. Status is tracked in `status.events.jsonl`, not in WP frontmatter.

## Work Package File Format

Each WP file **MUST** use YAML frontmatter:

```yaml
---
work_package_id: "WP01"
title: "Work Package Title"
dependencies: []
planning_base_branch: "{planning_branch}"
merge_target_branch: "{planning_branch}"
branch_strategy: "Planning artifacts were generated on {planning_branch}; completed changes must merge back into {planning_branch}."
subtasks:
  - "T001"
  - "T002"
phase: "Phase 1 - Setup"
assignee: ""
agent: ""
shell_pid: ""
history:
  - timestamp: "2025-01-01T00:00:00Z"
    agent: "system"
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 \u2013 Work Package Title

[Content follows...]
```

## Status Tracking

Status is tracked via the canonical event log (`status.events.jsonl`), not in WP frontmatter.
Use `spec-kitty agent tasks move-task` to change WP status:

```bash
spec-kitty agent tasks move-task <WPID> --to <lane>
```

Example:
```bash
spec-kitty agent tasks move-task WP01 --to doing
```

## File Naming

- Format: `WP01-kebab-case-slug.md`
- Examples: `WP01-setup-infrastructure.md`, `WP02-user-auth.md`
"""


def render_tasks_readme_content(planning_branch: str) -> str:
    """Render tasks/README.md with branch-aware example frontmatter."""
    return TASKS_README_TEMPLATE.format(planning_branch=planning_branch)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _commit_feature_file(
    file_path: Path,
    mission_slug: str,
    artifact_type: str,
    repo_root: Path,
    *,
    worktree_root: Path | None = None,
    create_time_target: CommitTarget | None = None,
) -> None:
    """Commit a single planning artifact to its seam-resolved primary home.

    This is a slim, typer-free version of the ``_commit_to_branch`` helper
    in the CLI module. It delegates straight to ``safe_commit`` with no
    try/except of its own, so it raises on BOTH a hard git failure and an
    empty changeset (``safe_commit`` itself raises ``RuntimeError`` when
    there is nothing to commit -- it does NOT silently no-op). Callers that
    know their changeset is always non-empty (e.g. the FR-001 ``meta.json``
    commit call sites, where the file genuinely differs from HEAD at create
    time) can safely treat any raise here as a hard failure.

    coord-primary-partition-lock WP02 (T007 / C-001 / C-006): the commit
    destination is derived from ``placement_seam(...).write_target(SPEC)``,
    NOT from the operator's current checkout. Pre-fix this constructed
    ``CommitTarget(ref=current_branch)`` directly, which is the create-time
    split-brain root (research.md D5) -- under a coord-routing mission whose
    resolved ``target_branch`` differs from the checkout, the metadata commit
    silently landed on whatever branch the operator happened to be parked on
    instead of the mission's actual primary home. ``SPEC`` is a
    ``_PRIMARY_ARTIFACT_KINDS`` member (same as ``PRIMARY_METADATA``, the kind
    the committed ``meta.json`` file itself belongs to): both resolve to the
    identical primary ``target_branch`` for every topology, so this is a pure
    derivation-source fix (seam vs. checkout), not a placement change.
    """
    if get_current_branch(repo_root) is None:
        raise MissionCreationError("Not in a git repository")

    # Mission creation runs pre-spec: the destination is the branch ``create``
    # reports (the planning destination), which is a non-protected planning
    # branch. Capability is STANDARD — the placement-matched commit needs no
    # protected-branch bookkeeping authorization. If a project legitimately
    # plans on a protected branch, WP05's placement projection routes the
    # commit; this caller does not duplicate that decision (T010).
    commit_msg = f"Add {artifact_type} for feature {mission_slug}"
    effective_worktree = worktree_root or repo_root
    seam_target = create_time_target if create_time_target is not None else placement_seam(repo_root, mission_slug).write_target(MissionArtifactKind.SPEC)
    safe_commit(
        repo_root=repo_root,
        worktree_root=effective_worktree,
        target=seam_target,
        message=commit_msg,
        paths=(file_path,),
        capability=GuardCapability.STANDARD,
    )


# ---------------------------------------------------------------------------
# Failure-atomic git rollback (WP12 / FR-011 / #3339)
# ---------------------------------------------------------------------------


def _list_coordination_branches(repo_root: Path) -> frozenset[str]:
    """Return the local ``kitty/mission-*`` branch names in ``repo_root``.

    Used to diff the coordination branches present before vs after a
    mission-create so the rollback deletes exactly the ref an aborted create
    minted, never a pre-existing one. A non-git or failing ``git`` invocation
    yields an empty set (nothing to roll back).
    """
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "branch",
            "--list",
            _COORDINATION_BRANCH_GLOB,
            "--format=%(refname:short)",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return frozenset()
    return frozenset(line.strip() for line in result.stdout.splitlines() if line.strip())


def _restore_git_state_after_failed_create(
    repo_root: Path,
    *,
    original_branch: str | None,
    original_commit: str | None,
    original_index_tree: str | None,
    pre_existing_coordination_branches: frozenset[str],
) -> None:
    """Best-effort rollback of a failed mission-create's git side-effects.

    Restores the operator's original checkout and deletes any coordination
    branch this create-run minted (FR-011, #3339), so a failed create leaves
    the operator on their original branch with no orphan branch.

    Rollback is best-effort and never raises — it must not mask the original
    creation failure. The checkout is restored *before* any branch delete
    because git refuses to delete a branch that is currently checked out.

    Single-writer assumption: mission-create is an operator action, so the
    coordination-branch diff (present now minus present before) identifies
    exactly the ref this call minted.
    """
    # 1. Restore the operator's checkout first (a checked-out branch cannot be
    #    deleted).
    if original_branch is not None:
        current = get_current_branch(repo_root)
        if current is not None and current != original_branch:
            subprocess.run(
                ["git", "-C", str(repo_root), "checkout", original_branch],
                capture_output=True,
                text=True,
                check=False,
            )
        if original_commit is not None:
            current_tip_result = subprocess.run(
                ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=False,
            )
            current_tip = current_tip_result.stdout.strip() if current_tip_result.returncode == 0 else None
            if current_tip and current_tip != original_commit:
                # A late failure can occur after the metadata commit. Restore
                # only this branch ref with compare-and-swap; keep the partial
                # scaffold in the worktree for resume-probe diagnosis.
                with contextlib.suppress(RefRestoreError):
                    restore_branch_ref(
                        repo_root,
                        original_branch,
                        original_commit,
                        expected_current_sha=current_tip,
                    )
            if original_index_tree is not None:
                # Restore the exact pre-invocation index, including unrelated
                # staged user changes, without touching worktree files.
                subprocess.run(
                    ["git", "-C", str(repo_root), "read-tree", original_index_tree],
                    capture_output=True,
                    text=True,
                    check=False,
                )
    # 2. Delete only the coordination branches that appeared during this create.
    orphaned = _list_coordination_branches(repo_root) - pre_existing_coordination_branches
    for branch in sorted(orphaned):
        subprocess.run(
            ["git", "-C", str(repo_root), "branch", "-D", branch],
            capture_output=True,
            text=True,
            check=False,
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_mission_core(
    repo_root: Path | None,
    mission_slug: str,
    *,
    mission: str | None = None,
    target_branch: str | None = None,
    friendly_name: str | None = None,
    purpose_tldr: str | None = None,
    purpose_context: str | None = None,
    pr_bound: bool = False,
    topology: MissionTopology = MissionTopology.COORD,
    force_recreate_coordination_branch: bool = False,
    allow_worktree_context: bool = False,
    owned_checkout: Path | None = None,
) -> MissionCreationResult:
    """Create a new mission, restoring git state if creation fails (FR-011).

    Failure-atomic wrapper around :func:`_create_mission_core_impl`. It captures
    the operator's branch/checkout and the pre-existing coordination branches
    *before* any git mutation, and on ANY failure restores the original checkout
    and deletes the orphan coordination branch the aborted run minted (#3339).
    See :func:`_create_mission_core_impl` for the full parameter contract.
    """
    # An explicit owned checkout is the write/commit surface. Snapshot that
    # checkout rather than the canonical primary so a late failure restores
    # the branch ref and index that this invocation actually mutated.
    rollback_root = owned_checkout.resolve() if owned_checkout is not None else repo_root
    if rollback_root is None:
        rollback_root = locate_project_root()
    original_branch: str | None = None
    original_commit: str | None = None
    original_index_tree: str | None = None
    pre_existing_coordination_branches: frozenset[str] = frozenset()
    if rollback_root is not None and is_git_repo(rollback_root):
        original_branch = get_current_branch(rollback_root)
        original_commit_result = subprocess.run(
            ["git", "-C", str(rollback_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if original_commit_result.returncode == 0:
            original_commit = original_commit_result.stdout.strip()
        original_index_result = subprocess.run(
            ["git", "-C", str(rollback_root), "write-tree"],
            capture_output=True,
            text=True,
            check=False,
        )
        if original_index_result.returncode == 0:
            original_index_tree = original_index_result.stdout.strip()
        pre_existing_coordination_branches = _list_coordination_branches(rollback_root)

    try:
        return _create_mission_core_impl(
            repo_root,
            mission_slug,
            mission=mission,
            target_branch=target_branch,
            friendly_name=friendly_name,
            purpose_tldr=purpose_tldr,
            purpose_context=purpose_context,
            pr_bound=pr_bound,
            topology=topology,
            force_recreate_coordination_branch=force_recreate_coordination_branch,
            allow_worktree_context=allow_worktree_context,
            owned_checkout=owned_checkout,
        )
    except BaseException:
        # Re-raised below; the rollback is pure cleanup and must not swallow or
        # replace the original failure (that is why we re-raise unconditionally).
        if rollback_root is not None:
            _restore_git_state_after_failed_create(
                rollback_root,
                original_branch=original_branch,
                original_commit=original_commit,
                original_index_tree=original_index_tree,
                pre_existing_coordination_branches=pre_existing_coordination_branches,
            )
        raise


def _create_mission_core_impl(
    repo_root: Path | None,
    mission_slug: str,
    *,
    mission: str | None = None,
    target_branch: str | None = None,
    friendly_name: str | None = None,
    purpose_tldr: str | None = None,
    purpose_context: str | None = None,
    pr_bound: bool = False,
    topology: MissionTopology = MissionTopology.COORD,
    force_recreate_coordination_branch: bool = False,
    allow_worktree_context: bool = False,
    owned_checkout: Path | None = None,
) -> MissionCreationResult:
    """Create a new feature with all scaffolding.

    This is the programmatic API for feature creation.  Unlike the CLI
    command, it returns a structured result and raises domain exceptions
    instead of calling ``typer.Exit()``.

    Parameters
    ----------
    repo_root:
        Absolute path to the project root (must contain ``.kittify/`` and
        ``kitty-specs/``).  When *None*, ``locate_project_root()`` is called
        automatically.
    mission_slug:
        Bare slug such as ``"user-auth"`` or ``"068-feature"`` (kebab-case).
    mission:
        Optional mission key (e.g. ``"documentation"``, ``"software-dev"``).
        Defaults to ``"software-dev"`` when not provided.
    target_branch:
        Explicit target branch for the feature.  When *None* the current
        git branch is used.
    friendly_name:
        Optional mission title shown on operator-facing surfaces. When omitted,
        it is derived from ``mission_slug``.
    purpose_tldr:
        Optional one-line product/CXO summary for the mission. When omitted,
        it defaults to the resolved ``friendly_name``.
    purpose_context:
        Optional short paragraph explaining the mission in stakeholder terms.
        When omitted, it defaults to a branch-aware summary sentence.
    pr_bound:
        Persist the confirmed pull-request binding in the initial metadata
        write and commit. Defaults to ``False``.
    topology:
        Operator's create-time mission shape (#2218). Defaults to
        :attr:`MissionTopology.COORD` for backward-compat. The coordination
        branch is minted only for the coordination-bearing shapes
        (``COORD`` / ``LANES_WITH_COORD``); ``SINGLE_BRANCH`` / ``LANES`` skip
        the mint and never write ``coordination_branch``. The explicit choice
        is persisted verbatim into ``meta.json`` — never re-derived from
        ``classify_topology`` (which cannot reproduce ``LANES`` pre-finalize).
    allow_worktree_context:
        Bypass the worktree-context guard (step 2) that otherwise raises when
        the *process* ``cwd`` resolves inside a git worktree. Defaults to
        ``False``, preserving the interactive/CLI guard that protects
        operators from accidentally scaffolding a mission inside a lane
        worktree instead of the project root checkout. Intended for
        programmatic callers — notably ``tests/_factories.make_mission()``
        (FR-008) — that pass an explicit ``repo_root`` pointing at an
        isolated (often temporary) repository while the test process itself
        happens to be running from within a lane worktree checkout, which is
        this project's normal execution context for its own test suite.
    owned_checkout:
        Explicit checkout root owned by this invocation. The path is validated
        against the independently resolved primary checkout before the existing
        worktree-context guard can be bypassed. ``None`` preserves the existing
        guard and write-root behavior exactly.

    Returns
    -------
    MissionCreationResult
        Structured result with all paths and metadata.

    Raises
    ------
    MissionCreationError
        On any validation or creation failure.
    charter.activation.pack_context.CharterPackConfigError
        When the project has no activated mission types (an absent or empty
        ``mission_type_activations`` set). This is the WP04 fail-closed at the
        mission-create / mission-type-use boundary: ``PackContext``
        construction is total, so the "provision your charter" error is
        raised here rather than at construction time.
    specify_cli.runtime.resolver.TemplateConfigurationError
        If the activated mission type cannot resolve its configured ``spec``
        template. Resolution happens before any mission state is created.
    """
    # ------------------------------------------------------------------
    # 1. Input validation
    # ------------------------------------------------------------------
    if not KEBAB_CASE_PATTERN.match(mission_slug):
        raise MissionCreationError(
            f"Invalid feature slug '{mission_slug}'. "
            "Must be kebab-case (lowercase letters, numbers, hyphens only)."
            "\n\nValid examples:"
            "\n  - user-auth"
            "\n  - fix-bug-123"
            "\n  - 068-feature-name"
            "\n  - new-dashboard"
            "\n\nInvalid examples:"
            "\n  - User-Auth (uppercase)"
            "\n  - user_auth (underscores)"
        )

    friendly_name_was_provided = friendly_name is not None
    normalized_friendly_name = " ".join((friendly_name or "").split())
    if friendly_name_was_provided and not normalized_friendly_name:
        raise MissionCreationError("Mission creation requires a non-empty friendly_name.")

    # ------------------------------------------------------------------
    # 2. Context guards
    # ------------------------------------------------------------------
    cwd = Path.cwd().resolve()
    ownership_claim: OwnershipClaim | None = None
    resolved_root = repo_root

    if owned_checkout is None:
        if not allow_worktree_context and is_worktree_context(cwd):
            raise MissionCreationError("Cannot create missions from inside a worktree. Run from the project root checkout.")
        if resolved_root is None:
            resolved_root = locate_project_root()
    else:
        if resolved_root is None:
            resolved_root = locate_project_root()
        if resolved_root is not None:
            resolved_root = resolved_root.resolve()
            ownership_claim = resolve_ownership_claim(
                owned_checkout.resolve(),
                resolved_primary=resolved_root,
            )
            ownership_error = error_for_claim(ownership_claim)
            if ownership_error is not None:
                raise ownership_error

    if resolved_root is None:
        raise MissionCreationError("Could not locate project root. Run from within spec-kitty repository.")

    effective_root = (
        ownership_claim.claimed_checkout if ownership_claim is not None and ownership_claim.validation_result is OwnershipValidationResult.OWNED else resolved_root
    )

    if not is_git_repo(resolved_root):
        raise MissionCreationError("Not in a git repository. Mission creation requires git.")

    current_branch = get_current_branch(effective_root)
    if not current_branch or current_branch == "HEAD":
        raise MissionCreationError("Must be on a branch to create missions (detached HEAD detected).")

    # ------------------------------------------------------------------
    # 3. Resolve planning branch
    # ------------------------------------------------------------------
    planning_branch = target_branch if target_branch else current_branch
    create_time_target = resolve_create_time_write_target(planning_branch)
    if not normalized_friendly_name:
        normalized_friendly_name = default_mission_display_name(mission_slug)

    normalized_purpose_tldr = " ".join((purpose_tldr or "").split()) if purpose_tldr is not None else normalized_friendly_name
    normalized_purpose_context = (
        " ".join((purpose_context or "").split()) if purpose_context is not None else default_mission_purpose_context(normalized_friendly_name, planning_branch)
    )
    purpose_errors = validate_purpose_summary(normalized_purpose_tldr, normalized_purpose_context)
    if purpose_errors:
        raise MissionCreationError(" ".join(purpose_errors))

    # Resolve the activated mission's specification template before creating
    # any mission state. A configuration failure must not leave a directory,
    # metadata, or lifecycle events that look like a successful creation.
    from charter.activation.mission_type_profiles import (
        existing_mission_types,
        resolve_mission_type_context,
    )
    from charter.activation.pack_context import CharterPackConfigError
    from specify_cli.runtime.resolver import resolve_configured_template

    # Fail-closed at the mission-create / mission-type-use boundary (WP04
    # re-architecture): ``PackContext`` construction is now total (an absent
    # or empty ``mission_type_activations`` key reads as ``frozenset()``
    # without raising, so the dozens of read / compose hot paths never crash).
    # The actionable "provision your charter" error therefore fires HERE, at
    # the narrowest funnel every mission-create path passes through (the CLI
    # ``agent mission create`` command, the ticket-first ``tracker`` flow, and
    # the ``make_mission`` test factory all call this function). A project
    # with an EMPTY activated set -- whether the key is absent or an authored
    # ``[]`` -- cannot host a mission: a mission requires at least one
    # activated mission type. Read/gating callers of ``existing_mission_types``
    # keep returning empty WITHOUT raising; only this require boundary raises.
    if not existing_mission_types(resolved_root):
        raise CharterPackConfigError(
            "This project has no activated mission types, so a mission cannot "
            "be created. A mission requires at least one activated mission "
            "type. Provision the project's charter: run `spec-kitty init` "
            "(new project) or `spec-kitty upgrade` (existing project), or add a "
            "non-empty `mission_type_activations` list to .kittify/config.yaml "
            "(or the charter.yaml it points to)."
        )

    selected_mission_type = mission or "software-dev"
    mission_type_context = resolve_mission_type_context(
        resolved_root,
        mission_type=selected_mission_type,
    )
    spec_template = resolve_configured_template(
        "spec",
        resolved_root,
        mission_type_context,
    )

    # ------------------------------------------------------------------
    # 4. Directory creation — human-slug + mid8 format (FR-032, FR-044)
    #
    # Pre-merge missions are identified by mission_id (ULID) only.
    # No feature_number is allocated here; mission_number stays None
    # until merge time (single-writer context on main).
    # ------------------------------------------------------------------
    # Mint the ULID first so we can derive mid8 for the directory name.
    # resolve_mid8 derives the mid8 from the declared mission_id (authoritative,
    # FR-004/NFR-003); mission_dir_name composes <human-slug>-<mid8> canonically,
    # stripping any NNN- prefix (FR-032, FR-044).
    mission_id = str(ULID())
    mission_slug_formatted = mission_dir_name(
        mission_slug,
        mid8=resolve_mid8("", mission_id=mission_id),
    )

    feature_dir = effective_root / KITTY_SPECS_DIR / mission_slug_formatted
    feature_dir.mkdir(parents=True, exist_ok=True)

    (feature_dir / "checklists").mkdir(exist_ok=True)
    (feature_dir / "research").mkdir(exist_ok=True)
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)

    (tasks_dir / ".gitkeep").touch()

    # Initialize empty event log so the feature has canonical status from birth.
    (feature_dir / "status.events.jsonl").touch(exist_ok=True)

    # Tasks README
    tasks_readme = tasks_dir / "README.md"
    tasks_readme.write_text(
        render_tasks_readme_content(planning_branch),
        encoding="utf-8",
    )

    # ------------------------------------------------------------------
    # 5. Spec template
    # ------------------------------------------------------------------
    spec_file = feature_dir / "spec.md"
    if not spec_file.exists():
        shutil.copy2(spec_template.path, spec_file)

    # NOTE: spec.md is intentionally NOT committed here (issue #846).
    # The configured scaffold remains on disk but untracked at create time.
    # The agent commits the populated spec.md from the /spec-kitty.specify
    # slash-template after writing substantive content. The substantive-content
    # gate at `setup-plan` entry (see specify_cli.missions._substantive) enforces
    # that spec.md is committed AND substantive before plan.md can be scaffolded.
    # See:
    #   kitty-specs/charter-e2e-827-followups-01KQAJA0/contracts/specify-plan-commit-boundary.md

    # ------------------------------------------------------------------
    # 6. meta.json
    # ------------------------------------------------------------------
    meta_file = feature_dir / "meta.json"
    meta: dict[str, Any] = load_meta_or_empty(feature_dir)

    # Mint canonical machine-facing identity. The ULID was already generated
    # above (needed for mid8 directory naming). The ULID is immutable after creation.
    # mission_number is null pre-merge; a dense display number is assigned only
    # at merge time (single-writer context on main). See FR-044.
    meta.setdefault("mission_id", mission_id)
    meta.setdefault("mission_number", None)  # JSON null — pre-merge missions have no number
    meta.setdefault("slug", mission_slug_formatted)
    meta.setdefault("mission_slug", mission_slug_formatted)
    meta.setdefault("friendly_name", normalized_friendly_name)
    meta.setdefault("purpose_tldr", normalized_purpose_tldr)
    meta.setdefault("purpose_context", normalized_purpose_context)
    meta.setdefault(_META_KEY_MISSION_TYPE, mission or "software-dev")
    meta.setdefault("target_branch", planning_branch)
    meta.setdefault(_META_KEY_CREATED_AT, now_utc_iso())
    if pr_bound:
        meta["pr_bound"] = True

    # ------------------------------------------------------------------
    # 6.5 Coordination branch (WP03 / issue #1348, #2218)
    #
    # Mint (or idempotently reuse) the per-mission coordination branch
    # ``kitty/mission-<slug>-<mid8>`` parented off ``planning_branch`` — but
    # ONLY for the coordination-bearing shapes the operator chose. The
    # branch-flat shapes (``SINGLE_BRANCH`` / ``LANES``) skip the mint and
    # never write ``coordination_branch``, so create-time topology choice is
    # honoured end-to-end (#2218). Persisting the branch ref in ``meta.json``
    # makes downstream commands self-describing — no re-derivation, no drift.
    # ------------------------------------------------------------------
    from specify_cli.missions._create import topology_mints_coordination_branch

    coordination_branch_value: str | None = None
    coordination_branch_created_flag = False
    if topology_mints_coordination_branch(topology):
        from specify_cli.missions._create import ensure_coordination_branch

        coordination_outcome = ensure_coordination_branch(
            repo_root=resolved_root,
            mission_slug=mission_slug_formatted,
            mission_id=mission_id,
            target_branch=planning_branch,
            force_recreate=force_recreate_coordination_branch,
        )
        coordination_branch_value = coordination_outcome.branch_name
        coordination_branch_created_flag = coordination_outcome.created
        meta["coordination_branch"] = coordination_outcome.branch_name

    # ------------------------------------------------------------------
    # 6.6 Mission topology (FR-002 / #2069, #2218)
    #
    # STORE the operator's explicit ``MissionTopology`` choice verbatim so it is
    # READ thereafter, never re-inferred from disk/git at resolve time. The
    # explicit choice is authoritative because ``classify_topology`` CANNOT
    # reproduce the ``LANES`` selection at create time (no ``lanes.json`` exists
    # pre-``finalize-tasks``). We only use the classifier to CORROBORATE the
    # coordination-determined cells (``COORD`` / ``SINGLE_BRANCH``): the minted
    # state must agree with the stored choice, else fail closed. ``flattened`` is
    # a separate boolean provenance flag, NOT a topology value.
    # ------------------------------------------------------------------
    from mission_runtime import classify_topology

    if topology in (MissionTopology.COORD, MissionTopology.SINGLE_BRANCH):
        corroborated = classify_topology(meta.get("coordination_branch") or None, has_lanes=False)
        if corroborated is not topology:
            raise MissionCreationError(
                f"Topology corroboration failed for '{mission_slug_formatted}': stored "
                f"'{topology.value}' but the minted coordination state classifies as "
                f"'{corroborated.value}'."
            )
    meta["topology"] = topology.value
    meta.setdefault("flattened", False)

    from specify_cli.mission_metadata import set_documentation_state, write_meta

    write_meta(feature_dir, meta)
    # FR-001 (#3673): do NOT suppress -- a hard git failure here must raise
    # so ``create_mission_core``'s existing rollback
    # (``_restore_git_state_after_failed_create``) fires. ``_commit_feature_file``
    # does NOT no-op on an empty changeset -- it calls ``safe_commit`` directly,
    # which itself RAISES on an empty changeset (see its docstring). That path
    # is safe here because ``meta.json`` genuinely differs from HEAD at create
    # time, so the commit is non-empty on the real paths. NFR-001: re-raise
    # with step context so the error names the failing step, not just the raw
    # underlying git error text.
    try:
        _commit_feature_file(
            meta_file,
            mission_slug_formatted,
            "meta",
            resolved_root,
            worktree_root=effective_root,
            create_time_target=create_time_target,
        )
    except _BOOTSTRAP_META_COMMIT_SKIPS as exc:
        logger.info(
            "Skipping bootstrap meta.json commit for %s on planning branch %s: %s",
            mission_slug_formatted,
            planning_branch,
            exc,
        )
    except Exception as exc:
        raise RuntimeError(f"meta.json commit failed: {exc}") from exc

    # ------------------------------------------------------------------
    # 7. Documentation state (if applicable)
    # ------------------------------------------------------------------
    if mission == "documentation":
        meta.setdefault(_META_KEY_MISSION_TYPE, "documentation")
        if "documentation_state" not in meta:
            doc_state: dict[str, Any] = {
                "iteration_mode": "initial",
                "divio_types_selected": [],
                "generators_configured": [],
                "target_audience": "developers",
                "last_audit_date": None,
                "coverage_percentage": 0.0,
            }
            set_documentation_state(feature_dir, doc_state)
        # FR-001 (#3673): identical fix, second call site -- not partial to
        # the primary mission-type branch (Acceptance Scenario 4). NFR-001:
        # re-raise with step context (see the primary call site above for the
        # full rationale on why the empty-changeset path is not a concern
        # here).
        try:
            _commit_feature_file(
                meta_file,
                mission_slug_formatted,
                "meta",
                resolved_root,
                worktree_root=effective_root,
                create_time_target=create_time_target,
            )
        except _BOOTSTRAP_META_COMMIT_SKIPS as exc:
            logger.info(
                "Skipping bootstrap documentation meta.json commit for %s on planning branch %s: %s",
                mission_slug_formatted,
                planning_branch,
                exc,
            )
        except Exception as exc:
            raise RuntimeError(f"meta.json commit failed: {exc}") from exc

    # ------------------------------------------------------------------
    # 8. Event emission
    #
    # Local canonical persistence MUST happen before any SaaS fan-out so
    # downstream dashboards and TeamSpace can replay a mission's full
    # history even when SaaS sync is offline (issue #1067).
    # ------------------------------------------------------------------
    try:
        from specify_cli.identity.project import load_identity
        from specify_cli.status import (
            MISSION_CREATED,
            _resolve_local_actor,
            emit_mission_created_local,
            read_lifecycle_events,
        )

        _identity = load_identity(resolved_root / ".kittify" / "config.yaml")
        creation_actor = _resolve_local_actor()
        expected_created_payload = build_mission_created_payload(
            mission_slug=mission_slug_formatted,
            mission_id=meta.get("mission_id"),
            mission_number=None,
            mission_type=str(meta.get(_META_KEY_MISSION_TYPE) or mission or "software-dev"),
            target_branch=planning_branch,
            wp_count=0,
            friendly_name=normalized_friendly_name,
            purpose_tldr=normalized_purpose_tldr,
            purpose_context=normalized_purpose_context,
            created_at=str(meta[_META_KEY_CREATED_AT]) if meta.get(_META_KEY_CREATED_AT) else None,
            actor=creation_actor,
        )
        emit_mission_created_local(
            feature_dir,
            mission_slug=mission_slug_formatted,
            mission_id=meta.get("mission_id"),
            mission_number=None,
            mission_type=str(meta.get(_META_KEY_MISSION_TYPE) or mission or "software-dev"),
            target_branch=planning_branch,
            wp_count=0,
            project_uuid=str(_identity.project_uuid) if _identity.project_uuid else None,
            project_slug=_identity.project_slug,
            friendly_name=normalized_friendly_name,
            purpose_tldr=normalized_purpose_tldr,
            purpose_context=normalized_purpose_context,
            created_at=str(meta[_META_KEY_CREATED_AT]) if meta.get(_META_KEY_CREATED_AT) else None,
            actor=creation_actor,
        )
        created_events = [event for event in read_lifecycle_events(feature_dir / "status.events.jsonl") if event.get("event_type") == MISSION_CREATED]
        if len(created_events) != 1:
            raise MissionCreationError(f"expected exactly one persisted MissionCreated event, found {len(created_events)}")
        persisted_created = created_events[0]
        if (
            persisted_created.get("aggregate_id") != meta.get("mission_id")
            or persisted_created.get("aggregate_type") != "Mission"
            or persisted_created.get("payload") != expected_created_payload
        ):
            raise MissionCreationError("persisted MissionCreated event does not match the canonical creation snapshot")
    except Exception as _local_evt_exc:  # noqa: BLE001
        raise MissionCreationError(
            "Local canonical MissionCreated persistence failed for "
            f"{mission_slug_formatted!r}: {_local_evt_exc}. The partial scaffold "
            "is retained for explicit resume-probe diagnosis; do not retry create "
            "until it is repaired or removed."
        ) from _local_evt_exc

    # Mission creation immediately scaffolds ``spec.md`` and opens
    # the specify phase. Record ``SpecifyStarted`` against the canonical
    # local log so that TeamSpace replay can show "currently specifying"
    # before the agent commits substantive spec content (which is where
    # ``setup-plan`` later emits ``SpecifyCompleted``). Without this event
    # the canonical lifecycle stream skips straight from ``MissionCreated``
    # to ``SpecifyCompleted``, leaving the specify-phase entry point
    # invisible to dashboards and TeamSpace — see issue #1067.
    try:
        from specify_cli.status import (
            SPECIFY_STARTED,
            emit_artifact_phase,
        )

        emit_artifact_phase(
            feature_dir,
            event_type=SPECIFY_STARTED,
            mission_slug=mission_slug_formatted,
            actor="spec-kitty mission create",
            artifact_path=str(spec_file.relative_to(effective_root)) if spec_file.is_relative_to(effective_root) else "spec.md",
        )
    except Exception as _phase_evt_exc:  # noqa: BLE001
        logger.debug(
            "Local SpecifyStarted persistence skipped for %s: %s",
            mission_slug_formatted,
            _phase_evt_exc,
        )

    # ------------------------------------------------------------------
    # 9. Consume pending origin if present (ticket-first flow)
    # ------------------------------------------------------------------
    origin_binding_attempted = False
    origin_binding_succeeded = False
    origin_binding_error: str | None = None

    origin_binding_attempted, origin_binding_succeeded, origin_binding_error, meta = _consume_pending_origin_if_present(
        repo_root=resolved_root,
        feature_dir=feature_dir,
        meta=meta,
    )

    # ------------------------------------------------------------------
    # 9.5 Commit the origin-ticket binding (squad follow-on to #2739/#2693)
    #
    # ``_consume_pending_origin_if_present`` -> ``bind_mission_origin`` calls
    # the SaaS binder FIRST, then writes the updated ``origin_ticket`` subtree
    # to ``meta.json`` locally via ``set_origin_ticket`` (``write_meta`` — a
    # plain disk write, no commit). The step-8.5 scaffold commit above already
    # landed BEFORE this write, so on the ticket-first flow a successful
    # origin bind leaves ``meta.json`` modified-uncommitted in the working
    # tree while the CLI's ``--json`` envelope reports the mission created —
    # ``git status --porcelain`` shows ``M meta.json`` even though creation
    # "succeeded". Land it through the SAME sanctioned commit surface used at
    # step 8.5 so the tree is clean the moment origin binding succeeds.
    # Mirrors step 8.5's FR-001 discipline: raise rather than silently leave
    # the tree dirty on a hard commit failure.
    # ------------------------------------------------------------------
    if origin_binding_succeeded:
        try:
            _commit_feature_file(
                meta_file,
                mission_slug_formatted,
                "origin-ticket binding",
                resolved_root,
                worktree_root=effective_root,
                create_time_target=create_time_target,
            )
        except Exception as exc:
            raise RuntimeError(f"origin-ticket binding commit failed: {exc}") from exc

    # ------------------------------------------------------------------
    # 10. Build result
    # ------------------------------------------------------------------
    created_files = [spec_file, meta_file, tasks_readme]

    return MissionCreationResult(
        feature_dir=feature_dir,
        mission_slug=mission_slug_formatted,
        mission_number=None,  # pre-merge: no display number assigned (FR-044)
        meta=meta,
        target_branch=planning_branch,
        current_branch=current_branch,
        created_files=created_files,
        origin_binding_attempted=origin_binding_attempted,
        origin_binding_succeeded=origin_binding_succeeded,
        origin_binding_error=origin_binding_error,
        coordination_branch=coordination_branch_value,
        coordination_branch_created=coordination_branch_created_flag,
        owned_checkout=(
            ownership_claim.claimed_checkout if ownership_claim is not None and ownership_claim.validation_result is OwnershipValidationResult.OWNED else None
        ),
        canonical_repo_root=resolved_root,
    )


def _consume_pending_origin_if_present(
    *,
    repo_root: Path,
    feature_dir: Path,
    meta: dict[str, Any],
) -> tuple[bool, bool, str | None, dict[str, Any]]:
    """Bind a staged pending origin after mission creation, if present.

    Dispatches to the registered PendingOriginConsumer via
    ``core.adapters.consume_pending_origin`` so that this module carries no
    direct INTEGRATION imports (FR-004/FR-006).  The concrete implementation
    lives in ``tracker/origin_consumer.py`` and is registered at tracker
    startup.  When no consumer is registered the call is a safe no-op
    that returns ``(False, False, None, meta)``.
    """
    from specify_cli.core.adapters import consume_pending_origin

    # Typed binding required: mypy uses follow_imports=skip for specify_cli.*
    # so the return of consume_pending_origin is seen as Any here; the
    # explicit annotation re-introduces the correct return type so the caller
    # does not propagate Any (no blanket suppression needed).
    result: tuple[bool, bool, str | None, dict[str, Any]] = consume_pending_origin(repo_root, feature_dir, meta)
    return result
