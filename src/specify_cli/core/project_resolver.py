"""Project path resolution helpers for Spec Kitty."""

from __future__ import annotations

from pathlib import Path


def locate_project_root(start: Path | None = None) -> Path | None:
    """Walk upwards from *start* (or CWD) to find the directory that owns .kittify.

    NOTE (#1971 — three-way resolver consolidation, deferred): this is the
    *simpler* of the two ``locate_project_root`` implementations. It deliberately
    does NOT honour ``SPECIFY_REPO_ROOT`` or follow worktree ``.git`` pointers;
    that authority lives in :func:`specify_cli.core.paths.locate_project_root`.
    The two were intentionally kept separate in WP05 (#1965) because the four
    callers of *this* resolver do not need env-var / worktree authority for
    correctness.

    Callers that do NOT require env-var / worktree authority (#1971 pre-analysis):
      cli/helpers.py         — interactive CLI root detection via ``get_project_root_or_exit``;
                               prints guidance and exits on None; CI sets env-var through the
                               paths.py resolver on a different code path, not here.
      cli/commands/lint.py   — uses ``locate_project_root() or Path.cwd()`` as ruff/mypy cwd;
                               falls back to cwd on None, so env-var authority is irrelevant
                               to lint correctness.
      compat/planner.py      — injectable ``project_root_resolver`` default for best-effort
                               upgrade-nag planning; the caller controls which resolver to
                               supply at construction time; never raises on None.
      core/__init__.py       — pure re-export shim; delegates to this function with no
                               additional authority assumptions.

    Full consolidation (collapsing this into ``paths.locate_project_root``) is
    scoped to #1971 to avoid import-cycle risk and scope creep here.
    """
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".kittify").is_dir():
            return candidate
    return None


def resolve_template_path(project_root: Path, mission_type: str, template_subpath: str | Path) -> Path | None:
    """Resolve a template path through a 5-tier precedence chain.

    Resolution order:
    1. Project mission: .kittify/missions/{key}/templates/{subpath}
    2. Project generic: .kittify/templates/{subpath}
    3. Global mission: ~/.kittify/missions/{key}/templates/{subpath}
    4. Global generic: ~/.kittify/templates/{subpath}
    5. Legacy fallback: templates/{subpath} (project root)

    Args:
        project_root: Root of the user project containing ``.kittify/``.
        mission_type: Mission key (e.g. ``"software-dev"``).
        template_subpath: Relative template path (e.g. ``"spec-template.md"``).

    Returns:
        Path to the resolved template, or None if not found at any tier.
    """
    from specify_cli.runtime.home import get_kittify_home

    subpath = Path(template_subpath)
    candidates = [
        # 1. Project mission-specific
        project_root / ".kittify" / "missions" / mission_type / "templates" / subpath,
        # 2. Project generic
        project_root / ".kittify" / "templates" / subpath,
    ]

    # 3. Global mission-specific + 4. Global generic
    try:
        global_home = get_kittify_home()
        candidates.append(global_home / "missions" / mission_type / "templates" / subpath)
        candidates.append(global_home / "templates" / subpath)
    except RuntimeError:
        pass

    # 5. Legacy project root fallback
    candidates.append(project_root / "templates" / subpath)

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


__all__ = [
    "locate_project_root",
    "resolve_template_path",
]
