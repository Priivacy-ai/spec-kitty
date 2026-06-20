"""Project path resolution helpers for Spec Kitty."""

from __future__ import annotations

from pathlib import Path


def locate_project_root(start: Path | None = None) -> Path | None:
    """Delegates to the authoritative implementation in :mod:`specify_cli.core.paths`.

    All resolution authority — ``SPECIFY_REPO_ROOT`` env-var check (Tier 1),
    git worktree ``.git`` pointer following (Tier 2), and ``.kittify`` directory
    walk (Tier 3) — lives in :func:`specify_cli.core.paths.locate_project_root`.

    The import is deferred to the function body (not module-level) to preserve
    import-cycle safety: ``core/__init__.py`` imports from this module, and a
    module-level import of ``paths`` here could trigger ``specify_cli`` package
    initialisation before it finishes loading. The deferred pattern fires only at
    call time, after the package is fully loaded. This is the same mechanism used
    by ``paths.py`` itself for its ``git_ops`` and ``_read_path_resolver``
    deferred imports. Reverting to a module-level import is a regression. (#1971)
    """
    from specify_cli.core.paths import locate_project_root as _authoritative
    result: Path | None = _authoritative(start)
    return result


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
