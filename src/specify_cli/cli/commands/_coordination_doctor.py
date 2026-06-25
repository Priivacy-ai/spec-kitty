"""Coordination + git-health cluster for ``doctor`` (WP07, #2059).

Extracts Cluster K out of ``doctor.py``: the git-version (RR-01) check, the
tracked-``.worktrees/`` hygiene check, the coordination-worktree health check,
and the lane sparse-checkout drift check. The ``_check_lane_sparse_checkout_drift``
CC19 monolith is decomposed into <=15-CC sub-helpers (per-lane scan + finding
assembly).

H2 / I-6 — CRITICAL: ``merge.path_is_under_worktrees`` is imported FUNCTION-LOCAL
inside :func:`_check_tracked_worktrees_content`. Hoisting it to module scope
reintroduces the ``doctor <-> merge`` module-load cycle. It must stay local.

Import discipline (one-way, I-2): imports shared infra from
:mod:`._doctor_shared`; never imports the CLI ``doctor`` module at module scope.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import typer

from specify_cli.core.constants import KITTY_SPECS_DIR
from specify_cli.core.paths import locate_project_root

from ._doctor_shared import console

# ``__all__`` lists this sibling's cross-module contract: the entrypoint +
# ``DoctorFinding`` + the health-check helpers ``doctor.py`` re-exports. The
# remaining helpers (``_detect_git_version``, ``_check_tracked_worktrees_content``)
# are intra-module (used here + by this module's own unit tests) and are
# deliberately NOT exported — listing them would register orphan public symbols
# under the dead-symbol gate (tests/architectural/test_no_dead_symbols).
__all__ = [
    "DoctorFinding",
    "run_coordination_health",
    "_check_git_version",
    "_check_coordination_worktree_health",
    "_check_lane_sparse_checkout_drift",
]


@dataclass
class DoctorFinding:
    """A single doctor finding emitted by a WP04 health check.

    Stable shape so that downstream tools (and tests) can rely on it.
    """

    severity: str  # "ok" | "warning" | "error"
    message: str
    next_step: str | None = None
    error_code: str | None = None
    extra: dict[str, object] = field(default_factory=dict)


_MIN_GIT_VERSION: tuple[int, int] = (2, 25)
_LANE_DRIFT_CODE = "LANE_SPARSE_CHECKOUT_DRIFT"


def _detect_git_version() -> tuple[int, int] | None:
    """Return ``(major, minor)`` of the local git binary, or ``None`` on failure."""
    import subprocess as _subprocess
    try:
        out = _subprocess.check_output(
            ["git", "--version"], text=True, stderr=_subprocess.DEVNULL,
        ).strip()
    except (OSError, _subprocess.CalledProcessError):
        return None
    # Output shape: "git version 2.45.1.windows.1" — take the first two numbers.
    parts = out.split()
    if len(parts) < 3:
        return None
    nums = parts[2].split(".")
    try:
        return int(nums[0]), int(nums[1])
    except (ValueError, IndexError):
        return None


def _check_git_version(
    detected: tuple[int, int] | None = None,
) -> list[DoctorFinding]:
    """RR-01: refuse to operate on git older than ``_MIN_GIT_VERSION``.

    ``detected`` is injectable for tests; production callers pass
    ``None`` and the function detects from the live binary.
    """
    version = detected if detected is not None else _detect_git_version()
    if version is None:
        return [DoctorFinding(
            severity="error",
            message="Could not detect git version. spec-kitty requires git >= 2.25.",
            next_step="Install or upgrade git to >= 2.25.",
            error_code="GIT_VERSION_UNDETECTABLE",
        )]
    if version < _MIN_GIT_VERSION:
        return [DoctorFinding(
            severity="error",
            message=(
                f"git {version[0]}.{version[1]} is older than the required "
                f"{_MIN_GIT_VERSION[0]}.{_MIN_GIT_VERSION[1]}. "
                "Sparse-checkout exclusion of status files requires the "
                "modern non-cone surface."
            ),
            next_step=(
                "Upgrade git to >= 2.25 — see https://git-scm.com/downloads."
            ),
            error_code="GIT_VERSION_TOO_OLD",
            extra={"detected": f"{version[0]}.{version[1]}"},
        )]
    return [DoctorFinding(
        severity="ok",
        message=f"git {version[0]}.{version[1]} satisfies the >= 2.25 requirement.",
    )]


def _check_tracked_worktrees_content(repo_root: Path) -> list[DoctorFinding]:
    """FR-035 (#1772 Bug 0): flag any TRACKED content under ``.worktrees/``.

    ``.worktrees/`` is execution scratch space and must never be committed.
    Tracked content there (e.g. ``.worktrees/<m>-coord/…`` junk) is the
    precondition for the #1772 merge-staging failures: finalize/recovery/merge
    flows could re-stage it, and post-merge validation could try to read it from
    a branch tree. This check uses ``git ls-files`` to surface such content with
    a remediation hint. It reuses the single ``.worktrees/`` predicate that the
    merge staging guards use (Randy Reducer: one predicate, no copies).
    """
    import subprocess as _subprocess

    # H2 / I-6: keep this import FUNCTION-LOCAL — hoisting it to module scope
    # reintroduces the doctor <-> merge module-load cycle.
    from specify_cli.cli.commands.merge import path_is_under_worktrees
    from specify_cli.core.constants import WORKTREES_DIR

    try:
        out = _subprocess.check_output(
            ["git", "-C", str(repo_root), "ls-files", "--", WORKTREES_DIR],
            text=True,
            stderr=_subprocess.DEVNULL,
        )
    except (OSError, _subprocess.CalledProcessError):
        # Not a git repo / git error — nothing to report here.
        return []

    tracked = [
        line
        for line in out.splitlines()
        if line.strip() and path_is_under_worktrees(Path(line.strip()))
    ]
    if not tracked:
        return [DoctorFinding(
            severity="ok",
            message=f"No tracked content under {WORKTREES_DIR}/.",
        )]

    preview = tracked[:10]
    more = "" if len(tracked) <= 10 else f" (+{len(tracked) - 10} more)"
    return [DoctorFinding(
        severity="error",
        message=(
            f"{len(tracked)} tracked file(s) under {WORKTREES_DIR}/ — this is "
            "execution scratch space and must never be committed. Tracked "
            "content here drives the #1772 merge-staging failures."
        ),
        next_step=(
            f"Remove it from version control: "
            f"`git rm -r --cached {WORKTREES_DIR}/` then commit, and ensure "
            f"`{WORKTREES_DIR}/` is gitignored."
        ),
        error_code="TRACKED_WORKTREES_CONTENT",
        extra={"tracked": preview, "tracked_count": len(tracked), "truncated": more != ""},
    )]


def _coordination_identity(
    mission_meta: dict[str, object],
) -> tuple[str, str, str] | None:
    """Return ``(coord_branch, mission_slug, mission_id)`` or None for legacy/incomplete.

    Returns None when the mission is legacy (no coordination_branch). A tuple of
    empty strings is never returned; an incomplete-but-coordinated mission yields
    ``("", "", "")`` so callers can distinguish "skip" (None) from "warn".
    """
    coord_branch = mission_meta.get("coordination_branch")
    mission_slug = mission_meta.get("mission_slug") or mission_meta.get("slug")
    mission_id = mission_meta.get("mission_id")
    if not isinstance(coord_branch, str) or not coord_branch:
        return None
    if not isinstance(mission_slug, str) or not isinstance(mission_id, str):
        return ("", "", "")
    return (coord_branch, mission_slug, mission_id)


def _coord_worktree_head_finding(
    worktree: Path, coord_branch: str, mission_slug: str
) -> DoctorFinding | None:
    """Return a finding if the coord worktree HEAD is off the coord branch."""
    import subprocess as _subprocess

    try:
        actual_head = _subprocess.check_output(
            ["git", "-C", str(worktree), "symbolic-ref", "HEAD"], text=True,
        ).strip()
    except _subprocess.CalledProcessError:
        actual_head = "<detached>"
    expected = f"refs/heads/{coord_branch}"
    if actual_head == expected or actual_head.removeprefix("refs/heads/") == coord_branch:
        return None
    return DoctorFinding(
        severity="warning",
        message=(
            f"Coordination worktree {worktree} is on {actual_head!r}, "
            f"expected {coord_branch!r}."
        ),
        next_step=(
            f"Inspect the worktree manually; then run "
            f"`spec-kitty agent worktree repair --mission {mission_slug}` "
            "to restore."
        ),
        error_code="COORDINATION_WORKTREE_BRANCH_MISMATCH",
    )


def _coord_worktree_dirty_finding(worktree: Path) -> DoctorFinding | None:
    """Return a finding if the coord worktree has uncommitted changes."""
    import subprocess as _subprocess

    try:
        dirty = _subprocess.check_output(
            ["git", "-C", str(worktree), "status", "--porcelain"], text=True,
        ).strip()
    except _subprocess.CalledProcessError:
        dirty = ""
    if not dirty:
        return None
    return DoctorFinding(
        severity="warning",
        message=f"Coordination worktree {worktree} has uncommitted changes.",
        next_step=(
            "Commit or discard the changes inside the coord worktree "
            "before next implement/review."
        ),
        error_code="COORDINATION_WORKTREE_DIRTY",
    )


def _check_coordination_worktree_health(
    repo_root: Path, mission_meta: dict[str, object],
) -> list[DoctorFinding]:
    """Verify the coordination worktree exists and is healthy.

    Returns one finding per discovered problem (or one ``ok`` finding if
    everything is fine). Skips silently for legacy missions (no
    ``coordination_branch`` field) because the coordination worktree
    concept does not apply there.
    """
    from specify_cli.coordination import CoordinationWorkspace

    identity = _coordination_identity(mission_meta)
    if identity is None:
        return []
    coord_branch, mission_slug, mission_id = identity
    if not mission_slug or not mission_id:
        return [DoctorFinding(
            severity="warning",
            message=(
                "meta.json carries coordination_branch but is missing "
                "mission_slug/mission_id; coord worktree health cannot be verified."
            ),
            next_step="Run `spec-kitty doctor identity --json` for details.",
            error_code="COORDINATION_META_INCOMPLETE",
        )]

    # Route through the authoritative resolver (WP03 / FR-009). resolve_mid8
    # never raises (it declines to ``""``). The ``or mission_id[:8]`` fallback
    # consciously PRESERVES the prior short-id tolerance.
    from specify_cli.lanes.branch_naming import resolve_mid8

    short = resolve_mid8(mission_slug, mission_id=mission_id) or mission_id[:8]
    worktree = CoordinationWorkspace.worktree_path(repo_root, mission_slug, short)

    if not worktree.exists():
        return [DoctorFinding(
            severity="warning",
            message=(
                f"Coordination worktree {worktree} is missing for "
                f"mission {mission_slug!r}."
            ),
            next_step=(
                f"Run `spec-kitty agent worktree repair --mission {mission_slug}` "
                "to recreate it."
            ),
            error_code="COORDINATION_WORKTREE_MISSING",
        )]

    findings: list[DoctorFinding] = []
    head_finding = _coord_worktree_head_finding(worktree, coord_branch, mission_slug)
    if head_finding is not None:
        findings.append(head_finding)
    dirty_finding = _coord_worktree_dirty_finding(worktree)
    if dirty_finding is not None:
        findings.append(dirty_finding)

    if not findings:
        findings.append(DoctorFinding(
            severity="ok",
            message=f"Coordination worktree {worktree} is healthy.",
        ))
    return findings


def _lane_sparse_file(lane_dir: Path) -> Path | None:
    """Resolve the lane's ``info/sparse-checkout`` path, or None if unresolvable."""
    import subprocess as _subprocess

    try:
        raw = _subprocess.check_output(
            ["git", "-C", str(lane_dir), "rev-parse",
             "--git-path", "info/sparse-checkout"],
            text=True,
        ).strip()
    except _subprocess.CalledProcessError:
        return None
    sparse_file = Path(raw)
    if not sparse_file.is_absolute():
        sparse_file = lane_dir / sparse_file
    return sparse_file


def _scan_lane_sparse_drift(
    lane_dir: Path, mission_slug: str, expected: set[str]
) -> DoctorFinding | None:
    """Return a drift finding for one lane worktree, or None when it is healthy."""
    repair_hint = (
        f"Run `spec-kitty agent worktree repair --mission {mission_slug}` to restore."
    )
    sparse_file = _lane_sparse_file(lane_dir)
    if sparse_file is None:
        return DoctorFinding(
            severity="warning",
            message=f"Could not resolve sparse-checkout path for {lane_dir}.",
            next_step=f"Run `spec-kitty agent worktree repair --mission {mission_slug}`.",
            error_code=_LANE_DRIFT_CODE,
        )
    if not sparse_file.exists():
        return DoctorFinding(
            severity="warning",
            message=(
                f"Lane worktree {lane_dir} is missing the sparse-checkout "
                "policy that excludes status files."
            ),
            next_step=repair_hint,
            error_code=_LANE_DRIFT_CODE,
        )
    present = {
        line.strip()
        for line in sparse_file.read_text().splitlines()
        if line.strip()
    }
    missing = expected - present
    if not missing:
        return None
    return DoctorFinding(
        severity="warning",
        message=(
            f"Lane worktree {lane_dir} sparse-checkout is missing "
            f"{len(missing)} expected pattern(s): {sorted(missing)}."
        ),
        next_step=repair_hint,
        error_code=_LANE_DRIFT_CODE,
        extra={"missing_patterns": sorted(missing)},
    )


def _check_lane_sparse_checkout_drift(
    repo_root: Path, mission_meta: dict[str, object],
) -> list[DoctorFinding]:
    """Verify every lane worktree carries the expected sparse-checkout patterns.

    Skips silently for legacy missions.
    """
    import subprocess as _subprocess
    from specify_cli.coordination import lane_sparse_checkout_patterns

    identity = _coordination_identity(mission_meta)
    if identity is None:
        return []
    _coord_branch, mission_slug, mission_id = identity
    if not mission_slug or not mission_id:
        return []

    from specify_cli.lanes.branch_naming import resolve_mid8

    short = resolve_mid8(mission_slug, mission_id=mission_id) or mission_id[:8]
    expected = set(lane_sparse_checkout_patterns(mission_slug, short))

    worktrees_dir = repo_root / ".worktrees"
    if not worktrees_dir.exists():
        return []

    # Cache `git worktree list --porcelain` so we don't shell out per lane.
    try:
        wt_list = _subprocess.check_output(
            ["git", "-C", str(repo_root), "worktree", "list", "--porcelain"],
            text=True,
        )
    except _subprocess.CalledProcessError:
        wt_list = ""

    findings: list[DoctorFinding] = []
    for lane_dir in sorted(worktrees_dir.iterdir()):
        # Only inspect lane worktrees for THIS mission (slug prefix + "-lane-").
        if not lane_dir.name.startswith(f"{mission_slug}-lane-"):
            continue
        if str(lane_dir.resolve()) not in wt_list:
            # Not a registered git worktree; skip silently.
            continue
        finding = _scan_lane_sparse_drift(lane_dir, mission_slug, expected)
        if finding is not None:
            findings.append(finding)

    if not findings:
        findings.append(DoctorFinding(
            severity="ok",
            message="All lane worktrees carry the expected sparse-checkout policy.",
        ))
    return findings


def _collect_coordination_findings(repo_root: Path) -> list[DoctorFinding]:
    """Run all coordination + git-health checks and return the aggregated findings."""
    findings: list[DoctorFinding] = []
    findings.extend(_check_git_version())
    # FR-035 (#1772 Bug 0): repo-level tracked-.worktrees/ hygiene check.
    findings.extend(_check_tracked_worktrees_content(repo_root))

    specs_dir = repo_root / KITTY_SPECS_DIR
    if not specs_dir.exists():
        return findings
    for mission_dir in sorted(specs_dir.iterdir()):
        if not mission_dir.is_dir():
            continue
        meta_path = mission_dir / "meta.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(meta, dict):
            continue
        findings.extend(_check_coordination_worktree_health(repo_root, meta))
        findings.extend(_check_lane_sparse_checkout_drift(repo_root, meta))
    return findings


def _emit_coordination_findings(findings: list[DoctorFinding], json_output: bool) -> None:
    """Render coordination findings as JSON or coloured human output."""
    if json_output:
        payload = [
            {
                "severity": f.severity,
                "message": f.message,
                "next_step": f.next_step,
                "error_code": f.error_code,
                "extra": f.extra,
            }
            for f in findings
        ]
        console.print_json(json.dumps(payload, indent=2))
        return
    for f in findings:
        colour = {
            "ok": "green", "warning": "yellow", "error": "red",
        }.get(f.severity, "white")
        console.print(f"[{colour}]{f.severity}[/{colour}]: {f.message}")
        if f.next_step:
            console.print(f"  → {f.next_step}")


def run_coordination_health(json_output: bool) -> None:
    """Entry point for ``doctor coordination`` (exit 1 iff any ``error`` finding)."""
    try:
        repo_root = locate_project_root()
    except Exception as exc:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1) from exc
    if repo_root is None:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1)

    findings = _collect_coordination_findings(repo_root)
    _emit_coordination_findings(findings, json_output)
    raise typer.Exit(1 if any(f.severity == "error" for f in findings) else 0)
