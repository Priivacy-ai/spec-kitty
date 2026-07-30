"""Per-project consent for the tracker SaaS transport (#3030 FR-029).

``tracker/saas_client.py`` was gated on **authentication and team scope only**
(``Authorization`` + ``X-Team-Slug``): ``project_uuid`` appeared nowhere in the
module, so the question "may *this project's* data leave the machine?" was never
asked on any of its ten endpoints. Three of them are POSTs (``push``, ``run``,
``bind_mission_origin``) carrying ``mission_slug``, ``project_slug``,
``mission_id`` and the external issue ``title`` — and in this product a
``mission_slug`` is a **client engagement name**, so shipping one is itself the
confidentiality breach rather than incidental metadata.

Worse than the interactive reach (``sync push`` / ``run`` / ``pull``): the bind
endpoint fires **non-interactively during mission creation**, via
``core/mission_creation.py`` → ``core.adapters.consume_pending_origin`` →
``tracker/origin_consumer.py`` → ``tracker/origin.bind_mission_origin``. No
operator action is required to reach it.

Why this module asks :func:`~specify_cli.invocation.adapters.resolve_egress_consent`
rather than resolving consent itself
---------------------------------------------------------------------------------

C-003: project consent is represented **once**. The single derivation of
"checkout → project → does that project consent" lives in ``sync/__init__.py``'s
``_egress_consent_resolver``, which reads the checkout's identity through
``routing.resolve_checkout_sync_routing_readonly`` and then asks
``sync.consent.consented_project_uuids`` — the same funnel the drain
(``delivery/selection.py``), the emitter, the daemon and ``local_commit`` all
walk, over the one declared precedence chain (project-local → machine index →
env). Re-deriving that here would be a second expression of one invariant, free
to drift, which is the defect class this mission keeps re-finding.

The seam is registered by ``sync`` into the CORE registry slot in
``invocation/adapters.py``, so reaching it costs one import and no new chain.
:class:`~specify_cli.invocation.adapters.EgressConsent` already carries the
fail-closed vocabulary this gate needs: **only** ``GRANTED`` permits egress, and
both undetermined causes (``NO_RESOLVER``, ``UNANSWERABLE``) refuse while staying
distinguishable for diagnosis.

Note the layering rule did **not** force this route.
``tests/architectural/test_integration_boundary.py`` forbids the CORE set
(``core/``, ``status/``, ``readiness/``, ``invocation/``) from importing the
INTEGRATION set with an allowlist ratcheted at zero — and ``tracker/`` is on the
*INTEGRATION* side, so it may import ``specify_cli.sync.*`` in any form (it
already does, at ``saas_client.py``'s module level). The registry route is chosen
on the single-chain ground above, not because a gate demanded it.

What a refusal is **not** allowed to be
---------------------------------------

Not ``is_saas_sync_enabled()``. That flag is machine-global *arming*, which the
spec states is never a grant and which is the 2026-07-27 incident's own
mechanism — one exported ``SPEC_KITTY_ENABLE_SAAS_SYNC`` carried five
never-opted-in projects along with the intended one. Not the team scope, not the
current working directory, and not "we have a token". Only the project that owns
the data can consent for it.

Not a silent proceed when the project cannot be determined, either. An
unresolvable project is a **refusal** (FR-003 / NFR-001): inability to determine
consent is never consent. This mission has now found that same defect
independently in four places, most recently as ``if sync_enabled is False`` where
the resolver returned ``None`` for two unrelated causes.
"""

from __future__ import annotations

from pathlib import Path

#: Refusal text for the case where no checkout was offered at all. Kept separate
#: from the resolver's own vocabulary because it is a *caller* fault — a transport
#: was constructed without being told whose data it carries — and the operator fix
#: differs from "this project has not opted in".
UNDETERMINED_PROJECT_REFUSAL = (
    "the project that owns this data could not be determined, so its consent to "
    "hosted sync could not be resolved; refusing to transmit (an undetermined "
    "project is never a consenting one)"
)


def project_egress_refusal(project_root: Path | None) -> str | None:
    """Return why *project_root*'s project may not transmit, or ``None`` to permit.

    ``None`` — and only ``None`` — is permission. Every other outcome, including
    every future :class:`~specify_cli.invocation.adapters.EgressConsent` member, is
    a refusal string suitable for an operator: these are interactive commands, and
    a silent no-op would leave someone running ``sync push`` believing their data
    shipped.

    *project_root* is the checkout that **owns the data being sent** — the mission's
    own repository, resolved from the mission's ``feature_dir`` or from the tracker
    config being pushed — never the process's current working directory. Passing
    ``None`` refuses.
    """
    if project_root is None:
        return UNDETERMINED_PROJECT_REFUSAL

    # Importing ``specify_cli.sync`` is what *registers* the resolver into the CORE
    # slot (``sync/__init__.py::register_default_handlers``). Without it a process
    # that never loaded the sync package would get ``NO_RESOLVER`` and refuse every
    # send — fail-closed, but a false denial for a project that has genuinely opted
    # in. Deliberately not suppressed into a permit: if sync cannot be imported at
    # all there is no consent chain to consult, and that is an undetermined answer.
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
            "mission and engagement identifiers must not be transmitted; record a "
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
    # A member added to EgressConsent after this module was written. ``permits_egress``
    # already refused it above; naming it here keeps the operator message honest
    # rather than silently reusing DENIED's remedy.
    return (
        f"hosted-sync consent for the project at {project_root} resolved to "
        f"{verdict.value!r}, which does not permit egress; refusing to transmit"
    )


# Only names with a real ``src/`` consumer are advertised — the symbol-level
# dead-code gate (``tests/architectural/test_no_dead_symbols.py``) is a shrink-only
# ratchet and does not count tests as callers. ``UNDETERMINED_PROJECT_REFUSAL`` stays
# importable and unadvertised (the idiom ``sync/consent.py`` uses for
# ``consent_index_health``) until a production reader for it lands.
__all__ = ["project_egress_refusal"]
