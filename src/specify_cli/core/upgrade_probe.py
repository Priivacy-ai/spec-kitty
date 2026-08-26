"""GitHub Releases upgrade probe with no-upgrade classification.

This module is the network-touching half of the "no-upgrade available" UX
introduced for FR-007 / WP09. It performs a single, timeout-bounded GET against
the programme's GitHub Releases endpoint and classifies the installed CLI
version.

The probe applies the **secure-design-checklist** tactic
(`packs/built-in/tactics/secure-design-checklist.tactic.yaml`) to the new
external surface. Specifically:

- **Least Privilege**: a single GET against release metadata, no secrets, no PII.
- **Fail-Safe Defaults**: every exception is caught and resolves to
  packaged private-release identity on the private-repo 404 path, otherwise
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

import importlib.resources
import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import httpx

from kernel.clock import datetime, now_utc

from specify_cli.core.version_compare import is_version_newer, try_parse_version

GITHUB_RELEASES_URL = "https://api.github.com/repos/spec-kitty/EXPERIMENTAL-spec-kitty/releases?per_page=100"
"""GitHub Releases endpoint for the programme's authoritative CLI release channel."""

RELEASE_IDENTITY_RESOURCE = "release_identity.json"
"""Packaged private-release identity used when GitHub hides the private repo."""

PYPI_JSON_URL = GITHUB_RELEASES_URL
"""Deprecated compatibility alias for older tests/callers."""

DEFAULT_TIMEOUT_S = 2.0
"""Hard ceiling on the probe wall-clock budget. Any timeout resolves to UNKNOWN."""


class UpgradeChannel(StrEnum):
    """Classification of installed CLI version relative to release metadata.

    The four values correspond to the channel-classification rules in
    ``contracts/upgrade-probe-and-notifier.md``.
    """

    ALREADY_CURRENT = "already_current"
    """Installed version equals the latest release (you're on the latest)."""

    AHEAD_OF_PYPI = "ahead_of_pypi"
    """Installed version > latest selected release and is itself a known release."""

    NO_UPGRADE_PATH = "no_upgrade_path"
    """Installed version not present in current-org GitHub Releases."""

    UPGRADE_AVAILABLE = "upgrade_available"
    """Installed version is older than the latest release; existing nag owns it."""

    UNKNOWN = "unknown"
    """Probe failed: timeout, HTTP error, parse error, or malformed response."""


@dataclass(frozen=True)
class UpgradeProbeResult:
    """Outcome of a single GitHub Releases probe.

    Frozen dataclass — caller cannot mutate. Serialized to JSON for the
    sibling notifier's cache; see ``upgrade_notifier`` for the cache schema.
    """

    installed_version: str
    """The value ``get_cli_version()`` returned at probe time."""

    latest_pypi_version: str | None
    """Latest selected GitHub release version, or ``None`` when the probe failed.

    Channel-aware (T022, C-CHN-2): when the rc channel is opted into (see
    ``prerelease`` on :func:`probe_pypi`), this is instead the highest
    version across ``releases`` (pre-releases included). Default-off (the
    common case) this is the highest stable GitHub Release, falling back to
    the highest release when the channel has no stable tag yet.
    """

    channel: UpgradeChannel
    """Classification of ``installed_version`` relative to release metadata."""

    probed_at: datetime
    """UTC timestamp of the probe. ISO-8601 when serialized to the cache."""

    error: str | None = None
    """Populated when ``channel == UNKNOWN``; otherwise ``None``."""

    releases: tuple[str, ...] = field(default=())
    """All known GitHub release versions. Empty tuple on probe failure.

    Kept in the result so the notifier's cache layer can re-classify if the
    installed version changes mid-cache-window without re-probing.
    """


def probe_pypi(
    cli_version: str,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    transport: httpx.BaseTransport | None = None,
    prerelease: bool | None = None,
) -> UpgradeProbeResult:
    """Query GitHub Releases and classify the installed CLI version.

    Args:
        cli_version: The installed CLI version (from ``get_cli_version()``).
        timeout_s: Hard timeout on the network call. Defaults to 2 s.
        transport: Optional httpx transport for tests (``MockTransport`` etc.).
            Production callers should leave this unset.
        prerelease: Channel override for tests. ``None`` (the production
            default) resolves the single read via
            ``core.channel.prerelease_enabled()`` — this function is the top
            of its own call graph (the notifier caller doesn't thread the
            channel through), so it is the one place the flag is read rather
            than accepted as a required argument. When True (T022, C-CHN-2),
            classification uses the highest version across all releases
            (pre-releases included) instead of the latest stable release.

    Returns:
        A well-formed ``UpgradeProbeResult``. Never raises.

    Notes:
        - The User-Agent identifies the CLI per the secure-design-checklist
          "Open Design" principle (auditable client identity).
        - The function swallows ``Exception`` deliberately. Release / network
          failures must not break the user's command invocation. The error
          message is captured in ``UpgradeProbeResult.error`` for debugging.
    """
    if prerelease is None:
        from specify_cli.core.channel import prerelease_enabled

        prerelease = prerelease_enabled()

    user_agent = f"spec-kitty-cli/{cli_version} (https://github.com/spec-kitty/EXPERIMENTAL-spec-kitty)"
    probed_at = now_utc()

    try:
        client_kwargs: dict[str, Any] = {
            "timeout": httpx.Timeout(timeout_s),
            "headers": {"User-Agent": user_agent},
        }
        if transport is not None:
            client_kwargs["transport"] = transport

        with httpx.Client(**client_kwargs) as client:
            response = client.get(GITHUB_RELEASES_URL)
            response.raise_for_status()
            payload = response.json()

        releases = _release_versions_from_payload(payload)
        if not releases:
            return _unknown(
                cli_version,
                probed_at,
                "GitHub Releases response did not include release tags",
            )

        release_latest = _highest_release(releases, include_prerelease=True)
        if release_latest is None:
            return _unknown(
                cli_version,
                probed_at,
                "GitHub Releases response did not include parseable release tags",
            )
        stable_latest = _highest_release(releases, include_prerelease=False) or release_latest
        channel_latest = _channel_latest(stable_latest, releases, prerelease=prerelease)
        channel = _classify(cli_version, channel_latest, releases)
        return UpgradeProbeResult(
            installed_version=cli_version,
            latest_pypi_version=channel_latest,
            channel=channel,
            probed_at=probed_at,
            error=None,
            releases=releases,
        )

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            fallback = _from_bundled_release_identity(cli_version, probed_at, prerelease=prerelease)
            if fallback is not None:
                return fallback
        return _unknown(cli_version, probed_at, f"{type(exc).__name__}: {exc}")
    except Exception as exc:  # noqa: BLE001 — fail-safe-default per secure-design-checklist
        return _unknown(cli_version, probed_at, f"{type(exc).__name__}: {exc}")


def _channel_latest(stable_latest: str, releases: tuple[str, ...], *, prerelease: bool) -> str:
    """Return the "latest" version to classify against, per the active channel.

    Default (``prerelease=False``, C-CHN-1): the highest stable GitHub release.
    Opted in (``prerelease=True``, C-CHN-2): the highest version across
    *releases* (pre-releases included), reusing ``simple_index._highest_version``
    as the single source of truth so this module and ``compat.provider`` never
    drift on "highest version, rc's included" semantics.
    """
    if not prerelease:
        return stable_latest

    from specify_cli.distribution.simple_index import _highest_version

    highest = _highest_version([stable_latest, *releases], include_prerelease=True)
    return highest if highest is not None else stable_latest


def _release_versions_from_payload(payload: object) -> tuple[str, ...]:
    """Extract sanitised release versions from the GitHub Releases JSON list."""
    if not isinstance(payload, list):
        return ()

    versions: list[str] = []
    for release in payload:
        if not isinstance(release, dict):
            continue
        if release.get("draft") is True:
            continue
        tag = release.get("tag_name")
        if not isinstance(tag, str):
            continue
        version = tag[1:] if tag.startswith("v") else tag
        if try_parse_version(version) is not None:
            versions.append(version)
    return tuple(dict.fromkeys(versions))


def _highest_release(releases: tuple[str, ...], *, include_prerelease: bool) -> str | None:
    from specify_cli.distribution.simple_index import _highest_version

    return _highest_version(list(releases), include_prerelease=include_prerelease)


def _bundled_release_versions() -> tuple[str, ...]:
    """Read the private-release identity shipped inside the installed wheel."""
    try:
        text = importlib.resources.files("specify_cli").joinpath(RELEASE_IDENTITY_RESOURCE).read_text(encoding="utf-8")
        payload = json.loads(text)
    except (OSError, json.JSONDecodeError, ModuleNotFoundError):
        return ()

    if not isinstance(payload, dict):
        return ()
    if payload.get("repository") != "spec-kitty/EXPERIMENTAL-spec-kitty":
        return ()
    version = payload.get("version")
    if not isinstance(version, str) or try_parse_version(version) is None:
        return ()
    return (version,)


def _from_bundled_release_identity(
    cli_version: str,
    probed_at: datetime,
    *,
    prerelease: bool,
) -> UpgradeProbeResult | None:
    releases = _bundled_release_versions()
    if not releases:
        return None
    release_latest = _highest_release(releases, include_prerelease=True)
    if release_latest is None:
        return None
    stable_latest = _highest_release(releases, include_prerelease=False) or release_latest
    channel_latest = _channel_latest(stable_latest, releases, prerelease=prerelease)
    return UpgradeProbeResult(
        installed_version=cli_version,
        latest_pypi_version=channel_latest,
        channel=_classify(cli_version, channel_latest, releases),
        probed_at=probed_at,
        error=None,
        releases=releases,
    )


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
    """Classify the installed version against release metadata per the contract.

    Returns ``UNKNOWN`` only when the installed version cannot be parsed as a
    PEP 440 version. Network/parse failures are handled upstream in
    :func:`probe_pypi`.
    """
    installed_ver = try_parse_version(installed)
    if installed_ver is None:
        return UpgradeChannel.UNKNOWN

    # A version that is not in the current org's release list is not a release
    # build, even if its version number sorts ahead of the latest release.
    if installed not in releases:
        return UpgradeChannel.NO_UPGRADE_PATH

    # ``latest`` may be malformed — try_parse_version falls through to the
    # upgrade-available classification below (via is_version_newer returning False)
    # rather than raising.
    latest_ver = try_parse_version(latest)

    if latest_ver is not None and installed_ver == latest_ver:
        return UpgradeChannel.ALREADY_CURRENT
    if is_version_newer(installed, latest):
        return UpgradeChannel.AHEAD_OF_PYPI

    # Installed version is in releases but is older than latest. There IS an
    # upgrade path, so the no-upgrade notifier must stay silent and let the
    # existing upgrade nag render the actionable prompt.
    return UpgradeChannel.UPGRADE_AVAILABLE


__all__ = [
    "DEFAULT_TIMEOUT_S",
    "UpgradeChannel",
    "UpgradeProbeResult",
    "probe_pypi",
]
