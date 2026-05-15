"""PyPI upgrade probe with no-upgrade classification.

This module is the network-touching half of the "no-upgrade available" UX
introduced for FR-007 / WP09. It performs a single, timeout-bounded GET against
PyPI's JSON metadata endpoint and classifies the installed CLI version.

The probe applies the **secure-design-checklist** tactic
(`src/doctrine/tactics/shipped/secure-design-checklist.tactic.yaml`) to the new
external surface. Specifically:

- **Least Privilege**: a single GET against a public endpoint, no auth, no PII.
- **Fail-Safe Defaults**: every exception is caught and resolves to
  ``UpgradeChannel.UNKNOWN`` with the error captured. No exception escapes
  into the CLI hot path.
- **Complete Mediation**: the timeout is enforced via ``httpx.Client(timeout=...)``
  and applied to the request.
- **Economy of Mechanism**: pure functions, frozen dataclasses, no I/O outside
  the GET. The cache is a sibling module's concern.

The probe **never** raises. Callers can rely on the returned
``UpgradeProbeResult`` being well-formed even on total network failure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import StrEnum
from typing import Any

import httpx
from packaging.version import InvalidVersion, Version

PYPI_JSON_URL = "https://pypi.org/pypi/spec-kitty-cli/json"
"""PyPI's standard JSON metadata endpoint for the ``spec-kitty-cli`` package."""

DEFAULT_TIMEOUT_S = 2.0
"""Hard ceiling on the probe wall-clock budget. Any timeout resolves to UNKNOWN."""


class UpgradeChannel(StrEnum):
    """Classification of installed CLI version relative to PyPI metadata.

    The four values correspond to the channel-classification rules in
    ``contracts/upgrade-probe-and-notifier.md``.
    """

    ALREADY_CURRENT = "already_current"
    """Installed version equals PyPI ``info.version`` (you're on the latest)."""

    AHEAD_OF_PYPI = "ahead_of_pypi"
    """Installed version > PyPI ``info.version`` (RC/dev build ahead of release)."""

    NO_UPGRADE_PATH = "no_upgrade_path"
    """Installed version not present in PyPI ``releases`` (non-PyPI build)."""

    UPGRADE_AVAILABLE = "upgrade_available"
    """Installed version is older than PyPI ``info.version``; existing nag owns it."""

    UNKNOWN = "unknown"
    """Probe failed: timeout, HTTP error, parse error, or malformed response."""


@dataclass(frozen=True)
class UpgradeProbeResult:
    """Outcome of a single PyPI probe.

    Frozen dataclass — caller cannot mutate. Serialized to JSON for the
    sibling notifier's cache; see ``upgrade_notifier`` for the cache schema.
    """

    installed_version: str
    """The value ``get_cli_version()`` returned at probe time."""

    latest_pypi_version: str | None
    """``info.version`` from PyPI, or ``None`` when the probe failed."""

    channel: UpgradeChannel
    """Classification of ``installed_version`` relative to PyPI metadata."""

    probed_at: datetime
    """UTC timestamp of the probe. ISO-8601 when serialized to the cache."""

    error: str | None = None
    """Populated when ``channel == UNKNOWN``; otherwise ``None``."""

    releases: tuple[str, ...] = field(default=())
    """All known PyPI release versions. Empty tuple on probe failure.

    Kept in the result so the notifier's cache layer can re-classify if the
    installed version changes mid-cache-window without re-probing.
    """


def probe_pypi(
    cli_version: str,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    transport: httpx.BaseTransport | None = None,
) -> UpgradeProbeResult:
    """Query PyPI and classify the installed CLI version.

    Args:
        cli_version: The installed CLI version (from ``get_cli_version()``).
        timeout_s: Hard timeout on the network call. Defaults to 2 s.
        transport: Optional httpx transport for tests (``MockTransport`` etc.).
            Production callers should leave this unset.

    Returns:
        A well-formed ``UpgradeProbeResult``. Never raises.

    Notes:
        - The User-Agent identifies the CLI per the secure-design-checklist
          "Open Design" principle (auditable client identity).
        - The function swallows ``Exception`` deliberately. PyPI / network
          failures must not break the user's command invocation. The error
          message is captured in ``UpgradeProbeResult.error`` for debugging.
    """
    user_agent = (
        f"spec-kitty-cli/{cli_version} "
        "(https://github.com/Priivacy-ai/spec-kitty)"
    )
    probed_at = datetime.now(UTC)

    try:
        client_kwargs: dict[str, Any] = {
            "timeout": httpx.Timeout(timeout_s),
            "headers": {"User-Agent": user_agent},
        }
        if transport is not None:
            client_kwargs["transport"] = transport

        with httpx.Client(**client_kwargs) as client:
            response = client.get(PYPI_JSON_URL)
            response.raise_for_status()
            payload = response.json()

        info = payload.get("info") or {}
        latest = info.get("version")
        if not isinstance(latest, str) or not latest:
            return _unknown(
                cli_version,
                probed_at,
                "PyPI response missing info.version",
            )

        releases_dict = payload.get("releases") or {}
        if not isinstance(releases_dict, dict):
            return _unknown(
                cli_version,
                probed_at,
                "PyPI response releases is not an object",
            )
        releases = tuple(releases_dict.keys())

        channel = _classify(cli_version, latest, releases)
        return UpgradeProbeResult(
            installed_version=cli_version,
            latest_pypi_version=latest,
            channel=channel,
            probed_at=probed_at,
            error=None,
            releases=releases,
        )

    except Exception as exc:  # noqa: BLE001 — fail-safe-default per secure-design-checklist
        return _unknown(cli_version, probed_at, f"{type(exc).__name__}: {exc}")


def _unknown(cli_version: str, probed_at: datetime, error: str) -> UpgradeProbeResult:
    """Build an UNKNOWN-channel result with a debug-friendly error string."""
    return UpgradeProbeResult(
        installed_version=cli_version,
        latest_pypi_version=None,
        channel=UpgradeChannel.UNKNOWN,
        probed_at=probed_at,
        error=error,
        releases=(),
    )


def _classify(
    installed: str,
    latest: str,
    releases: tuple[str, ...],
) -> UpgradeChannel:
    """Classify the installed version against PyPI metadata per the contract.

    Returns ``UNKNOWN`` only when the installed version cannot be parsed as a
    PEP 440 version. Network/parse failures are handled upstream in
    :func:`probe_pypi`.
    """
    try:
        installed_ver = Version(installed)
    except InvalidVersion:
        return UpgradeChannel.UNKNOWN

    latest_ver: Version | None
    try:
        latest_ver = Version(latest)
    except InvalidVersion:
        # Latest is malformed — fall through to releases-membership check.
        latest_ver = None

    if latest_ver is not None and installed_ver == latest_ver:
        return UpgradeChannel.ALREADY_CURRENT
    if latest_ver is not None and installed_ver > latest_ver:
        return UpgradeChannel.AHEAD_OF_PYPI

    # installed != latest (or latest unparseable). Check releases membership.
    if installed not in releases:
        return UpgradeChannel.NO_UPGRADE_PATH

    # Installed version is in releases but is older than latest. There IS an
    # upgrade path, so the no-upgrade notifier must stay silent and let the
    # existing upgrade nag render the actionable prompt.
    return UpgradeChannel.UPGRADE_AVAILABLE


__all__ = [
    "PYPI_JSON_URL",
    "DEFAULT_TIMEOUT_S",
    "UpgradeChannel",
    "UpgradeProbeResult",
    "probe_pypi",
]
