"""Doctor check for workspace husks (#1833, FR-007).

A "husk" is an entry under ``.worktrees/`` that lacks a ``.git`` entry, so it
is not a usable git worktree: git commands run inside it silently walk up to
the primary repository. Once the fall-through-is-failure guards (Class D)
land, pre-existing husks start producing structured resolution errors — this
check makes operator recovery a single command:

    spec-kitty doctor workspaces        # report
    spec-kitty doctor workspaces --fix  # remove unregistered husks

Deletion safety (R5): ``--fix`` removes ONLY husks that are NOT registered in
``git worktree list``. A registered-but-broken worktree (e.g. its ``.git``
file was deleted) is never removed automatically; it is reported for manual
``git worktree repair`` / ``git worktree remove``.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "HuskEntry",
    "HuskFixResult",
    "HuskReport",
    "fix_workspace_husks",
    "scan_workspace_husks",
]

WORKTREES_DIRNAME = ".worktrees"


@dataclass(frozen=True)
class HuskEntry:
    """One ``.worktrees/`` entry that lacks a ``.git`` entry."""

    path: str  # relative to repo root
    registered: bool  # True when `git worktree list` still registers the path


@dataclass(frozen=True)
class HuskReport:
    """Scan result for the workspace husk check."""

    worktrees_dir: str
    husks: list[HuskEntry] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        return not self.husks

    def to_dict(self) -> dict[str, object]:
        return {
            "worktrees_dir": self.worktrees_dir,
            "healthy": self.healthy,
            "husks": [
                {"path": entry.path, "registered": entry.registered}
                for entry in self.husks
            ],
        }


@dataclass(frozen=True)
class HuskFixResult:
    """Outcome of ``--fix``: what was removed and what was preserved."""

    removed: list[str] = field(default_factory=list)
    skipped_registered: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "removed": list(self.removed),
            "skipped_registered": list(self.skipped_registered),
        }


def _registered_worktree_paths(repo_root: Path) -> set[Path]:
    """Return resolved paths registered in ``git worktree list --porcelain``."""
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    registered: set[Path] = set()
    if result.returncode != 0:
        return registered
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            raw = line[len("worktree "):].strip()
            try:
                registered.add(Path(raw).resolve())
            except OSError:
                continue
    return registered


def scan_workspace_husks(repo_root: Path) -> HuskReport:
    """List ``.worktrees/*`` directories lacking a ``.git`` entry.

    Each husk is annotated with whether ``git worktree list`` still registers
    it (registered husks need manual ``git worktree repair``/``remove``).
    """
    worktrees_dir = repo_root / WORKTREES_DIRNAME
    report = HuskReport(worktrees_dir=str(worktrees_dir))
    if not worktrees_dir.is_dir():
        return report

    registered = _registered_worktree_paths(repo_root)
    husks: list[HuskEntry] = []
    for entry in sorted(worktrees_dir.iterdir(), key=lambda path: path.name):
        if not entry.is_dir():
            continue
        if (entry / ".git").exists():
            continue
        husks.append(
            HuskEntry(
                path=str(entry.relative_to(repo_root)),
                registered=entry.resolve() in registered,
            )
        )
    return HuskReport(worktrees_dir=str(worktrees_dir), husks=husks)


def fix_workspace_husks(repo_root: Path) -> tuple[HuskReport, HuskFixResult]:
    """Remove unregistered husks; never touch registered worktrees (R5).

    Returns the pre-fix report plus the fix outcome.
    """
    report = scan_workspace_husks(repo_root)
    removed: list[str] = []
    skipped_registered: list[str] = []
    for entry in report.husks:
        if entry.registered:
            skipped_registered.append(entry.path)
            continue
        shutil.rmtree(repo_root / entry.path)
        removed.append(entry.path)
    return report, HuskFixResult(removed=removed, skipped_registered=skipped_registered)
