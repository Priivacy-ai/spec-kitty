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

from specify_cli.core.commit_guard import GuardCapability
from specify_cli.git.commit_helpers import safe_commit
from kernel.paths import to_posix

UPGRADE_COMMIT_SKIP_WARNING = "Could not auto-commit upgrade changes; please review and commit manually."

DETACHED_HEAD_WARNING = (
    "Checkout is on a detached HEAD; skipped auto-committing upgrade changes — please review and commit manually."
)


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

        # With -z format, renames/copies include a second NUL-separated
        # path.  We take the *destination* (new name); the source (old name)
        # is intentionally discarded because we care about "what exists now".
        if ("R" in status or "C" in status) and i < len(entries) and entries[i]:
            path = entries[i]
            i += 1

        normalized = to_posix(path.strip())
        if normalized.startswith("./"):
            normalized = normalized[2:]

        if normalized:
            paths.add(normalized)

    return paths


def is_upgrade_commit_eligible(path: str, checkout: Path) -> bool:
    """Return True when a changed file should be included in upgrade auto-commit."""
    normalized = to_posix(path.strip())
    if not normalized:
        return False

    # Ignore paths that are outside the repo and root-level files — except
    # .gitignore: the gitignore-backfill migrations write it, and leaving it
    # dirty is exactly the merge-blocking churn #2385 reports.
    if normalized.startswith("../"):
        return False
    if "/" not in normalized and normalized != ".gitignore":
        return False

    # Never auto-commit ~/.kittify when users run inside their home directory.
    return not (checkout.resolve() == Path.home().resolve() and normalized.startswith(".kittify/"))


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
        destination_ref = "main"

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
