"""Per-project consent for the widen-mode SaaS transport (#3030 FR-030).

``saas_client/client.py`` had **no consent consumer anywhere in the package**: a
grep for the consent chain returned zero hits, exactly as it did for
``tracker/``. Both packages touch no spec-kitty store at all, which is why a
dossier whose unit of reasoning was *the store* could not see them — egress is a
property of *senders*.

What leaks here is subtler than a payload and no less disclosing: four of the
five endpoints are GETs that carry ``mission_id`` **in the URL path**, documented
as "ULID **or slug**" — and in this product a mission slug is a client engagement
name. A request line is not a safer place to put one than a request body.

Reached from ``cli/commands/decision.py``, ``cli/commands/charter/interview.py``,
``missions/plan/{plan,specify}_interview.py`` and four ``widen/*`` modules.

Why this asks :func:`~specify_cli.invocation.adapters.resolve_egress_consent`
----------------------------------------------------------------------------

Same reason as ``tracker/egress_consent.py``, and the reasoning is recorded in
full there: C-003 says project consent is represented **once**, and the one
derivation of "checkout → project → does that project consent" is the resolver
``sync`` registers into the CORE slot in ``invocation/adapters.py``, which walks
``sync.consent.consented_project_uuids`` — the same funnel as the drain, the
emitter, the daemon and ``local_commit``. Re-deriving it here would make a second
copy of an invariant that must not drift.

The layering rule did not force the route: ``saas_client/`` is on the
*INTEGRATION* side of ``tests/architectural/test_integration_boundary.py``, so it
may import ``specify_cli.sync.*`` in any form. It is chosen because the funnel is
already written, already fail-closed, and must stay singular.

This module is a near-duplicate of its ``tracker/`` sibling **by necessity**: the
two packages share no parent inside this change's scope, and inventing one would
be an architectural decision recorded nowhere. What is duplicated is the *call*,
not the chain — the chain is still resolved in exactly one place.
"""

from __future__ import annotations

from pathlib import Path

#: See ``tracker/egress_consent.py`` for why "no checkout offered" is kept
#: distinct from "this project has not opted in": the operator's fix differs.
UNDETERMINED_PROJECT_REFUSAL = (
    "the project that owns this data could not be determined, so its consent to "
    "hosted sync could not be resolved; refusing to transmit (an undetermined "
    "project is never a consenting one)"
)


def project_egress_refusal(project_root: Path | None) -> str | None:
    """Return why *project_root*'s project may not transmit, or ``None`` to permit.

    ``None`` — and only ``None`` — is permission. ``project_root`` is the checkout
    that owns the mission or decision record being sent, threaded from
    :meth:`~specify_cli.saas_client.client.SaasClient.from_env`'s ``repo_root``;
    ``None`` refuses.
    """
    if project_root is None:
        return UNDETERMINED_PROJECT_REFUSAL

    # Importing ``specify_cli.sync`` is what registers the resolver into the CORE
    # slot. Without it an unloaded sync package yields ``NO_RESOLVER`` — fail-closed,
    # but a false denial for a project that genuinely opted in. A failure to import
    # degrades to a refusal, never to a permit.
    try:
        import specify_cli.sync  # noqa: F401, PLC0415  (imported for registration)
    except Exception as exc:  # noqa: BLE001 - degrades to a refusal, never a permit
        return (
            "the hosted-sync package could not be loaded, so this project's consent "
            f"could not be resolved; refusing to transmit ({exc})"
        )

    from specify_cli.invocation.adapters import (  # noqa: PLC0415
        EgressConsent,
        resolve_egress_consent,
    )

    verdict = resolve_egress_consent(Path(project_root))
    if verdict.permits_egress:
        return None

    if verdict is EgressConsent.DENIED:
        return (
            f"the project at {project_root} has not consented to hosted sync, so its "
            "mission and decision identifiers must not be transmitted; record a "
            "decision in the project's own .kittify/config.yaml (sync.enabled) or "
            "run `spec-kitty sync opt-in` for it"
        )
    if verdict is EgressConsent.NO_RESOLVER:
        return (
            "no hosted-sync consent resolver is registered, so this project's "
            "consent could not be resolved; refusing to transmit"
        )
    if verdict is EgressConsent.UNANSWERABLE:
        return (
            f"consent for the project at {project_root} could not be determined "
            "(the consent chain raised or answered with a non-bool); refusing to "
            "transmit, because inability to determine consent is not consent"
        )
    return (
        f"hosted-sync consent for the project at {project_root} resolved to "
        f"{verdict.value!r}, which does not permit egress; refusing to transmit"
    )


# See the note in ``tracker/egress_consent.py``: only names with a real ``src/``
# consumer are advertised, so the symbol-level dead-code ratchet stays honest.
__all__ = ["project_egress_refusal"]
