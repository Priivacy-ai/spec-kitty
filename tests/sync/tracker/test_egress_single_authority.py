"""Acceptance harness for mission ``egress-single-authority-01KZN7CB`` (WP01).

ATDD, red-first. This mission collapses the tracker-egress gate's two independent
consent/routing evaluations (the enforcing resolver in ``sync/__init__.py`` and the
reporting classifier ``egress_verdict._classify_channel1``) into one, sourcing the
reported ``channel1_state`` from the same :class:`~specify_cli.sync.consent.ConsentDecision`
that enforces the grant/refuse outcome. See ``kitty-specs/egress-single-authority-01KZN7CB/``
for spec.md / plan.md / data-model.md / quickstart.md / contracts/egress-consent-contract.md.

Six subtasks, two kinds of check (WP01's own Definition of Done):

* **Invariance guards -- green throughout** (T001 enforcement-equivalence matrix incl. the
  permit row and every consent-precedence level, T002 hosted byte-identity + the SaaS
  widen-transport string, T005 no-local-import-of-``sync.consent``/``sync.routing`` in
  ``egress.py`` and the ``root is None`` -> ``undetermined`` pin).
* **Behavior-change cells -- red now, green only after WP03** (T003 exactly-one-resolution,
  T004 the degraded-return enumeration driving ``channel1_state`` from the single authority,
  T005's iterate-all-``EgressConsent``-members guard over the *split* member set, T006's
  ``_classify_channel1``-absence pin and the degraded-state-improvement golden).

Every golden is captured **in-test**, from the live pre-change code path, never hand-typed --
so a literal that happens to match today's output cannot pass a check meant to catch drift.

Fixture builders (``_write_config``, ``_project_block``, ``_no_record_root``,
``_recorded_refusal_root``, ``_recorded_grant_root``, ``_not_consentable_root``,
``_with_tracker_egress``) are copied from the proven sibling harness
``tests/sync/tracker/test_tracker_egress_verdict_3108.py``, which this file complements
(that file owns SC-001's narrower "8-cell join" pins; this file owns the mission's own
single-authority acceptance criteria).
"""

from __future__ import annotations

import ast
import inspect
import re
import subprocess
import sys
import uuid as uuid_module
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from specify_cli.cli.commands import sync as sync_module
from specify_cli.egress import UNDETERMINED_PROJECT_REFUSAL, project_egress_refusal
from specify_cli.invocation import propagator
from specify_cli.invocation.adapters import EgressConsent, resolve_egress_consent
from specify_cli.invocation.record import OpStartedEvent
from specify_cli.saas_client.client import SAAS_EGRESS_IDENTIFIER_KINDS
from specify_cli.saas_client.errors import SaasConsentError
from specify_cli.tracker.config import EGRESS_PERMITTED, EGRESS_REFUSED
from specify_cli.tracker.egress_verdict import (
    CHANNEL1_UNDETERMINED,
    OUTCOME_PERMIT,
    OUTCOME_REFUSE,
    EgressDestination,
    TrackerEgressVerdict,
    _JOIN,
    _refusing_channels,
    _resolve_channel2,
    tracker_egress_verdict,
)
from specify_cli.tracker.local_service import LOCAL_SUBPROCESS_EGRESS_IDENTIFIER_KINDS
from specify_cli.tracker.saas_client import TRACKER_EGRESS_IDENTIFIER_KINDS

# `integration`, not `[unit, fast]`: this file spawns subprocesses (the module-level
# no-import-time-`specify_cli.sync` probe, T005) and drives the machine-global,
# home-scoped consent index (T001's `granted_machine_index` row) -- both are Rule-2
# violators of the `fast` lane's sub-second, no-subprocess-fan-out contract, per
# `tests/architectural/test_pytest_marker_correctness.py`.
pytestmark = [pytest.mark.integration]

DESTINATIONS: tuple[EgressDestination, ...] = (
    EgressDestination.LOCAL_SUBPROCESS,
    EgressDestination.HOSTED_SERVICE,
)

#: The identifier-set fragment each destination's **owning transport** passes -- imported
#: from those transports rather than restated, so a fragment reworded in production cannot
#: leave this suite asserting stale text.
_IDENTIFIERS_FOR: dict[EgressDestination, str] = {
    EgressDestination.LOCAL_SUBPROCESS: LOCAL_SUBPROCESS_EGRESS_IDENTIFIER_KINDS,
    EgressDestination.HOSTED_SERVICE: TRACKER_EGRESS_IDENTIFIER_KINDS,
}


# ---------------------------------------------------------------------------
# Fixture helpers -- copied from tests/sync/tracker/test_tracker_egress_verdict_3108.py
# (the proven per-state builders named in the WP01 prompt).
# ---------------------------------------------------------------------------


def _write_config(root: Path, tracker_block: str = "", *, project_block: str | None = None) -> Path:
    """Write a minimal ``.kittify/config.yaml``.

    ``project_block`` supplies the ``project:`` section verbatim (indented already) when the
    scenario needs a resolvable identity; omitted entirely for the "not consentable" scenario.
    """
    config_path = root / ".kittify" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    parts = []
    if project_block is not None:
        parts.append(project_block)
    if tracker_block:
        parts.append(tracker_block)
    config_path.write_text("".join(parts), encoding="utf-8")
    return config_path


def _project_block(project_uuid: str | None = None) -> str:
    # A *fresh* uuid per call, never a shared constant -- see the sibling suite's own
    # comment: the consent index is machine-global and uuid-keyed and outlives any single
    # test's tmp_path, so a shared uuid would let one test's recorded decision leak into
    # another's "no record" fixture as a stale machine-index hit.
    project_uuid = project_uuid or str(uuid_module.uuid4())
    return (
        "project:\n"
        f"  uuid: {project_uuid}\n"
        "  slug: egress-single-authority-suite\n"
        "  node_id: node00000001\n"
        "  repo_slug: spec-kitty-tests/egress-single-authority-suite\n"
        f"  build_id: {project_uuid}\n"
    )


def _no_record_root(tmp_path: Path, name: str = "no-record") -> Path:
    """A checkout with a resolvable identity but no Channel-1 record at all."""
    root = tmp_path / name
    _write_config(root, project_block=_project_block())
    return root


def _recorded_refusal_root(tmp_path: Path, name: str = "recorded-refusal") -> Path:
    """A checkout with an identity and an explicit ``sync.enabled: false``."""
    root = tmp_path / name
    _write_config(root, "sync:\n  enabled: false\n", project_block=_project_block())
    return root


def _recorded_grant_root(tmp_path: Path, name: str = "recorded-grant") -> Path:
    """A checkout with an identity and an explicit ``sync.enabled: true`` (Channel 1 permits)."""
    root = tmp_path / name
    _write_config(root, "sync:\n  enabled: true\n", project_block=_project_block())
    return root


def _not_consentable_root(tmp_path: Path, name: str = "not-consentable") -> Path:
    """A checkout with no ``project:`` block at all -- identity never resolves."""
    root = tmp_path / name
    _write_config(root)
    return root


def _with_tracker_egress(root: Path, egress_line: str) -> None:
    """Append a ``tracker: {egress: ...}`` block onto an already-written config."""
    config_path = root / ".kittify" / "config.yaml"
    existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    config_path.write_text(existing + "tracker:\n" + egress_line, encoding="utf-8")


def _assert_never_raises(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Call *fn*, converting any raised exception into a named ``pytest.fail`` -- NFR-003's
    "never raises" contract, checked with a diagnosable failure rather than a bare traceback.
    """
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 - the failure this helper exists to catch
        pytest.fail(f"{fn!r} raised {type(exc).__name__}: {exc}")


class _CapturingConsole:
    """A minimal ``console_out`` stand-in for the ``sync doctor`` renderer: collects printed
    strings, nothing else. Copied from
    ``tests/cli/commands/test_sync_doctor_tracker_egress_3108.py``, the same capture surface
    T006 is asked to drive (U1: the renderer, not a full ``spec-kitty`` subprocess).
    """

    def __init__(self) -> None:
        self.lines: list[str] = []

    def print(self, text: str = "") -> None:
        self.lines.append(text)

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


_RICH_MARKUP_RE = re.compile(r"\[/?[a-zA-Z_ ]+\]")


def _strip_markup(text: str) -> str:
    """Drop rich's ``[tag]``/``[/tag]`` markup -- ``_CapturingConsole`` is a bare stand-in,
    not a real ``rich.console.Console``, so it stores raw markup verbatim rather than
    interpreting it. Copied from the sibling doctor suite's own helper.
    """
    return _RICH_MARKUP_RE.sub("", text)


def _flat(text: str) -> str:
    return " ".join(_strip_markup(text).split())


@pytest.fixture(autouse=True)
def _isolated_sync_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolated ``SPEC_KITTY_HOME`` per test, and the env-var consent level disarmed by
    default (mirrors ``tests/sync/test_consent_resolver_3030.py``'s own autouse fixture).

    Required because T001's ``granted_machine_index`` row writes to the machine-global,
    uuid-keyed consent index, and several T004 cases assert on the env-armed / disarmed
    boundary explicitly -- neither may bleed into the real ``~/.spec-kitty`` or across tests.
    """
    home = tmp_path / "spec-kitty-home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)


# ---------------------------------------------------------------------------
# T001 -- Enforcement-equivalence matrix (SC-001 / NFR-001). Invariance guard:
# green throughout. Independently re-derives the enforced (refused,
# refusing_channels) pair from the primitives the mission pins unchanged
# (`resolve_egress_consent(...).permits_egress`, `_resolve_channel2`, `_JOIN`,
# `_refusing_channels`) rather than from `tracker_egress_verdict`'s own
# diagnostic composition -- which is exactly what WP02/WP03 are permitted to
# change. A regression that flips any cell's enforced answer reds here
# regardless of how the diagnostic-reporting internals are refactored.
# ---------------------------------------------------------------------------

#: One row per consent-precedence level (project-local / machine-index / env) plus the
#: three refusal shapes NFR-001 names explicitly. `env` can never itself grant
#: (`consent.py::_answer_env` always returns `None` -- machine-global arming, never a
#: per-project decision), so its row proves the *refusal* is unchanged with that level
#: armed rather than proving an unreachable "granted via env" state.
_CHANNEL1_ROW_LABELS: tuple[str, ...] = (
    "granted_project_local",
    "granted_machine_index",
    "no_record",
    "no_record_env_armed",
    "recorded_refusal",
    "not_consentable",
)

#: Channel 2's full value set (FR-005): absent, the two legal values, and a fault (an
#: illegal near-miss string).
_CHANNEL2_CASES: tuple[tuple[str, str | None], ...] = (
    ("absent", None),
    (EGRESS_REFUSED, EGRESS_REFUSED),
    (EGRESS_PERMITTED, EGRESS_PERMITTED),
    ("fault", "yes"),
)

_T001_CELLS_EXERCISED: set[tuple[str, str, str]] = set()


def _build_channel1_root(tmp_path: Path, label: str, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a checkout whose real Channel-1 answer is decided at *label*'s named row."""
    root = tmp_path / "checkout"
    if label == "granted_project_local":
        _write_config(root, "sync:\n  enabled: true\n", project_block=_project_block())
    elif label == "granted_machine_index":
        uuid = str(uuid_module.uuid4())
        _write_config(root, project_block=_project_block(uuid))
        from specify_cli.sync.consent import set_project_consent

        set_project_consent(uuid, True)
    elif label == "no_record":
        _write_config(root, project_block=_project_block())
    elif label == "no_record_env_armed":
        monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
        _write_config(root, project_block=_project_block())
    elif label == "recorded_refusal":
        _write_config(root, "sync:\n  enabled: false\n", project_block=_project_block())
    elif label == "not_consentable":
        _write_config(root)
    else:  # pragma: no cover - exhaustiveness guard
        raise AssertionError(f"unhandled row label: {label!r}")
    return root


def _golden_outcome(root: Path, destination: EgressDestination) -> tuple[bool, frozenset[str]]:
    """Independently re-derive the enforced ``(refused, refusing_channels)`` pair.

    Built only from the primitives the mission's own contract pins unchanged: the
    enforcing boolean (``resolve_egress_consent(...).permits_egress``, unaffected by the
    ``EgressConsent`` split -- ``permits_egress`` stays true only for ``GRANTED``), and
    ``egress_verdict``'s own ``_resolve_channel2`` / ``_JOIN`` / ``_refusing_channels`` --
    none of which the mission's data-model changes. This deliberately does **not**
    recompute ``channel1_state`` or ``message``, which the mission is permitted to change.
    """
    channel1_permits = resolve_egress_consent(root).permits_egress
    channel2_state, _channel2_raw = _resolve_channel2(root)
    outcome = _JOIN[(channel2_state, destination)]
    if outcome == OUTCOME_PERMIT:
        return False, frozenset()
    if outcome == OUTCOME_REFUSE:
        return True, _refusing_channels(
            channel2_refuses=True, channel1_permits=channel1_permits, overall_refused=True
        )
    # OUTCOME_DEFER / OUTCOME_DEFER_REPORTED_NOOP -- Channel 1 decides.
    refused = not channel1_permits
    return refused, _refusing_channels(
        channel2_refuses=False, channel1_permits=channel1_permits, overall_refused=refused
    )


class TestT001EnforcementEquivalenceMatrix:
    @pytest.mark.parametrize("channel1_label", _CHANNEL1_ROW_LABELS)
    @pytest.mark.parametrize(
        "channel2_label,channel2_value", _CHANNEL2_CASES, ids=[c[0] for c in _CHANNEL2_CASES]
    )
    @pytest.mark.parametrize("destination", DESTINATIONS, ids=["local_subprocess", "hosted_service"])
    def test_cell_matches_the_independently_derived_golden(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        channel1_label: str,
        channel2_label: str,
        channel2_value: str | None,
        destination: EgressDestination,
    ) -> None:
        root = _build_channel1_root(tmp_path, channel1_label, monkeypatch)
        if channel2_value is not None:
            _with_tracker_egress(root, f"  egress: {channel2_value}\n")

        golden_refused, golden_refusing_channels = _golden_outcome(root, destination)
        verdict = tracker_egress_verdict(
            root, destination=destination, identifiers=_IDENTIFIERS_FOR[destination]
        )

        assert verdict.refused == golden_refused, (
            f"{channel1_label}/{channel2_label}/{destination.value}: enforced `refused` "
            f"drifted from the golden (NFR-001) -- golden={golden_refused}, "
            f"verdict={verdict.refused}"
        )
        assert verdict.refusing_channels == golden_refusing_channels, (
            f"{channel1_label}/{channel2_label}/{destination.value}: `refusing_channels` "
            f"drifted from the golden -- golden={sorted(golden_refusing_channels)}, "
            f"verdict={sorted(verdict.refusing_channels)}"
        )
        # No previously-refused cell may now permit: the equality assertion above already
        # forbids this (a golden-refused cell whose verdict flips to `refused=False` fails
        # it directly), so this is the same invariant, not a separate re-check.
        if golden_refused:
            assert verdict.refused is True

        _T001_CELLS_EXERCISED.add((channel1_label, channel2_label, destination.value))

    def test_matrix_ran_every_cell_incl_permit_row_and_every_precedence_level(self) -> None:
        """Non-vacuity (reviewer guidance): the matrix must have actually *executed* the
        permit row and every consent-precedence level, not merely declared them.
        """
        expected_total = len(_CHANNEL1_ROW_LABELS) * len(_CHANNEL2_CASES) * len(DESTINATIONS)
        print(f"T001 matrix: ran {len(_T001_CELLS_EXERCISED)} of {expected_total} declared cells")
        assert len(_T001_CELLS_EXERCISED) == expected_total  # golden-count: cardinality-is-contract

        exercised_channel1_labels = {cell[0] for cell in _T001_CELLS_EXERCISED}
        assert exercised_channel1_labels == set(_CHANNEL1_ROW_LABELS), (
            "every consent-precedence-level row (project-local/machine-index/env) and both "
            "refusal-shape rows must have executed"
        )
        exercised_channel2_labels = {cell[1] for cell in _T001_CELLS_EXERCISED}
        assert EGRESS_PERMITTED in exercised_channel2_labels, (
            "the permit row (SC-001/NFR-001's own explicit mandate) must be exercised"
        )


# ---------------------------------------------------------------------------
# T002 -- Hosted byte-identity + saas_client string (SC-002 / NFR-002 / FR-004).
# Invariance guard: green throughout.
# ---------------------------------------------------------------------------


class TestT002HostedByteIdentity:
    def test_hosted_channel1_message_is_byte_identical_across_the_three_refusal_states(
        self, tmp_path: Path
    ) -> None:
        """NFR-002: byte-identical **for the same project root** across all three refusal
        reasons -- ``_DENIED_TEMPLATE`` embeds ``{project_root}`` but never the refusal
        *reason*, so the root must be held fixed while only the on-disk state (and
        therefore which of the three reasons applies) varies. Comparing across three
        differently-named roots would conflate "the template doesn't vary by reason" with
        "the template doesn't vary by root", which NFR-002 does not claim.
        """
        identifiers = TRACKER_EGRESS_IDENTIFIER_KINDS
        root = tmp_path / "checkout"
        uuid = str(uuid_module.uuid4())

        # State 1: no record at all. Golden captured live, not hand-typed.
        _write_config(root, project_block=_project_block(uuid))
        golden = project_egress_refusal(root, identifiers)
        assert golden is not None

        # State 2: recorded refusal, same root.
        _write_config(root, "sync:\n  enabled: false\n", project_block=_project_block(uuid))
        assert project_egress_refusal(root, identifiers) == golden, (
            "recorded_refusal: HOSTED_SERVICE refusal text must be byte-identical across "
            "all three refusal states (NFR-002)"
        )

        # State 3: not consentable, same root (identity removed).
        _write_config(root)
        assert project_egress_refusal(root, identifiers) == golden, (
            "not_consentable: HOSTED_SERVICE refusal text must be byte-identical across "
            "all three refusal states (NFR-002)"
        )

        # And the verdict's own `.message` at HOSTED_SERVICE renders the identical string
        # (the composer must never recompose it -- FR-016's carve-out).
        verdict = tracker_egress_verdict(
            root, destination=EgressDestination.HOSTED_SERVICE, identifiers=identifiers
        )
        assert verdict.message == golden

    def test_saas_consent_error_string_is_byte_identical_and_not_covered_by_the_hosted_pin(
        self, tmp_path: Path
    ) -> None:
        """FR-004: ``saas_client/client.py``'s ``SaasConsentError`` string is a *separate*
        pin from T002's hosted-tracker pin above -- the two transports pass different
        identifier fragments, so they are provably independent checks, not one check
        exercised twice. Same fixed-root discipline as the pin above (NFR-002 varies the
        refusal *reason*, not the root).
        """
        assert SAAS_EGRESS_IDENTIFIER_KINDS != TRACKER_EGRESS_IDENTIFIER_KINDS, (
            "the widen-mode SaaS client's identifier fragment must differ from the "
            "tracker's, or this pin and T002's hosted pin would be the same assertion"
        )

        identifiers = SAAS_EGRESS_IDENTIFIER_KINDS
        root = tmp_path / "checkout"
        uuid = str(uuid_module.uuid4())

        _write_config(root, project_block=_project_block(uuid))
        golden = str(SaasConsentError(project_egress_refusal(root, identifiers)))

        _write_config(root, "sync:\n  enabled: false\n", project_block=_project_block(uuid))
        refusal = project_egress_refusal(root, identifiers)
        assert str(SaasConsentError(refusal)) == golden, (
            "recorded_refusal: SaasConsentError(project_egress_refusal(...)) must be "
            "byte-identical across all three refusal states"
        )

        _write_config(root)
        refusal = project_egress_refusal(root, identifiers)
        assert str(SaasConsentError(refusal)) == golden, (
            "not_consentable: SaasConsentError(project_egress_refusal(...)) must be "
            "byte-identical across all three refusal states"
        )


# ---------------------------------------------------------------------------
# T003 -- One-resolution count (SC-003 / NFR-004). Behavior-change cell: RED
# now (the current tree resolves each twice -- once via the registered
# enforcing resolver, once via `_classify_channel1`'s independent re-derivation).
# This is also C-003's rebuild of the deleted `TestReportingSplitNeverFlipsEnforcement`
# guarantee: that test forced the second authority to disagree and proved the
# enforced answer did not move; this test proves there is no longer a second
# authority to disagree with, by counting.
# ---------------------------------------------------------------------------


class TestT003OneResolutionEach:
    def test_gated_verdict_resolves_routing_and_consent_exactly_once(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from specify_cli.sync import consent as consent_module
        from specify_cli.sync import routing as routing_module

        routing_calls: list[Path] = []
        real_routing = routing_module.resolve_checkout_sync_routing_readonly

        def _counting_routing(root: Path) -> Any:
            routing_calls.append(root)
            return real_routing(root)

        consent_calls: list[tuple[Any, ...]] = []
        real_consent = consent_module.resolve_project_consent

        def _counting_consent(*args: Any, **kwargs: Any) -> Any:
            consent_calls.append(args)
            return real_consent(*args, **kwargs)

        monkeypatch.setattr(routing_module, "resolve_checkout_sync_routing_readonly", _counting_routing)
        monkeypatch.setattr(consent_module, "resolve_project_consent", _counting_consent)

        # A refusing root: reaches both the enforcing resolver (always) and, on the
        # current (pre-WP03) tree, the independent `_classify_channel1` re-derivation
        # (only invoked when Channel 1 refuses) -- so this fixture is the one that
        # actually exercises both call sites today.
        root = _recorded_refusal_root(tmp_path)
        tracker_egress_verdict(
            root,
            destination=EgressDestination.LOCAL_SUBPROCESS,
            identifiers=_IDENTIFIERS_FOR[EgressDestination.LOCAL_SUBPROCESS],
        )

        assert len(routing_calls) == 1, (
            f"red now (SC-003/NFR-004): expected exactly one checkout-routing resolution "
            f"per gated verdict, got {len(routing_calls)} -- the enforcing resolver and "
            f"the independent `_classify_channel1` each resolve it today; green once WP03 "
            f"sources channel1_state from the single authority"
        )
        assert len(consent_calls) == 1, (
            f"red now (SC-003/NFR-004): expected exactly one project-consent resolution "
            f"per gated verdict, got {len(consent_calls)}"
        )


# ---------------------------------------------------------------------------
# T004 -- NFR-003 fail-closed enumeration. Behavior-change cell: RED now for
# the generic-wording assertion (today's degraded *enforcing* return does not
# drive `channel1_state` -- the independent classifier re-derives a specific,
# unrelated label from the *real* routing/consent chain instead, ignoring the
# degraded resolver entirely). The "refuses" and "never raises" halves are
# already true today and stay true.
# ---------------------------------------------------------------------------

_DEGRADED_RESOLVER_CASES: tuple[str, ...] = (
    "bare_bool_false",
    "none",
    "unrecognized_value",
    "import_failure",
)


def _apply_degraded_resolver(case_name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject a degraded return via the registered-resolver slot, or (for the
    import-failure case) via a ``sys.modules`` blocker -- the two injection mechanisms
    the WP01 prompt names. The import-failure case never reaches the resolver slot at
    all (``project_egress_refusal``'s own ``import specify_cli.sync`` fails first).
    """
    import specify_cli.invocation.adapters as adapters_module

    if case_name == "bare_bool_false":
        monkeypatch.setattr(adapters_module, "_egress_consent_resolver", lambda _path: False)
    elif case_name == "none":
        monkeypatch.setattr(adapters_module, "_egress_consent_resolver", lambda _path: None)
    elif case_name == "unrecognized_value":
        monkeypatch.setattr(adapters_module, "_egress_consent_resolver", lambda _path: "not-a-real-answer")
    elif case_name == "import_failure":
        monkeypatch.setitem(sys.modules, "specify_cli.sync", None)
    else:  # pragma: no cover - exhaustiveness guard
        raise AssertionError(f"unhandled degraded case: {case_name!r}")


def _minimal_op_started_event() -> OpStartedEvent:
    return OpStartedEvent(
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


class TestT004NFR003DegradedEnumeration:
    @pytest.mark.parametrize("case_name", _DEGRADED_RESOLVER_CASES)
    @pytest.mark.parametrize("destination", DESTINATIONS, ids=["local_subprocess", "hosted_service"])
    def test_degraded_return_refuses_generic_and_never_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case_name: str, destination: EgressDestination
    ) -> None:
        # A resolvable identity with no record: `_classify_channel1`, unaware of the
        # degraded enforcing return, would today derive a concrete `no_record` label from
        # the *real* (unpatched) routing/consent chain -- exactly the divergence this test
        # exists to catch.
        root = _no_record_root(tmp_path)
        identifiers = _IDENTIFIERS_FOR[destination]
        _apply_degraded_resolver(case_name, monkeypatch)

        verdict = _assert_never_raises(
            tracker_egress_verdict, root, destination=destination, identifiers=identifiers
        )
        assert isinstance(verdict, TrackerEgressVerdict)
        assert verdict.refused is True, f"{case_name}: a degraded resolver must refuse, never permit"

        consent = _assert_never_raises(resolve_egress_consent, root)
        assert isinstance(consent, EgressConsent)
        assert consent.permits_egress is False, f"{case_name}: the permits_egress sink must not grant"

        # The propagator sink: consent-gated, must never raise regardless of the degraded
        # shape (NFR-003).
        _assert_never_raises(propagator._propagate_one, _minimal_op_started_event(), root)

        assert "could not be determined in detail" in verdict.message, (
            f"{case_name}: red now (NFR-003/T004) -- today's degraded enforcing return "
            f"does not drive channel1_state; the independent _classify_channel1 "
            f"re-derives a specific, unrelated label instead "
            f"(channel1_state={verdict.channel1_state!r}). Goes green once WP03 sources "
            f"channel1_state from the single authority."
        )


# ---------------------------------------------------------------------------
# T005 -- C-004 no-local-import + C-001 members + root-is-None (green + red mix).
# ---------------------------------------------------------------------------


class TestT005NoLocalImportMembersUndetermined:
    def test_egress_module_has_no_local_import_of_sync_consent_or_routing(self) -> None:
        """Invariance guard: green now, guards against relocation in WP02 (C-004).

        Parses imports (``ast``), not a substring scan -- so a comment or docstring
        mentioning ``sync.consent``/``sync.routing`` cannot false-positive, and an aliased
        or ``from``-form import cannot false-negative.
        """
        import specify_cli.egress as egress_module

        source = inspect.getsource(egress_module)
        tree = ast.parse(source)
        forbidden_submodules = {"consent", "routing"}
        violations: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    parts = alias.name.split(".")
                    if "sync" in parts:
                        idx = parts.index("sync")
                        if idx + 1 < len(parts) and parts[idx + 1] in forbidden_submodules:
                            violations.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                mod_parts = (node.module or "").split(".")
                if "sync" in mod_parts:
                    idx = mod_parts.index("sync")
                    if idx + 1 < len(mod_parts) and mod_parts[idx + 1] in forbidden_submodules:
                        violations.append(f"from {node.module} import ...")
                    if idx + 1 == len(mod_parts):
                        for alias in node.names:
                            if alias.name in forbidden_submodules:
                                violations.append(f"from {node.module} import {alias.name}")

        assert violations == [], (
            f"egress.py must hold no import of sync.consent/sync.routing (C-004): {violations}"
        )

    def test_egress_module_imports_cleanly_with_specify_cli_sync_blocked(self) -> None:
        """Dynamic belt-and-suspenders for the static AST pin above (mirrors the sibling
        3108 suite's own probe for ``egress_verdict.py``): run in a subprocess with
        ``specify_cli.sync`` blocked at import time, so a stale ``sys.modules`` cache in
        *this* process cannot hide a real dependency.
        """
        script = (
            "import sys\n"
            "class _Blocker:\n"
            "    def find_module(self, name, path=None):\n"
            "        if name == 'specify_cli.sync' or name.startswith('specify_cli.sync.'):\n"
            "            raise ImportError('specify_cli.sync is blocked for this probe')\n"
            "        return None\n"
            "sys.meta_path.insert(0, _Blocker())\n"
            "import specify_cli.egress\n"
            "print('IMPORTED_OK')\n"
        )
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=60)
        if "IMPORTED_OK" in result.stdout:
            return

        control = subprocess.run(
            [sys.executable, "-c", "import specify_cli.egress; print('CONTROL_OK')"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if "CONTROL_OK" not in control.stdout:
            pytest.skip(
                f"interpreter {sys.executable!r} cannot import specify_cli even without the "
                f"sync blocker (no editable install on its path) -- the import-isolation "
                f"probe is not meaningful here; control stderr={control.stderr!r}"
            )
        pytest.fail(
            f"specify_cli.egress import failed with specify_cli.sync blocked yet imports "
            f"fine without it -- a real import-time dependency on specify_cli.sync. "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )

    def test_split_members_permits_egress_false_except_granted(self) -> None:
        """Behavior-change cell: RED now (C-001).

        Asserts the *specific split member set* the data-model requires
        (``NO_RECORD``/``RECORDED_REFUSAL``/``NOT_CONSENTABLE`` replacing today's single
        ``DENIED``), not merely "every member but GRANTED refuses" -- that boolean
        property already trivially holds for today's four-member enum and would pass
        both before and after, hiding the very split this subtask exists to pin.
        """
        expected_member_names = {
            "GRANTED",
            "NO_RECORD",
            "RECORDED_REFUSAL",
            "NOT_CONSENTABLE",
            "NO_RESOLVER",
            "UNANSWERABLE",
        }
        actual_member_names = {member.name for member in EgressConsent}
        assert actual_member_names == expected_member_names, (
            f"red now (C-001): the split members do not exist yet -- found "
            f"{sorted(actual_member_names)}, expected {sorted(expected_member_names)}"
        )

        for member in EgressConsent:
            if member is EgressConsent.GRANTED:
                assert member.permits_egress is True, f"{member} must permit"
            else:
                assert member.permits_egress is False, f"{member} must refuse (C-001)"

    @pytest.mark.parametrize("destination", DESTINATIONS, ids=["local_subprocess", "hosted_service"])
    def test_root_none_produces_undetermined(self, destination: EgressDestination) -> None:
        """Invariance guard: green now and after (post-plan NOTE-2)."""
        verdict = tracker_egress_verdict(None, destination=destination, identifiers=_IDENTIFIERS_FOR[destination])
        assert verdict.channel1_state == CHANNEL1_UNDETERMINED
        assert verdict.refused is True
        assert verdict.message == UNDETERMINED_PROJECT_REFUSAL


# ---------------------------------------------------------------------------
# T006 -- sync doctor parity + degraded golden + symbol-absence (SC-005 / SC-004).
# ---------------------------------------------------------------------------


class TestT006SyncDoctorParityDegradedGoldenSymbolAbsence:
    @pytest.mark.parametrize(
        "builder",
        [_recorded_grant_root, _no_record_root, _recorded_refusal_root, _not_consentable_root],
        ids=["granted", "no_record", "recorded_refusal", "not_consentable"],
    )
    def test_renderer_parity_for_granted_and_three_refusal_states(
        self, tmp_path: Path, builder: Callable[[Path], Path]
    ) -> None:
        """Invariance guard: green throughout (SC-005).

        Captures the rendered state/remedy from the live renderer (capture surface U1 --
        the same ``_render_tracker_egress_row`` the sibling
        ``test_sync_doctor_tracker_egress_3108.py`` drives, not a full ``spec-kitty``
        subprocess) and asserts it is derived field-for-field from the verdict's own
        fields -- never a hand-typed literal -- so the same assertion holds both before
        and after WP03.
        """
        root = builder(tmp_path)
        for destination in DESTINATIONS:
            verdict = tracker_egress_verdict(
                root, destination=destination, identifiers=_IDENTIFIERS_FOR[destination]
            )
            console_out = _CapturingConsole()
            issues: list[str] = []
            sync_module._render_tracker_egress_row(console_out, issues, verdict, binding_present=True)
            flat_row = _flat(console_out.text)

            expected_verb = "REFUSED" if verdict.refused else "permitted"
            assert flat_row.startswith(f"{verdict.destination.value} {expected_verb}"), (
                f"{builder.__name__}/{destination.value}: row header must report the "
                f"verdict's own `refused` field: {flat_row!r}"
            )
            expected_state_wording = sync_module._CHANNEL1_STATE_WORDING[verdict.channel1_state]
            assert expected_state_wording in flat_row, (
                f"{builder.__name__}/{destination.value}: Channel-1 state "
                f"{verdict.channel1_state!r} must render as {expected_state_wording!r}"
            )
            assert _flat(verdict.message) in flat_row
            for remedy in verdict.remedies:
                assert _flat(remedy) in flat_row

    def test_import_failure_no_longer_masquerades_as_no_record(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Behavior-change cell: RED now (SC-005).

        The degraded states are an intended **improvement**, so this pins the new
        behaviour against a golden captured live from a genuine ``no_record`` checkout --
        never asserted "unchanged" (SC-005 forbids that framing explicitly). Today,
        import-failure masquerades as ``no_record``: same reported state, same rendered
        remedy, indistinguishable to the operator from a project that genuinely has no
        record at all.
        """
        root = _no_record_root(tmp_path)
        destination = EgressDestination.LOCAL_SUBPROCESS
        identifiers = _IDENTIFIERS_FOR[destination]

        golden_no_record_state = tracker_egress_verdict(
            root, destination=destination, identifiers=identifiers
        ).channel1_state

        monkeypatch.setitem(sys.modules, "specify_cli.sync", None)
        degraded_verdict = tracker_egress_verdict(root, destination=destination, identifiers=identifiers)

        assert degraded_verdict.refused is True
        assert degraded_verdict.channel1_state != golden_no_record_state, (
            f"red now (SC-005): import-failure must no longer masquerade as no_record -- "
            f"today it renders identically ({degraded_verdict.channel1_state!r} == "
            f"{golden_no_record_state!r})"
        )

    def test_classify_channel1_symbol_is_absent_from_egress_verdict(self) -> None:
        """Behavior-change cell: RED now (SC-004).

        ``_classify_channel1`` and its two non-authoritativeness pins are deleted, not
        migrated, once WP03 lands (C-002).
        """
        import specify_cli.tracker.egress_verdict as mod

        assert not hasattr(mod, "_classify_channel1"), (
            "red now (SC-004): _classify_channel1 must be deleted once channel1_state is "
            "sourced from the single authority, not carried forward"
        )
