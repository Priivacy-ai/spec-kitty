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

from specify_cli.tracker.gateway import TrackerGatewayToken

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
