"""Unit tests for specify_cli.invocation.adapters.

Covers the two seams' *different* degradation contracts, the register/dispatch
round-trip, idempotency by qualified name, and exception suppression.

The two seams degrade differently on purpose (#3030 FR-025). ``get_saas_client``
degrades to ``None`` — no transport, so nothing can leave. The consent seam
degrades to a **refusal**: it used to return ``bool | None`` where ``None`` meant
both "unregistered" and "the resolver raised", and the propagator tested
``is False``, so both undetermined cases were read as permission to transmit.
Every verdict here is asserted through ``permits_egress``, the one property the
propagator branches on, because asserting the member alone would not catch a
member that starts permitting egress.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.invocation.adapters import (
    EgressConsent,
    get_saas_client,
    register_egress_consent_resolver,
    register_saas_client_factory,
    reset_adapters,
    resolve_egress_consent,
)
from specify_cli.sync.consent import ConsentDecision, ConsentLevel

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# A dummy repo path — never touched on disk; only fed through the in-memory
# adapter registry (to mocked resolvers/factories). A rooted non-temp literal
# keeps it clear of the test-tree tmp-literal ratchet.
_DUMMY_PATH = Path("/repo")


@pytest.fixture(autouse=True)
def _clean_adapters() -> None:  # type: ignore[return]
    """Reset the adapter registry before and after every test."""
    reset_adapters()
    yield
    reset_adapters()


# ---------------------------------------------------------------------------
# resolve_egress_consent — an unanswered question is not consent
# ---------------------------------------------------------------------------


def test_resolve_egress_consent_refuses_when_unregistered() -> None:
    """No registered resolver must NOT permit egress.

    Distinguishable from a fault (``NO_RESOLVER`` names the cause: the sync
    package was never loaded) but identical in verdict.
    """
    result = resolve_egress_consent(_DUMMY_PATH)

    assert result is EgressConsent.NO_RESOLVER
    assert result.permits_egress is False


# ---------------------------------------------------------------------------
# get_saas_client — safe-degrade when no factory is registered
# ---------------------------------------------------------------------------


def test_get_saas_client_returns_none_when_unregistered() -> None:
    """Dispatching with no registered factory must return None."""
    result = get_saas_client(_DUMMY_PATH)
    assert result is None


# ---------------------------------------------------------------------------
# register_egress_consent_resolver — dispatch round-trip
# ---------------------------------------------------------------------------


def test_resolve_egress_consent_grants_from_registered_resolver() -> None:
    """A resolver answering ``EgressConsent.GRANTED`` is the ONE verdict that permits egress."""
    mock_resolver = MagicMock(return_value=EgressConsent.GRANTED)
    register_egress_consent_resolver(mock_resolver)

    result = resolve_egress_consent(_DUMMY_PATH)

    mock_resolver.assert_called_once_with(_DUMMY_PATH)
    assert result is EgressConsent.GRANTED
    assert result.permits_egress is True


def test_resolve_egress_consent_denies_from_registered_resolver() -> None:
    """A resolver answering a recognized refusal member is passed through unchanged.

    ``NO_RECORD`` stands in for all three refusal members split from the former
    ``DENIED`` — the port does not re-derive *why* the resolver refused, it only
    validates the returned value is a recognized :class:`EgressConsent` member.
    """
    register_egress_consent_resolver(lambda _path: EgressConsent.NO_RECORD)

    result = resolve_egress_consent(_DUMMY_PATH)

    assert result is EgressConsent.NO_RECORD
    assert result.permits_egress is False


def test_resolve_egress_consent_refuses_a_none_answer() -> None:
    """A resolver written against the RETIRED ``bool | None`` contract refuses.

    ``None`` was the value that meant "proceed" at the old call site. A resolver
    that survives a rewrite and keeps returning it must not keep meaning that —
    the seam cannot tell an obsolete resolver from a broken one, and neither is
    consent.
    """
    register_egress_consent_resolver(lambda _path: None)  # type: ignore[arg-type,return-value]

    result = resolve_egress_consent(_DUMMY_PATH)

    assert result is EgressConsent.UNANSWERABLE
    assert result.permits_egress is False


def test_resolve_egress_consent_refuses_a_bare_bool_answer() -> None:
    """A resolver written against the RETIRED ``bool``-returning contract refuses.

    The registered resolver's contract changed from ``Callable[[Path], bool]`` to
    ``Callable[[Path], EgressConsent]`` (egress-single-authority mission, T008): a
    bare ``True``/``False`` is no longer recognized as a member, so it must refuse
    exactly like ``None`` does — never a permit, never a raise, and the raw value
    must never reach a ``permits_egress`` call.
    """
    register_egress_consent_resolver(lambda _path: True)  # type: ignore[arg-type,return-value]

    result = resolve_egress_consent(_DUMMY_PATH)

    assert result is EgressConsent.UNANSWERABLE
    assert result.permits_egress is False


def test_only_granted_permits_egress() -> None:
    """Exactly one member of the enum permits egress — the whole point of it.

    Iterates the enum rather than listing members, so a member added later is
    covered by this assertion instead of quietly defaulting to permitted.
    """
    permitting = [member for member in EgressConsent if member.permits_egress]

    assert permitting == [EgressConsent.GRANTED]


# ---------------------------------------------------------------------------
# register_saas_client_factory — dispatch round-trip
# ---------------------------------------------------------------------------


def test_get_saas_client_calls_registered_factory() -> None:
    """After registration the factory is called with the path and result is returned."""
    fake_client = MagicMock()
    mock_factory = MagicMock(return_value=fake_client)
    register_saas_client_factory(mock_factory)

    result = get_saas_client(_DUMMY_PATH)

    mock_factory.assert_called_once_with(_DUMMY_PATH)
    assert result is fake_client


# ---------------------------------------------------------------------------
# Idempotency — re-registering the same qualified name replaces the entry
# ---------------------------------------------------------------------------


def test_register_egress_consent_resolver_idempotent_by_qualname() -> None:
    """Re-registering a resolver with the same qualname replaces it."""
    call_log: list[str] = []

    def _resolver_v1(path: Path) -> bool:  # noqa: ARG001
        call_log.append("v1")
        return True

    def _resolver_v2(path: Path) -> bool:  # noqa: ARG001
        call_log.append("v2")
        return False

    # Rename v2 to share v1's qualified name, simulating a module reload
    _resolver_v2.__qualname__ = _resolver_v1.__qualname__
    _resolver_v2.__module__ = _resolver_v1.__module__

    register_egress_consent_resolver(_resolver_v1)
    register_egress_consent_resolver(_resolver_v2)

    resolve_egress_consent(_DUMMY_PATH)

    # Only v2 (the replacement) should have been called
    assert call_log == ["v2"]


def test_register_saas_client_factory_idempotent_by_qualname() -> None:
    """Re-registering a factory with the same qualname replaces it."""
    call_log: list[str] = []

    def _factory_v1(path: Path) -> object:  # noqa: ARG001
        call_log.append("v1")
        return object()

    def _factory_v2(path: Path) -> object:  # noqa: ARG001
        call_log.append("v2")
        return object()

    _factory_v2.__qualname__ = _factory_v1.__qualname__
    _factory_v2.__module__ = _factory_v1.__module__

    register_saas_client_factory(_factory_v1)
    register_saas_client_factory(_factory_v2)

    get_saas_client(_DUMMY_PATH)

    assert call_log == ["v2"]


# ---------------------------------------------------------------------------
# Exception suppression — a raising handler degrades, but never to permission
# ---------------------------------------------------------------------------


def test_resolve_egress_consent_refuses_on_resolver_exception() -> None:
    """A raising resolver is caught AND refused.

    The measured half of FR-025 that needed no bad configuration to reach: five
    ``config.yaml`` shapes (FR-023) make the consent chain raise, and the raise
    used to land on the same ``None`` as "no resolver", which the propagator sent
    through.
    """

    def _exploding_resolver(_path: Path) -> bool:
        raise RuntimeError("boom")

    register_egress_consent_resolver(_exploding_resolver)

    result = resolve_egress_consent(_DUMMY_PATH)

    assert result is EgressConsent.UNANSWERABLE
    assert result.permits_egress is False


def test_get_saas_client_returns_none_on_factory_exception() -> None:
    """An exception in the factory is caught; dispatch returns None."""

    def _exploding_factory(_path: Path) -> object:
        raise RuntimeError("boom")

    register_saas_client_factory(_exploding_factory)

    result = get_saas_client(_DUMMY_PATH)

    assert result is None


# ---------------------------------------------------------------------------
# register_saas_client_factory — export pin (SC-008, #3109 seam, Decision D-1)
# ---------------------------------------------------------------------------


def test_register_saas_client_factory_is_exported_from_invocation_package() -> None:
    """Pins the *export* half of the `#3109` seam (SC-008).

    D-1 keeps ``register_saas_client_factory`` rather than deleting it: the
    read side (``get_saas_client``) has a live production consumer inside the
    propagator's consent gate, so the write side stays too, to keep the empty
    seam legible as a decision rather than an oversight. A decision to keep
    something is not self-enforcing — nothing else in the diff would notice if
    the re-export quietly disappeared, so the keep half needs its own pin.

    This is the *export* half specifically, not the definition: deleting the
    ``def`` in ``adapters.py`` is already a collection-time ``ImportError`` in
    two other test modules (pinned by a node-id baseline), so it is not a
    discriminating before-state. What is genuinely unpinned today is
    ``invocation/__init__.py``'s re-export (``:21``) and its ``__all__`` entry
    (``:111``) — ``adapters.py`` itself declares no ``__all__``, nothing in
    ``src/`` imports the symbol via the package (``from specify_cli.invocation
    import ...``), and ``test_all_declarations_required.py`` gates only
    ``src/charter/`` and ``src/kernel/``, not this package.

    Verified red (in a throwaway worktree, never in this lane) by removing
    only ``__init__.py:21`` and ``:111`` — never by deleting the ``def``.
    """
    import specify_cli.invocation as invocation_pkg

    assert "register_saas_client_factory" in invocation_pkg.__all__
    # Identity, not just presence: the re-exported name must be the *same*
    # callable as the one this module already imports directly from
    # ``adapters`` — proof the package re-export is wired, not shadowed by an
    # unrelated same-named object.
    assert invocation_pkg.register_saas_client_factory is register_saas_client_factory


# ---------------------------------------------------------------------------
# Propagator safe-degrade via the seam (integration-style unit test)
# ---------------------------------------------------------------------------


def test_propagator_safe_degrades_when_seam_unregistered(tmp_path: Path) -> None:
    """propagator._propagate_one must not raise when no adapters are registered.

    With nothing registered the consent gate answers ``NO_RESOLVER`` and fires
    first, so no client lookup and no send happens. (Before FR-025 this early
    return came from the *auth* gate instead: the consent gate did not fire,
    because an unregistered seam was read as permission — a no-op that depended
    on there being no transport rather than on there being no consent.)
    This test imports propagator directly to verify the wiring without
    requiring the sync package.
    """
    from specify_cli.invocation import propagator
    from specify_cli.invocation.record import OpStartedEvent

    record = OpStartedEvent(
        invocation_id="01HXYZABCDEFGH1JK2MN3PQRST",
        profile_id="test-profile",
        action="implement",
        request_text="",
        actor="claude",
        mode_of_work="task_execution",
        governance_context_hash="abcdef0123456789",
        governance_context_available=False,
        started_at="2026-01-01T00:00:00Z",
    )

    # Must not raise; should silently return (sync-gate or auth-gate).
    propagator._propagate_one(record, tmp_path)


# ---------------------------------------------------------------------------
# Real registered factory contract tests (NFR-003 / Degradation Contract)
# These tests exercise the ACTUAL factory registered by specify_cli.sync —
# NOT a patched _get_saas_client — verifying the production registration.
# ---------------------------------------------------------------------------


@pytest.fixture()  # type: ignore[untyped-decorator]
def _registered_sync_handlers() -> Iterator[None]:
    """Reset adapters, register the real sync factories, then clean up.

    Uses SPEC_KITTY_SYNC_MINIMAL_IMPORT=1 to prevent module-level
    auto-registration; we call register_default_handlers explicitly so the
    registry is always in a known state when the test runs.
    """
    reset_adapters()
    os.environ["SPEC_KITTY_SYNC_MINIMAL_IMPORT"] = "1"
    try:
        from specify_cli.sync import register_default_handlers

        register_default_handlers()
        yield
    finally:
        os.environ.pop("SPEC_KITTY_SYNC_MINIMAL_IMPORT", None)
        reset_adapters()


def test_sync_registers_no_saas_client_factory(
    _registered_sync_handlers: None,
) -> None:
    """The sync package registers a consent resolver and **no** client factory (FR-032).

    Replaces three cases that pinned the behaviour of a factory since deleted
    (``..._returns_none_when_not_authenticated``,
    ``..._returns_none_when_ws_client_not_connected``,
    ``..._returns_existing_client_when_connected``). All three drove that factory by
    setting ``token_manager._ws_client`` — and setting it in a test was the **only**
    way that attribute has ever been assigned. ``src/`` contains no ``=`` and no
    ``setattr`` for it, and ``specify_cli/auth/`` does not declare it, so the factory
    returned ``None`` in every real process and ``invocation/propagator.py``'s send
    has never executed outside this suite. Two of the three were passing for the
    wrong reason (a ``None`` that agreed with their assertion by accident) and the
    third asserted a production behaviour that did not exist.

    The pin is inverted and kept live: a connected client on the token manager still
    yields no transport, because there is no factory to find it. This reds if anyone
    re-registers one — which is the hazard FR-032 removed, not a detail.
    """
    mock_ws = MagicMock()
    mock_ws.connected = True

    mock_tm = MagicMock()
    mock_tm.is_authenticated = True
    mock_tm.get_current_session.return_value = MagicMock()
    mock_tm._ws_client = mock_ws

    with patch("specify_cli.auth.get_token_manager", return_value=mock_tm):
        result = get_saas_client(_DUMMY_PATH)

    assert result is None, (
        "specify_cli.sync registered a SaaS-client factory. That opens the "
        "invocation propagator's egress path, which carries request_text verbatim; "
        "#3030 FR-032 removed it deliberately. If this is intended, prove the "
        "propagator's consent gate holds against the new transport first."
    )


def test_registered_consent_resolver_denies_non_project_path(
    _registered_sync_handlers: None,
) -> None:
    """A path that is no project denies cleanly — as NOT_CONSENTABLE, not as a fault.

    Answered with a recognized refusal member rather than by raising: the
    ordinary non-project traversal is not a fault and must not land on the
    fault log, while still refusing. This is the case the leak was measured on —
    it needs no bad configuration anywhere, only a ``repo_root`` that is not a
    project root.
    """
    with patch(
        "specify_cli.sync.routing.resolve_checkout_sync_routing_readonly",
        return_value=None,
    ):
        result = resolve_egress_consent(_DUMMY_PATH)

    assert result is EgressConsent.NOT_CONSENTABLE
    assert result.permits_egress is False


def test_registered_consent_resolver_denies_unidentifiable_project(
    _registered_sync_handlers: None,
) -> None:
    """Routing resolved but named no project → not consentable (NFR-001).

    This is the shape an unreadable or non-mapping ``.kittify/config.yaml`` takes
    after FR-022 / FR-023: routing answers with ``project_uuid=None`` instead of
    raising. There is no uuid to ask about, so the consent authority is not
    consulted at all.
    """
    mock_routing = MagicMock()
    mock_routing.project_uuid = None

    with (
        patch(
            "specify_cli.sync.routing.resolve_checkout_sync_routing_readonly",
            return_value=mock_routing,
        ),
        patch("specify_cli.sync.consent.resolve_project_consent") as mock_consent,
    ):
        result = resolve_egress_consent(_DUMMY_PATH)

    assert result is EgressConsent.NOT_CONSENTABLE
    mock_consent.assert_not_called()


def test_registered_consent_resolver_asks_the_funnel_for_the_projects_uuid(
    _registered_sync_handlers: None,
) -> None:
    """GRANTED comes from the consent authority, keyed on the project's own uuid.

    Pins the two arguments as well as the verdict: the uuid is the project's, and
    the checkout is offered as a level-1 root, without which a committed in-repo
    refusal would be unreachable at decision time. Also pins that the resolver is
    asked exactly once (egress-single-authority mission Decision 2 — one
    ``resolve_project_consent`` call, not a separate lookup plus a set-membership
    check).
    """
    mock_routing = MagicMock()
    mock_routing.project_uuid = "11111111-1111-4111-8111-111111111111"
    mock_routing.repo_root = _DUMMY_PATH

    granted_decision = ConsentDecision(
        granted=True,
        level=ConsentLevel.PROJECT_LOCAL,
        project_uuid="11111111-1111-4111-8111-111111111111",
        reason="recorded in the project's own config",
    )

    with (
        patch(
            "specify_cli.sync.routing.resolve_checkout_sync_routing_readonly",
            return_value=mock_routing,
        ),
        patch(
            "specify_cli.sync.consent.resolve_project_consent",
            return_value=granted_decision,
        ) as mock_consent,
    ):
        result = resolve_egress_consent(_DUMMY_PATH)

    assert result is EgressConsent.GRANTED
    mock_consent.assert_called_once_with(
        "11111111-1111-4111-8111-111111111111",
        checkout_roots=[_DUMMY_PATH],
    )


def test_registered_consent_resolver_denies_when_project_consent_is_recorded_refused(
    _registered_sync_handlers: None,
) -> None:
    """A recorded refusal for THIS uuid denies, regardless of any other project's state.

    Before this mission, the resolver tested membership of this uuid in a *set*
    returned by ``consented_project_uuids`` — testing for non-emptiness instead of
    membership was exactly the bug class this mission is about (one consenting
    project authorising a batch it does not belong to). Calling
    ``resolve_project_consent`` for one uuid at a time closes that class **by
    construction** (Decision 2): there is no set to mis-test membership against
    any more. This pins the by-construction claim for the shape that would have
    been the old bug's actual symptom — a refusing decision for the uuid asked
    about, mapped to the recorded-refusal member.
    """
    mock_routing = MagicMock()
    mock_routing.project_uuid = "11111111-1111-4111-8111-111111111111"
    mock_routing.repo_root = _DUMMY_PATH

    refusing_decision = ConsentDecision(
        granted=False,
        level=ConsentLevel.MACHINE_INDEX,
        project_uuid="11111111-1111-4111-8111-111111111111",
        reason="recorded refusal at the machine index",
    )

    with (
        patch(
            "specify_cli.sync.routing.resolve_checkout_sync_routing_readonly",
            return_value=mock_routing,
        ),
        patch(
            "specify_cli.sync.consent.resolve_project_consent",
            return_value=refusing_decision,
        ) as mock_consent,
    ):
        result = resolve_egress_consent(_DUMMY_PATH)

    assert result is EgressConsent.RECORDED_REFUSAL
    assert result.permits_egress is False
    mock_consent.assert_called_once_with(
        "11111111-1111-4111-8111-111111111111",
        checkout_roots=[_DUMMY_PATH],
    )


def test_registered_consent_resolver_denies_with_no_consent_record(
    _registered_sync_handlers: None,
) -> None:
    """An absent consent record maps to NO_RECORD, distinct from a recorded refusal.

    ``ConsentLevel.ABSENT`` is the terminal default ``resolve_project_consent``
    returns when nothing was ever recorded for the project — the split-mapping's
    other refusal branch (data-model, egress-single-authority mission).
    """
    mock_routing = MagicMock()
    mock_routing.project_uuid = "11111111-1111-4111-8111-111111111111"
    mock_routing.repo_root = _DUMMY_PATH

    absent_decision = ConsentDecision(
        granted=False,
        level=ConsentLevel.ABSENT,
        project_uuid="11111111-1111-4111-8111-111111111111",
        reason="no consent record for this project",
    )

    with (
        patch(
            "specify_cli.sync.routing.resolve_checkout_sync_routing_readonly",
            return_value=mock_routing,
        ),
        patch(
            "specify_cli.sync.consent.resolve_project_consent",
            return_value=absent_decision,
        ),
    ):
        result = resolve_egress_consent(_DUMMY_PATH)

    assert result is EgressConsent.NO_RECORD
    assert result.permits_egress is False
