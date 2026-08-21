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
from collections.abc import Callable, Sequence
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


class GatewayAuthorizationError(TrackerGatewayError):
    """Raised when a gateway call has no fresh token or no execution context.

    A scoped program gateway must never run a command it cannot attribute
    and time-bound authorization for -- an expired token or a missing
    ``LocalExecutionContext`` both fail closed here, before any scope check
    or command inspection runs.
    """


class GatewayScopeViolationError(TrackerGatewayError):
    """Raised when a call's execution context is outside the token's granted scope.

    Local fallback used only when the installed ``spec_kitty_tracker``
    predates ``spec_kitty_tracker.errors.ScopeViolationError`` (added in the
    landed TRK-M1-02 kernel, 0.5.x); see :func:`_try_import_scope_violation_error`.
    When that type is importable, :class:`GatewayCommandRunner` raises it
    directly instead -- host-owned scope enforcement is exactly the
    "Production raise sites are host territory (TRK-M1-04/05)" case named in
    its docstring, and callers that already handle
    ``spec_kitty_tracker.errors.ScopeViolationError`` should not also need to
    handle a second, gateway-local type when a current tracker package is
    installed.
    """

    def __init__(self, message: str, *, expected_scope: str, actual_scope: str) -> None:
        super().__init__(message)
        self.expected_scope = expected_scope
        self.actual_scope = actual_scope


class GatewayForbiddenOperationError(TrackerGatewayError):
    """Raised when a command attempts an assign/close/approve/release operation.

    The Beads program gateway never lets a tracker-sync call assign, close,
    approve, or release a Bead, and never lets it bypass Spec Kitty's own
    self-claim/review/publication flow (docs/TRACKER_ARCH_ROLE.md:43 in the
    rearchitecture control-plane repository; ``BeadsConnector`` A5 in the
    landed TRK-M1-03 kernel already denies these at the patch/argument
    level). This is independent, defense-in-depth enforcement at the
    command-runner boundary: it holds even for a caller that builds a raw
    ``bd`` argv directly and hands it to the runner, bypassing
    ``BeadsConnector`` entirely.
    """


_FORBIDDEN_SUBCOMMANDS = frozenset({"close", "assign", "approve", "release"})
_FORBIDDEN_FLAGS = frozenset({"--assignee", "--approve", "--release"})
_FORBIDDEN_STATUS_VALUES = frozenset({"closed", "done", "tombstone"})


def _forbidden_operation_reason(command: Sequence[str]) -> str | None:
    """None if ``command`` is allowed; otherwise a human-readable denial reason.

    Pure and stateless by design (TRK-M1-04 node criterion: never bypass
    self-claim/review/publication) -- the same command is denied for the
    same reason on every call, with no memory of prior attempts, so a
    retried or duplicated attempt can never slip past a gate that already
    refused it once.
    """
    argv = list(command)
    for arg in argv:
        if arg in _FORBIDDEN_SUBCOMMANDS:
            return f"forbidden subcommand {arg!r}"
        if arg in _FORBIDDEN_FLAGS:
            return f"forbidden flag {arg!r}"
    for index, arg in enumerate(argv):
        if arg != "--status" or index + 1 >= len(argv):
            continue
        value = argv[index + 1].strip().lower()
        if value in _FORBIDDEN_STATUS_VALUES:
            return f"forbidden terminal status {value!r} via --status"
    return None


def _try_import_scope_violation_error() -> type[Exception] | None:
    """``spec_kitty_tracker.errors.ScopeViolationError`` if the installed
    tracker package exposes it (0.5.x+), else ``None``. A separate,
    monkeypatchable function so the fallback path (:class:`GatewayScopeViolationError`)
    is exercisable without needing an actual old-tracker-package install."""
    try:
        from spec_kitty_tracker.errors import ScopeViolationError
    except ImportError:
        return None
    return ScopeViolationError


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


class _CommandRunnerLike(Protocol):
    """Structural shape of ``spec_kitty_tracker.connectors.cli_runner.CommandRunner``.

    Typed with ``context: LocalExecutionContext`` (not the broader
    ``_ExecutionContextLike`` union) so that
    ``spec_kitty_tracker.connectors.cli_runner.SubprocessCommandRunner`` and
    ``BeadsConnector``'s own injected runner both satisfy it structurally --
    this is what :class:`GatewayCommandRunner` actually delegates to.
    """

    def run(
        self,
        command: Sequence[str],
        *,
        cwd: str | None = None,
        context: LocalExecutionContext | None = None,
    ) -> str: ...


class GatewayCommandRunner:
    """Host program gateway ``CommandRunner`` (TRK-M1-04).

    Implements the ``spec_kitty_tracker.connectors.cli_runner.CommandRunner``
    protocol (TRK-M1-02 A4) so a ``BeadsConnector``/``FPConnector`` can be
    wired through it instead of the package's default
    ``SubprocessCommandRunner``. Every ``run()`` call enforces, in order,
    before delegating to the wrapped inner runner:

    1. **token-valid**: :meth:`TrackerGatewayToken.is_fresh` must hold, else
       :class:`GatewayAuthorizationError`.
    2. **scope-preserving**: an execution context must be supplied and
       :meth:`TrackerGatewayToken.covers` it, else a scope-violation error
       (:class:`GatewayScopeViolationError`, or
       ``spec_kitty_tracker.errors.ScopeViolationError`` when the installed
       tracker package exposes it).
    3. **never assign/close/approve/release, never bypass self-claim/
       review/publication**: :func:`_forbidden_operation_reason` inspects
       the raw ``bd`` argv independently of whatever ``BeadsConnector``
       itself already denies, else :class:`GatewayForbiddenOperationError`.

    A denied/forbidden attempt is recorded (bounded, most-recent-N) and
    surfaced by :meth:`authority_report` as ``denied_operations``,
    satisfying the "exposes authority/freshness/conflicts" node criterion
    together with ``conflicts`` (populated externally via
    :meth:`record_conflicts`, e.g. from a completed ``SyncEngine.sync()``'s
    ``SyncResult.conflicts``).
    """

    def __init__(
        self,
        token: TrackerGatewayToken,
        *,
        inner: _CommandRunnerLike | None = None,
        clock: Callable[[], float] | None = None,
        history_limit: int = 20,
    ) -> None:
        self._token = token
        self._inner: _CommandRunnerLike = inner if inner is not None else _default_inner_runner()
        self._clock: Callable[[], float] = clock if clock is not None else time.time
        self._denied: list[str] = []
        self._history_limit = history_limit
        self._conflicts: tuple[str, ...] = ()

    @property
    def token(self) -> TrackerGatewayToken:
        return self._token

    def run(
        self,
        command: Sequence[str],
        *,
        cwd: str | None = None,
        context: LocalExecutionContext | None = None,
    ) -> str:
        now = self._clock()
        if not self._token.is_fresh(now=now):
            raise GatewayAuthorizationError(
                f"tracker gateway token for actor={self._token.actor!r} "
                f"repository={self._token.repository!r} expired at "
                f"{self._token.expires_at!r} (now={now!r})"
            )
        if context is None:
            raise GatewayAuthorizationError(
                "GatewayCommandRunner requires a LocalExecutionContext on every call; "
                "a scoped program gateway must never run a command with unknown scope."
            )
        if not self._token.covers(context):
            self._raise_scope_violation(context)

        reason = _forbidden_operation_reason(command)
        if reason is not None:
            self._record_denied(reason)
            raise GatewayForbiddenOperationError(
                f"tracker program gateway refused command {list(command)!r}: {reason} "
                "(assign/close/approve/release and self-claim/review/publication bypass "
                "are host-owned, never tracker-sync-owned)"
            )

        return self._inner.run(command, cwd=cwd, context=context)

    def _record_denied(self, reason: str) -> None:
        self._denied.append(reason)
        if len(self._denied) > self._history_limit:
            self._denied = self._denied[-self._history_limit :]

    def _raise_scope_violation(self, context: LocalExecutionContext) -> None:
        expected = f"actor={self._token.actor!r} repository={self._token.repository!r}"
        if self._token.mission_id is not None:
            expected += f" mission_id={self._token.mission_id!r}"
        if self._token.task_id is not None:
            expected += f" task_id={self._token.task_id!r}"
        actual = (
            f"actor={context.actor!r} repository={context.repository!r} "
            f"mission_id={context.mission_id!r} task_id={context.task_id!r}"
        )
        message = f"tracker program gateway scope violation: token covers {expected}, call is {actual}"

        error_type = _try_import_scope_violation_error()
        if error_type is None:
            raise GatewayScopeViolationError(message, expected_scope=expected, actual_scope=actual)
        raise error_type(message, expected_scope=expected, actual_scope=actual)  # type: ignore[call-arg]

    def record_conflicts(self, conflicts: Sequence[object]) -> None:
        """Attach the most recent sync conflicts for :meth:`authority_report` to surface.

        Intentionally accepts anything ``str()``-able (e.g.
        ``spec_kitty_tracker.conflicts.ConflictRecord`` instances) rather
        than importing the tracker package's conflict type at module scope.
        """
        self._conflicts = tuple(str(item) for item in conflicts)

    def authority_report(
        self, context: LocalExecutionContext | None = None
    ) -> GatewayAuthorityReport:
        """The combined authority/freshness/conflicts view the node criterion names.

        ``authorized`` is freshness AND (no context given, or the token
        covers it); ``context=None`` reports authority independent of any
        particular call's scope.
        """
        now = self._clock()
        fresh = self._token.is_fresh(now=now)
        authorized = fresh and (context is None or self._token.covers(context))
        return GatewayAuthorityReport(
            authorized=authorized,
            fresh=fresh,
            actor=self._token.actor,
            repository=self._token.repository,
            mission_id=self._token.mission_id,
            task_id=self._token.task_id,
            denied_operations=tuple(self._denied),
            conflicts=self._conflicts,
        )


@dataclass(frozen=True, slots=True)
class GatewayAuthorityReport:
    """What the TRK-M1-04 node criteria calls "authority/freshness/conflicts", together."""

    authorized: bool
    fresh: bool
    actor: str
    repository: str
    mission_id: str | None
    task_id: str | None
    denied_operations: tuple[str, ...]
    conflicts: tuple[str, ...]


def _default_inner_runner() -> _CommandRunnerLike:
    from spec_kitty_tracker.connectors.cli_runner import SubprocessCommandRunner

    return SubprocessCommandRunner()
