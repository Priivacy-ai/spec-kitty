"""``DoctrineService`` builders (WP06 T031, #2532) — the US1-frozen region.

Relocated verbatim from ``charter.context``: :func:`_build_doctrine_service`
and :func:`_build_activation_aware_doctrine_service` — the **LAST** cluster of
the ``context.py`` decomposition (research.md Decision 7/8, extraction step
13). This is the region US1 (#3064 / mission
``charter-delivery-finish-context-degod``'s empty-charter workstream) touched
via ``_build_activation_aware_doctrine_service``'s "always wrap" contract
(R5); it is extracted here byte-identical, against the now-frozen US1 code —
no logic changes.

Cycle note: :func:`_build_activation_aware_doctrine_service` calls
:func:`_build_doctrine_service` via a function-local
``from charter.context import _build_doctrine_service`` rather than a direct
intra-module reference. Several existing tests (e.g.
``tests/charter/test_context_include_activation.py::_patch_service``) patch
only ``charter.context._build_doctrine_service`` and rely on that single seam
covering BOTH the wrapped (agent-profile) and unwrapped paths — a guarantee
that held for free while both functions lived in ``charter.context`` itself.
Routing the inner call back through ``charter.context`` (which re-exports
this module's :func:`_build_doctrine_service` by reference) preserves that
single-patch-point contract after the relocation. :func:`_build_doctrine_service`
similarly resolves ``infer_repo_languages`` via a function-local import from
``charter.context`` — ``tests/charter/test_context.py`` patches
``charter.context.infer_repo_languages`` directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import doctrine.service as _doctrine_service_module

from charter._doctrine_paths import resolve_project_root

__all__ = [
    "_build_activation_aware_doctrine_service",
    "_build_doctrine_service",
]


def _build_doctrine_service(
    repo_root: Path,
    *,
    org_roots: list[Path] | None = None,
) -> _doctrine_service_module.DoctrineService:
    """Build a DoctrineService for the given repo root.

    The project-root candidate list (in priority order):
    1. ``.kittify/doctrine/``  — Phase 3 synthesis target (FR-009 / T025).
    2. ``src/doctrine/``       — code-local built-in-layer path.
    3. ``doctrine/``           — flat fallback.

    Discovery is conditional on directory presence so legacy (pre-synthesis)
    projects see byte-identical behaviour (R-2 mitigation).

    Cross-reference: ``compiler._default_doctrine_service`` uses the same
    ``resolve_project_root`` helper from ``charter._doctrine_paths``.

    WP07: callers in ``specify_cli`` may supply explicit *org_roots* (a list
    of org doctrine snapshot paths) so the resulting service includes the
    configured org layer in provenance tracking.  Charter-internal callers
    omit the argument and get the built-in-plus-project baseline.
    """
    from doctrine.service import DoctrineService
    from charter.context import infer_repo_languages  # noqa: PLC0415 — patch seam, see module docstring

    # built_in_root=None → the repositories self-resolve ``packs/built-in/<kind>``
    # (WP04 seam). Mission relocate-builtin-doctrine-packs moved the built-in
    # artefacts out of ``src/doctrine`` into ``packs/built-in``; a
    # ``resolve_doctrine_root()`` here would point at the emptied ``src/doctrine``
    # tree and silently load nothing.
    project_root = resolve_project_root(repo_root)
    # Only pass ``org_roots`` when it carries paths so charter-internal
    # callers see byte-identical kwargs (preserves existing test stubs and
    # downstream constructors that may not declare the parameter).
    if org_roots:
        return DoctrineService(
            built_in_root=None,
            project_root=project_root,
            active_languages=infer_repo_languages(repo_root),
            org_roots=org_roots,
        )
    return DoctrineService(
        built_in_root=None,
        project_root=project_root,
        active_languages=infer_repo_languages(repo_root),
    )


def _build_activation_aware_doctrine_service(
    repo_root: Path, *, org_roots: list[Path] | None = None
) -> object:
    """Build an *activation-aware* doctrine service for ``--include`` fetches.

    FR-016: ``charter context --include agent-profile:<id>`` must inherit the
    charter activation gate so that a non-activated profile is treated as a
    structured miss rather than silently rendered. This is the **scoped**
    counterpart to :func:`_build_doctrine_service`: it builds the same inner
    service (identical kwargs) and wraps it with the activation-aware
    :class:`charter.resolver.DoctrineService`, supplying a freshly constructed
    :class:`~charter.pack_context.PackContext` for *repo_root*.

    Only the ``agent-profile`` include branch routes through this helper; the
    other five callers of :func:`_build_doctrine_service` are deliberately left
    on the unwrapped service so their return type and behaviour are unchanged.

    Single builder contract (R5): the service is ALWAYS wrapped, even when
    ``activated_agent_profiles is None``. The wrapper's three-state filter
    treats ``None`` as "admit all", so the unrestricted case stays byte-identical
    in *behaviour* to the legacy fetch path while giving both activation-service
    builders one contract — ``_inner`` is always valid and ``.agent_profiles``
    is always a gated ``dict``. This matches
    :func:`specify_cli.doctrine_service_factory.build_activation_aware_doctrine_service`,
    which also wraps unconditionally.
    """
    from charter.context import _build_doctrine_service  # noqa: PLC0415
    from charter.pack_context import PackContext
    from charter.resolver import DoctrineService as ActivationAwareDoctrineService

    inner = _build_doctrine_service(repo_root, org_roots=org_roots)
    pack_context = PackContext.from_config(repo_root)
    return ActivationAwareDoctrineService(inner, pack_context=pack_context)
