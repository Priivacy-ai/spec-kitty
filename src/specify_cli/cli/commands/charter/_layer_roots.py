"""Resolve doctrine layer roots for charter CLI commands."""

from __future__ import annotations

from pathlib import Path

__all__ = ["resolve_layer_roots"]


def resolve_layer_roots(repo_root: Path) -> dict[str, Path]:
    """Resolve org/project doctrine roots for *repo_root*.

    Root resolution lives in ``specify_cli`` and the resolved paths are handed
    to lower charter/doctrine layers as data (C-008).
    """
    from specify_cli.doctrine.config import resolve_org_roots

    roots: dict[str, Path] = {}

    project_root = repo_root / ".kittify"
    if (project_root / "doctrine").is_dir():
        roots["project"] = project_root

    for org_root in resolve_org_roots(repo_root):
        if (org_root / "doctrine").is_dir():
            roots["org"] = org_root
            break

    return roots
