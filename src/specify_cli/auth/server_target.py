"""Canonical hosted-server resolution for the surfaces that still call out.

Re-homed from ``specify_cli.sync.target_authority`` when the sync transport was
deleted (issue #5): auth login and the SaaS tracker client still need one
answer to "which server are we hitting?", resolved with a single precedence —
``SPEC_KITTY_SAAS_URL`` over ``config.toml [sync].server_url`` over
:data:`DEFAULT_SERVER_URL` — and the same fail-closed split-brain guard
(env and config disagreeing without a clean whole-process override), decided
*before* any network call.

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

#: Documented default target when neither config nor env supplies one.
DEFAULT_SERVER_URL = "https://spec-kitty-dev.fly.dev"

#: Mirrors ``specify_cli.auth.config._ENV_VAR``; named here so the split-brain
#: message and env read share one literal (Sonar S1192). Explicitly typed:
#: consumers under ``follow_imports = "skip"`` would otherwise see ``Any``.
SAAS_URL_ENV_VAR: str = "SPEC_KITTY_SAAS_URL"

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
    """Read the raw ``[sync].server_url`` key, ``None`` when absent or unreadable."""
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
    return None if value is None else str(value)


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

    Precedence: env first, then config, then :data:`DEFAULT_SERVER_URL`. A
    missing config key compares against the default so env-equal-to-default is
    *not* an override and env-differs-from-default *is*.
    """
    effective_config = _normalize_url(configured_server_url or DEFAULT_SERVER_URL)
    if env_server_url is None:
        return OverrideMode.NONE, effective_config
    env_normalized = _normalize_url(env_server_url)
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


def resolve_server_target(*, process_wide_override: bool = True) -> ResolvedServerTarget:
    """Resolve the single canonical hosted-server target.

    Reads ``[sync].server_url`` and ``SPEC_KITTY_SAAS_URL``, classifies the
    :class:`OverrideMode`, and fails-closed on an ambiguous split-brain before
    any network call. Purely descriptive: no network, no config mutation.
    """
    configured_server_url = _read_configured_server_url()
    env_server_url = _read_env_server_url()
    override_mode, resolved_server_url = _classify_override(
        configured_server_url,
        env_server_url,
        process_wide_override=process_wide_override,
    )
    _guard_split_brain(override_mode, configured_server_url, env_server_url)
    return ResolvedServerTarget(
        configured_server_url=configured_server_url,
        env_server_url=env_server_url,
        override_mode=override_mode,
        resolved_server_url=resolved_server_url,
    )
