"""Versioned recognized-daemon handshake for project-store cutover.

Migration never guesses that an arbitrary process is a Spec Kitty daemon.  It
first verifies the loopback health payload and exact package identity, then uses
the authenticated shutdown endpoint as the quiesce boundary.  Old or foreign
processes are reported as unrecognized residue and are never killed by this
module.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


MIGRATION_DAEMON_PROTOCOL_VERSION = 1


class DaemonCutoverError(RuntimeError):
    """A recognized-daemon cutover handshake failed closed."""


class DaemonProtocolMismatchError(DaemonCutoverError):
    """The loopback process is not the expected current daemon binary."""


class DaemonUnreachableError(DaemonCutoverError):
    """The previously recognized loopback process is genuinely unreachable."""


@dataclass(frozen=True, slots=True)
class QuiesceAcknowledgement:
    """Durable evidence that one recognized daemon accepted quiescence."""

    migration_id: str
    migration_protocol: int
    daemon_protocol: int
    package_version: str


@dataclass(frozen=True, slots=True)
class RestartAcknowledgement:
    """Evidence that the current daemon binary is healthy after cutover."""

    migration_id: str
    daemon_protocol: int
    package_version: str


FetchJson = Callable[[urllib.request.Request, float], dict[str, object]]
RestartDaemon = Callable[[], object]


def _loopback_base_url(value: str) -> str:
    normalized = value.rstrip("/")
    parsed = urllib.parse.urlsplit(normalized)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("daemon cutover protocol requires a valid loopback port") from exc
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost"}
        or port is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("daemon cutover protocol requires an exact loopback URL")
    return normalized


def _fetch_json(request: urllib.request.Request, timeout: float) -> dict[str, object]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 -- loopback URL is supplied by daemon discovery
            payload = response.read()
    except (OSError, urllib.error.URLError) as exc:
        raise DaemonUnreachableError("daemon loopback endpoint is unreachable") from exc
    try:
        raw: Any = json.loads(payload.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise DaemonCutoverError("reachable daemon returned an invalid handshake payload") from exc
    if not isinstance(raw, dict):
        raise DaemonCutoverError("daemon handshake response must be an object")
    return {str(key): value for key, value in raw.items()}


class DaemonCutoverProtocol:
    """Authenticated, versioned quiesce/restart controller for one daemon."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        package_version: str,
        expected_daemon_protocol: int,
        fetch_json: FetchJson = _fetch_json,
        restart_daemon: RestartDaemon | None = None,
        timeout_seconds: float = 2.0,
    ) -> None:
        normalized = _loopback_base_url(base_url)
        if not token:
            raise ValueError("daemon cutover token is required")
        if not package_version:
            raise ValueError("daemon package version is required")
        if expected_daemon_protocol <= 0:
            raise ValueError("expected daemon protocol must be positive")
        if timeout_seconds <= 0:
            raise ValueError("daemon handshake timeout must be positive")
        self._base_url = normalized
        self._token = token
        self._package_version = package_version
        self._expected_daemon_protocol = expected_daemon_protocol
        self._fetch_json = fetch_json
        self._restart_daemon = restart_daemon
        self._timeout_seconds = timeout_seconds

    def _health(self) -> tuple[int, str]:
        request = urllib.request.Request(f"{self._base_url}/api/health")
        payload = self._fetch_json(request, self._timeout_seconds)
        protocol = payload.get("protocol_version")
        package = payload.get("package_version")
        if (
            payload.get("status") != "ok"
            or not isinstance(protocol, int)
            or isinstance(protocol, bool)
            or protocol != self._expected_daemon_protocol
            or package != self._package_version
        ):
            raise DaemonProtocolMismatchError("running daemon does not match the recognized protocol/package")
        return protocol, str(package)

    def quiesce(self, migration_id: str) -> QuiesceAcknowledgement:
        """Verify current identity, request shutdown, and return exact evidence."""
        migration = migration_id.strip()
        if not migration:
            raise ValueError("migration identity is required")
        daemon_protocol, package = self._health()
        body = json.dumps(
            {
                "token": self._token,
                "migration_id": migration,
                "migration_protocol": MIGRATION_DAEMON_PROTOCOL_VERSION,
                "phase": "quiesce",
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url}/api/shutdown",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        response = self._fetch_json(request, self._timeout_seconds)
        if response.get("status") not in {"quiesced", "stopping"}:
            raise DaemonCutoverError("recognized daemon did not acknowledge quiescence")
        remote_migration_protocol = response.get("migration_protocol", MIGRATION_DAEMON_PROTOCOL_VERSION)
        if remote_migration_protocol != MIGRATION_DAEMON_PROTOCOL_VERSION:
            raise DaemonProtocolMismatchError("daemon migration protocol changed during quiesce")
        deadline = time.monotonic() + self._timeout_seconds
        while time.monotonic() < deadline:
            try:
                self._health()
            except DaemonUnreachableError:
                break
            except DaemonCutoverError:
                raise
            time.sleep(0.01)
        else:
            raise DaemonCutoverError("recognized daemon acknowledged shutdown but did not quiesce")
        return QuiesceAcknowledgement(
            migration_id=migration,
            migration_protocol=MIGRATION_DAEMON_PROTOCOL_VERSION,
            daemon_protocol=daemon_protocol,
            package_version=package,
        )

    def restart(self, migration_id: str) -> RestartAcknowledgement:
        """Start the current binary through the injected daemon lifecycle seam."""
        migration = migration_id.strip()
        if not migration:
            raise ValueError("migration identity is required")
        if self._restart_daemon is None:
            return RestartAcknowledgement(
                migration_id=migration,
                daemon_protocol=0,
                package_version=self._package_version,
            )
        self._restart_daemon()
        deadline = time.monotonic() + self._timeout_seconds
        last_error: DaemonCutoverError | None = None
        while time.monotonic() < deadline:
            try:
                protocol, package = self._health()
                return RestartAcknowledgement(migration, protocol, package)
            except DaemonCutoverError as exc:
                last_error = exc
                time.sleep(0.01)
        raise DaemonCutoverError("restarted daemon did not become healthy") from last_error


def discover_daemon_cutover_protocol() -> DaemonCutoverProtocol | None:
    """Return a controller only for the healthy exact current daemon binary."""
    from specify_cli.sync.daemon import (
        DAEMON_PROTOCOL_VERSION,
        DaemonIntent,
        _get_package_version,
        ensure_sync_daemon_running,
        get_sync_daemon_status,
    )

    status = get_sync_daemon_status()
    if not status.healthy:
        if any(value is not None for value in (status.url, status.port, status.token, status.pid)):
            raise DaemonProtocolMismatchError("daemon state exists but is not a recognized healthy current binary")
        return None
    expected_package = _get_package_version()
    if status.url is None or status.token is None or status.package_version != expected_package or status.protocol_version != DAEMON_PROTOCOL_VERSION:
        raise DaemonProtocolMismatchError("healthy daemon metadata does not match the current package/protocol")

    def restart() -> object:
        return ensure_sync_daemon_running(
            intent=DaemonIntent.REMOTE_REQUIRED,
            force_explicit=True,
        )

    return DaemonCutoverProtocol(
        base_url=status.url,
        token=status.token,
        package_version=expected_package,
        expected_daemon_protocol=DAEMON_PROTOCOL_VERSION,
        restart_daemon=restart,
    )


__all__ = [
    "DaemonCutoverError",
    "DaemonCutoverProtocol",
    "DaemonProtocolMismatchError",
    "DaemonUnreachableError",
    "discover_daemon_cutover_protocol",
    "MIGRATION_DAEMON_PROTOCOL_VERSION",
    "QuiesceAcknowledgement",
    "RestartAcknowledgement",
]
