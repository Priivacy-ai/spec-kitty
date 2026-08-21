"""Local Beads program gateway (TRK-M1-04).

TRK-M1-04 node criteria (``docs/BEADS_PROGRAM_GRAPH.json``): "Host adapter
maps Tracker calls through token-valid program gateway, preserves mission/
task/team/repository scope, exposes authority/freshness/conflicts, and
cannot assign/close/approve/release Beads or bypass self-claim/review/
publication."

``spec_kitty_tracker``'s local/native connectors (``BeadsConnector``,
``FPConnector``) accept a caller-supplied
``spec_kitty_tracker.context.LocalExecutionContext`` and an injectable
``spec_kitty_tracker.connectors.cli_runner.CommandRunner`` (TRK-M1-02 A3/A4)
so a host can attribute and scope every call instead of falling back to the
package's default direct-subprocess runner. This module is that host-owned
runner: a Spec Kitty CLI concern, never imported by ``spec_kitty_tracker``
itself (``spec_kitty_tracker.errors.ScopeViolationError``'s docstring: "not a
:class:`TrackerContractError` -- ... Production raise sites are host
territory (TRK-M1-04/05; TRK-M1-06 N7)").

``spec_kitty_tracker>=0.5`` (the landed TRK-M1-02/03 kernel) is required to
actually construct a gateway-backed ``BeadsConnector`` via
:func:`build_gateway_beads_connector` -- ``LocalExecutionContext`` and the
capability-negotiation flags do not exist in the currently-PyPI-published
0.4.x line. Every import of ``spec_kitty_tracker`` in this module is
therefore deferred into function bodies (mirroring
``specify_cli/tracker/factory.py``'s existing "spec-kitty-tracker is not
installed" pattern) so the module itself imports cleanly, and
:class:`TrackerGatewayToken`/:class:`GatewayCommandRunner` are usable with a
duck-typed execution-context stand-in, regardless of the installed tracker
package version.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from spec_kitty_tracker.context import LocalExecutionContext


class _ExecutionContextLike(Protocol):
    """Structural shape this module relies on for a ``LocalExecutionContext``.

    Duck-typed on purpose: :class:`TrackerGatewayToken.covers` and
    :class:`GatewayCommandRunner` never ``isinstance``-check against
    ``spec_kitty_tracker.context.LocalExecutionContext`` -- they only read
    these four attributes -- so gateway logic tests exercise real behavior
    without depending on any particular installed tracker package version.
    """

    actor: str
    repository: str
    mission_id: str | None
    task_id: str | None


class TrackerGatewayError(RuntimeError):
    """Base error for the local tracker program gateway (TRK-M1-04)."""


@dataclass(frozen=True, slots=True)
class TrackerGatewayToken:
    """A validated, scope-bound capability for the local Beads program gateway.

    Minted by the host (Spec Kitty CLI) -- never by ``spec_kitty_tracker`` or
    by Beads itself -- and required before :class:`GatewayCommandRunner` will
    run any ``bd`` command. Authorization is ``(actor, repository)`` plus
    optional ``(mission_id, task_id)`` narrowing: a token with
    ``mission_id``/``task_id`` unset is scoped to the whole repository
    (broad); one with them set is scoped to exactly that mission/task
    (narrow). Freshness is TTL-based (``issued_at + ttl_seconds``).
    """

    token: str
    actor: str
    repository: str
    team: str | None = None
    mission_id: str | None = None
    task_id: str | None = None
    issued_at: float = field(default_factory=time.time)
    ttl_seconds: float = 300.0

    def __post_init__(self) -> None:
        if not self.token.strip():
            raise ValueError("TrackerGatewayToken.token must not be empty")
        if not self.actor.strip():
            raise ValueError("TrackerGatewayToken.actor must not be empty")
        if not self.repository.strip():
            raise ValueError("TrackerGatewayToken.repository must not be empty")
        if self.ttl_seconds <= 0:
            raise ValueError("TrackerGatewayToken.ttl_seconds must be positive")

    @property
    def expires_at(self) -> float:
        return self.issued_at + self.ttl_seconds

    def is_fresh(self, *, now: float | None = None) -> bool:
        """True strictly before ``expires_at`` -- expiry itself is stale (fail closed)."""
        current = time.time() if now is None else now
        return current < self.expires_at

    def covers(self, context: _ExecutionContextLike | LocalExecutionContext) -> bool:
        """True if this token's granted scope covers ``context``.

        A broad token (``mission_id``/``task_id`` unset) covers any
        matching-repository context. A narrow token additionally requires an
        exact match on whichever of ``mission_id``/``task_id`` it carries;
        a context missing that field never satisfies a narrow token
        (fail closed -- an unscoped call is never treated as in-scope).
        """
        if self.actor != context.actor:
            return False
        if self.repository != context.repository:
            return False
        if self.mission_id is not None and self.mission_id != context.mission_id:
            return False
        return not (self.task_id is not None and self.task_id != context.task_id)
