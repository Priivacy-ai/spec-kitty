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

from kernel.clock import now_epoch

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from spec_kitty_tracker import BeadsConnector
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
    """Raised when a command's ``bd`` subcommand is not on the gateway allow-list.

    TRK-M1-04 node criterion (verbatim): the gateway "cannot assign/close/
    approve/release Beads" and never lets a tracker-sync call "bypass self-
    claim/review/publication" (docs/TRACKER_ARCH_ROLE.md:43 in the
    rearchitecture control-plane repository; ``BeadsConnector`` A5 in the
    landed TRK-M1-03 kernel already denies assignment/terminal-transition
    patches at the patch/argument level). This is independent,
    defense-in-depth enforcement at the command-runner boundary: it holds
    even for a caller that builds a raw ``bd`` argv directly and hands it to
    the runner, bypassing ``BeadsConnector`` entirely.

    Two independent adversarial reviews (Renata REJECT, TRK-M1-04) found
    that a finite *deny*-list against ``bd`` 1.2.2's real surface can never
    be complete: beyond the many close-equivalent subcommands (``gate
    resolve`` -- documented verbatim as "equivalent to bd close <gate-id>",
    ``epic close-eligible``, ``supersede --with``, ``duplicate --of``,
    ``duplicates --auto-merge``, ``delete --force``, ``reopen``, ``assign``),
    ``bd``'s done-category statuses are themselves user-configurable
    (``bd config set status.custom ...``) -- a status-*value* blacklist is
    structurally unable to enumerate a caller-defined vocabulary. This
    module therefore inverts the control: deny-by-default, allow-list only
    the exact read/query and non-lifecycle-write subcommand paths the
    tracker adapter actually issues (see :data:`_ALLOWED_SUBCOMMAND_PATHS`),
    with the sole further guard on the two allow-listed write paths being an
    absolute, spelling-independent ban on the *flags* that carry lifecycle
    meaning (``--assignee``/``-a``, ``--status``/``-s``, ``--claim`` --
    banned outright, never gated on the value that follows them, precisely
    because no finite value list can keep up with a configurable status
    vocabulary).
    """


#: The complete, exact allow-list: every ``bd`` subcommand path the tracker
#: adapter legitimately needs, matched as a full path tuple (not just the
#: first token) so a two-word forbidden operation sharing a first token with
#: an allowed one-word operation (e.g. hypothetical ``gate show`` vs. the
#: denied ``gate resolve``) cannot slip past a check written against only
#: ``argv[1]``. Sourced from the actual call sites in the landed TRK-M1-02/03
#: kernel's ``spec_kitty_tracker.connectors.beads.BeadsConnector``:
#: ``list_issues`` -> ``list``, ``get_issue`` -> ``show``, ``create_issue`` ->
#: ``create``, ``update_issue`` -> ``update``, ``upsert_link`` -> ``dep add``,
#: ``add_comment`` -> ``comments add``. Everything else -- every close/
#: cancel/delete/supersede/duplicate/merge/config-mutation/self-claim
#: subcommand ``bd --help`` lists, and anything ``bd`` might add in a future
#: release -- is refused by default, with no enumeration required.
_ALLOWED_SUBCOMMAND_PATHS: frozenset[tuple[str, ...]] = frozenset(
    {
        ("list",),
        ("show",),
        ("create",),
        ("update",),
        ("dep", "add"),
        ("comments", "add"),
    }
)

#: Parent subcommands whose *second* token extends the matched path (``bd
#: dep add`` / ``bd comments add``). Every other ``bd`` subcommand this
#: module knows of (``gate``, ``epic``, ``merge-slot``, ``config``, ...) is
#: matched on its first token alone -- since none of those first tokens are
#: themselves allow-listed, their second-word spelling is irrelevant: ``bd
#: gate resolve`` and a hypothetical ``bd gate show`` are both refused
#: because ``"gate"`` alone is not on :data:`_ALLOWED_SUBCOMMAND_PATHS`.
_COMPOUND_SUBCOMMAND_PARENTS = frozenset({"dep", "comments"})

#: ``bd``'s own root-level flags (``bd --help``, "Flags:" section) that can
#: appear before the subcommand token. Split into value-taking (consume the
#: following token too) and boolean, so :func:`_extract_subcommand_path` can
#: skip past them to find the real subcommand -- an unrecognized dash-
#: prefixed token is conservatively treated as boolean (skip one token),
#: which only ever shifts the scan forward and can never cause a forbidden
#: subcommand token to be skipped over undetected (see module test suite's
#: "global flags before subcommand" coverage).
_GLOBAL_VALUE_FLAGS = frozenset({"--actor", "--db", "-C", "--directory", "--dolt-auto-commit"})

#: Lifecycle-carrying flags banned outright on the two allow-listed WRITE
#: paths, independent of whatever value follows them. This is a *flag-name*
#: ban, not a value blacklist: bd's flag surface for ``create``/``update`` is
#: fixed by the installed bd version (unlike its status *vocabulary*, which
#: is user-configurable), so enumerating flag names here does not carry the
#: same "cannot be made complete" defect the prior status-value blacklist
#: had. ``update --status``/``-s`` is banned for every value, including a
#: superficially-safe non-terminal one -- the gateway cannot know, from a
#: bare string, whether a given installation's ``status.custom`` config
#: makes that value a done-category status; any status transition is
#: lifecycle and is host-owned, never tracker-sync-owned.
_LIFECYCLE_FLAGS_BY_ALLOWED_WRITE: dict[tuple[str, ...], frozenset[str]] = {
    ("create",): frozenset({"--assignee", "-a"}),
    ("update",): frozenset({"--assignee", "-a", "--status", "-s", "--claim"}),
}


def _canonicalize_argv(command: Sequence[str]) -> list[str]:
    """Split every glued ``--flag=value``/``-f=value`` token into two tokens.

    ``bd``'s flag parser (Cobra/pflag) accepts a single-value flag as either
    split two-token (``--flag value``) or glued equals (``--flag=value``,
    or for any short flag, ``-f=value``). This split is purely syntactic --
    it needs no alias table or per-flag knowledge, so it is applied
    generically to *every* long flag and every single-character short flag,
    not just a hardcoded list of "known" ones. Every check downstream
    matches against the split two-token shape; without this normalization
    step a caller could dodge a flag-name check simply by picking the glued
    spelling of an already-forbidden flag (Renata REJECT, TRK-M1-04:
    reproduced live against ``bd update --help``'s ``-a``/``-s`` shorthands
    and glued ``=`` form).
    """
    canonical: list[str] = []
    for arg in command:
        flag, sep, value = arg.partition("=")
        if sep and (flag.startswith("--") or (flag.startswith("-") and len(flag) == 2)):
            canonical.append(flag)
            canonical.append(value)
            continue
        canonical.append(arg)
    return canonical


def _extract_subcommand_path(argv: Sequence[str]) -> tuple[str, ...]:
    """The canonicalized ``bd`` subcommand path (1 or 2 tokens), or ``()``.

    Skips the command executable name (``argv[0]``, e.g. ``"bd"``) and any
    root-level global flags -- value-taking ones (:data:`_GLOBAL_VALUE_FLAGS`)
    consume their following token too; anything else dash-prefixed is
    conservatively treated as boolean-shaped and skipped alone -- to find
    the first positional token, which is the subcommand. A literal ``--``
    (pflag's "stop parsing flags" marker) ends the skip immediately, so a
    caller cannot hide the real subcommand behind it. If the first token is
    a compound parent (:data:`_COMPOUND_SUBCOMMAND_PARENTS`, e.g. ``dep``),
    and a following non-flag token exists, it extends the path to two
    tokens -- so ``bd dep add ...`` and ``bd dep remove ...`` are
    distinguished, and a bare ``bd dep --blocks ...`` (no explicit
    sub-subcommand) yields the one-token path ``("dep",)``, which is not
    itself allow-listed and is therefore refused.
    """
    tokens = list(argv[1:])
    index = 0
    stop_skipping = False
    while index < len(tokens):
        arg = tokens[index]
        if not stop_skipping and arg == "--":
            stop_skipping = True
            index += 1
            continue
        if not stop_skipping and arg.startswith("-"):
            index += 2 if arg in _GLOBAL_VALUE_FLAGS else 1
            continue
        break
    if index >= len(tokens):
        return ()
    path = [tokens[index]]
    if (
        tokens[index] in _COMPOUND_SUBCOMMAND_PARENTS
        and index + 1 < len(tokens)
        and not tokens[index + 1].startswith("-")
    ):
        path.append(tokens[index + 1])
    return tuple(path)


def _forbidden_operation_reason(command: Sequence[str]) -> str | None:
    """None if ``command`` is allowed; otherwise a human-readable denial reason.

    Pure and stateless by design (TRK-M1-04 node criterion: never bypass
    self-claim/review/publication) -- the same command is denied for the
    same reason on every call, with no memory of prior attempts, so a
    retried or duplicated attempt can never slip past a gate that already
    refused it once. Deny-by-default: a subcommand path not exactly present
    in :data:`_ALLOWED_SUBCOMMAND_PATHS` is refused outright, with no need to
    separately enumerate every forbidden operation ``bd`` exposes today or
    might add later. The two allow-listed write paths additionally forbid
    their lifecycle flags (:data:`_LIFECYCLE_FLAGS_BY_ALLOWED_WRITE`)
    regardless of spelling (:func:`_canonicalize_argv` already normalized
    glued-equals/short-flag spellings) or value.
    """
    argv = _canonicalize_argv(command)
    path = _extract_subcommand_path(argv)
    if path not in _ALLOWED_SUBCOMMAND_PATHS:
        joined = " ".join(path) if path else "<none>"
        return f"subcommand {joined!r} is not on the tracker gateway allow-list"

    forbidden_flags = _LIFECYCLE_FLAGS_BY_ALLOWED_WRITE.get(path)
    if forbidden_flags:
        for arg in argv:
            if arg in forbidden_flags:
                joined = " ".join(path)
                return (
                    f"forbidden lifecycle flag {arg!r} on allow-listed subcommand {joined!r}"
                )
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
        current = now_epoch() if now is None else now  # kernel.clock single door (M2 canonical integration)
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
       review/publication**: :func:`_forbidden_operation_reason` matches the
       raw ``bd`` argv's subcommand path against a deny-by-default
       allow-list (:data:`_ALLOWED_SUBCOMMAND_PATHS`), independently of
       whatever ``BeadsConnector`` itself already denies, else
       :class:`GatewayForbiddenOperationError`.

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


class TrackerGatewayUnavailableError(TrackerGatewayError):
    """Raised when the installed ``spec_kitty_tracker`` predates the program
    gateway's required surface (``spec_kitty_tracker.context.LocalExecutionContext``,
    added in the landed TRK-M1-02 kernel, 0.5.x -- not yet published to PyPI
    at the time this module was written; see
    ``docs/development/how-to/local-overrides.md`` Pattern A for how to
    develop/test against it locally in the meantime).
    """


def _try_import_gateway_beads_types() -> tuple[type, type, type] | None:
    """``(BeadsConnector, BeadsConnectorConfig, LocalExecutionContext)`` if the
    installed tracker package exposes all three, else ``None``. A separate,
    monkeypatchable function (mirroring :func:`_try_import_scope_violation_error`)
    so :func:`build_gateway_beads_connector`'s unavailable-package path is
    exercisable without needing an actual old-tracker-package install."""
    try:
        from spec_kitty_tracker import BeadsConnector, BeadsConnectorConfig
        from spec_kitty_tracker.context import LocalExecutionContext
    except ImportError:
        return None
    return BeadsConnector, BeadsConnectorConfig, LocalExecutionContext


def build_gateway_beads_connector(
    *,
    token: TrackerGatewayToken,
    workspace: str,
    command: str = "bd",
    cwd: str | None = None,
    runner: GatewayCommandRunner | None = None,
) -> tuple[BeadsConnector, GatewayCommandRunner]:
    """Construct a ``BeadsConnector`` wired through the local program gateway.

    This is the host-owned wiring TRK-M1-04's node criteria describes: the
    returned connector's ``LocalExecutionContext`` is derived from ``token``
    (so ``BeadsConnector`` preserves mission/task/team/repository scope --
    TRK-M1-02 A3/A4), and every ``bd`` invocation the connector issues is
    routed through a :class:`GatewayCommandRunner` bound to the same token
    (so it is token-valid and cannot assign/close/approve/release -- see
    :class:`GatewayCommandRunner`'s docstring), never the package's default
    direct-subprocess ``SubprocessCommandRunner``
    (``BeadsConnector.__init__``'s own fail-closed rule already refuses a
    scoped ``context`` without an explicit ``runner``; this function is what
    supplies that explicit runner).

    Raises :class:`TrackerGatewayUnavailableError` if the installed
    ``spec_kitty_tracker`` predates ``LocalExecutionContext`` (needs 0.5+).
    """
    imported = _try_import_gateway_beads_types()
    if imported is None:
        raise TrackerGatewayUnavailableError(
            "spec-kitty-tracker>=0.5 (spec_kitty_tracker.context.LocalExecutionContext) "
            "is required to build a program-gateway Beads connector (TRK-M1-04); "
            "the installed spec-kitty-tracker predates it."
        )
    beads_connector_cls, beads_connector_config_cls, local_execution_context_cls = imported

    context = local_execution_context_cls(
        actor=token.actor,
        repository=token.repository,
        team=token.team,
        mission_id=token.mission_id,
        task_id=token.task_id,
    )
    gateway_runner = runner if runner is not None else GatewayCommandRunner(token)
    config = beads_connector_config_cls(workspace=workspace, command=command, cwd=cwd, context=context)
    connector = beads_connector_cls(config, runner=gateway_runner)
    return connector, gateway_runner
