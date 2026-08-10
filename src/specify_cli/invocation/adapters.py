"""Invocation adapter registry for egress-consent and SaaS-client seams.

Provides a decoupled resolver boundary so that invocation/propagator.py
does not need to depend on the sync package.  The sync package registers
its concrete implementations at startup; sync -> invocation.adapters is
the clean dependency direction.

The dispatch functions are non-raising, but "non-raising" is not the same
as "safe": what a failed lookup *degrades to* is the whole question, and
one of these two seams guards a confidentiality boundary while the other
does not.

* :func:`get_saas_client` degrades to ``None``, which means "no transport"
  — nothing can leave, so absence is safe.
* :func:`resolve_egress_consent` degrades to a **refusal**.  It used to be
  ``resolve_sync_routing``, returning ``bool | None`` where ``None`` meant
  both "no resolver registered" *and* "the registered resolver raised";
  the propagator then tested ``if answer is False: return``, so both
  undetermined cases were read as permission to send.  Measured on
  2026-07-30 with no consent record anywhere: a ``repo_root`` that is not a
  project root sent one envelope carrying ``request_text`` verbatim, and so
  did a resolver that raised (#3030 FR-025).  The tri-state is gone: the
  seam now answers with :class:`EgressConsent`, only ``GRANTED`` permits
  egress, and the two undetermined causes are distinguishable for
  diagnosis while both refuse.

Mirrors the ``status/adapters.py`` idiom (C-007, FR-008).
"""

from __future__ import annotations

import enum
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class EgressConsent(enum.Enum):
    """Whether an Op recorded in a checkout may be transmitted off the machine.

    Six members rather than a boolean or a ``bool | None``, because the
    caller's decision must be impossible to spell wrongly.  ``None`` carried two
    unrelated meanings and the guard tested only one of them; here every member
    is asked the same question — :attr:`permits_egress` — and only one answers
    yes.  The three former ``DENIED`` members and the two undetermined members
    each stay separate because they need different operator responses (record a
    decision, establish an identity, load a package, or fix a fault), not
    because they differ in verdict: none of the five is consent (FR-003's rule,
    re-derived here because this path never called
    ``is_sync_enabled_for_checkout``).
    """

    #: The project that owns the checkout has consented to hosted sync.
    GRANTED = "granted"
    #: No consent record exists for the project at all — split from the former
    #: ``DENIED`` so the operator is told "record a decision" rather than
    #: "your decision was refused" (data-model: ``ConsentLevel.ABSENT``).
    NO_RECORD = "no_record"
    #: A consent decision is recorded and it is a refusal — split from the
    #: former ``DENIED`` (data-model: a non-absent, non-granting level, incl.
    #: ``ConsentLevel.UNDETERMINED`` — a consciously chosen mapping, not a
    #: silent catch-all).
    RECORDED_REFUSAL = "recorded_refusal"
    #: The project could not be identified, which is permanently non-consentable
    #: (NFR-001) — split from the former ``DENIED`` (data-model: routing
    #: resolved no ``project_uuid``).
    NOT_CONSENTABLE = "not_consentable"
    #: No resolver is registered: the INTEGRATION sync package was never loaded.
    #: Costless to refuse — without sync there is also no client to send through.
    NO_RESOLVER = "no_resolver"
    #: The registered resolver raised, or answered with something that is not a
    #: recognized :class:`EgressConsent` member.  Consent could not be
    #: determined, so it was not given.
    UNANSWERABLE = "unanswerable"

    @property
    def permits_egress(self) -> bool:
        """True only for :attr:`GRANTED`.

        The single place this verdict is turned into a branch.  Callers must ask
        this rather than comparing against a member, so that adding a future
        member cannot silently widen egress.
        """
        return self is EgressConsent.GRANTED


# Single-slot registries — the sync package registers one concrete
# implementation per slot at startup.  Using ``None`` as the sentinel
# means "no implementation registered" which is the correct initial
# state for CORE modules that are loaded before INTEGRATION packages.
_egress_consent_resolver: Callable[[Path], EgressConsent] | None = None
_saas_client_factory: Callable[[Path], Any | None] | None = None


def _callable_key(fn: Callable[..., Any]) -> str:
    """Return a stable identity key for a registered callable.

    Uses ``__module__`` + ``__qualname__`` (falling back to ``__name__``)
    so that the same logical callable is treated as identical across
    module reloads that produce fresh function objects.
    """
    module = getattr(fn, "__module__", None)
    qualname = getattr(fn, "__qualname__", None)
    name = qualname if isinstance(qualname, str) else getattr(fn, "__name__", None)
    if isinstance(module, str) and isinstance(name, str):
        return f"{module}.{name}"
    if isinstance(name, str):
        return name
    return repr(fn)


def register_egress_consent_resolver(
    fn: Callable[[Path], EgressConsent],
) -> None:
    """Register the egress-consent resolver (idempotent by qualified name).

    The resolver is asked "does the project that owns this checkout consent to
    hosted sync, and — when it does not — why not?" and must answer with an
    :class:`EgressConsent` member (the decision-carrying return; the split
    mapping from the underlying consent record lives in the resolver itself,
    not here — see :func:`resolve_egress_consent`).  It is *not* asked "is sync
    configured for this checkout" — that question was what this slot used to
    hold, and answering it is how one project's Ops travelled under another
    project's configuration (#3030 FR-025).

    Called once at sync package startup. **Re-registration replaces the
    existing resolver unconditionally.** Not "when the qualified name
    matches" — both arms of the ``existing_key == new_key`` branch below
    assign ``fn``, so the comparison changes nothing but the control flow
    taken to reach the same assignment; a callable with a *different*
    ``__qualname__`` replaces the entry just as completely. The invariant
    that does hold is the one that matters: at most one resolver is ever
    registered, so re-importing or reloading ``specify_cli.sync`` (e.g. in
    test processes) is safe and does not stack multiple resolvers.

    The dead comparison itself is left in place: it is pre-existing,
    identical in the sibling registrar below (:func:`register_saas_client_factory`),
    and removing it from both is a behaviour-preserving simplification
    outside this mission's scope.

    Not thread-safe by design (registration runs before concurrent
    access begins).
    """
    global _egress_consent_resolver  # noqa: PLW0603
    new_key = _callable_key(fn)
    if _egress_consent_resolver is not None:
        existing_key = _callable_key(_egress_consent_resolver)
        if existing_key == new_key:
            _egress_consent_resolver = fn
            return
    _egress_consent_resolver = fn


def register_saas_client_factory(
    fn: Callable[[Path], Any | None],
) -> None:
    """Register the SaaS-client factory (idempotent by qualified name).

    Nothing registers a factory today (#3030 FR-032) — the seam exists but
    is never called in production. See :func:`propagator._get_saas_client`
    for the canonical record of why this stays empty and the ``request_text``
    hazard a future registration would open. (No line range: the symbol is the
    durable anchor. An earlier draft cited ``propagator.py:70-83``, but the
    function begins at ``:58`` and nothing pins those numbers.)
    **Re-registration replaces the existing factory unconditionally.** Not "when
    the qualified name matches" — that was this docstring's last remaining false
    sentence, and FR-018 is precisely about not leaving one here. Both arms of the
    ``existing_key == new_key`` branch below assign ``fn``, so the comparison
    changes nothing but the control flow taken to reach the same assignment; a
    callable with a *different* ``__qualname__`` replaces the entry just as
    completely. The invariant that does hold is the one that matters: at most one
    factory is ever registered, so reloading ``specify_cli.sync`` cannot stack
    several.

    The dead comparison itself is left in place: it is pre-existing, identical in
    the sibling registrar above, and removing it from both is a behaviour-preserving
    simplification outside this mission's scope. Filed rather than folded — see the
    mission's follow-up record.
    """
    global _saas_client_factory  # noqa: PLW0603
    new_key = _callable_key(fn)
    if _saas_client_factory is not None:
        existing_key = _callable_key(_saas_client_factory)
        if existing_key == new_key:
            _saas_client_factory = fn
            return
    _saas_client_factory = fn


def resolve_egress_consent(path: Path) -> EgressConsent:
    """Ask the registered resolver whether *path*'s project consents to egress.

    Never raises, and never degrades to permission:

    - no resolver registered → :attr:`EgressConsent.NO_RESOLVER`
    - resolver raised → :attr:`EgressConsent.UNANSWERABLE`
    - resolver answered with something that is not a recognized
      :class:`EgressConsent` member → :attr:`EgressConsent.UNANSWERABLE` (this
      catches a resolver written against the retired ``bool | None`` contract:
      returning ``True``/``False``/``None`` used to be the whole contract, and a
      resolver that survives a rewrite and keeps returning a bare value must
      not keep being read as an answer — a raw non-:class:`EgressConsent` value
      must never reach a :attr:`permits_egress` call)
    - a recognized :class:`EgressConsent` member → that member, unchanged (the
      split mapping from the underlying consent record lives in the resolver
      itself — see :func:`register_egress_consent_resolver` — not here)

    A raising resolver is logged at WARNING, not DEBUG.  It is not routine
    degradation: some project's audit trail is being dropped, and #3030 FR-023
    counted five distinct config shapes that make the consent chain raise.
    """
    if _egress_consent_resolver is None:
        return EgressConsent.NO_RESOLVER
    try:
        answer = _egress_consent_resolver(path)
    except Exception:  # noqa: BLE001
        logger.warning(
            "egress-consent resolver raised for %s; refusing to propagate (consent could not be determined, which is not consent)",
            path,
            exc_info=True,
        )
        return EgressConsent.UNANSWERABLE
    if isinstance(answer, EgressConsent):
        return answer
    logger.warning(
        "egress-consent resolver returned %r (not an EgressConsent) for %s; refusing to propagate",
        answer,
        path,
    )
    return EgressConsent.UNANSWERABLE


def get_saas_client(path: Path) -> Any | None:
    """Dispatch to the registered SaaS-client factory.

    Returns the factory's result, or ``None`` when:
    - no factory has been registered (safe-degrade on missing sync package), or
    - the registered factory raises any exception.

    Never raises.

    **No production code registers a factory today** (#3030 FR-032), so in a real
    process this is the first branch, every time. The ``sync`` package used to
    register one whose entire body read ``token_manager._ws_client`` — an attribute
    nothing in ``src/`` assigns — making it a ``None``-returning phantom; it was
    deleted rather than wired up, because wiring it would have turned three egress
    paths live at once in the middle of a confidentiality incident. The slot survives
    as the seam a real transport would be registered into; whoever does that owns
    proving the consent gate above each consumer holds.
    """
    if _saas_client_factory is None:
        return None
    try:
        return _saas_client_factory(path)
    except Exception:  # noqa: BLE001
        logger.debug(
            "SaaS-client factory raised; safe-degrading to None",
            exc_info=True,
        )
        return None


def reset_adapters() -> None:
    """Clear both registered slots (test-only utility).

    Call only from test teardown to prevent state bleed between tests.
    Production code must never call this.
    """
    global _egress_consent_resolver, _saas_client_factory  # noqa: PLW0603
    _egress_consent_resolver = None
    _saas_client_factory = None
