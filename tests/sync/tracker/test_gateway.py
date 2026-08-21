"""Tests for the local Beads program gateway (TRK-M1-04).

TRK-M1-04 node criteria (docs/BEADS_PROGRAM_GRAPH.json): "Host adapter maps
Tracker calls through token-valid program gateway, preserves mission/task/
team/repository scope, exposes authority/freshness/conflicts, and cannot
assign/close/approve/release Beads or bypass self-claim/review/publication."

``specify_cli.tracker.gateway`` is the host-owned adapter that satisfies
this: a ``TrackerGatewayToken`` (a validated, scope-bound capability minted
by the host, never by ``spec_kitty_tracker`` or by Beads) and a
``GatewayCommandRunner`` implementing the
``spec_kitty_tracker.connectors.cli_runner.CommandRunner`` protocol
(TRK-M1-02 A4) that a ``BeadsConnector`` is wired through instead of the
package's default ``SubprocessCommandRunner``.

This first group covers ``TrackerGatewayToken`` in isolation: construction
validation, TTL-based freshness, and scope coverage (``covers``). No
``spec_kitty_tracker`` import is required for these -- ``covers`` only does
attribute access on its ``context`` argument, so a plain duck-typed stand-in
exercises it without depending on the installed tracker package version.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from specify_cli.tracker.gateway import (
    GatewayAuthorizationError,
    GatewayCommandRunner,
    GatewayForbiddenOperationError,
    GatewayScopeViolationError,
    TrackerGatewayToken,
    _try_import_scope_violation_error,
)

#: A scope violation raises spec_kitty_tracker.errors.ScopeViolationError when
#: the installed tracker package exposes it (0.5.x+, always true in this dev
#: venv per Pattern A -- docs/development/how-to/local-overrides.md), else
#: falls back to GatewayScopeViolationError. Both share the same
#: expected_scope/actual_scope attribute contract, so tests that only need
#: "some scope-violation error was raised, with the right attributes" assert
#: against whichever type is actually live rather than assuming one.
_SCOPE_VIOLATION_TYPE = _try_import_scope_violation_error() or GatewayScopeViolationError

pytestmark = [pytest.mark.unit, pytest.mark.fast]


@dataclass(frozen=True, slots=True)
class _FakeContext:
    """Duck-typed stand-in for ``spec_kitty_tracker.context.LocalExecutionContext``."""

    actor: str
    repository: str
    team: str | None = None
    mission_id: str | None = None
    task_id: str | None = None


# ---------------------------------------------------------------------------
# Construction validation
# ---------------------------------------------------------------------------


def test_token_minimal_construction() -> None:
    token = TrackerGatewayToken(token="tok-1", actor="ivan", repository="spec-kitty")

    assert token.actor == "ivan"
    assert token.repository == "spec-kitty"
    assert token.team is None
    assert token.mission_id is None
    assert token.task_id is None


def test_token_is_frozen() -> None:
    token = TrackerGatewayToken(token="tok-1", actor="ivan", repository="spec-kitty")

    with pytest.raises(AttributeError):
        token.actor = "someone-else"  # type: ignore[misc]


@pytest.mark.parametrize("value", ["", "   "])
def test_token_rejects_empty_token(value: str) -> None:
    with pytest.raises(ValueError):
        TrackerGatewayToken(token=value, actor="ivan", repository="spec-kitty")


@pytest.mark.parametrize("value", ["", "   "])
def test_token_rejects_empty_actor(value: str) -> None:
    with pytest.raises(ValueError):
        TrackerGatewayToken(token="tok-1", actor=value, repository="spec-kitty")


@pytest.mark.parametrize("value", ["", "   "])
def test_token_rejects_empty_repository(value: str) -> None:
    with pytest.raises(ValueError):
        TrackerGatewayToken(token="tok-1", actor="ivan", repository=value)


@pytest.mark.parametrize("ttl", [0, -1, -300.0])
def test_token_rejects_non_positive_ttl(ttl: float) -> None:
    with pytest.raises(ValueError):
        TrackerGatewayToken(token="tok-1", actor="ivan", repository="spec-kitty", ttl_seconds=ttl)


# ---------------------------------------------------------------------------
# Freshness (TTL)
# ---------------------------------------------------------------------------


def test_token_is_fresh_before_expiry() -> None:
    token = TrackerGatewayToken(token="tok-1", actor="ivan", repository="spec-kitty", issued_at=1000.0, ttl_seconds=60.0)

    assert token.expires_at == 1060.0
    assert token.is_fresh(now=1059.999) is True


def test_token_is_not_fresh_at_or_after_expiry() -> None:
    token = TrackerGatewayToken(token="tok-1", actor="ivan", repository="spec-kitty", issued_at=1000.0, ttl_seconds=60.0)

    assert token.is_fresh(now=1060.0) is False
    assert token.is_fresh(now=1200.0) is False


# ---------------------------------------------------------------------------
# Scope coverage
# ---------------------------------------------------------------------------


def test_broad_token_covers_matching_actor_and_repository_regardless_of_mission_task() -> None:
    token = TrackerGatewayToken(token="tok-1", actor="ivan", repository="spec-kitty")

    assert token.covers(_FakeContext(actor="ivan", repository="spec-kitty")) is True
    assert (
        token.covers(_FakeContext(actor="ivan", repository="spec-kitty", mission_id="m1", task_id="TRK-M1-04"))
        is True
    )


@pytest.mark.parametrize(
    "context",
    [
        _FakeContext(actor="debbie", repository="spec-kitty"),
        _FakeContext(actor="ivan", repository="spec-kitty-tracker"),
        _FakeContext(actor="debbie", repository="spec-kitty-tracker"),
    ],
)
def test_token_never_covers_mismatched_actor_or_repository(context: _FakeContext) -> None:
    token = TrackerGatewayToken(token="tok-1", actor="ivan", repository="spec-kitty")

    assert token.covers(context) is False


def test_narrow_token_requires_matching_mission_id() -> None:
    token = TrackerGatewayToken(token="tok-1", actor="ivan", repository="spec-kitty", mission_id="m1")

    assert token.covers(_FakeContext(actor="ivan", repository="spec-kitty", mission_id="m1")) is True
    assert token.covers(_FakeContext(actor="ivan", repository="spec-kitty", mission_id="m2")) is False
    assert token.covers(_FakeContext(actor="ivan", repository="spec-kitty", mission_id=None)) is False


def test_narrow_token_requires_matching_task_id() -> None:
    token = TrackerGatewayToken(
        token="tok-1", actor="ivan", repository="spec-kitty", mission_id="m1", task_id="TRK-M1-04"
    )

    assert (
        token.covers(_FakeContext(actor="ivan", repository="spec-kitty", mission_id="m1", task_id="TRK-M1-04"))
        is True
    )
    assert (
        token.covers(_FakeContext(actor="ivan", repository="spec-kitty", mission_id="m1", task_id="TRK-M1-05"))
        is False
    )


# ---------------------------------------------------------------------------
# GatewayCommandRunner
# ---------------------------------------------------------------------------


@dataclass
class _FakeInnerRunner:
    """Records every delegated call; returns a canned string."""

    output: str = "ok"
    calls: list[tuple[tuple[str, ...], str | None, _FakeContext | None]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.calls = []

    def run(self, command, *, cwd=None, context=None) -> str:
        self.calls.append((tuple(command), cwd, context))
        return self.output


def _token(**overrides) -> TrackerGatewayToken:
    defaults = {"token": "tok-1", "actor": "ivan", "repository": "spec-kitty", "issued_at": 1000.0, "ttl_seconds": 60.0}
    defaults.update(overrides)
    return TrackerGatewayToken(**defaults)


def _ctx(**overrides) -> _FakeContext:
    defaults = {"actor": "ivan", "repository": "spec-kitty"}
    defaults.update(overrides)
    return _FakeContext(**defaults)


def test_runner_delegates_an_allowed_command_to_the_inner_runner() -> None:
    inner = _FakeInnerRunner(output="bd-output")
    runner = GatewayCommandRunner(_token(), inner=inner, clock=lambda: 1001.0)
    ctx = _ctx()

    result = runner.run(["bd", "--json", "list"], cwd="/repo", context=ctx)

    assert result == "bd-output"
    assert inner.calls == [(("bd", "--json", "list"), "/repo", ctx)]


def test_runner_denies_when_token_is_expired() -> None:
    inner = _FakeInnerRunner()
    runner = GatewayCommandRunner(_token(ttl_seconds=60.0), inner=inner, clock=lambda: 1060.0)

    with pytest.raises(GatewayAuthorizationError):
        runner.run(["bd", "--json", "list"], context=_ctx())

    assert inner.calls == []


def test_runner_denies_when_context_is_missing() -> None:
    inner = _FakeInnerRunner()
    runner = GatewayCommandRunner(_token(), inner=inner, clock=lambda: 1001.0)

    with pytest.raises(GatewayAuthorizationError):
        runner.run(["bd", "--json", "list"], context=None)

    assert inner.calls == []


def test_runner_raises_scope_violation_for_mismatched_context() -> None:
    inner = _FakeInnerRunner()
    runner = GatewayCommandRunner(_token(), inner=inner, clock=lambda: 1001.0)

    with pytest.raises(_SCOPE_VIOLATION_TYPE) as exc_info:
        runner.run(["bd", "--json", "list"], context=_ctx(actor="debbie"))

    assert "ivan" in exc_info.value.expected_scope
    assert "debbie" in exc_info.value.actual_scope
    assert inner.calls == []


def test_scope_violation_falls_back_to_local_error_type_when_tracker_package_lacks_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the installed spec_kitty_tracker predates ScopeViolationError (0.4.x),
    the gateway still fails closed with its own equivalent error type instead of
    raising an unrelated ImportError."""
    import specify_cli.tracker.gateway as gateway_module

    monkeypatch.setattr(gateway_module, "_try_import_scope_violation_error", lambda: None)
    inner = _FakeInnerRunner()
    runner = GatewayCommandRunner(_token(), inner=inner, clock=lambda: 1001.0)

    with pytest.raises(gateway_module.GatewayScopeViolationError):
        runner.run(["bd", "--json", "list"], context=_ctx(repository="other-repo"))


@pytest.mark.parametrize(
    "command",
    [
        ["bd", "--json", "close", "BD-1"],
        ["bd", "--json", "assign", "BD-1", "ivan"],
        ["bd", "--json", "approve", "BD-1"],
        ["bd", "--json", "release", "BD-1"],
        ["bd", "--json", "create", "title", "--assignee", "ivan"],
        ["bd", "--json", "update", "BD-1", "--status", "closed"],
        ["bd", "--json", "update", "BD-1", "--status", "done"],
        ["bd", "--json", "update", "BD-1", "--status", "tombstone"],
    ],
)
def test_runner_refuses_assign_close_approve_release_operations(command: list[str]) -> None:
    inner = _FakeInnerRunner()
    runner = GatewayCommandRunner(_token(), inner=inner, clock=lambda: 1001.0)

    with pytest.raises(GatewayForbiddenOperationError):
        runner.run(command, context=_ctx())

    assert inner.calls == []


def test_runner_allows_a_non_terminal_status_update() -> None:
    inner = _FakeInnerRunner()
    runner = GatewayCommandRunner(_token(), inner=inner, clock=lambda: 1001.0)

    runner.run(["bd", "--json", "update", "BD-1", "--status", "in_progress"], context=_ctx())

    assert len(inner.calls) == 1


def test_runner_denies_the_forbidden_command_every_time_it_is_attempted() -> None:
    """Idempotency/race requirement: denial is a pure function of the command,
    never a one-shot gate that a retried/duplicate attempt could slip past."""
    inner = _FakeInnerRunner()
    runner = GatewayCommandRunner(_token(), inner=inner, clock=lambda: 1001.0)
    command = ["bd", "--json", "close", "BD-1"]

    for _ in range(3):
        with pytest.raises(GatewayForbiddenOperationError):
            runner.run(command, context=_ctx())

    assert inner.calls == []


def test_runner_reevaluates_scope_independently_per_call() -> None:
    """No cross-call caching: a runner that permits one context must still
    independently deny the next call whose context is out of scope."""
    inner = _FakeInnerRunner()
    runner = GatewayCommandRunner(_token(), inner=inner, clock=lambda: 1001.0)

    runner.run(["bd", "--json", "list"], context=_ctx())
    with pytest.raises(_SCOPE_VIOLATION_TYPE):
        runner.run(["bd", "--json", "list"], context=_ctx(repository="other-repo"))

    assert len(inner.calls) == 1


# ---------------------------------------------------------------------------
# authority_report / record_conflicts -- "exposes authority/freshness/conflicts"
# ---------------------------------------------------------------------------


def test_authority_report_reflects_a_fresh_authorized_token() -> None:
    runner = GatewayCommandRunner(_token(mission_id="m1", task_id="TRK-M1-04"), inner=_FakeInnerRunner(), clock=lambda: 1001.0)

    report = runner.authority_report(_ctx(mission_id="m1", task_id="TRK-M1-04"))

    assert report.authorized is True
    assert report.fresh is True
    assert report.actor == "ivan"
    assert report.repository == "spec-kitty"
    assert report.mission_id == "m1"
    assert report.task_id == "TRK-M1-04"
    assert report.denied_operations == ()
    assert report.conflicts == ()


def test_authority_report_reflects_an_expired_token_as_unauthorized() -> None:
    runner = GatewayCommandRunner(_token(ttl_seconds=60.0), inner=_FakeInnerRunner(), clock=lambda: 1060.0)

    report = runner.authority_report()

    assert report.fresh is False
    assert report.authorized is False


def test_authority_report_reflects_an_out_of_scope_context_as_unauthorized_but_fresh() -> None:
    runner = GatewayCommandRunner(_token(), inner=_FakeInnerRunner(), clock=lambda: 1001.0)

    report = runner.authority_report(_ctx(repository="other-repo"))

    assert report.fresh is True
    assert report.authorized is False


def test_authority_report_with_no_context_reports_token_authority_alone() -> None:
    runner = GatewayCommandRunner(_token(), inner=_FakeInnerRunner(), clock=lambda: 1001.0)

    report = runner.authority_report()

    assert report.authorized is True
    assert report.fresh is True


def test_authority_report_accumulates_denied_operations_up_to_the_history_limit() -> None:
    runner = GatewayCommandRunner(_token(), inner=_FakeInnerRunner(), clock=lambda: 1001.0, history_limit=2)

    for command in (
        ["bd", "--json", "close", "BD-1"],
        ["bd", "--json", "assign", "BD-1", "ivan"],
        ["bd", "--json", "approve", "BD-1"],
    ):
        with pytest.raises(GatewayForbiddenOperationError):
            runner.run(command, context=_ctx())

    report = runner.authority_report()

    assert len(report.denied_operations) == 2
    assert "forbidden subcommand 'assign'" in report.denied_operations[0]
    assert "forbidden subcommand 'approve'" in report.denied_operations[1]


def test_record_conflicts_is_surfaced_by_authority_report() -> None:
    runner = GatewayCommandRunner(_token(), inner=_FakeInnerRunner(), clock=lambda: 1001.0)

    runner.record_conflicts(["title conflict on BD-1", "status conflict on BD-2"])
    report = runner.authority_report()

    assert report.conflicts == ("title conflict on BD-1", "status conflict on BD-2")


def test_record_conflicts_replaces_rather_than_accumulates() -> None:
    runner = GatewayCommandRunner(_token(), inner=_FakeInnerRunner(), clock=lambda: 1001.0)

    runner.record_conflicts(["first sync's conflict"])
    runner.record_conflicts(["second sync's conflict"])
    report = runner.authority_report()

    assert report.conflicts == ("second sync's conflict",)


def test_token_property_returns_the_configured_token() -> None:
    token = _token()
    runner = GatewayCommandRunner(token, inner=_FakeInnerRunner(), clock=lambda: 1001.0)

    assert runner.token is token
