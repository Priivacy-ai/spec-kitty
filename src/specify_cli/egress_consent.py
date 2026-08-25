"""The one registration site of the default egress-consent resolver (C-003).

**What lives here.** The single derivation of "does the project that owns this
checkout consent to hosted sync" — moved verbatim out of ``sync/__init__.py``'s
``register_default_handlers``, where it was a nested closure registered as a
side effect of importing ``specify_cli.sync``. The derivation itself is
unchanged; see :func:`_build_default_egress_consent_resolver` for the two calls
it is made of, and ``specify_cli/egress.py``'s FR-012 section for why it must
have exactly one home.

Why wiring it is an explicit call, not an import side effect
-----------------------------------------------------------

The old wiring made the egress gate's correctness depend on an *unrelated*
import: a process answered consent questions properly only if something had
happened to import the whole sync package first, whose module tail then ran
``register_default_handlers()``. Three consequences, all defects:

* **The gate was silently absent in minimal processes.**
  ``SPEC_KITTY_SYNC_MINIMAL_IMPORT=1`` (the ``doctor restart-daemon`` fast path
  sets it) skips exactly that module tail, so a process that had loaded sync
  still held no resolver and every send was refused with ``NO_RESOLVER`` —
  fail-closed, but a false denial for a project that genuinely opted in.
* **The coupling was invisible.** Nothing in ``egress.py`` said "importing sync
  here is load-bearing"; the comment did, but comments do not fail builds.
  Deleting or reshuffling the sync package's import-time block would have
  downgraded every consent answer to ``NO_RESOLVER`` with no red test.
* **One transport's bootstrap registered another seam's handlers.** Answering a
  consent question dragged in the status fan-out registrations, the dossier
  emitter adapter, and the rest of the sync package init.

Now :func:`ensure_default_egress_consent_resolver` is called by name where the
answer is needed (:func:`specify_cli.egress._egress_decision`) and by tests that
want the production wiring. Importing this module registers nothing.

Why the hosted-sync chain is imported at **ensure** time, every time
--------------------------------------------------------------------

:func:`ensure_default_egress_consent_resolver` imports
``specify_cli.sync.routing`` / ``specify_cli.sync.consent`` so that an
unimportable hosted-sync package fails *there* — loudly, with the exception in
hand — rather than being masked by whatever resolver a previous call left in the
slot. This placement keeps two degradations honest at once:

* **FR-013**: ``invocation.adapters.resolve_egress_consent`` converts a raising
  resolver into ``UNANSWERABLE`` and drops the exception text, but
  ``egress.py``'s own handler around the ensure call renders the import-failure
  refusal that names the actual fault.
* **SC-005**: an unimportable chain must never masquerade as a concrete consent
  verdict (a ``no_record`` rendered from a stale registration reads to the
  operator exactly like a project that never opted in). Re-proving loadability
  per decision is what keeps the two distinguishable.

A resolver that raises on ordinary answers (a bad config shape, say) still lands
on the ``UNANSWERABLE`` path as before; only "the package could not be loaded"
is an ensure-time failure.

Importing this module therefore does not import the sync package, which is
what lets ``import specify_cli.egress`` succeed in a process where
``specify_cli.sync`` is blocked — pinned by
``tests/sync/tracker/test_egress_single_authority.py`` and, structurally, by
``tests/architectural/test_egress_consent_boundary.py``.

Late binding, and the test contract it carries
----------------------------------------------

The returned resolver holds the *modules*, not the functions: each call looks
``resolve_checkout_sync_routing_readonly`` /
``resolve_project_consent`` up on the captured module object, so patches on
``specify_cli.sync.routing`` / ``specify_cli.sync.consent`` are respected on
every invocation (the same late-binding contract the nested closure documented).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from specify_cli.invocation.adapters import (
    EgressConsent,
    egress_consent_resolver_registered,
    register_egress_consent_resolver,
)


def _build_default_egress_consent_resolver() -> Callable[[Path], EgressConsent]:
    """Import the hosted-sync consent chain and return the resolver bound to it.

    **Which project is asking** comes from the checkout's resolved identity, via
    the read-only routing resolver. That is the single derivation of
    checkout → project (#3030), and it already carries the FR-022 / FR-023
    hardening: an unreadable or non-mapping ``.kittify/config.yaml`` yields
    ``project_uuid=None`` instead of raising, and an unidentifiable project is
    never consentable (NFR-001), so it denies here.

    **Whether that project consents** comes from one call to
    ``consent.resolve_project_consent`` — the same authority used by the drain
    and emitter, walking the one declared precedence chain. Deliberately NOT
    ``effective_sync_enabled``: that chain also honours the repo-slug-keyed
    ``[sync.repo_defaults]`` record, which FR-019 condemns precisely because it
    is keyed on a mutable git remote and cannot speak for a project. One
    authority and one split mapping preserve the current main contract.

    Returns an ``EgressConsent`` member, never a bare bool. The registry seam
    maps a raise to ``UNANSWERABLE``; this resolver classifies ordinary absence,
    refusal, grant, and non-consentable paths explicitly.
    """
    from specify_cli.sync import consent as _consent_module
    from specify_cli.sync import routing as _routing_module

    def resolve_egress_consent_for_checkout(path: Path) -> EgressConsent:
        """Answer for the checkout at *path*, per the module docstring's mapping."""
        routing = _routing_module.resolve_checkout_sync_routing_readonly(path)
        if routing is None or not routing.project_uuid:
            return EgressConsent.NOT_CONSENTABLE
        uuid = str(routing.project_uuid)
        decision = _consent_module.resolve_project_consent(uuid, checkout_roots=[routing.repo_root])
        if decision.granted:
            return EgressConsent.GRANTED
        if decision.level is _consent_module.ConsentLevel.ABSENT:
            return EgressConsent.NO_RECORD
        return EgressConsent.RECORDED_REFUSAL

    return resolve_egress_consent_for_checkout


def ensure_default_egress_consent_resolver() -> None:
    """Ensure the default egress-consent resolver answers for this process.

    The explicit replacement for the old import side effect: calling this is how
    a process obtains working consent answers, and it may be called before every
    decision rather than tracked. Two properties, both load-bearing:

    * **The chain's loadability is re-proven on every call.** The hosted-sync
      package is imported here each time, so a process where
      ``specify_cli.sync`` has become unimportable fails *here* — loudly, with
      the exception in hand — instead of silently falling back to whatever a
      previously-wired resolver answers. An unimportable chain must never
      masquerade as a concrete consent verdict (#3030 SC-005).
    * **An occupied slot is never clobbered.** Registration happens only when
      :func:`specify_cli.invocation.adapters.egress_consent_resolver_registered`
      answers false, so a deliberately-injected alternate (a test double, or a
      future transport's own resolver) is asked rather than silently replaced.
    """
    resolver = _build_default_egress_consent_resolver()
    if not egress_consent_resolver_registered():
        register_egress_consent_resolver(resolver)


__all__ = ["ensure_default_egress_consent_resolver"]
