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

    # FR-013: register the first resolved org pack root regardless of whether it
    # nests a ``doctrine/`` subdir. Runtime resolves org packs from the *flat*
    # ``<pack>/<plural>/`` layout (``resolve_org_roots`` → ``DoctrineService``),
    # which has no ``<pack>/doctrine/`` subdir; gating on ``doctrine/.is_dir()``
    # silently dropped those packs so flat-layout artifacts failed to activate
    # ("Unknown <kind> ID"). The layout-tolerant scan in
    # ``pack_manager._scan_layer_dirs`` accepts both flat and nested packs.
    for org_root in resolve_org_roots(repo_root):
        if org_root.is_dir():
            roots["org"] = org_root
            break

    return roots
