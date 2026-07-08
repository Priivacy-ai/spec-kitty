"""Reusable mission-creation logic extracted from the CLI command.

This module provides ``create_mission_core()`` -- the programmatic API
for creating a new mission directory with all scaffolding. The CLI
command ``create()`` is a thin wrapper around this function.
"""

from __future__ import annotations

from specify_cli.core.constants import KITTY_SPECS_DIR
import contextlib
import logging
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ulid import ULID

from mission_runtime import MissionArtifactKind, MissionTopology, placement_seam
from specify_cli.core.commit_guard import GuardCapability
from specify_cli.core.git_ops import get_current_branch, is_git_repo
from specify_cli.core.mission_payload import (
    default_mission_display_name,
    default_mission_purpose_context,
)
from specify_cli.core.paths import is_worktree_context, locate_project_root
from specify_cli.git import safe_commit
from specify_cli.lanes.branch_naming import mission_dir_name, resolve_mid8
from specify_cli.mission_metadata import load_meta_or_empty, validate_purpose_summary

logger = logging.getLogger(__name__)

# coord-primary-partition-lock WP02 (T009 / S1192): the ``meta`` field names
# repeated across the metadata-assembly block below (default + event-emission
# reads) hoisted to named constants rather than restated as literals.
_META_KEY_MISSION_TYPE = "mission_type"
_META_KEY_CREATED_AT = "created_at"


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
) -> None:
    """Commit a single planning artifact to its seam-resolved primary home.

    This is a slim, typer-free version of the ``_commit_to_branch`` helper
    in the CLI module.  It raises on hard failures and silently succeeds
    when there is nothing to commit.

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
    seam_target = placement_seam(repo_root, mission_slug).write_target(MissionArtifactKind.SPEC)
    safe_commit(
        repo_root=repo_root,
        worktree_root=repo_root,
        target=seam_target,
        message=commit_msg,
        paths=(file_path,),
        capability=GuardCapability.STANDARD,
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
    topology: MissionTopology = MissionTopology.COORD,
    force_recreate_coordination_branch: bool = False,
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
    topology:
        Operator's create-time mission shape (#2218). Defaults to
        :attr:`MissionTopology.COORD` for backward-compat. The coordination
        branch is minted only for the coordination-bearing shapes
        (``COORD`` / ``LANES_WITH_COORD``); ``SINGLE_BRANCH`` / ``LANES`` skip
        the mint and never write ``coordination_branch``. The explicit choice
        is persisted verbatim into ``meta.json`` — never re-derived from
        ``classify_topology`` (which cannot reproduce ``LANES`` pre-finalize).

    Returns
    -------
    MissionCreationResult
        Structured result with all paths and metadata.

    Raises
    ------
    MissionCreationError
        On any validation or creation failure.
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
    if is_worktree_context(cwd):
        raise MissionCreationError("Cannot create missions from inside a worktree. Run from the project root checkout.")

    resolved_root = repo_root
    if resolved_root is None:
        resolved_root = locate_project_root()
    if resolved_root is None:
        raise MissionCreationError("Could not locate project root. Run from within spec-kitty repository.")

    if not is_git_repo(resolved_root):
        raise MissionCreationError("Not in a git repository. Mission creation requires git.")

    current_branch = get_current_branch(resolved_root)
    if not current_branch or current_branch == "HEAD":
        raise MissionCreationError("Must be on a branch to create missions (detached HEAD detected).")

    # ------------------------------------------------------------------
    # 3. Resolve planning branch
    # ------------------------------------------------------------------
    planning_branch = target_branch if target_branch else current_branch
    if not normalized_friendly_name:
        normalized_friendly_name = default_mission_display_name(mission_slug)

    normalized_purpose_tldr = " ".join((purpose_tldr or "").split()) if purpose_tldr is not None else normalized_friendly_name
    normalized_purpose_context = (
        " ".join((purpose_context or "").split())
        if purpose_context is not None
        else default_mission_purpose_context(normalized_friendly_name, planning_branch)
    )
    purpose_errors = validate_purpose_summary(normalized_purpose_tldr, normalized_purpose_context)
    if purpose_errors:
        raise MissionCreationError(" ".join(purpose_errors))

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

    feature_dir = resolved_root / KITTY_SPECS_DIR / mission_slug_formatted
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
        spec_template_candidates = [
            resolved_root / ".kittify" / "templates" / "spec-template.md",
            resolved_root / "templates" / "spec-template.md",
        ]
        for template in spec_template_candidates:
            if template.exists():
                shutil.copy2(template, spec_file)
                break
        else:
            spec_file.touch()

    # NOTE: spec.md is intentionally NOT committed here (issue #846).
    # The empty scaffold remains on disk but untracked at create time.
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
    meta.setdefault(_META_KEY_CREATED_AT, datetime.now(timezone.utc).isoformat())  # noqa: UP017

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
    with contextlib.suppress(Exception):
        _commit_feature_file(meta_file, mission_slug_formatted, "meta", resolved_root)

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
        with contextlib.suppress(Exception):
            _commit_feature_file(meta_file, mission_slug_formatted, "meta", resolved_root)

    # ------------------------------------------------------------------
    # 8. Event emission
    #
    # Local canonical persistence MUST happen before any SaaS fan-out so
    # downstream dashboards and TeamSpace can replay a mission's full
    # history even when SaaS sync is offline (issue #1067).
    # ------------------------------------------------------------------
    try:
        from specify_cli.identity.project import load_identity
        from specify_cli.status import emit_mission_created_local

        _identity = load_identity(resolved_root / ".kittify" / "config.yaml")
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
        )
    except Exception as _local_evt_exc:  # noqa: BLE001
        logger.warning(
            "Local canonical MissionCreated persistence failed for %s: %s",
            mission_slug_formatted,
            _local_evt_exc,
        )

    # Mission creation immediately scaffolds an empty ``spec.md`` and opens
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
            artifact_path=str(spec_file.relative_to(resolved_root))
            if spec_file.is_relative_to(resolved_root)
            else "spec.md",
        )
    except Exception as _phase_evt_exc:  # noqa: BLE001
        logger.debug(
            "Local SpecifyStarted persistence skipped for %s: %s",
            mission_slug_formatted,
            _phase_evt_exc,
        )

    # Dossier sync (fire-and-forget via registered adapter)
    # SaaS fan-out is already handled by emit_mission_created_local above —
    # it calls fire_lifecycle_saas_fanout internally via append_lifecycle_event.
    # No direct INTEGRATION imports needed here (FR-004/FR-006).
    from specify_cli.status import fire_dossier_sync

    fire_dossier_sync(feature_dir, mission_slug_formatted, resolved_root)

    # ------------------------------------------------------------------
    # 9. Consume pending origin if present (ticket-first flow)
    # ------------------------------------------------------------------
    origin_binding_attempted = False
    origin_binding_succeeded = False
    origin_binding_error: str | None = None

    origin_binding_attempted, origin_binding_succeeded, origin_binding_error, meta = (
        _consume_pending_origin_if_present(
            repo_root=resolved_root,
            feature_dir=feature_dir,
            meta=meta,
        )
    )

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
    result: tuple[bool, bool, str | None, dict[str, Any]] = consume_pending_origin(
        repo_root, feature_dir, meta
    )
    return result
