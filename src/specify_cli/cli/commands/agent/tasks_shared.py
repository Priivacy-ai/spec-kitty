"""Cross-family shared helpers relocated out of ``tasks.py`` (WP02, #2058/#2305).

Mission ``tasks-py-degod-wave2-01KWH9EQ`` FR-002/FR-003: the ~20 helpers used
across the five ``agent tasks`` command families (or exported/patched as part
of the ``tasks`` compatibility surface) live here, moved VERBATIM from
``tasks.py``. Family-specific glue (``_mt_*``/``_mr_*``/``_st_*``/``_ms_*``/
``_ft_*``), the ``_do_*`` orchestrators, the port adapters, and the Typer
command bodies stay behind for their own relocation WPs.

**Seam bridge** (research.md D1, the ``mission_finalize.py`` template idiom):
``tasks.py`` re-imports every symbol defined here, so ``tasks.<name>`` remains
a module attribute and every historical ``@patch("...agent.tasks.<name>")`` /
``monkeypatch.setattr(tasks, "<name>")`` target keeps resolving. To make those
patches keep INTERCEPTING (not merely resolving), relocated bodies route every
call to a patched seam symbol — infra names from the D7 seam inventory
(``get_main_repo_root``, ``subprocess``, ``console``, ``ProtectionPolicy``,
``resolve_placement_only``, ``resolve_topology``,
``routes_through_coordination``, ``resolve_workspace_for_wp``, …) and moved
siblings — through a lazy in-function import of the ``tasks`` module
(``from specify_cli.cli.commands.agent import tasks as _tasks``) and call
``_tasks.<attr>(...)``. The lazy import is cycle-safe (never module scope).

Per-symbol routing/interception evidence:
``kitty-specs/tasks-py-degod-wave2-01KWH9EQ/seam-checklist.md`` (Layer 4 of
the parity contract); interception pins live in
``tests/specify_cli/cli/commands/agent/test_tasks_shared_seam.py``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import typer

from kernel._safe_re import re
from mission_runtime import MissionArtifactKind
from specify_cli.agent_tasks_ports import Render
from specify_cli.cli.commands.agent.tasks_outline import TASKS_MD_FILENAME, TaskIdResolutionOutcome, TaskIdResult
from specify_cli.cli.commands.agent.tasks_parsing_validation import (
    _validate_ready_for_review as _seam_validate_ready_for_review,
)
from specify_cli.cli.selector_resolution import resolve_mission_handle
from specify_cli.core.constants import KITTY_SPECS_DIR
from specify_cli.mission_metadata import resolve_mission_identity
from specify_cli.missions._read_path_resolver import (
    candidate_feature_dir_for_mission,
    resolve_planning_read_dir,
)
from specify_cli.status import is_dossier_snapshot as _is_dossier_snapshot

logger = logging.getLogger(__name__)


def resolve_primary_branch(repo_root: Path) -> str:
    """Resolve the primary branch name (main, master, etc.).

    Delegates to the centralized implementation in core.git_ops.

    Returns:
        Detected primary branch name.
    """
    from specify_cli.core.git_ops import resolve_primary_branch as _resolve

    branch: str = _resolve(repo_root)
    return branch


def _review_currency_check_branch(
    *,
    main_repo_root: Path,
    mission_slug: str,
    target_branch: str,
    workspace: object | None,
) -> str:
    from specify_cli.cli.commands.agent import tasks as _tasks

    context = getattr(workspace, "context", None)
    base_branch = getattr(context, "base_branch", None)
    if base_branch:
        return str(base_branch)

    try:
        # base-ref read under coord topology — coord kind preserves G-2
        # (write-surface-coherence WP02 / T031 site 3): review-currency compares
        # against the coordination BASE ref under coord topology. STATUS_STATE keeps
        # the coord ref; a primary kind would read the primary ref as the base and
        # corrupt the currency comparison.
        placement = _tasks.resolve_placement_only(
            main_repo_root, mission_slug, kind=MissionArtifactKind.STATUS_STATE
        )
    except Exception as exc:  # noqa: BLE001 -- legacy fixtures keep target-branch fallback
        logger.debug("Could not resolve review currency placement: %s", exc)
        return target_branch

    # FR-005 / FR-001b: the coord-vs-primary decision reads the WP02 STORED
    # topology via the ONE canonical predicate, never a per-ref ``.kind``.
    if _tasks.routes_through_coordination(_tasks.resolve_topology(main_repo_root, mission_slug)):
        coord_ref: str = placement.ref
        return coord_ref
    return target_branch


# ---------------------------------------------------------------------------
# FR-015 / C-003 / C-004: review-handoff runtime-state deny-list
# ---------------------------------------------------------------------------
# Spec-kitty writes review-lock.json and other ephemeral runtime state under
# ``.spec-kitty/`` inside each worktree, and merge/status metadata under
# ``.kittify/`` at the repo root. These directories are git-ignored but do
# show up in ``git status --porcelain`` as untracked noise, which historically
# tripped the "uncommitted changes in worktree" guard in
# ``_validate_ready_for_review`` when an external reviewer (the review lock)
# had only just done its job (issue #589).
#
# C-003: this is a *fixed named list*, NOT a pattern match. Do not add
# entries here without explicit spec coverage; re-opening the door to pattern
# matching lets untracked source files silently slip past the guard.
# C-004: paths OUTSIDE this list still reach the blocking branch unchanged,
# so genuine uncommitted implementation work continues to block review handoff.
_RUNTIME_STATE_DENY_LIST: tuple[str, ...] = (".spec-kitty/", ".kittify/")


# ---------------------------------------------------------------------------
# Mission charter-e2e-827-followups-01KQAJA0 / C-006: dossier snapshot exclude
# ---------------------------------------------------------------------------
# The dossier snapshot at <feature_dir>/.kittify/dossiers/<mission>/snapshot-
# latest.json is a mutable derived artifact. Per the EXCLUDE ownership policy
# (single policy — see ``specify_cli.status.preflight``), it must be filtered
# from any preflight that bypasses ``.gitignore`` so the writer's update does
# not self-block the next ``move-task`` transition.
def _filter_runtime_state_paths(porcelain_output: str) -> str:
    """Strip lines whose path falls under spec-kitty's own runtime-state dirs.

    Input is the raw ``git status --porcelain`` output. Each line has the
    format ``XY path`` where ``XY`` is a two-character status code followed by
    a single space. A ``startswith`` check against the fixed deny-list is
    used intentionally (C-003): no regex, no glob expansion, no fuzzy match.

    Dossier ``snapshot-latest.json`` paths are also stripped here per the
    EXCLUDE ownership policy (C-006); the snapshot writer must never
    self-block a transition.

    Returns a newline-joined string with deny-listed entries removed. Lines
    whose path is OUTSIDE the deny list are preserved verbatim so the
    downstream guard still blocks on genuine drift (C-004).
    """
    kept: list[str] = []
    for line in porcelain_output.splitlines():
        if not line.strip():
            continue
        # git status --porcelain format: first 3 chars are "XY " status prefix.
        path_part = line[3:] if len(line) > 3 else line.strip()
        if any(path_part.startswith(prefix) for prefix in _RUNTIME_STATE_DENY_LIST):
            continue
        if _is_dossier_snapshot(path_part):
            continue
        kept.append(line)
    return "\n".join(kept)


def _emit_sparse_session_warning(repo_root: Path, command: str) -> None:
    """Emit the FR-010/FR-019 sparse-checkout session warning once per process.

    Called from every state-mutating tasks handler at command entry so
    reviewers and implementers discover they are operating inside a
    sparse-checkout worktree before they commit partial work. The underlying
    ``warn_if_sparse_once`` helper from WP02 is self-memoizing (first caller
    wins the ``command`` label) and swallows detection errors, so this
    wrapper is safe to call unconditionally and never crashes the command.
    """
    try:
        from specify_cli.git.sparse_checkout import warn_if_sparse_once

        warn_if_sparse_once(repo_root, command=command)
    except Exception as _exc:  # noqa: BLE001 - defensive; must never break CLI
        # FR-010 contract: detection failures must never break the CLI command
        # that invoked this hook. Log to the module logger at debug level so
        # the failure is still traceable without tripping the ``S110`` lint.
        logging.getLogger(__name__).debug(
            "sparse-checkout session warning failed for %s: %s",
            command,
            _exc,
        )


def _ensure_target_branch_checked_out(
    repo_root: Path,
    mission_slug: str,
    json_output: bool,
) -> tuple[Path, str]:
    """Resolve branch context without auto-checkout (respects user's current branch).

    Returns:
        (main_repo_root, current_branch)
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    from specify_cli.core.git_ops import get_current_branch, resolve_target_branch

    # Write path: keep main-repo-root resolution so canonical serialization
    # pins to the primary checkout regardless of where the operator stands.
    main_repo_root = _tasks.get_main_repo_root(repo_root)

    # Check for detached HEAD using robust branch detection
    current_branch = get_current_branch(main_repo_root)
    if current_branch is None:
        raise RuntimeError("Detached HEAD — checkout a branch before continuing")

    # Resolve branch routing (unified logic, no auto-checkout)
    resolution = resolve_target_branch(mission_slug, main_repo_root, current_branch, respect_current=True)

    # Show consistent branch banner
    if not json_output:
        if not resolution.should_notify:
            _tasks.console.print(f"[bold cyan]Branch:[/bold cyan] {current_branch} (target for this mission)")
        else:
            _tasks.console.print(f"[bold yellow]Branch:[/bold yellow] on '{resolution.current}', mission targets '{resolution.target}'")

    # Return current branch (no checkout performed)
    return main_repo_root, resolution.current


def _find_mission_slug(
    explicit_mission: str | None = None,
    *,
    json_output: bool = False,
    repo_root: Path | None = None,
    render: Render | None = None,
) -> str:
    """Require an explicit mission slug (no auto-detection).

    When repo_root is supplied the handle is resolved via the canonical
    mission resolver (resolve_mission_handle), which handles ambiguous
    numeric-prefix handles, mid8 prefixes, and full ULID forms.  The
    resolver calls sys.exit(2) on error so no try/except is needed.

    Args:
        explicit_mission: Mission slug provided via --mission.
        json_output: Propagate to resolver error rendering.
        repo_root: Repository root; if provided, enables canonical resolver.

    Returns:
        Mission slug (e.g., "008-unified-python-cli")

    Raises:
        typer.Exit: If mission slug is not provided.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks

    if not explicit_mission or not explicit_mission.strip():
        err = "--mission <slug> is required"
        if json_output:
            render = render or _tasks.RealRender()
            print(render.json_envelope({"error": err}))
        else:
            _tasks.console.print(f"[red]Error:[/red] {err}")
        raise typer.Exit(1)

    raw_handle = explicit_mission.strip()
    if repo_root is not None:
        # Write path: keep main-repo-root resolution so canonical serialization
        # pins to the primary checkout regardless of where the operator stands.
        # Note: repo_root from locate_project_root() already resolves to the main
        # checkout; get_main_repo_root() here guards against caller passing a
        # worktree path directly.
        legacy_dir = candidate_feature_dir_for_mission(_tasks.get_main_repo_root(repo_root), raw_handle)
        if legacy_dir.exists():
            # F-001: the candidate resolver canonicalizes mid8/ULID/numeric
            # handles, so the resolved directory's NAME — not the raw operator
            # handle — is the canonical mission slug downstream consumers need.
            legacy_name: str = legacy_dir.name
            return legacy_name
        try:
            resolved = resolve_mission_handle(raw_handle, repo_root, json_mode=json_output)
            resolved_slug: str = resolved.mission_slug
            return resolved_slug
        except (SystemExit, typer.Exit):
            if legacy_dir.exists():
                fallback_name: str = legacy_dir.name
                return fallback_name
            raise

    return raw_handle


def _output_result(
    json_mode: bool,
    data: dict[str, Any],
    success_message: str | None = None,
    *,
    render: Render | None = None,
) -> None:
    """Output result in JSON or human-readable format.

    Args:
        json_mode: If True, output JSON; else use Rich console
        data: Data to output (used for JSON mode)
        success_message: Message to display in human mode
        render: Optional Render seam; defaults to the compact production adapter
    """
    from specify_cli.cli.commands.agent import tasks as _tasks

    if json_mode:
        render = render or _tasks.RealRender()
        print(render.json_envelope(data))
    elif success_message:
        _tasks.console.print(success_message)


def _output_error(
    json_mode: bool,
    error_message: str,
    diagnostic: dict[str, Any] | None = None,
    *,
    render: Render | None = None,
) -> None:
    """Output error in JSON or human-readable format.

    Args:
        json_mode: If True, output JSON; else use Rich console
        error_message: Error message to display
        render: Optional Render seam; defaults to the compact production adapter
    """
    from specify_cli.cli.commands.agent import tasks as _tasks

    if json_mode:
        render = render or _tasks.RealRender()
        print(render.json_envelope(diagnostic if diagnostic is not None else {"error": error_message}))
    else:
        _tasks.console.print(f"[red]Error:[/red] {error_message}")


def _protected_branch_status_commit_error(branch: str, repo_root: Path, command: str) -> str | None:
    from specify_cli.cli.commands.agent import tasks as _tasks

    # ProtectionPolicy.resolve is the sole I/O boundary (FR-007/NFR-003):
    # config+hatch reads happen once; is_protected() is I/O-free.
    if not _tasks.ProtectionPolicy.resolve(repo_root).is_protected(branch):
        return None
    return (
        f"Refusing to run `{command}` with auto-commit on protected branch "
        f"'{branch}' before mutating status files. Run status commit "
        "operations from an allowed coordination/lane branch, or rerun with "
        "--no-auto-commit when you intentionally want to handle the status "
        "artifact commit manually."
    )


def _coord_topology_active(repo_root: Path, mission_slug: str) -> bool:
    """Return True if the coordination worktree exists for this mission."""
    try:
        from specify_cli.coordination.workspace import CoordinationWorkspace
        from specify_cli.lanes.branch_naming import resolve_transaction_mid8
        # Authoritative topology resolver (FR-004/#1918): a coord-worktree lookup
        # needs the REAL mid8 to name its dir. With no declared mission_id/mid8 the
        # seam falls back to the embedded ``<slug>-<mid8>`` tail (genuine slug) and
        # returns "" only for a legacy/flattened mission with no coord topology —
        # exactly the historical mid8_from_slug behaviour for resolvable slugs.
        mid8 = resolve_transaction_mid8(
            mission_slug, mission_id=None, mid8=None, coordination_branch=None
        )
        path = CoordinationWorkspace.worktree_path(repo_root, mission_slug, mid8)
        exists: bool = path.exists()
        return exists
    except Exception:
        return False


def _skip_target_branch_commit(repo_root: Path, mission_slug: str, target_branch: str) -> bool:
    """Return True when the direct WP-file commit to a protected primary must be skipped.

    NOT a routing authority (write-surface-coherence WP02 / T032 / G-1): the
    commit DESTINATION for the WP file is owned solely by the kind authority
    (``resolve_placement_only(kind=WORK_PACKAGE_TASK)``). This flag only decides
    whether to SKIP the direct primary commit in the genuine protected-primary
    case — coord topology active AND the primary ``target_branch`` is protected —
    where committing directly to the protected ref is refused and the status
    transition committed to the coordination branch is authoritative. It selects
    no ref; it suppresses a commit that the protection policy would refuse anyway.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks

    # ProtectionPolicy.resolve is the sole I/O boundary (FR-007/NFR-003):
    # config+hatch reads happen once; is_protected() is I/O-free.
    skip: bool = (
        _tasks._coord_topology_active(repo_root, mission_slug)
        and _tasks.ProtectionPolicy.resolve(repo_root).is_protected(target_branch)
    )
    return skip


def _mission_identity_payload(feature_dir: Path) -> dict[str, str | int | None]:
    # ``mission_number`` is ``int | None`` on ``MissionIdentity`` (display-only,
    # ``null`` pre-merge); slug/type are ``str``. The value is threaded verbatim
    # into machine-facing JSON payloads, so the return type carries the real
    # heterogeneity instead of coercing (byte-parity: no string-cast of the
    # number). Consumers spread this into ``dict[str, object]`` result maps.
    identity = resolve_mission_identity(feature_dir)
    return {
        "mission_slug": identity.mission_slug,
        "mission_number": identity.mission_number,
        "mission_type": identity.mission_type,
    }


def _resolve_git_common_dir(main_repo_root: Path) -> Path:
    """Resolve absolute git common-dir for the repository."""
    from specify_cli.cli.commands.agent import tasks as _tasks

    result = _tasks.subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        cwd=main_repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    raw_value = result.stdout.strip()
    if not raw_value:
        raise RuntimeError("Unable to resolve git common directory")
    common_dir = Path(raw_value)
    if not common_dir.is_absolute():
        common_dir = (main_repo_root / common_dir).resolve()
    return common_dir


def _check_unchecked_subtasks(repo_root: Path, mission_slug: str, wp_id: str, _force: bool) -> list[str]:
    """Check for unchecked subtasks in tasks.md for a given WP.

    Args:
        repo_root: Repository root path
        mission_slug: Feature slug (e.g., "010-lane-only-runtime")
        wp_id: Work package ID (e.g., "WP01")
        force: If True, only warn; if False, fail on unchecked tasks

    Returns:
        List of unchecked task IDs (empty if all checked or not found)

    Raises:
        typer.Exit: If unchecked tasks found and force=False
    """
    from specify_cli.cli.commands.agent import tasks as _tasks

    # Write path: keep main-repo-root resolution so canonical serialization
    # pins to the primary checkout regardless of where the operator stands.
    main_repo_root = _tasks.get_main_repo_root(repo_root)
    # WP04 / FR-006: ``tasks.md`` is a TASKS_INDEX (primary-partition) artifact —
    # read it from PRIMARY (INV-5) so a coord-topology mission's stale ``-coord``
    # husk cannot shadow the real primary ``tasks.md`` (#2062 read-side close).
    from mission_runtime import MissionArtifactKind

    feature_dir = resolve_planning_read_dir(
        main_repo_root, mission_slug, kind=MissionArtifactKind.TASKS_INDEX
    )
    tasks_md = feature_dir / TASKS_MD_FILENAME

    if not tasks_md.exists():
        return []  # No tasks.md, can't check

    content = tasks_md.read_text(encoding="utf-8")

    # Find canonical subtasks for this WP. Only unchecked rows of the form
    # ``- [ ] T### <desc>`` count as blocking. Validation/procedure/checklist
    # command rows (e.g. ``- [ ] swift test``, ``- [ ] git status --short``),
    # prose, and anything inside fenced code blocks are intentionally ignored —
    # they are not work-package subtasks and must not block a lane transition.
    lines = content.split("\n")
    unchecked: list[str] = []
    in_wp_section = False
    in_code_fence = False

    # Canonical subtask row: ``- [ ] T001 ...``. A ``T`` id of at least three
    # digits is mandatory (``\d{3,}`` so ids past T999 still block).
    canonical_unchecked = re.compile(r"^-\s*\[\s*\]\s*(T\d{3,})\b")

    for line in lines:
        stripped = line.strip()

        # Toggle fenced-code-block state on ``` or ~~~ markers. Task-like lines
        # inside fenced code blocks (examples in implementation notes) must not
        # be treated as real subtasks.
        if stripped.startswith(("```", "~~~")):
            in_code_fence = not in_code_fence
            continue

        if in_code_fence:
            continue

        # Check if we entered this WP's section
        if re.search(rf"^#{{2,4}}[^#].*{wp_id}\b", line):
            in_wp_section = True
            continue

        # Check if we entered a different WP section
        if in_wp_section and re.search(r"^#{2,4}[^#].*WP\d{2}\b", line):
            break  # Left this WP's section

        # Look for unchecked canonical task rows in this WP's section
        if in_wp_section:
            unchecked_match = canonical_unchecked.match(stripped)
            if unchecked_match:
                unchecked.append(unchecked_match.group(1))

    return unchecked


def _validate_ready_for_review(
    repo_root: Path,
    mission_slug: str,
    wp_id: str,
    force: bool,
    target_lane: str = "for_review",
) -> tuple[bool, list[str]]:
    """Validate that WP is ready for review by checking for uncommitted changes.

    Thin wrapper over the WP06 seam
    (:func:`tasks_parsing_validation._validate_ready_for_review`). The
    ``tasks``-resident collaborators are passed in from that module's live
    namespace at call time so the existing ``@patch("...agent.tasks.<name>")``
    contracts (e.g. ``get_main_repo_root``, ``get_mission_type``,
    ``get_feature_target_branch``, ``resolve_workspace_for_wp``, the git
    helpers, and ``console``) continue to apply unchanged. Behaviour,
    validation order, error strings, and the (bool, list[str]) return shape
    are preserved exactly.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks

    verdict: tuple[bool, list[str]] = _seam_validate_ready_for_review(
        repo_root,
        mission_slug,
        wp_id,
        force,
        target_lane=target_lane,
        get_main_repo_root=_tasks.get_main_repo_root,
        get_mission_type=_tasks.get_mission_type,
        get_feature_target_branch=_tasks.get_feature_target_branch,
        resolve_workspace_for_wp=_tasks.resolve_workspace_for_wp,
        review_currency_check_branch=_tasks._review_currency_check_branch,
        behind_commits_touch_only_planning_artifacts=_tasks._behind_commits_touch_only_planning_artifacts,
        filter_runtime_state_paths=_tasks._filter_runtime_state_paths,
        list_wp_branch_specs_changes_for_guard=_tasks._list_wp_branch_specs_changes_for_guard,
        console=_tasks.console,
    )
    return verdict


def _wp_branch_merged_into_target(
    repo_root: Path,
    mission_slug: str,
    wp_id: str,
    target_branch: str,
) -> tuple[bool, str]:
    """Check whether a lane branch tip is reachable from the target branch.

    Returns:
        (is_merged, message)
    """
    from specify_cli.cli.commands.agent import tasks as _tasks

    workspace = _tasks.resolve_workspace_for_wp(repo_root, mission_slug, wp_id)
    wp_branch = workspace.branch_name
    if wp_branch is None:
        return (
            False,
            (
                "Cannot verify merge ancestry: no branch name resolved for "
                f"workspace of {wp_id}.\nEither merge and keep the branch ref "
                "available, or provide --done-override-reason."
            ),
        )

    branch_exists = _tasks.subprocess.run(
        ["git", "rev-parse", "--verify", wp_branch],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if branch_exists.returncode != 0:
        return (
            False,
            (f"Cannot verify merge ancestry: branch '{wp_branch}' not found.\nEither merge and keep branch ref available, or provide --done-override-reason."),
        )

    merged_check = _tasks.subprocess.run(
        ["git", "merge-base", "--is-ancestor", wp_branch, target_branch],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if merged_check.returncode == 0:
        return True, f"Merge ancestry verified: {wp_branch} is merged into {target_branch}."

    return (
        False,
        (
            f"Merge ancestry check failed: {wp_branch} is not merged into {target_branch}.\n"
            f"Merge first, or provide --done-override-reason to record a conscious exception."
        ),
    )


def _filter_by_planning_tip_content(
    worktree_path: Path, candidates: list[str], base_branch: str
) -> list[str]:
    """Drop candidates byte-identical to the planning-branch tip (FR-007 / #2274).

    Runs ``git diff <planning_tip> HEAD -- <path>`` for each candidate.  An
    empty diff means the file is byte-identical to the planning tip (e.g. after
    a planning-branch rebase that brought no content change) and must not be
    flagged as a lane-hygiene violation.  On any git failure the candidate is
    kept conservatively so the guard never silently loses signal.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks

    planning_tip_result = _tasks.subprocess.run(
        ["git", "rev-parse", base_branch],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if planning_tip_result.returncode != 0 or not planning_tip_result.stdout.strip():
        return candidates

    planning_tip = planning_tip_result.stdout.strip()
    files: list[str] = []
    for path in candidates:
        content_diff = _tasks.subprocess.run(
            ["git", "diff", planning_tip, "HEAD", "--", path],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        # Non-empty diff or git error → genuinely diverges from planning tip; keep.
        if content_diff.returncode != 0 or content_diff.stdout.strip():
            files.append(path)
    return files


def _list_wp_branch_mission_specs_changes(worktree_path: Path, base_branch: str) -> list[str]:
    """Return kitty-specs/ files genuinely diverged from the planning-branch tip.

    Uses a two-pass strategy (FR-007 / #2274):

    1. Merge-base history diff: ``git diff --name-only <merge_base>..HEAD``
       identifies candidate paths touched on the lane branch.
    2. Content re-check: ``git diff <planning_tip> HEAD -- <path>`` filters out
       any candidate whose content is byte-identical to the planning-branch tip.

    This prevents false positives after a planning-branch rebase where the lane
    branch shares only an ancient merge-base but the file content matches.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks

    merge_base_result = _tasks.subprocess.run(
        ["git", "merge-base", "HEAD", base_branch],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if merge_base_result.returncode != 0:
        return []

    merge_base = merge_base_result.stdout.strip()
    if not merge_base:
        return []

    diff_result = _tasks.subprocess.run(
        ["git", "diff", "--name-only", f"{merge_base}..HEAD", "--", f"{KITTY_SPECS_DIR}/"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if diff_result.returncode != 0:
        return []

    seen: set[str] = set()
    candidates: list[str] = []
    for raw in diff_result.stdout.splitlines():
        path = raw.strip()
        if not path or not path.startswith(f"{KITTY_SPECS_DIR}/"):
            continue
        if path in seen:
            continue
        seen.add(path)
        candidates.append(path)

    if not candidates:
        return []

    return _tasks._filter_by_planning_tip_content(worktree_path, candidates, base_branch)


def _list_wp_branch_specs_changes_for_guard(worktree_path: Path, base_branch: str) -> list[str]:
    # The dynamically-named ``_list_wp_branch_<KITTY_SPECS_DIR>_changes`` alias
    # lives in the ``tasks`` namespace (assigned there next to the seam
    # re-imports) — reading it through ``_tasks`` at call time preserves the
    # historical ``tasks._list_wp_branch_kitty_specs_changes`` patch seam.
    from specify_cli.cli.commands.agent import tasks as _tasks

    patched_or_alias = getattr(_tasks, "_list_wp_branch_" + KITTY_SPECS_DIR.replace("-", "_") + "_changes")
    changes: list[str] = patched_or_alias(worktree_path=worktree_path, base_branch=base_branch)
    return changes


def _mark_status_json_payload(results: list[TaskIdResult]) -> dict[str, object]:
    """Return the contracted mark-status --json payload."""
    summary = {
        "updated": sum(1 for result in results if result.outcome == TaskIdResolutionOutcome.UPDATED),
        "already_satisfied": sum(1 for result in results if result.outcome == TaskIdResolutionOutcome.ALREADY_SATISFIED),
        "not_found": sum(1 for result in results if result.outcome == TaskIdResolutionOutcome.NOT_FOUND),
    }
    return {
        "results": [
            {
                "id": result.id,
                "outcome": result.outcome.value,
                "format": result.format.value if result.format else None,
                "message": result.message,
            }
            for result in results
        ],
        "summary": summary,
    }
