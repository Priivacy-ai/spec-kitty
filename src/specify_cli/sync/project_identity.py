"""Backward-compatible shim.

The canonical home for ProjectIdentity is specify_cli.identity.project.
This module re-exports all public names for backward compatibility.
Callers outside specify_cli.dossier may continue to import from here.
"""

from specify_cli.identity.project import (  # noqa: F401
    ProjectIdentity,
    atomic_write_config,
    derive_project_slug,
    ensure_identity,
    generate_build_id,
    generate_node_id,
    generate_project_uuid,
    is_writable,
    load_identity,
)

# ``ensure_identity`` remains importable for explicit legacy callers of this shim,
# but is intentionally omitted from ``__all__`` so wildcard imports do not promote
# a write-boundary helper as part of the trimmed public surface.
__all__ = [
    "ProjectIdentity",
    "atomic_write_config",
    "derive_project_slug",
    "generate_build_id",
    "generate_node_id",
    "generate_project_uuid",
    "is_writable",
    "load_identity",
]
