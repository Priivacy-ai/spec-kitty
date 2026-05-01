"""Hosted-readiness evaluator for the Spec Kitty SaaS sync subsystem.

Stability contract: ``kitty-specs/082-stealth-gated-saas-sync-hardening/contracts/hosted_readiness.md``

Every non-``READY`` state produces a ``ReadinessResult`` whose ``message`` names the
missing prerequisite explicitly (NFR-002) and whose ``next_action`` gives one
concrete actionable step.  Wording is frozen in ``_WORDING`` and asserted
byte-for-byte by ``tests/saas/test_readiness_unit.py``.

Call :func:`evaluate_readiness` with keyword-only arguments; it **never raises** —
any unexpected exception is converted into a ``HOST_UNREACHABLE`` result with
the exception type in ``details["error"]``.
"""

from __future__ import annotations

import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Mapping


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class ReadinessState(str, Enum):
    """Discrete readiness states in check order.

    The evaluator checks states in *declaration order* — cheapest and most
    consequential first.  The first failing state short-circuits the chain.
    Adding new members is additive; removing or renaming requires a follow-up
    mission.
    """

    ROLLOUT_DISABLED = "rollout_disabled"
    MISSING_AUTH = "missing_auth"
    MISSING_HOST_CONFIG = "missing_host_config"
    HOST_UNREACHABLE = "host_unreachable"
    MISSING_MISSION_BINDING = "missing_mission_binding"
    READY = "ready"


@dataclass(frozen=True)
class ReadinessResult:
    """Immutable snapshot of the hosted-readiness evaluation.

    ``is_ready`` is a convenience property; callers should switch on ``state``
    for structured handling.
    """

    state: ReadinessState
    message: str
    next_action: str | None
    details: Mapping[str, str] = field(default_factory=dict)

    @property
    def is_ready(self) -> bool:
        """True iff ``state`` is :attr:`ReadinessState.READY`."""
        return self.state is ReadinessState.READY


# ---------------------------------------------------------------------------
# Stable failure-message catalog (module-private)
# ---------------------------------------------------------------------------
#
# Each entry is (message_template, next_action_template).  Entries for
# HOST_UNREACHABLE and MISSING_MISSION_BINDING contain ``{server_url}`` /
# ``{feature_slug}`` placeholders, resolved at construction time by
# ``_build_result``.  Do not use f-strings here — keep the catalog as plain
# string literals so tests can assert them byte-for-byte.

_WORDING: dict[ReadinessState, tuple[str, str]] = {
    ReadinessState.ROLLOUT_DISABLED: (
        "Hosted SaaS sync is not enabled on this machine.",
        "Set `SPEC_KITTY_ENABLE_SAAS_SYNC=1` to opt in.",
    ),
    ReadinessState.MISSING_AUTH: (
        "No SaaS authentication token is present.",
        "Run `spec-kitty auth login`.",
    ),
    ReadinessState.MISSING_HOST_CONFIG: (
        "No SaaS host URL is configured.",
        "Set `SPEC_KITTY_SAAS_URL` in your environment.",
    ),
    ReadinessState.HOST_UNREACHABLE: (
        "The configured SaaS host did not respond within 2 seconds.",
        "Check network connectivity to `{server_url}` and retry.",
    ),
    ReadinessState.MISSING_MISSION_BINDING: (
        "No tracker binding exists for feature `{feature_slug}`.",
        "Run `spec-kitty tracker bind` from this repo.",
    ),
}


def _build_result(state: ReadinessState, **fmt_kwargs: str) -> ReadinessResult:
    """Look up wording, format placeholders, and return a ``ReadinessResult``.

    For ``READY``, returns a result with empty ``message`` and ``None``
    ``next_action`` — no lookup needed.
    """
    if state is ReadinessState.READY:
        return ReadinessResult(state=state, message="", next_action=None)

    message_tmpl, next_action_tmpl = _WORDING[state]
    message = message_tmpl.format(**fmt_kwargs) if fmt_kwargs else message_tmpl
    next_action = next_action_tmpl.format(**fmt_kwargs) if fmt_kwargs else next_action_tmpl
    return ReadinessResult(state=state, message=message, next_action=next_action)


# ---------------------------------------------------------------------------
# Private probe helpers (no-raise contract)
# ---------------------------------------------------------------------------
#
# Each helper catches its own exceptions and returns a signal value.  They are
# module-level so unit tests can monkeypatch them via
# ``monkeypatch.setattr("specify_cli.saas.readiness._probe_auth", ...)``.


def _probe_rollout() -> bool:
    """Return True iff SaaS sync is enabled via the environment variable."""
    from specify_cli.saas.rollout import is_saas_sync_enabled  # avoid circular at module level

    try:
        return bool(is_saas_sync_enabled())
    except Exception:  # noqa: BLE001
        return False


def _probe_auth(repo_root: Path) -> bool:
    """Return True iff the process-wide TokenManager reports an active session.

    Monkeypatch target for unit tests:
        ``specify_cli.saas.readiness._probe_auth``

    The ``repo_root`` parameter is accepted for API consistency and may be
    used by future callers that need per-repo credential isolation.  The
    current TokenManager is process-wide (``specify_cli.auth.get_token_manager``).
    """
    # ``repo_root`` is reserved for future per-repo credential isolation.
    _ = repo_root
    try:
        from specify_cli.auth import get_token_manager  # local import — auth may not be in path

        return bool(get_token_manager().is_authenticated)
    except Exception:  # noqa: BLE001
        return False


def _probe_host_config() -> str | None:
    """Return the configured SaaS base URL, or ``None`` if not configured.

    Calls ``specify_cli.auth.config.get_saas_base_url()`` which reads the
    ``SPEC_KITTY_SAAS_URL`` environment variable.  Returns ``None`` when that
    function raises ``ConfigurationError`` (env var unset or empty).

    Per decision D-5 this is the authoritative host URL surface — do NOT fall
    back to ``SyncConfig.get_server_url()``.
    """
    try:
        from specify_cli.auth.config import get_saas_base_url
        from specify_cli.auth.errors import ConfigurationError

        try:
            url: str = get_saas_base_url()
            return url
        except ConfigurationError:
            return None
    except Exception:  # noqa: BLE001
        return None


def _probe_reachability(server_url: str, timeout_s: float = 2.0) -> bool:
    """Return True iff a HEAD request to ``server_url`` succeeds within the budget.

    Uses only ``urllib.request`` (stdlib) so there is no dependency on
    ``httpx`` / ``requests`` here.  Any exception — connection refused, DNS
    failure, timeout, etc. — returns ``False``.
    """
    try:
        req = urllib.request.Request(server_url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout_s):  # noqa: S310  # nosec B310
            return True
    except Exception:  # noqa: BLE001
        return False


def _probe_mission_binding(repo_root: Path) -> bool:
    """Return True iff a tracker binding exists in ``repo_root``.

    Delegates to ``specify_cli.tracker.config.load_tracker_config`` — the
    same path used by tracker CLI commands.  Returns ``False`` if no binding
    is configured or if any error occurs.
    """
    try:
        from specify_cli.tracker.config import load_tracker_config

        config = load_tracker_config(repo_root)
        return bool(config.is_configured)
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# Public evaluator
# ---------------------------------------------------------------------------


def evaluate_readiness(
    *,
    repo_root: Path,
    feature_slug: str | None = None,
    require_mission_binding: bool = False,
    probe_reachability: bool = False,
) -> ReadinessResult:
    """Evaluate all hosted-sync prerequisites in contract-defined order.

    Returns a :class:`ReadinessResult` whose ``state`` identifies the first
    failing prerequisite (or ``READY`` when all pass).  **Never raises** —
    any unexpected exception inside the evaluator body is converted to a
    ``HOST_UNREACHABLE`` result with ``details["error"]`` set to the exception
    type name.

    Check order (short-circuits on first failure):

    1. Rollout gate (``SPEC_KITTY_ENABLE_SAAS_SYNC``)
    2. Auth (``TokenManager.is_authenticated``)
    3. Host config (``SPEC_KITTY_SAAS_URL`` via ``get_saas_base_url()``)
    4. Reachability — only when ``probe_reachability=True``
    5. Mission binding — only when ``require_mission_binding=True``
    6. ``READY``

    Args:
        repo_root: Absolute path to the repository root; used to locate auth,
            config, and tracker bindings.
        feature_slug: Active feature slug.  Required when
            ``require_mission_binding=True`` (otherwise ignored).
        require_mission_binding: When ``True``, an absent tracker binding
            causes ``MISSING_MISSION_BINDING``; otherwise binding is not
            checked.
        probe_reachability: When ``True``, issue a single bounded HTTP
            ``HEAD`` against the configured URL.  Adds up to 2 seconds of
            latency; omit for fast local-only checks.

    Returns:
        A frozen :class:`ReadinessResult`.
    """
    try:
        # Step 1: rollout gate
        if not _probe_rollout():
            return _build_result(ReadinessState.ROLLOUT_DISABLED)

        # Step 2: auth
        if not _probe_auth(repo_root):
            return _build_result(ReadinessState.MISSING_AUTH)

        # Step 3: host config — also captures server_url for later steps
        server_url = _probe_host_config()
        if server_url is None:
            return _build_result(ReadinessState.MISSING_HOST_CONFIG)

        # Step 4: reachability (optional)
        if probe_reachability and not _probe_reachability(server_url):
            return _build_result(ReadinessState.HOST_UNREACHABLE, server_url=server_url)

        # Step 5: mission binding (optional)
        if require_mission_binding and not _probe_mission_binding(repo_root):
            return _build_result(
                ReadinessState.MISSING_MISSION_BINDING,
                feature_slug=feature_slug or "",
            )

        # All applicable checks passed.
        return _build_result(ReadinessState.READY)

    except Exception as exc:  # noqa: BLE001
        return ReadinessResult(
            state=ReadinessState.HOST_UNREACHABLE,
            message=_WORDING[ReadinessState.HOST_UNREACHABLE][0],
            next_action=_WORDING[ReadinessState.HOST_UNREACHABLE][1].format(server_url=""),
            details={"error": type(exc).__name__},
        )
