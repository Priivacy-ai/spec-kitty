"""Single construction seam for activation-aware doctrine services (FR-010).

This module exposes :func:`build_activation_aware_doctrine_service`, the one
place profile surfaces (``profile list``/``profile show``, ``charter context
--include``) should call to obtain a :class:`charter.resolver.DoctrineService`
that already has per-kind charter activation filters applied.

It generalises the construction pattern used by
``specify_cli.cli.commands.charter.generate._build_doctrine_service_with_org_layer``
(``charter/generate.py:46-74``): build the inner
:class:`doctrine.service.DoctrineService` rooted at built-in doctrine, the
project layer, and configured org packs, then wrap it in
:class:`charter.resolver.DoctrineService` together with a
:class:`~charter.pack_context.PackContext` snapshot of the project's
activation state.

Layer rule (C-005)
------------------
This factory lives in ``specify_cli.*`` precisely because it imports from
``charter.*`` and ``doctrine.service`` — the allowed dependency direction is
``specify_cli → charter → doctrine``.  It must **not** be placed inside
``charter.*`` or ``doctrine.*``, which are forbidden from importing
``specify_cli``.  The activation wrapper itself is **reused** from
``charter.resolver`` (C-003); it is never re-implemented here.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from charter.resolver import DoctrineService as ActivationAwareDoctrineService

__all__ = ["build_activation_aware_doctrine_service"]


def build_activation_aware_doctrine_service(
    repo_root: Path,
) -> ActivationAwareDoctrineService:
    """Build an activation-filtered doctrine service for ``repo_root``.

    Constructs the inner :class:`doctrine.service.DoctrineService` rooted at
    built-in doctrine + project layer + configured org packs (reusing the
    existing root resolvers), then wraps it with
    :class:`charter.resolver.DoctrineService` and a
    :class:`~charter.pack_context.PackContext` built from
    ``.kittify/config.yaml``.

    The returned wrapper applies the three-state ``activated_agent_profiles``
    contract on its ``.agent_profiles`` property (and the equivalent filters
    for paradigms/procedures):

    * key absent from config → all built-in profiles are available;
    * explicit empty set → no profiles are available;
    * explicit set of IDs → only those profiles are available.

    Parameters
    ----------
    repo_root:
        Repository root containing ``.kittify/config.yaml``.

    Returns
    -------
    charter.resolver.DoctrineService
        The activation-aware wrapper around the inner doctrine service.
    """
    from charter._doctrine_paths import resolve_project_root
    from charter.pack_context import PackContext
    from charter.resolver import DoctrineService as ActivationDoctrineService
    from doctrine.drg.org_pack_config import resolve_org_roots
    from doctrine.service import DoctrineService

    project_root = resolve_project_root(repo_root)
    org_roots = [root for root in resolve_org_roots(repo_root) if root.exists()]

    # built_in_root=None lets each repository self-resolve the built-in tier via
    # ``resolve_pack_root("built-in")`` (packs/built-in/<kind>) — the WP04 seam.
    # Passing resolve_doctrine_root() here post-relocation yields the emptied
    # ``src/doctrine/<kind>/built-in`` and silently loads nothing.
    inner = DoctrineService(
        built_in_root=None,
        project_root=project_root,
        org_roots=org_roots,
    )

    pack_context = PackContext.from_config(repo_root)
    return ActivationDoctrineService(inner, pack_context=pack_context)
