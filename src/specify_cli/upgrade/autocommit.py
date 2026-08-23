"""Canonical per-checkout auto-commit for ``spec-kitty upgrade`` (#2392).

One routine, applied uniformly to every checkout an upgrade run touches —
the main checkout and each live ``.worktrees/*`` (coordination + lane) —
so upgrade/migration churn always lands as a commit instead of dirtying the
tree and tripping the ``spec-kitty merge`` worktree-dirty guard
(#1826/NFR-002) later.

The invariant (epic #2392): every path an upgrade run writes or migrates,
in every checkout it touches, must end in exactly one auto-commit — with
the commit-set derived from that checkout's real ``git status --porcelain``
diff against a pre-write baseline, never a hardcoded file list (#2105).
The baseline diff also guarantees pre-existing uncommitted work in a
checkout (e.g. in-flight WP edits in a lane worktree) is never swept into
an upgrade commit.

Callers:

* ``specify_cli.cli.commands.upgrade`` — the main checkout (both the
  no-migrations and the migrations paths).
* ``specify_cli.upgrade.runner.MigrationRunner._upgrade_worktrees`` — each
  sibling worktree, right after that worktree's migration/metadata writes
  (#2385).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from mission_runtime import CommitTarget

from specify_cli.core.agent_config import get_auto_commit_default
from specify_cli.core.commit_guard import GuardCapability
from specify_cli.git.commit_helpers import safe_commit
from kernel.paths import to_posix

UPGRADE_COMMIT_SKIP_WARNING = "Could not auto-commit upgrade changes; please review and commit manually."

DETACHED_HEAD_WARNING = (
    "Checkout is on a detached HEAD; skipped auto-committing upgrade changes — please review and commit manually."
)

BRANCH_DETECTION_FAILED_WARNING = (
    "Could not determine the current branch; skipped auto-committing upgrade changes — "
    "please review and commit manually."
)


def should_auto_commit(repo_root: Path, *, dry_run: bool, manual_review: bool) -> bool:
    """Decide whether the **main** checkout should auto-commit upgrade churn.

    The sole gate consulted by the main-checkout commit path (C2, FR-003/
    FR-004): dry-run and manual-review (preserved-customized-files) always
    suppress the commit; otherwise the decision defers to the project's
    configured ``auto_commit`` default. Deliberately does not read or
    duplicate the ``$HOME`` eligibility guard in
    :func:`is_upgrade_commit_eligible` (C-001, D-7) — that stays where it is.
    """
    if dry_run or manual_review:
        return False
    return bool(get_auto_commit_default(repo_root))


def should_auto_commit_for_worktree(repo_root: Path, *, dry_run: bool) -> bool:
    """Decide whether the **worktree fan-out** should auto-commit upgrade churn.

    Deliberately excludes the main checkout's ``manual_review`` signal (D-10):
    manual review is evaluated *per worktree* by the runner's own
    ``worktree_manual_review`` gate, so folding the main checkout's
    manual-review state into this decision would wrongly suppress every
    worktree commit — an NFR-002 breach of observable (e).
    """
    if dry_run:
        return False
    return bool(get_auto_commit_default(repo_root))


def git_status_paths(repo_path: Path) -> set[str] | None:
    """Return git status paths for *repo_path* using porcelain -z output.

    Returns ``None`` when ``git status`` fails (e.g. not a git repo) so
    callers can distinguish "no dirty files" from "unable to determine".
    """
    result = subprocess.run(
        ["git", "status", "--porcelain", "-z"],
        cwd=repo_path,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None

    entries = result.stdout.decode("utf-8", errors="replace").split("\0")
    paths: set[str] = set()

    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if not entry or len(entry) < 4:
            continue

        status = entry[:2]
        path = entry[3:]

        # With -z format, renames/copies report the *destination* (new name)
        # first — it is already in ``path`` — followed by a second
        # NUL-separated entry holding the *source* (old name). Consume and
        # discard the source because we care about "what exists now"; taking
        # it instead would stage a path that no longer exists (#2492).
        if ("R" in status or "C" in status) and i < len(entries) and entries[i]:
            i += 1

        normalized = to_posix(path.strip())
        if normalized.startswith("./"):
            normalized = normalized[2:]

        if normalized:
            paths.add(normalized)

    return paths


def is_upgrade_commit_eligible(path: str, checkout: Path) -> bool:
    """Return True when a changed file should be included in upgrade auto-commit.

    Ownership of a path is decided by the pre-run **baseline** in
    :func:`prepare_upgrade_commit_files` — anything already dirty before the
    run is never swept — not by where the path sits in the tree. A file that
    was clean at baseline and is dirty after the run was written by the run,
    and the #2392 invariant says every such write must land in the one
    auto-commit. That includes root-level files: the gitignore-backfill
    migrations (``.gitignore``, #2385), the merge-driver/diff-attribute
    migrations (``.gitattributes``), ``m_3_2_8_provision_kitty_env``
    (``.claudeignore``) and the root-level session-presence surfaces
    (``AGENTS.md``/``GEMINI.md``, auto-created by surface repair before the
    churn commit, #2491) all write at the root. An earlier depth-based
    rule ("no ``/`` in the path → operator-owned, skip") plus a hand-kept
    allowlist of exceptions drifted four times in six months and left those
    files dirty after every upgrade — and, for ``.gitattributes`` in
    worktrees, tripped the ``spec-kitty merge`` dirty guard (#2492
    follow-up). The baseline is the only ownership signal that is not a
    hardcoded file list (#2105), so it is the one we rely on.

    Two guards stay, both about *where the checkout is*, not the path depth:

    * paths outside the checkout (``../``) are never committed;
    * when the checkout **is** ``$HOME`` (the #3652 hazard — a home
      directory that self-qualifies as a project), neither ``~/.kittify``
      nor any root-level file is committed: root files there are the
      operator's dotfiles, never ours.
    """
    normalized = to_posix(path.strip())
    if not normalized:
        return False

    if normalized.startswith("../"):
        return False

    # Never auto-commit ~/.kittify or root-level dotfiles/files when users
    # run inside their home directory.
    if checkout.resolve() == Path.home().resolve():
        return not (normalized.startswith(".kittify/") or "/" not in normalized)

    return True


def expand_upgrade_commit_path(checkout: Path, relative_path: str) -> list[Path]:
    """Expand a changed path into the concrete file paths git will stage.

    ``git status --porcelain -z`` may report untracked directories as a single
    path (for example ``.agents/skills/new-skill``). ``git add <dir>`` stages
    the files inside that directory, but ``safe_commit``'s backstop compares the
    staged file paths against the requested path list. Expand directories here
    so the expected set matches what git will actually stage.
    """
    normalized = to_posix(relative_path.strip())
    absolute_path = checkout / normalized

    if absolute_path.exists() and absolute_path.is_dir() and not absolute_path.is_symlink():
        return sorted(child.relative_to(checkout) for child in absolute_path.rglob("*") if not child.is_dir())

    return [Path(normalized)]


def prepare_upgrade_commit_files(
    checkout: Path,
    baseline_paths: set[str] | None,
) -> list[Path]:
    """Collect newly changed checkout files after an upgrade run.

    Returns an empty list when *baseline_paths* is ``None`` (git status
    failed at baseline time) to avoid accidentally committing unrelated work.
    """
    if baseline_paths is None:
        return []

    current_paths = git_status_paths(checkout)
    if current_paths is None:
        return []

    new_paths = sorted(path for path in current_paths if path not in baseline_paths and is_upgrade_commit_eligible(path, checkout))
    files_to_commit: list[Path] = []
    seen_paths: set[str] = set()
    for path in new_paths:
        for expanded_path in expand_upgrade_commit_path(checkout, path):
            normalized = to_posix(expanded_path)
            if normalized in seen_paths:
                continue
            seen_paths.add(normalized)
            files_to_commit.append(Path(normalized))
    return files_to_commit


def commit_touched_checkout(
    checkout: Path,
    baseline_paths: set[str] | None,
    from_version: str,
    to_version: str,
) -> tuple[bool, list[str], str | None]:
    """Auto-commit the upgrade churn a run introduced in *checkout*.

    The commit-set is the porcelain diff against *baseline_paths* (captured
    before any upgrade write to this checkout), filtered through the
    eligibility rules — never a hardcoded list (#2105). Works identically for
    the main checkout and for coord/lane worktrees (#2385): the commit lands
    on whatever branch the checkout has checked out.

    Returns ``(committed, paths, warning)``.
    """
    files_to_commit = prepare_upgrade_commit_files(checkout, baseline_paths)
    if not files_to_commit:
        return False, [], None

    commit_message = f"chore: apply spec-kitty upgrade changes ({from_version} -> {to_version})"
    committed_paths = [to_posix(path) for path in files_to_commit]
    try:
        destination_ref = subprocess.check_output(
            ["git", "-C", str(checkout), "branch", "--show-current"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        # Branch detection genuinely failed (git error, missing binary, ...).
        # Never fabricate "main" here (FR-013/C7) — that risks landing upgrade
        # churn on a branch the checkout was never actually on. Skip with a
        # warning, same shape as the detached-HEAD path below.
        return False, committed_paths, BRANCH_DETECTION_FAILED_WARNING

    if not destination_ref:
        # Detached HEAD (or bare checkout): there is no branch to land the
        # bookkeeping commit on. Never guess a ref here — committing upgrade
        # churn onto the wrong branch is worse than leaving it for review.
        return False, committed_paths, DETACHED_HEAD_WARNING

    # The upgrade flow runs outside any mission, so there is no coordination
    # split to reconcile: the current branch is landing == coordination ==
    # target. Construct a ref-only CommitTarget (C-007) for it and assert the
    # upgrade bookkeeping capability explicitly (T009 / FR-008). The old reliance
    # on the "chore: apply spec-kitty upgrade changes" message-prefix exception is
    # now irrelevant — the message is just a message; the capability carries the
    # authorization to land on a protected branch (e.g. the operator's main).
    upgrade_target = CommitTarget(ref=destination_ref)

    try:
        safe_commit(
            repo_root=checkout,
            worktree_root=checkout,
            target=upgrade_target,
            message=commit_message,
            paths=tuple(files_to_commit),
            capability=GuardCapability.UPGRADE_BOOKKEEPING,
        )
    except Exception:
        return (
            False,
            committed_paths,
            UPGRADE_COMMIT_SKIP_WARNING,
        )

    return True, committed_paths, None
