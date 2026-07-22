"""Packager-facing ``DistributionProfile`` and its resolver.

Precedence for :func:`resolve_distribution_profile`:

1. ``spec_kitty.distribution_profile`` entry point (zero-arg callable/type →
   :class:`DistributionProfile`)
2. Synthesize from :func:`resolve_cli_package_name` +
   :func:`resolve_upgrade_provider` (Phase 1 thin aliases)
3. Stock defaults (what those resolvers return when nothing is registered)

Never raises. Multi-registration picks the first entry point name
alphabetically (same deterministic rule as the upgrade-provider resolver).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from importlib.metadata import EntryPoint, entry_points

from specify_cli.compat.provider import LatestVersionProvider, PyPIProvider
from specify_cli.distribution.package_name import (
    DEFAULT_CLI_PACKAGE_NAME,
    resolve_cli_package_name,
)
from specify_cli.distribution.upgrade_provider import resolve_upgrade_provider

__all__ = [
    "DISTRIBUTION_PROFILE_GROUP",
    "DistributionProfile",
    "clear_distribution_profile_cache",
    "resolve_distribution_profile",
    "stock_distribution_profile",
]

DISTRIBUTION_PROFILE_GROUP = "spec_kitty.distribution_profile"

_cached_profile: DistributionProfile | None = None


_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class DistributionProfile:
    """Aggregated packager knobs for CLI identity, upgrade source, and UX.

    Attributes:
        package_name: Canonical distribution name (never from a runtime env var).
        package_aliases: Ordered fallbacks for installed-version lookup.
        upgrade_provider: Resolved :class:`LatestVersionProvider` instance, or
            ``None`` when the packager leaves upgrade lookup unset.
        index_url: Primary simple/PyPI-compatible index for remediation argv.
        extra_index_url: Secondary index for remediation argv.
        data_freshness_seconds: Optional TTL override for re-query decisions.
        disable_public_pypi_notifier: When ``True``, suppress the stock
            public-PyPI “no upgrade” notice.
        version_label: Optional ``--version`` banner label; ``None`` means use
            ``package_name``.
    """

    package_name: str
    package_aliases: tuple[str, ...] = ()
    upgrade_provider: LatestVersionProvider | object | None = None
    index_url: str | None = None
    extra_index_url: str | None = None
    data_freshness_seconds: int | None = None
    disable_public_pypi_notifier: bool = False
    version_label: str | None = None


def clear_distribution_profile_cache() -> None:
    """Clear the process-level memo (tests only)."""
    global _cached_profile
    _cached_profile = None


def stock_distribution_profile() -> DistributionProfile:
    """Return the public-PyPI / ``spec-kitty-cli`` stock profile."""
    return DistributionProfile(
        package_name=DEFAULT_CLI_PACKAGE_NAME,
        package_aliases=(),
        upgrade_provider=PyPIProvider(),
        index_url=None,
        extra_index_url=None,
        data_freshness_seconds=None,
        disable_public_pypi_notifier=False,
        version_label=None,
    )


def resolve_distribution_profile() -> DistributionProfile:
    """Return the active distribution profile. Never raises."""
    global _cached_profile
    if _cached_profile is not None:
        return _cached_profile
    profile = _resolve_distribution_profile_uncached()
    _cached_profile = profile
    return profile


def _resolve_distribution_profile_uncached() -> DistributionProfile:
    try:
        discovered = list(entry_points(group=DISTRIBUTION_PROFILE_GROUP))
    except Exception:
        return _synthesize_from_phase1()

    selected = _select_entry_point(discovered)
    if selected is None:
        return _synthesize_from_phase1()

    loaded_profile = _profile_from_entry_point(selected)
    if loaded_profile is not None:
        return loaded_profile

    return _synthesize_from_phase1()


def _synthesize_from_phase1() -> DistributionProfile:
    """Build a minimal profile from Phase 1 resolvers (FR-017 thin aliases)."""
    try:
        package_name = resolve_cli_package_name()
    except Exception:
        package_name = DEFAULT_CLI_PACKAGE_NAME

    try:
        provider: LatestVersionProvider | object | None = resolve_upgrade_provider()
    except Exception:
        provider = PyPIProvider()

    # Derive from the single stock definition so field defaults (index_url,
    # freshness TTL, notifier flag, …) live in one place and cannot drift; only
    # the Phase-1-resolvable fields are overridden.
    return replace(
        stock_distribution_profile(),
        package_name=package_name,
        upgrade_provider=provider,
    )


def _select_entry_point(discovered: list[EntryPoint]) -> EntryPoint | None:
    if not discovered:
        return None
    if len(discovered) == 1:
        return discovered[0]
    return sorted(discovered, key=lambda entry: entry.name)[0]


def _profile_from_entry_point(entry: EntryPoint) -> DistributionProfile | None:
    try:
        loaded = entry.load()
    except Exception:
        _log.debug(
            "spec_kitty.distribution_profile entry point %r failed to load; using stock profile",
            entry.name,
            exc_info=True,
        )
        return None

    try:
        if isinstance(loaded, DistributionProfile):
            return loaded
        if isinstance(loaded, type):
            instance = loaded()
            return instance if isinstance(instance, DistributionProfile) else None
        if callable(loaded):
            value = loaded()
            return value if isinstance(value, DistributionProfile) else None
    except Exception:
        return None

    return None
