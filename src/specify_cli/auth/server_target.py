"""Canonical hosted-server resolution for the surfaces that still call out.

Re-homed from ``specify_cli.sync.target_authority`` when the sync transport was
deleted (issue #5): auth login and the SaaS tracker client still need one
answer to "which server are we hitting?", resolved with a single precedence —
``SPEC_KITTY_SAAS_URL`` over ``config.toml [sync].server_url`` — and two
fail-closed guards, decided *before* any network call: an ambiguous split-brain
(env and config disagreeing without a clean whole-process override) and a
missing target entirely (#179 — the resolver never guesses a tenant; with no
env value and no config value it raises :class:`ConfigurationError`, the same
remedy ``auth login`` has always printed).

The queue-scope half of the old resolver died with the sync transport; what
remains is purely descriptive — no network, no config mutation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum

import toml

from specify_cli.auth.config import get_saas_base_url
from specify_cli.auth.errors import ConfigurationError

_LOG = logging.getLogger(__name__)

#: Mirrors ``specify_cli.auth.config._ENV_VAR``; named here so the fail-closed
#: and split-brain messages and the env read share one literal (Sonar S1192).
#: Explicitly typed: consumers under ``follow_imports = "skip"`` would
#: otherwise see ``Any``.
SAAS_URL_ENV_VAR: str = "SPEC_KITTY_SAAS_URL"

#: The fail-closed remedy printed when neither source names a target (#179).
#: Same wording ``auth login`` has always shown, so every hosted surface gives
#: one answer instead of silently resolving to a stale host.
_NO_TARGET_MESSAGE = "No hosted server is configured. Set {env_var} (or set [sync].server_url in your config.toml), then try again."

_SPLIT_BRAIN_MESSAGE = (
    "Server target split-brain detected before any network call: config.toml "
    "[sync].server_url={config!r} disagrees with environment "
    "{env_var}={env!r}. Either set {env_var} as an explicit whole-process "
    "override so every hosted call resolves to a single target, or remove "
    "{env_var}."
)


class OverrideMode(StrEnum):
    """How the resolved target was chosen (descriptive only)."""

    NONE = "none"
    PROCESS_OVERRIDE = "process_override"
    SETUP_ONLY = "setup_only"


class ServerTargetSplitBrainError(RuntimeError):
    """Raised when env and config disagree without a clean whole-process override.

    The message names both URLs and the source so an operator can reconcile
    ``config.toml`` and ``SPEC_KITTY_SAAS_URL``.
    """

    def __init__(self, *, configured_server_url: str | None, env_server_url: str | None) -> None:
        super().__init__(
            _SPLIT_BRAIN_MESSAGE.format(
                config=configured_server_url,
                env=env_server_url,
                env_var=SAAS_URL_ENV_VAR,
            )
        )
        self.configured_server_url = configured_server_url
        self.env_server_url = env_server_url


@dataclass(frozen=True, slots=True)
class ResolvedServerTarget:
    """The resolved hosted-server target plus its provenance."""

    configured_server_url: str | None
    env_server_url: str | None
    override_mode: OverrideMode
    resolved_server_url: str

    def to_diagnostics_dict(self) -> dict[str, str | None]:
        """Return the resolution inputs for structured output."""
        return {
            "configured_server_url": self.configured_server_url,
            "env_server_url": self.env_server_url,
            "override_mode": self.override_mode.value,
            "resolved_server_url": self.resolved_server_url,
        }


def _normalize_url(url: str) -> str:
    """Normalize a URL for comparison and resolution: strip + drop trailing ``/``."""
    return url.strip().rstrip("/")


def _read_configured_server_url() -> str | None:
    """Read ``[sync].server_url``, normalizing absent/unreadable/blank to ``None``.

    Blank gets the same treatment the env read gives a whitespace-only value
    (#179): an empty string is no opinion, not a candidate target, so it must
    not slip past the fail-closed guard or pose as a disagreeing config value.
    """
    from specify_cli.paths import get_runtime_root

    config_file = get_runtime_root().base / "config.toml"
    if not config_file.exists():
        return None
    try:
        data = toml.load(config_file)
    except (toml.TomlDecodeError, OSError):
        return None
    sync_table = data.get("sync")
    if not isinstance(sync_table, dict):
        return None
    value = sync_table.get("server_url")
    if value is None:
        return None
    return _normalize_url(str(value)) or None


def _read_env_server_url() -> str | None:
    """Read ``SPEC_KITTY_SAAS_URL``, normalizing blank/whitespace to ``None``."""
    try:
        raw = get_saas_base_url()
    except ConfigurationError:
        return None
    normalized = _normalize_url(str(raw))
    return normalized or None


def _classify_override(
    configured_server_url: str | None,
    env_server_url: str | None,
    *,
    process_wide_override: bool,
) -> tuple[OverrideMode, str]:
    """Decide ``(override_mode, resolved_server_url)`` — pure, no I/O.

    Precedence: env first, then config. At least one source must be present —
    ``resolve_server_target`` fails closed before calling this. A missing
    config key is *no opinion*, not a candidate target: an env-only machine
    resolves cleanly (to the env URL) even in a setup-only context, because
    with no configured value there is nothing for the env var to disagree with.
    """
    if env_server_url is None:
        # Caller guarantees the config value is set on this path.
        return OverrideMode.NONE, _normalize_url(str(configured_server_url))
    env_normalized = _normalize_url(env_server_url)
    if configured_server_url is None:
        return OverrideMode.PROCESS_OVERRIDE, env_normalized
    effective_config = _normalize_url(configured_server_url)
    if env_normalized == effective_config:
        return OverrideMode.NONE, effective_config
    if process_wide_override:
        # Whole-process override: env wins everywhere.
        return OverrideMode.PROCESS_OVERRIDE, env_normalized
    # Disagreement scoped to a setup/diagnostic context — the guard fails-closed.
    return OverrideMode.SETUP_ONLY, effective_config


def _guard_split_brain(
    override_mode: OverrideMode,
    configured_server_url: str | None,
    env_server_url: str | None,
) -> None:
    """Fail-closed for an ambiguous env/config disagreement."""
    if override_mode is OverrideMode.SETUP_ONLY:
        raise ServerTargetSplitBrainError(
            configured_server_url=configured_server_url,
            env_server_url=env_server_url,
        )


def _warn_process_override(
    override_mode: OverrideMode,
    configured_server_url: str | None,
    resolved_server_url: str,
) -> None:
    """Log when a whole-process override silently redirects a *configured* target.

    Only fires when ``configured_server_url`` names an actual, different target
    that ``{env_var}`` is overriding — an env-only machine has no configured
    opinion to override, so it is not a redirection and stays quiet (#117:
    editing ``[sync].server_url`` or ``{env_var}`` used to be cross-checked
    against a durable per-project admission binding before that binding was
    deleted with the sync transport; this is the visible signal that survives
    without resurrecting that store).
    """
    if override_mode is OverrideMode.PROCESS_OVERRIDE and configured_server_url is not None:
        _LOG.warning(
            "%s=%r overrides configured [sync].server_url=%r for this process; "
            "bearer-token-bearing traffic now targets %r instead of the configured host.",
            SAAS_URL_ENV_VAR,
            resolved_server_url,
            configured_server_url,
            resolved_server_url,
        )


def resolve_server_target(*, process_wide_override: bool = True) -> ResolvedServerTarget:
    """Resolve the single canonical hosted-server target.

    Reads ``[sync].server_url`` and ``SPEC_KITTY_SAAS_URL``, classifies the
    :class:`OverrideMode`, and fails-closed before any network call — both on an
    ambiguous split-brain and (issue #179) on no target at all. Purely
    descriptive: no network, no config mutation.

    Raises:
        ConfigurationError: When neither the env var nor ``config.toml`` names
            a server. The CLI has no business guessing a tenant.
        ServerTargetSplitBrainError: When env and config disagree without a
            clean whole-process override.
    """
    configured_server_url = _read_configured_server_url()
    env_server_url = _read_env_server_url()
    if env_server_url is None and configured_server_url is None:
        raise ConfigurationError(_NO_TARGET_MESSAGE.format(env_var=SAAS_URL_ENV_VAR))
    override_mode, resolved_server_url = _classify_override(
        configured_server_url,
        env_server_url,
        process_wide_override=process_wide_override,
    )
    _guard_split_brain(override_mode, configured_server_url, env_server_url)
    _warn_process_override(override_mode, configured_server_url, resolved_server_url)
    return ResolvedServerTarget(
        configured_server_url=configured_server_url,
        env_server_url=env_server_url,
        override_mode=override_mode,
        resolved_server_url=resolved_server_url,
    )
