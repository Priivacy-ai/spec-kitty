"""Lane-based merge operations.

Two-tier merge flow:
1. Lane → Mission: merge a lane branch into the mission integration branch.
2. Mission → Target: merge the mission branch into the target (e.g. main).

Both operations use temporary merge workspaces and the stale-lane
blocker to prevent overlapping file conflicts.

Strategy note (FR-006, FR-007):
- Lane→mission always uses merge commits (no-ff) regardless of strategy.
- Mission→target honors the ``strategy`` parameter (default: SQUASH).
"""

from __future__ import annotations

from mission_runtime import MissionArtifactKind
from specify_cli.missions._read_path_resolver import resolve_planning_read_dir
import os
import subprocess
import sys
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from specify_cli.coordination.coherence import is_toolchain_generated_churn
from specify_cli.git.ref_advance import advance_branch_ref
from specify_cli.lanes._git import branch_exists as _shared_branch_exists
from specify_cli.lanes.branch_naming import lane_branch_name, worktree_path as _worktree_path
from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.persistence import read_lanes_json
from specify_cli.lanes.stale_check import StaleCheckResult, check_lane_staleness
from specify_cli.merge.config import MergeStrategy


@dataclass(frozen=True)
class _MergeDriverSpec:
    """One custom git merge driver: config identity + ``.gitattributes`` mapping.

    ``config_key`` is the ``merge.<key>.*`` git-config namespace; ``pattern`` /
    ``target`` compose the ``<pattern> merge=<config_key>`` attributes line that
    routes matching paths to this driver (C-006).
    """

    config_key: str
    name: str
    command: str
    pattern: str

    @property
    def attributes_line(self) -> str:
        return f"{self.pattern} merge={self.config_key}"


# C-006: the canonical merge-driver registry. Every both-sides-divergent
# ``kitty-specs/**`` bookkeeping artifact that must reconcile (not clobber) under
# ``git merge --squash -X theirs`` carries a driver here. Generalized from the
# single event-log driver (DIRECTIVE_044 — parametrized, not cloned).
_MERGE_DRIVERS: tuple[_MergeDriverSpec, ...] = (
    _MergeDriverSpec(
        config_key="spec-kitty-event-log",
        name="Spec Kitty event log union merge",
        command="spec-kitty merge-driver-event-log %O %A %B",
        pattern="kitty-specs/**/status.events.jsonl",
    ),
    _MergeDriverSpec(
        config_key="spec-kitty-meta",
        name="Spec Kitty mission meta field merge",
        command="spec-kitty merge-driver-meta %O %A %B",
        pattern="kitty-specs/**/meta.json",
    ),
    _MergeDriverSpec(
        config_key="spec-kitty-traces",
        name="Spec Kitty mission traces union merge",
        command="spec-kitty merge-driver-traces %O %A %B",
        pattern="kitty-specs/**/traces/*.md",
    ),
)


@dataclass
class LaneMergeResult:
    """Outcome of a lane merge operation."""

    success: bool
    lane_id: str
    merged_into: str
    errors: list[str] = field(default_factory=list)
    stale_check: StaleCheckResult | None = None


@dataclass
class MissionMergeResult:
    """Outcome of a mission-to-target merge."""

    success: bool
    mission_branch: str
    target_branch: str
    commit: str | None = None
    already_applied: bool = False
    errors: list[str] = field(default_factory=list)


def _resolve_lane_manifest(
    repo_root: Path,
    mission_slug: str,
    lanes_manifest: LanesManifest | None,
) -> LanesManifest | None:
    """Return the provided manifest or load it from disk."""
    if lanes_manifest is not None:
        return lanes_manifest
    # FR-001 (#2185): ``lanes.json`` is LANE_STATE (PRIMARY-partition) — it lives
    # ONLY on the PRIMARY checkout post-#2106. The coord-aware resolver lands on
    # the STATUS-only ``-coord`` husk (no lanes.json), so route by kind.
    feature_dir = resolve_planning_read_dir(
        repo_root, mission_slug, kind=MissionArtifactKind.LANE_STATE
    )
    return read_lanes_json(feature_dir)


def _try_auto_rebase_if_stale(
    stale: StaleCheckResult,
    lane: ExecutionLane,
    branch: str,
    mission_branch: str,
    mission_slug: str,
    repo_root: Path,
) -> StaleCheckResult:
    """If the lane is stale and a worktree exists, attempt auto-rebase and recheck."""
    if not stale.is_stale:
        return stale
    worktree_path = _worktree_path(
        repo_root, mission_slug, mission_id=None, lane_id=lane.lane_id
    )
    if not worktree_path.exists():
        return stale
    from specify_cli.lanes.auto_rebase import attempt_auto_rebase

    report = attempt_auto_rebase(
        lane, branch, mission_branch, repo_root, worktree_path
    )
    if report.succeeded:
        return check_lane_staleness(lane, branch, mission_branch, repo_root)
    return stale


def consolidate_lane_into_mission(
    repo_root: Path,
    mission_slug: str,
    lane_id: str,
    lanes_manifest: LanesManifest | None = None,
) -> LaneMergeResult:
    """Consolidate a lane branch into the mission integration branch.

    This is the *lane-consolidation* merge (one of a mission's several lane
    branches folded into the single mission branch) -- distinct from
    :func:`integrate_mission_into_target`, which performs the later
    *branch-integration* merge of the whole mission branch into the target
    (Primary) branch. Naming these two merge steps apart removes the
    overloaded bare "merge" ambiguity (FR-003/FR-008).

    Performs stale-lane check before merging. If the lane is stale
    (overlapping files changed in mission), the merge is blocked.

    Args:
        repo_root: Repository root.
        mission_slug: Feature slug.
        lane_id: Lane to merge (e.g., "lane-a").
        lanes_manifest: Pre-loaded manifest (loaded from disk if None).

    Returns:
        LaneMergeResult with success/error status.
    """
    lanes_manifest = _resolve_lane_manifest(repo_root, mission_slug, lanes_manifest)
    if lanes_manifest is None:
        return LaneMergeResult(
            success=False, lane_id=lane_id, merged_into="",
            errors=["No lanes.json found for this feature"],
        )

    lane = next(
        (c for c in lanes_manifest.lanes if c.lane_id == lane_id),
        None,
    )
    if lane is None:
        return LaneMergeResult(
            success=False, lane_id=lane_id, merged_into="",
            errors=[f"Lane {lane_id} not found in lanes.json"],
        )

    branch = lane_branch_name(
        mission_slug,
        lane_id,
        planning_base_branch=lanes_manifest.target_branch,
    )
    mission_branch = lanes_manifest.mission_branch

    if not _branch_exists(repo_root, branch):
        return LaneMergeResult(
            success=False, lane_id=lane_id, merged_into=mission_branch,
            errors=[f"Lane branch {branch} does not exist"],
        )

    stale = check_lane_staleness(lane, branch, mission_branch, repo_root)
    stale = _try_auto_rebase_if_stale(
        stale, lane, branch, mission_branch, mission_slug, repo_root,
    )
    if stale.is_stale:
        return LaneMergeResult(
            success=False, lane_id=lane_id, merged_into=mission_branch,
            errors=[
                f"Lane {lane_id} is stale: overlapping files {stale.stale_files}. "
                f"{stale.remediation}"
            ],
            stale_check=stale,
        )

    try:
        _merge_branch_into(repo_root, branch, mission_branch)
    except RuntimeError as e:
        return LaneMergeResult(
            success=False, lane_id=lane_id, merged_into=mission_branch,
            errors=[str(e)],
        )

    return LaneMergeResult(
        success=True, lane_id=lane_id, merged_into=mission_branch,
    )


def integrate_mission_into_target(
    repo_root: Path,
    mission_slug: str,
    lanes_manifest: LanesManifest | None = None,
    *,
    strategy: MergeStrategy = MergeStrategy.SQUASH,
    allow_already_applied: bool = False,
) -> MissionMergeResult:
    """Integrate the mission branch into the target (Primary) branch.

    This is the *branch-integration* merge -- the final step of a mission,
    folding the single mission integration branch into the repository's
    target/Primary branch (e.g. ``main``). It is distinct from
    :func:`consolidate_lane_into_mission`, the earlier *lane-consolidation*
    merge that folds individual lane branches into the mission branch; keeping
    the two named apart removes the overloaded bare "merge" ambiguity
    (FR-003/FR-008).

    Only the mission branch may integrate into the target branch.

    Args:
        repo_root: Repository root.
        mission_slug: Feature slug.
        lanes_manifest: Pre-loaded manifest (loaded from disk if None).
        strategy: Merge strategy for the mission→target step (FR-006/T010).
            Defaults to SQUASH. Lane→mission is NOT affected by this parameter.

    Returns:
        MissionMergeResult with success/error status.
    """
    if lanes_manifest is None:
        # FR-001 (#2185): LANE_STATE read — PRIMARY-partition (see above).
        feature_dir = resolve_planning_read_dir(
            repo_root, mission_slug, kind=MissionArtifactKind.LANE_STATE
        )
        lanes_manifest = read_lanes_json(feature_dir)
        if lanes_manifest is None:
            return MissionMergeResult(
                success=False, mission_branch="", target_branch="",
                errors=["No lanes.json found for this feature"],
            )

    mission_branch = lanes_manifest.mission_branch
    target_branch = lanes_manifest.target_branch

    if not _branch_exists(repo_root, mission_branch):
        return MissionMergeResult(
            success=False, mission_branch=mission_branch,
            target_branch=target_branch,
            errors=[f"Mission branch {mission_branch} does not exist"],
        )

    try:
        # T010: honor strategy for mission→target only; lane→mission is not touched
        changed = _merge_branch_into(
            repo_root,
            mission_branch,
            target_branch,
            strategy=strategy,
            allow_noop_squash=allow_already_applied,
        )
    except RuntimeError as e:
        return MissionMergeResult(
            success=False, mission_branch=mission_branch,
            target_branch=target_branch, errors=[str(e)],
        )

    # Get the merge commit.
    commit = _rev_parse(repo_root, target_branch) if changed else None

    return MissionMergeResult(
        success=True,
        mission_branch=mission_branch,
        target_branch=target_branch,
        commit=commit,
        already_applied=not changed,
    )


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _branch_exists(repo_root: Path, branch: str) -> bool:
    # Routes the existence check through the shared lanes/_git helper while
    # preserving the merge pipeline's single env authority (_make_merge_env);
    # the env composes through rather than forking the helper (#1904).
    return bool(_shared_branch_exists(repo_root, branch, env=_make_merge_env()))


def _git_config_get(repo_root: Path, key: str) -> str | None:
    """Return a local git config value or ``None`` when unset/unreadable."""
    result = subprocess.run(
        ["git", "config", "--local", "--get", key],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        env=_make_merge_env(),
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _git_common_dir(repo_root: Path) -> Path | None:
    """Return the repository's shared git common dir (worktree-safe)."""
    result = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        env=_make_merge_env(),
    )
    if result.returncode != 0:
        return None
    raw = Path(result.stdout.strip())
    return raw if raw.is_absolute() else (repo_root / raw)


def _set_local_git_config(repo_root: Path, key: str, value: str) -> None:
    """Set a local git-config *key* to *value* when it is not already current."""
    if _git_config_get(repo_root, key) == value:
        return
    subprocess.run(
        ["git", "config", "--local", key, value],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
        env=_make_merge_env(),
    )


def _ensure_info_attributes(repo_root: Path) -> list[str]:
    """Map the driver patterns in the shared ``.git/info/attributes``.

    The ephemeral merge worktree (``_merge_branch_into``) checks out the target
    branch tip, which need not carry a committed ``.gitattributes`` (fresh repos,
    test fixtures). ``$GIT_COMMON_DIR/info/attributes`` applies to every linked
    worktree, so seeding the driver patterns there makes the custom drivers fire
    under ``git merge --squash -X theirs`` regardless of what a branch committed.
    Additive and idempotent: operator lines are preserved; missing lines appended.

    Returns the attribute lines it newly appended (``[]`` when everything was
    already present), so the caller can tear down *exactly* its own seeding —
    see :func:`_remove_info_attributes` / :func:`_ephemeral_merge_driver_activation`.
    """
    common_dir = _git_common_dir(repo_root)
    if common_dir is None:
        return []
    info_dir = common_dir / "info"
    attributes_path = info_dir / "attributes"
    existing = (
        attributes_path.read_text(encoding="utf-8").splitlines()
        if attributes_path.exists()
        else []
    )
    missing = [
        spec.attributes_line
        for spec in _MERGE_DRIVERS
        if spec.attributes_line not in existing
    ]
    if not missing:
        return []
    info_dir.mkdir(parents=True, exist_ok=True)
    attributes_path.write_text(
        "\n".join([*existing, *missing]).rstrip("\n") + "\n", encoding="utf-8"
    )
    return missing


def _remove_info_attributes(repo_root: Path, added_lines: list[str]) -> None:
    """Tear down the driver attribute lines :func:`_ensure_info_attributes` seeded.

    Removes *only* ``added_lines`` from ``$GIT_COMMON_DIR/info/attributes``,
    leaving any pre-existing operator lines untouched. If the file is left empty
    (we seeded it into an otherwise-absent file), it is unlinked so the repo is
    restored to its prior state. Idempotent: an empty ``added_lines`` or a
    missing file is a no-op.

    This is the load-bearing half of the #2709/#2711 split: the git-config driver
    *definitions* persist (intended, inert without an attribute mapping), but the
    ``info/attributes`` *activation* is repo-global across worktrees and MUST NOT
    outlive the ephemeral squash merge — otherwise a later ``auto_rebase`` in the
    same repo finds the git driver pre-activated and resolves
    ``status.events.jsonl`` via ``spec-kitty merge-driver-event-log`` on PATH
    before its in-process ``R-STATUS-EVENTS-JSONL-UNION`` classifier can run.
    """
    if not added_lines:
        return
    common_dir = _git_common_dir(repo_root)
    if common_dir is None:
        return
    attributes_path = common_dir / "info" / "attributes"
    if not attributes_path.exists():
        return
    remaining = [
        line
        for line in attributes_path.read_text(encoding="utf-8").splitlines()
        if line not in added_lines
    ]
    if remaining:
        attributes_path.write_text(
            "\n".join(remaining).rstrip("\n") + "\n", encoding="utf-8"
        )
    else:
        attributes_path.unlink()


def _ensure_merge_driver_git_config(repo_root: Path) -> None:
    """Ensure every custom merge driver's git-*config* is present (no attributes).

    Sets the ``merge.<key>.name`` / ``merge.<key>.driver`` git-config for the
    whole :data:`_MERGE_DRIVERS` registry (event-log union, ``meta.json`` field
    merge, ``traces/*.md`` union) so the drivers are *defined*. ``spec-kitty
    init`` may run before the project becomes a git repository, so the upgrade
    migration cannot always install the local merge-driver config at init time;
    the merge path self-heals that gap here (C-006 / DIRECTIVE_044).

    It deliberately does **not** seed ``.git/info/attributes``: defining a driver
    is inert until an attribute maps a path to it. This is the entry point the
    stale-lane auto-rebase pipeline uses. Auto-rebase owns its own in-process
    event-log union classifier (``R-STATUS-EVENTS-JSONL-UNION``) as the fallback
    for repos that have not committed a ``.gitattributes`` mapping; pre-seeding
    ``.git/info/attributes`` here would pre-activate the git driver and silently
    pre-empt that fallback (the #2709/#2711 regression), coupling auto-rebase to
    the external ``spec-kitty merge-driver-*`` subcommands being on PATH.
    """
    if not (repo_root / ".git").exists():
        return

    for spec in _MERGE_DRIVERS:
        _set_local_git_config(repo_root, f"merge.{spec.config_key}.name", spec.name)
        _set_local_git_config(repo_root, f"merge.{spec.config_key}.driver", spec.command)


@contextmanager
def _ephemeral_merge_driver_activation(repo_root: Path) -> Iterator[None]:
    """Activate the custom drivers for ONE ephemeral merge, then tear the seeding down.

    Used by the squash mission→target merge (``_merge_branch_into``): its
    ephemeral merge worktree checks out the target-branch tip, which need not
    carry a committed ``.gitattributes`` (fresh repos, test fixtures), so the
    driver patterns must be seeded into ``$GIT_COMMON_DIR/info/attributes`` for
    the custom drivers to fire under ``git merge --squash -X theirs`` (C-006 /
    DIRECTIVE_044).

    Seeding happens *before* the merge (so the drivers fire during it) and is
    torn down *after* (so it does not persist). Only the ``info/attributes``
    activation is ephemeral — the git-config driver *definitions*
    (:func:`_ensure_merge_driver_git_config`) and the committed ``.gitattributes``
    remain, since they are the intended persistent surface and are inert without
    an active attribute mapping. Distinct from :func:`_ensure_merge_driver_git_config`,
    which only *defines* the drivers without activating them — see that docstring
    for why auto-rebase must not seed attributes, and :func:`_remove_info_attributes`
    for why leaving this seeding in place re-couples auto-rebase to the external
    ``spec-kitty merge-driver-*`` subcommands (the #2709/#2711 regression).
    """
    if not (repo_root / ".git").exists():
        yield
        return

    _ensure_merge_driver_git_config(repo_root)
    added = _ensure_info_attributes(repo_root)
    try:
        yield
    finally:
        _remove_info_attributes(repo_root, added)


def _make_merge_env() -> dict[str, str]:
    """Single environment authority for the lane-merge pipeline (AC-F1).

    Prepends the current venv's bin directory to PATH so that git's merge
    driver invocation of ``spec-kitty merge-driver-event-log`` resolves to the
    same spec-kitty binary that is currently running, not a stale global one.

    Every subprocess invocation in this module routes its ``env`` through
    this helper — no inline ``os.environ`` copies with ad-hoc PATH/GIT_*
    mutations (FR-008b; ratchet in
    ``tests/architectural/test_merge_pipeline_ratchets.py``).
    """
    venv_bin = str(Path(sys.executable).parent)
    env = os.environ.copy()
    env["PATH"] = venv_bin + os.pathsep + env.get("PATH", "")
    return env


def _rev_parse(repo_root: Path, ref: str) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", ref],
        cwd=str(repo_root), capture_output=True, text=True, env=_make_merge_env(),
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _merge_branch_into(
    repo_root: Path,
    source_branch: str,
    target_branch: str,
    *,
    strategy: MergeStrategy = MergeStrategy.MERGE,
    allow_noop_squash: bool = False,
) -> bool:
    """Merge source_branch into target_branch using a temporary worktree.

    Creates a detached worktree at the target branch tip, merges source
    into it using the specified strategy, then fast-forwards the target branch
    ref to the result. The main repo's checkout is never changed.

    Uses --detach to avoid "branch already checked out" errors when
    target_branch is the currently checked-out branch.

    Strategy behavior:
    - MERGE (default for lane→mission): ``git merge --no-ff``  — preserves structure
    - SQUASH: ``git merge --squash`` + explicit commit
    - REBASE: ``git rebase`` then fast-forward

    Raises RuntimeError on merge failure (including conflicts).
    """
    import tempfile

    tmp_dir = tempfile.mkdtemp(prefix="kitty-merge-")
    tmp_path = Path(tmp_dir)

    # Single environment authority for the lane-merge pipeline (AC-F1).
    _env = _make_merge_env()

    # Seed the custom-driver ``info/attributes`` activation for the duration of
    # this ephemeral merge only, and remove the merge worktree on exit. The
    # activation is torn down when the ``with`` block closes (LIFO: worktree
    # removed first, then ``info/attributes`` restored) so it never persists into
    # a later ``auto_rebase`` (#2709/#2711 — see _ephemeral_merge_driver_activation).
    with ExitStack() as _stack:
        _stack.enter_context(_ephemeral_merge_driver_activation(repo_root))
        _stack.callback(
            lambda: subprocess.run(
                ["git", "worktree", "remove", str(tmp_path), "--force"],
                cwd=str(repo_root), capture_output=True, env=_env,
            )
        )

        # Create detached worktree at target branch tip.
        result = subprocess.run(
            ["git", "worktree", "add", "--detach", str(tmp_path), target_branch],
            cwd=str(repo_root), capture_output=True, text=True, env=_env,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to create merge worktree: {result.stderr.strip()}"
            )

        if strategy == MergeStrategy.SQUASH:
            # Squash all commits from source into a single new commit.
            # -X theirs: when the mission branch (source) conflicts with the
            # target on kitty-specs/ planning artifacts, the mission branch
            # version is authoritative (it carries the reviewed, finalized state).
            result = subprocess.run(
                ["git", "merge", "--squash", "-X", "theirs", source_branch],
                cwd=str(tmp_path), capture_output=True, text=True, env=_env,
            )
            if result.returncode != 0:
                subprocess.run(
                    ["git", "merge", "--abort"],
                    cwd=str(tmp_path), capture_output=True, env=_env,
                )
                raise RuntimeError(
                    f"Squash merge of {source_branch} into {target_branch} failed: "
                    f"{result.stderr.strip() or result.stdout.strip()}"
                )
            # Squash merges do not record ancestry. On retry after a previous
            # successful squash, Git reports a clean index and a plain commit
            # would fail in this detached worktree with "Not currently on any
            # branch." Only explicit resume callers may treat that as
            # idempotent success; ordinary callers need a real merge result.
            staged = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=str(tmp_path), capture_output=True, text=True, env=_env,
            )
            if staged.returncode == 0:
                if allow_noop_squash:
                    return False
                raise RuntimeError(
                    f"Squash merge of {source_branch} into {target_branch} "
                    "produced no changes; target may already contain this tree. "
                    "Retry with merge resume if recovering an interrupted merge."
                )
            if staged.returncode not in (0, 1):
                raise RuntimeError(
                    f"Could not inspect squash merge result for {source_branch} "
                    f"into {target_branch}: {staged.stderr.strip()}"
                )
            # Commit the squashed result.
            result = subprocess.run(
                [
                    "git", "-c", "commit.gpgsign=false",
                    "commit", "-m",
                    f"feat({source_branch}): squash merge of mission",
                ],
                cwd=str(tmp_path), capture_output=True, text=True, env=_env,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Squash commit into {target_branch} failed: "
                    f"{result.stderr.strip() or result.stdout.strip()}"
                )
        elif strategy == MergeStrategy.REBASE:
            # Rebase source onto target in the isolated worktree, then
            # fast-forward target to the rebased detached HEAD. Do not check
            # out or rewrite source_branch in the user's main checkout.
            result = subprocess.run(
                ["git", "checkout", "--detach", source_branch],
                cwd=str(tmp_path), capture_output=True, text=True, env=_env,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Failed to check out {source_branch} in merge worktree: "
                    f"{result.stderr.strip() or result.stdout.strip()}"
                )
            # Rebase source on top of target.
            result = subprocess.run(
                ["git", "rebase", target_branch],
                cwd=str(tmp_path), capture_output=True, text=True, env=_env,
            )
            if result.returncode != 0:
                subprocess.run(
                    ["git", "rebase", "--abort"],
                    cwd=str(tmp_path), capture_output=True, env=_env,
                )
                raise RuntimeError(
                    f"Rebase of {source_branch} onto {target_branch} failed: "
                    f"{result.stderr.strip() or result.stdout.strip()}"
                )
            # Get the rebased HEAD SHA.
            rebased_sha = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(tmp_path), capture_output=True, text=True, check=True, env=_env,
            ).stdout.strip()
            # Fast-forward the target branch to the rebased tip, resyncing any
            # worktree that has target_branch checked out (#1826 / AC-B2).
            # Coordination status residue is excluded from the dirty gate via
            # the single residue authority (FR-012 / #1878).
            advance_branch_ref(
                repo_root,
                target_branch,
                rebased_sha,
                env=_env,
                is_residue=is_toolchain_generated_churn,
            )
            return True  # early return — ref already updated
        else:
            # MERGE strategy (default for lane→mission): no-ff merge commit.
            result = subprocess.run(
                ["git", "merge", source_branch, "--no-edit",
                 "-m", f"Merge {source_branch} into {target_branch}"],
                cwd=str(tmp_path), capture_output=True, text=True, env=_env,
            )
            if result.returncode != 0:
                subprocess.run(
                    ["git", "merge", "--abort"],
                    cwd=str(tmp_path), capture_output=True, env=_env,
                )
                raise RuntimeError(
                    f"Merge of {source_branch} into {target_branch} failed: "
                    f"{result.stderr.strip() or result.stdout.strip()}"
                )

        # Get the resulting commit SHA.
        merge_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(tmp_path), capture_output=True, text=True, check=True, env=_env,
        ).stdout.strip()

        # Update the target branch ref to point to the merge commit, resyncing
        # any worktree that has target_branch checked out (#1826 / AC-B2).
        # Coordination status residue is excluded from the dirty gate via the
        # single residue authority (FR-012 / #1878).
        advance_branch_ref(
            repo_root,
            target_branch,
            merge_commit,
            env=_env,
            is_residue=is_toolchain_generated_churn,
        )
        return True
