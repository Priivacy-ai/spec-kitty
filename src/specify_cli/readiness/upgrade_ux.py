"""Upgrade-readiness UX (WS3, issue Priivacy-ai/spec-kitty#1092).

Real prompt UX layered over the existing upgrade-nag chain:

- Snooze cadence (24h → 48h → 7d) anchored per remote version.
- Four choices: Upgrade now, Always keep me up to date, Not now, Never ask again.
- Safe auto-upgrade only for known-safe installers
  (``compat._detect.install_method.is_safe_for_auto_upgrade``).
- Env-driven preferences for "always", "never-ask", and a hard kill switch.

Hard guarantees:

- This module MUST NEVER prompt, MUST NEVER mutate the cache for a Not-now
  decision, and MUST NEVER invoke an auto-upgrade subprocess when the
  canonical ``_should_suppress_nag()`` returns True.  That predicate is the
  single source of truth for suppression (``--json``, ``--quiet``,
  ``--help``, ``--version``, ``CI``, non-TTY, ``SPEC_KITTY_NO_NAG``).
- This module MUST NOT add a new pip dependency.  Only stdlib + already-shipped
  pieces of the CLI.

Entry point: :func:`run_upgrade_ux`.  Called from the readiness coordinator
on the hosted-enabled path.  The legacy hosted-disabled path continues to
call ``_render_nag_if_needed`` directly and is unchanged.
"""

from __future__ import annotations

import os
import re
import subprocess  # noqa: S404 — required to invoke the existing `spec-kitty upgrade` binary
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Literal, Protocol, cast

if TYPE_CHECKING:
    import typer

    from specify_cli.compat._adapters.uv_receipt import UvReceiptResult
    from specify_cli.compat._detect.runtime import InstalledCliRuntime
    from specify_cli.compat.cache import NagCacheRecord
    from specify_cli.compat.install_events import UvToolInstallationVerified, VerificationConfidence
    from specify_cli.compat.remediation import RemediationCommand


class _CliStatusLike(Protocol):
    @property
    def installed_version(self) -> str: ...

    @property
    def latest_version(self) -> str | None: ...

    @property
    def latest_source(self) -> str: ...


class _PlanResultLike(Protocol):
    @property
    def cli_status(self) -> _CliStatusLike: ...


class _NagCacheLike(Protocol):
    def write(self, record: NagCacheRecord) -> None: ...

# Public env keys (WS3 acceptance criterion 4).
ENV_UPGRADE_AUTO = "SPEC_KITTY_UPGRADE_AUTO"
ENV_UPGRADE_NEVER_ASK = "SPEC_KITTY_UPGRADE_NEVER_ASK"
ENV_UPGRADE_DISABLED = "SPEC_KITTY_UPGRADE_DISABLED"

_TRUTHY = frozenset({"1", "true", "yes", "on"})
_VERSION_RE = re.compile(r"^[A-Za-z0-9.\-+]{1,64}$")


def _truthy(raw: str | None) -> bool:
    """Stable truthy parser shared with ``saas.rollout``."""
    if not raw:
        return False
    return raw.strip().casefold() in _TRUTHY


# ---------------------------------------------------------------------------
# Choice + cadence
# ---------------------------------------------------------------------------


class UpgradeChoice(StrEnum):
    """Four prompt choices presented to the user.

    Values are stable identifiers; tests assert against them.
    """

    UPGRADE_NOW = "upgrade_now"
    ALWAYS = "always"
    NOT_NOW = "not_now"
    NEVER_ASK = "never_ask"


# Ladder of snooze durations (anchored per remote version).
_CADENCE_SECONDS: dict[str | None, tuple[str, int]] = {
    None: ("24h", 24 * 3600),
    "24h": ("48h", 48 * 3600),
    "48h": ("7d", 7 * 24 * 3600),
    "7d": ("7d", 7 * 24 * 3600),  # ceiling
}


def advance_snooze(
    current: str | None, *, now: datetime
) -> tuple[str, datetime]:
    """Advance the cadence ladder one step.

    The mapping is::

        None -> 24h (+24h)
        24h  -> 48h (+48h)
        48h  -> 7d  (+7d)
        7d   -> 7d  (+7d)   # ceiling

    Args:
        current: Current snooze step token, or ``None`` for "no snooze yet".
        now: Current UTC datetime; ``snoozed_until = now + step_duration``.

    Returns:
        ``(next_step_token, snoozed_until)``.
    """
    next_step, seconds = _CADENCE_SECONDS[current]
    return next_step, now + timedelta(seconds=seconds)


# ---------------------------------------------------------------------------
# Effective-preference resolution
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EffectivePreference:
    """Per-invocation resolved user preference.

    Combines persisted NagCache state with env-var overrides.  The env
    overrides take effect for the current invocation only; they do not
    persist into the cache unless the user explicitly picks the matching
    choice at the prompt.
    """

    disabled: bool  # kill switch — short-circuit everything
    never_ask: bool
    always_upgrade: bool


def resolve_effective_preference(
    *,
    persisted_never_ask: bool,
    persisted_always_upgrade: bool,
    env: dict[str, str] | None = None,
) -> EffectivePreference:
    """Merge persisted preferences with env-var overrides.

    Args:
        persisted_never_ask: ``NagCacheRecord.never_ask``.
        persisted_always_upgrade: ``NagCacheRecord.always_upgrade``.
        env: Environment mapping (defaults to ``os.environ``).

    Returns:
        Effective preference flags for this invocation.
    """
    if env is None:
        env = dict(os.environ)
    return EffectivePreference(
        disabled=_truthy(env.get(ENV_UPGRADE_DISABLED)),
        never_ask=persisted_never_ask or _truthy(env.get(ENV_UPGRADE_NEVER_ASK)),
        always_upgrade=persisted_always_upgrade or _truthy(env.get(ENV_UPGRADE_AUTO)),
    )


# ---------------------------------------------------------------------------
# Cadence anchoring
# ---------------------------------------------------------------------------


def needs_reset(
    *,
    record_remote_version: str | None,
    current_latest: str | None,
) -> bool:
    """Return True if the remote version has changed since the last cycle.

    A reset clears ``snooze_step`` / ``snoozed_until`` / ``never_ask``
    (per spec acceptance criterion 1, "A new remote version resets the
    cadence" — and the "Never ask again" choice is also bound to the
    specific remote version the user said it about).

    Args:
        record_remote_version: ``NagCacheRecord.remote_version_seen``.
        current_latest: ``CliStatus.latest_version`` from the planner.

    Returns:
        True iff ``record_remote_version is None`` or differs from
        ``current_latest`` (and ``current_latest`` is not None).
    """
    if current_latest is None:
        # Planner couldn't determine a remote; don't churn cadence.
        return False
    return record_remote_version != current_latest


def is_currently_snoozed(
    *, snoozed_until: datetime | None, now: datetime
) -> bool:
    """Return True iff the prompt should be suppressed by an active snooze."""
    if snoozed_until is None:
        return False
    return now < snoozed_until


# ---------------------------------------------------------------------------
# Post-upgrade verification helpers (T025)
# ---------------------------------------------------------------------------

# Module-level event inspection hook — populated by _emit_install_verified_event().
# Tests may clear this list and inspect it to verify event emission.
_emitted_install_events: list[object] = []


def _check_entrypoint_present(receipt: UvReceiptResult) -> bool:
    """Return True if the spec-kitty entrypoint was found post-upgrade.

    Uses ``bin_dir`` as a proxy: UvReceiptReader populates ``bin_dir``
    only when the spec-kitty entrypoint is present in the receipt.
    """
    return receipt.bin_dir is not None


def _derive_confidence(exit_code: int | None, entrypoint_match: bool) -> VerificationConfidence:
    """Derive VerificationConfidence from exit code and entrypoint presence.

    Rules (spec FR-014):
    - HIGH:   exit_code == 0 AND entrypoint_match == True
    - MEDIUM: exit_code == 0 AND entrypoint_match == False
    - LOW:    exit_code != 0
    """
    from specify_cli.compat.install_events import VerificationConfidence as _VC  # noqa: PLC0415

    if exit_code == 0 and entrypoint_match:
        return _VC.HIGH
    if exit_code == 0:
        return _VC.MEDIUM
    return _VC.LOW


def _derive_package_binding(receipt: UvReceiptResult) -> str:
    """Return package name + specifier from the first receipt requirement, or 'unknown'."""
    if not receipt.requirements:
        return "unknown"
    req = receipt.requirements[0]
    specifier = req.specifier or ""
    binding = req.name + specifier
    return binding if binding else "unknown"


def _emit_install_verified_event(event: UvToolInstallationVerified) -> None:
    """Best-effort emit: append to module-level list for test inspection.

    NFR-007: swallows all errors; never logs or transmits receipt_path.
    """
    import contextlib  # noqa: PLC0415

    with contextlib.suppress(Exception):
        _emitted_install_events.append(event)


# ---------------------------------------------------------------------------
# History record append helper (T026)
# ---------------------------------------------------------------------------


def _append_upgrade_attempt_record(
    completed: subprocess.CompletedProcess[bytes],
    runtime: InstalledCliRuntime,
    *,
    target_version: str | None,
) -> None:
    """Best-effort append to UpgradeAttemptStore.  Swallows all errors (NFR-008)."""
    try:  # noqa: BLE001
        import ulid  # type: ignore[import-not-found]  # python-ulid has no stubs  # noqa: PLC0415
        from specify_cli.compat.history import (  # noqa: PLC0415
            UpgradeAttemptOutcome,
            UpgradeAttemptRecord,
            UpgradeAttemptStore,
        )

        outcome = (
            UpgradeAttemptOutcome.SUCCESS
            if completed.returncode == 0
            else UpgradeAttemptOutcome.FAILURE
        )
        record = UpgradeAttemptRecord(
            attempt_id=str(ulid.ULID()),
            timestamp=datetime.now(UTC),
            install_method=runtime.install_method,
            intent="upgrade",
            outcome=outcome,
            exit_code=completed.returncode,
            target_version=target_version,
        )
        UpgradeAttemptStore().append(record)
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Auto-upgrade subprocess (the only side-effecting helper in this module)
# ---------------------------------------------------------------------------


def _default_upgrade_runner(
    cmd: RemediationCommand,
    runtime: InstalledCliRuntime,
    *,
    target_version: str | None = None,
) -> subprocess.CompletedProcess[bytes]:
    """Invoke the owning installer's upgrade command via subprocess.

    Returns a CompletedProcess.  Never raises; on OSError / timeout
    returns a CompletedProcess with returncode=1 so the caller can treat
    it as "failed".

    Auto-upgrade safety:

    - Consumes ``cmd.argv`` and ``cmd.env`` from the pre-built RemediationCommand
      so installer-specific behaviour (--python, UV_TOOL_DIR, etc.) is fully
      determined by the remediation planner.
    - Hard 5-minute timeout (upgrades that take longer are pathological
      and should be observed by the user, not auto-driven).
    - ``check=False`` — caller inspects the return code.

    Post-completion side-effects (both best-effort / fail-safe):
    - UV_TOOL installs: emits ``UvToolInstallationVerified`` event (FR-014).
    - All install methods: appends ``UpgradeAttemptRecord`` to history store (FR-012).
    """
    from specify_cli.compat._detect.install_method import InstallMethod  # noqa: PLC0415

    if cmd.argv is None:
        return subprocess.CompletedProcess(args=[], returncode=1)

    argv = list(cmd.argv)
    merged_env: dict[str, str] | None = {**os.environ, **cmd.env} if cmd.env else None

    try:
        completed: subprocess.CompletedProcess[bytes] = subprocess.run(  # noqa: S603,S607 — fixed argv; PATH lookup is intentional
            argv,
            check=False,
            env=merged_env,
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired):
        completed = subprocess.CompletedProcess(args=argv, returncode=1)

    # T025: Emit UvToolInstallationVerified (UV_TOOL only, best-effort, NFR-007)
    if runtime.install_method == InstallMethod.UV_TOOL:
        try:  # noqa: BLE001
            from specify_cli.compat._adapters.uv_receipt import UvReceiptReader  # noqa: PLC0415
            from specify_cli.compat.install_events import UvToolInstallationVerified  # noqa: PLC0415

            post_receipt = UvReceiptReader.read_for_executable(sys.executable)
            entrypoint_match = _check_entrypoint_present(post_receipt)
            confidence = _derive_confidence(completed.returncode, entrypoint_match)
            event = UvToolInstallationVerified(
                receipt_path=post_receipt.receipt_path,
                entrypoint_match=entrypoint_match,
                package_binding=_derive_package_binding(post_receipt),
                confidence=confidence,
            )
            _emit_install_verified_event(event)
        except Exception:  # noqa: BLE001
            pass

    # T026: Append UpgradeAttemptRecord (all install methods, best-effort)
    _append_upgrade_attempt_record(completed, runtime, target_version=target_version)

    return completed


# ---------------------------------------------------------------------------
# Mutation helpers (pure: take + return a NagCacheRecord)
# ---------------------------------------------------------------------------


def apply_choice(
    record_kwargs: dict[str, object],
    *,
    choice: UpgradeChoice,
    current_latest: str | None,
    now: datetime,
) -> dict[str, object]:
    """Return updated NagCacheRecord kwargs for the chosen action.

    Pure function: callers re-construct the record via ``dataclasses.replace``
    using these kwargs.

    Args:
        record_kwargs: Current record kwargs (as from ``dataclasses.asdict``-like).
        choice: The user's choice.
        current_latest: Remote latest_version from the planner.
        now: Current UTC datetime.

    Returns:
        Updated kwargs dict.
    """
    updated: dict[str, object] = dict(record_kwargs)
    # Anchor cadence to the version the user is responding about.
    if current_latest is not None:
        updated["remote_version_seen"] = current_latest

    if choice == UpgradeChoice.UPGRADE_NOW:
        # Clear snooze on a successful upgrade attempt (the caller may
        # still re-set it if the upgrade subprocess fails); also reset
        # cadence so a new version restarts cleanly.
        updated["snooze_step"] = None
        updated["snoozed_until"] = None
    elif choice == UpgradeChoice.ALWAYS:
        updated["always_upgrade"] = True
        updated["snooze_step"] = None
        updated["snoozed_until"] = None
    elif choice == UpgradeChoice.NOT_NOW:
        current_step = updated.get("snooze_step")
        if not isinstance(current_step, str):
            current_step = None
        next_step, snoozed_until = advance_snooze(current_step, now=now)
        updated["snooze_step"] = next_step
        updated["snoozed_until"] = snoozed_until
    elif choice == UpgradeChoice.NEVER_ASK:
        updated["never_ask"] = True
        updated["snooze_step"] = None
        updated["snoozed_until"] = None

    return updated


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------


PromptCallback = Callable[[], UpgradeChoice]


def _default_prompt() -> UpgradeChoice:
    """Default interactive 4-choice prompt rendered on stderr.

    Returns the selected ``UpgradeChoice``.  On EOF / interrupted input the
    safest fallback is "Not now" — never silently treat an unparseable
    response as "Upgrade now".
    """
    # Local imports to keep module-load cost low.
    from rich.console import Console  # noqa: PLC0415

    out = Console(stderr=True)
    out.print()
    out.print("[bold]A spec-kitty upgrade is available.[/bold]")
    out.print("  [1] Upgrade now")
    out.print("  [2] Always keep me up to date")
    out.print("  [3] Not now")
    out.print("  [4] Never ask again")
    try:
        raw = input("Choose [1-4, default 3]: ").strip()
    except (EOFError, KeyboardInterrupt):
        return UpgradeChoice.NOT_NOW
    mapping = {
        "1": UpgradeChoice.UPGRADE_NOW,
        "2": UpgradeChoice.ALWAYS,
        "3": UpgradeChoice.NOT_NOW,
        "": UpgradeChoice.NOT_NOW,
        "4": UpgradeChoice.NEVER_ASK,
    }
    return mapping.get(raw, UpgradeChoice.NOT_NOW)


def _print_unsafe_installer_guidance(method_name: str) -> None:
    """Emit guidance for installers that are not auto-upgrade-safe."""
    from rich.console import Console  # noqa: PLC0415

    out = Console(stderr=True)
    out.print(
        f"[yellow]spec-kitty cannot auto-upgrade for install method '{method_name}'.[/yellow]"
    )
    out.print("  Upgrade manually with the package manager you used to install spec-kitty,")
    out.print("  or run `spec-kitty upgrade` interactively.")


@dataclass(frozen=True)
class UpgradeUxOutcome:
    """Structured result of one ``run_upgrade_ux`` invocation.

    Useful for tests and for coordinator wiring.  All fields are
    inspection-only; the function may also have mutated the on-disk cache.
    """

    ran: bool  # entered the UX path (vs short-circuit)
    prompted: bool  # presented the 4-choice prompt
    choice: UpgradeChoice | None
    auto_upgrade_attempted: bool
    auto_upgrade_exit_code: int | None
    guidance_only: bool  # unsafe installer → printed guidance, no mutation


def _inactive_outcome() -> UpgradeUxOutcome:
    return UpgradeUxOutcome(False, False, None, False, None, False)


def _noop_active_outcome() -> UpgradeUxOutcome:
    return UpgradeUxOutcome(True, False, None, False, None, False)


def _stash_plan_result(ctx: typer.Context | None, result: object) -> None:
    if ctx is not None and ctx.obj is None:
        ctx.obj = {}
    if ctx is not None and isinstance(ctx.obj, dict):
        ctx.obj["compat_plan_result"] = result


def _build_record_kwargs(
    result: _PlanResultLike,
    existing: NagCacheRecord | None,
    now: datetime,
) -> dict[str, object]:
    return {
        "cli_version_key": result.cli_status.installed_version,
        "latest_version": result.cli_status.latest_version,
        "latest_source": result.cli_status.latest_source,
        "fetched_at": now,
        "last_shown_at": existing.last_shown_at if existing is not None else None,
        "remote_version_seen": existing.remote_version_seen if existing is not None else None,
        "snooze_step": existing.snooze_step if existing is not None else None,
        "snoozed_until": existing.snoozed_until if existing is not None else None,
        "always_upgrade": existing.always_upgrade if existing is not None else False,
        "never_ask": existing.never_ask if existing is not None else False,
    }


def _optional_str_value(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _optional_datetime_value(value: object) -> datetime | None:
    return value if isinstance(value, datetime) else None


def _reset_anchor_if_needed(kwargs: dict[str, object], current_latest: str | None) -> None:
    if needs_reset(
        record_remote_version=_optional_str_value(kwargs.get("remote_version_seen")),
        current_latest=current_latest,
    ):
        kwargs["snooze_step"] = None
        kwargs["snoozed_until"] = None
        kwargs["never_ask"] = False
        kwargs["remote_version_seen"] = current_latest


def _persist_and_return(cache: _NagCacheLike, kwargs: dict[str, object], outcome: UpgradeUxOutcome) -> UpgradeUxOutcome:
    _persist(cache, kwargs)
    return outcome


def _run_auto_upgrade_if_safe(
    *,
    safe: bool,
    method: object,
    latest_version: str | None,
    upgrade_runner: Callable[[], int] | None,
) -> tuple[bool, int | None, bool]:
    if safe:
        if upgrade_runner is None:
            from dataclasses import replace as _replace  # noqa: PLC0415

            from specify_cli.compat._detect.install_method import InstallMethod  # noqa: PLC0415
            from specify_cli.compat._detect.runtime import detect_runtime as _detect_runtime  # noqa: PLC0415
            from specify_cli.compat.remediation import RemediationIntent, plan_remediation  # noqa: PLC0415

            raw_runtime = _detect_runtime()
            # Override install_method with what installer_detector() returned —
            # in tests the injected detector may differ from detect_runtime().
            # Receipt-derived fields (python, tool_dir, etc.) come from detect_runtime().
            runtime = (
                _replace(raw_runtime, install_method=method, safe_for_auto_upgrade=True)
                if isinstance(method, InstallMethod)
                else raw_runtime
            )
            cmd = plan_remediation(runtime, RemediationIntent.UPGRADE, latest_version)
            runner_exit = _default_upgrade_runner(cmd, runtime, target_version=latest_version).returncode
        else:
            runner_exit = upgrade_runner()
        return True, runner_exit, False
    _print_unsafe_installer_guidance(str(method))
    return False, None, True


def _handle_always_preference(
    *,
    cache: _NagCacheLike,
    kwargs: dict[str, object],
    safe: bool,
    method: object,
    current_latest: str | None,
    upgrade_runner: Callable[[], int] | None,
) -> UpgradeUxOutcome:
    attempted, exit_code, guidance_only = _run_auto_upgrade_if_safe(
        safe=safe,
        method=method,
        latest_version=current_latest,
        upgrade_runner=upgrade_runner,
    )
    if exit_code == 0:
        kwargs["snooze_step"] = None
        kwargs["snoozed_until"] = None
    return _persist_and_return(
        cache,
        kwargs,
        UpgradeUxOutcome(True, False, UpgradeChoice.UPGRADE_NOW if attempted else None, attempted, exit_code, guidance_only),
    )


def _handle_prompt_choice(
    *,
    cache: _NagCacheLike,
    kwargs: dict[str, object],
    choice: UpgradeChoice,
    current_latest: str | None,
    now: datetime,
    safe: bool,
    method: object,
    upgrade_runner: Callable[[], int] | None,
) -> UpgradeUxOutcome:
    kwargs["last_shown_at"] = now
    new_kwargs = apply_choice(kwargs, choice=choice, current_latest=current_latest, now=now)
    auto_upgrade_attempted = False
    exit_code: int | None = None
    guidance_only = False
    if choice in (UpgradeChoice.UPGRADE_NOW, UpgradeChoice.ALWAYS):
        auto_upgrade_attempted, exit_code, guidance_only = _run_auto_upgrade_if_safe(
            safe=safe,
            method=method,
            latest_version=current_latest,
            upgrade_runner=upgrade_runner,
        )
    return _persist_and_return(
        cache,
        new_kwargs,
        UpgradeUxOutcome(True, True, choice, auto_upgrade_attempted, exit_code, guidance_only),
    )


def run_upgrade_ux(  # noqa: C901,PLR0911,PLR0912,PLR0913,PLR0915 — orchestrator with many short-circuit branches
    ctx: typer.Context | None,
    *,
    suppressed: bool,
    now: datetime | None = None,
    env: dict[str, str] | None = None,
    prompt: PromptCallback | None = None,
    upgrade_runner: Callable[[], int] | None = None,
    installer_detector: Callable[[], object] | None = None,
) -> UpgradeUxOutcome:
    """Drive the upgrade-readiness UX for one CLI invocation.

    This is the single entry point the coordinator calls on the hosted-on
    path.  It is fully exception-safe; the coordinator's outer try/except
    treats any escape as a no-op result.

    Args:
        ctx: The Typer context (for the legacy nag stash; may be ``None``
            in test paths).
        suppressed: Result of ``_should_suppress_nag()`` from the caller.
            When True, this function returns immediately without prompting,
            without invoking a subprocess, and without writing the cache.
        now: Current UTC datetime (defaults to ``datetime.now(UTC)``).
        env: Environment mapping (defaults to ``os.environ``).
        prompt: Injectable prompt callback for testing.
        upgrade_runner: Injectable subprocess runner for testing.
        installer_detector: Injectable installer detector (returns an
            ``InstallMethod``).

    Returns:
        An :class:`UpgradeUxOutcome` describing what happened.

    The function MUST NOT raise.  All internal exceptions are swallowed
    and recorded as ``ran=False`` outcomes.
    """
    if suppressed:
        return _inactive_outcome()

    if now is None:
        now = datetime.now(UTC)
    if env is None:
        env = dict(os.environ)
    if prompt is None:
        prompt = _default_prompt
    try:
        # Deferred imports.
        from specify_cli.compat import (  # noqa: PLC0415
            Decision,
            Invocation,
            NagCache,
        )
        from specify_cli.compat import plan as compat_plan  # noqa: PLC0415
        from specify_cli.compat._detect.install_method import (  # noqa: PLC0415
            InstallMethod,
            is_safe_for_auto_upgrade,
        )
        from specify_cli.compat._detect.runtime import detect_runtime  # noqa: PLC0415

        if installer_detector is None:
            def _default_installer_detector() -> object:
                return detect_runtime().install_method
            installer_detector = _default_installer_detector

        # Kill switch (env-only; not persisted).
        if _truthy(env.get(ENV_UPGRADE_DISABLED)):
            return _inactive_outcome()

        # Build invocation & planner output.
        inv = Invocation.from_argv()
        if inv.suppresses_nag():
            # Defence-in-depth — caller already supplied `suppressed`.
            return _inactive_outcome()

        result = compat_plan(inv)
        _stash_plan_result(ctx, result)

        if result.decision != Decision.ALLOW_WITH_NAG:
            return _inactive_outcome()

        # Load cache.
        cache = NagCache.default()
        existing = cache.read()
        kwargs = _build_record_kwargs(result, existing, now)

        current_latest = result.cli_status.latest_version

        # Anchor reset: a new remote version clears snooze + never_ask.
        _reset_anchor_if_needed(kwargs, current_latest)

        # Resolve effective preferences (env can elevate but never demote).
        pref = resolve_effective_preference(
            persisted_never_ask=bool(kwargs["never_ask"]),
            persisted_always_upgrade=bool(kwargs["always_upgrade"]),
            env=env,
        )

        if pref.never_ask:
            # Honour preference; do not prompt.  Persist the anchor so a
            # new remote version naturally re-prompts.
            return _persist_and_return(cache, kwargs, _noop_active_outcome())

        # Active snooze?
        if is_currently_snoozed(
            snoozed_until=_optional_datetime_value(kwargs.get("snoozed_until")),
            now=now,
        ):
            return _persist_and_return(cache, kwargs, _noop_active_outcome())

        method = installer_detector()
        safe = is_safe_for_auto_upgrade(method) if isinstance(method, InstallMethod) else False

        # Always-upgrade path: short-circuit the prompt.
        if pref.always_upgrade:
            return _handle_always_preference(
                cache=cache,
                kwargs=kwargs,
                safe=safe,
                method=method,
                current_latest=current_latest,
                upgrade_runner=upgrade_runner,
            )

        # Interactive prompt path.
        choice = prompt()
        return _handle_prompt_choice(
            cache=cache,
            kwargs=kwargs,
            choice=choice,
            current_latest=current_latest,
            now=now,
            safe=safe,
            method=method,
            upgrade_runner=upgrade_runner,
        )
    except Exception:  # noqa: BLE001 — UX path must never raise out of the CLI.
        return _inactive_outcome()


def _persist(cache: _NagCacheLike, kwargs: dict[str, object]) -> None:
    """Best-effort write of a NagCacheRecord to disk.

    Swallows any exception — cache mutation failure must not block the CLI.
    """
    try:
        from specify_cli.compat import NagCacheRecord  # noqa: PLC0415

        cli_version_key = kwargs["cli_version_key"]
        latest_source = kwargs["latest_source"]
        fetched_at = kwargs["fetched_at"]
        if (
            not isinstance(cli_version_key, str)
            or not isinstance(latest_source, str)
            or latest_source not in ("pypi", "none")
            or not isinstance(fetched_at, datetime)
        ):
            return
        canonical_source = cast(Literal["pypi", "none"], latest_source)
        snooze_raw = kwargs.get("snooze_step")
        if snooze_raw == "24h":
            snooze_step: Literal["24h", "48h", "7d"] | None = "24h"
        elif snooze_raw == "48h":
            snooze_step = "48h"
        elif snooze_raw == "7d":
            snooze_step = "7d"
        else:
            snooze_step = None
        record = NagCacheRecord(
            cli_version_key=cli_version_key,
            latest_version=_optional_str_value(kwargs.get("latest_version")),
            latest_source=canonical_source,
            fetched_at=fetched_at,
            last_shown_at=_optional_datetime_value(kwargs.get("last_shown_at")),
            remote_version_seen=_optional_str_value(kwargs.get("remote_version_seen")),
            snooze_step=snooze_step,
            snoozed_until=_optional_datetime_value(kwargs.get("snoozed_until")),
            always_upgrade=bool(kwargs.get("always_upgrade", False)),
            never_ask=bool(kwargs.get("never_ask", False)),
        )
        cache.write(record)
    except Exception:  # noqa: BLE001
        pass


__all__ = [
    # ENV_UPGRADE_AUTO, ENV_UPGRADE_NEVER_ASK: demoted — env-var constants
    # consumed only within this module (WP01 harden-dead-symbol-gate-01KW0RJR).
    "ENV_UPGRADE_DISABLED",
    # EffectivePreference, PromptCallback, UpgradeUxOutcome, advance_snooze:
    # demoted — no cross-module src/ from-import callers (WP01).
    "UpgradeChoice",
    "apply_choice",
    "is_currently_snoozed",
    "needs_reset",
    "resolve_effective_preference",
    "run_upgrade_ux",
]
