"""WebSocket client for real-time sync with exponential backoff reconnection.

As of WP08 (browser-mediated OAuth), this client fetches its ephemeral
WebSocket token via ``specify_cli.auth.websocket.provision_ws_token`` (which
uses the process-wide ``TokenManager``). All tokens and server URLs flow
through the ``auth`` package; this module does not read legacy credential
state directly.
"""

import asyncio
import hashlib
import inspect
import json
import logging
import random
from contextlib import suppress
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import ParseResult, parse_qsl, urlparse

import websockets
from websockets import ConnectionClosed

from specify_cli.auth import get_token_manager
from specify_cli.auth.errors import (
    AuthenticationError,
    NotAuthenticatedError,
    TokenRefreshError,
)
from specify_cli.auth.websocket import provision_ws_token
from specify_cli.core.contract_gate import validate_outbound_payload
from specify_cli.sync._team import resolve_private_team_id_for_ingress
from specify_cli.sync.feature_flags import (
    is_saas_sync_enabled,
    saas_sync_disabled_message,
)
from specify_cli.sync.project_identity import ProjectIdentity

logger = logging.getLogger(__name__)

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
_SYNC_PROTOCOL_HEADER = "X-Spec-Kitty-Sync-Protocol"
_SYNC_PROTOCOL_VERSION = "2.0"


@dataclass(frozen=True, slots=True)
class _EventOutboxResult:
    event_id: str
    status: str


def _websocket_auth_headers_kwarg(ws_token: str) -> dict[str, dict[str, str]]:
    """Return the auth-header kwarg name supported by the installed websockets."""
    parameters = inspect.signature(websockets.connect).parameters
    header_kwarg = "extra_headers" if "extra_headers" in parameters and "additional_headers" not in parameters else "additional_headers"
    return {
        header_kwarg: {
            "Authorization": f"Bearer {ws_token}",
            _SYNC_PROTOCOL_HEADER: _SYNC_PROTOCOL_VERSION,
        }
    }


class ConnectionStatus:
    """Connection status constants"""

    CONNECTED = "Connected"
    RECONNECTING = "Reconnecting"
    OFFLINE = "Offline"
    BATCH_MODE = "OfflineBatchMode"


class WebSocketClient:
    """
    WebSocket client for spec-kitty sync protocol.

    Handles:
    - Connection management via ``provision_ws_token`` (pre-connect token provisioning)
    - Event sending/receiving
    - Heartbeat (pong responses)
    - Automatic reconnection with exponential backoff

    The client no longer stores or refreshes tokens itself — every connect
    attempt calls ``provision_ws_token()`` which delegates to the shared
    ``TokenManager`` (single-flight refresh, consistent 401 semantics).
    """

    # Reconnection configuration
    MAX_RECONNECT_ATTEMPTS = 10
    BASE_DELAY_SECONDS = 0.5  # 500ms
    MAX_DELAY_SECONDS = 30.0
    JITTER_RANGE = 1.0  # +/- 1 second
    ACK_TIMEOUT_SECONDS = 5.0

    def __init__(
        self,
        project_identity: ProjectIdentity | None = None,
        repo_root: Path | None = None,
    ):
        """
        Initialize WebSocket client.

        Args:
            project_identity: ProjectIdentity for build_id in heartbeats.
            repo_root: Path to the repository root, used for LocalCommit state
                persistence (``sync-state.json``) and on-connect flush.
                Defaults to ``Path.cwd()`` if not provided.

        Notes:
            Server URL and authentication are resolved on every ``connect()``
            call via ``provision_ws_token``. There is no direct token argument.
        """
        self._project_identity = project_identity
        self._repo_root: Path = repo_root if repo_root is not None else Path.cwd()
        self.ws: websockets.ClientConnection | None = None
        self.connected = False
        self.status = ConnectionStatus.OFFLINE
        self.message_handler: Callable | None = None
        self.reconnect_attempts = 0
        self._listen_task: asyncio.Task | None = None
        self._pending_responses: dict[tuple[str, ...], asyncio.Future[dict[str, Any]]] = {}

    async def connect(self):
        """Establish WebSocket connection with authentication.

        Flow:
        1. Gate on the SaaS-sync feature flag.
        2. Fetch a fresh ws_token + ws_url via ``provision_ws_token`` (which
           single-flight-refreshes the access token if needed).
        3. Open the WS upgrade at ``ws_url`` with an Authorization Bearer header.
        4. Receive the initial snapshot and start the listener task.
        """
        if not is_saas_sync_enabled():
            self.connected = False
            self.status = ConnectionStatus.OFFLINE
            raise AuthenticationError(saas_sync_disabled_message())

        # Resolve the Private Teamspace id via the strict shared helper.
        # On None the helper has already emitted a structured warning, and the
        # local command MUST still succeed (FR-010), so we silently go OFFLINE
        # rather than raise.
        team_id = resolve_private_team_id_for_ingress(
            get_token_manager(),
            endpoint="/api/v1/ws-token",
        )
        if team_id is None:
            self.connected = False
            self.status = ConnectionStatus.OFFLINE
            return

        try:
            ws_bundle = await provision_ws_token(team_id)
        except NotAuthenticatedError:
            self.connected = False
            self.status = ConnectionStatus.OFFLINE
            logger.warning("Not authenticated; run `spec-kitty auth login`")
            raise
        except TokenRefreshError as exc:
            self.connected = False
            self.status = ConnectionStatus.OFFLINE
            logger.exception("Token refresh failed: %s", exc)
            raise
        except Exception as exc:
            self.connected = False
            self.status = ConnectionStatus.OFFLINE
            logger.warning("Sync WebSocket connection failed: %s", exc)
            raise

        ws_url = ws_bundle.get("ws_url")
        ws_token = ws_bundle.get("ws_token")
        if not ws_url or not ws_token:
            self.connected = False
            self.status = ConnectionStatus.OFFLINE
            raise AuthenticationError("WebSocket provisioning returned an incomplete bundle.")

        ws_url = self._normalize_ws_url(ws_url)

        try:
            self.ws = await websockets.connect(
                ws_url,
                **_websocket_auth_headers_kwarg(ws_token),
                ping_interval=None,  # We handle heartbeat manually
                ping_timeout=None,
            )
            self.connected = True
            self.status = ConnectionStatus.CONNECTED

            # Receive initial snapshot
            await self._receive_snapshot()

            # The listener must own acknowledgement correlation before any
            # reconnect flush can disclose a frame.
            self._listen_task = asyncio.create_task(self._listen())

            # Reconnect flushes use the same durable Event/LocalCommit attempts as
            # live relay.  Failures keep their original item parked; connection
            # establishment itself remains usable for later recovery.
            try:
                await self._flush_pending_project_events()
                from specify_cli.sync.local_commit import (  # noqa: PLC0415
                    flush_pending_local_commits_async,
                )

                await flush_pending_local_commits_async(self._repo_root, self)
            except Exception:  # noqa: BLE001
                logger.warning("Project sync reconnect flush failed; items remain parked", exc_info=True)

            logger.info("Connected to sync server")
            return

        except websockets.InvalidStatus as e:
            if e.response.status_code == 401:
                logger.warning("WebSocket rejected token; user should re-authenticate")
            else:
                logger.warning(
                    "Sync WebSocket connection failed: HTTP %s",
                    e.response.status_code,
                )
            self.connected = False
            self.status = ConnectionStatus.OFFLINE
            raise
        except Exception as e:
            self.connected = False
            self.status = ConnectionStatus.OFFLINE
            logger.warning("Sync WebSocket connection failed: %s", e)
            raise

    async def disconnect(self):
        """Close WebSocket connection"""
        if self.connected and self.ws is not None and self._listen_task is not None:
            try:
                await self._flush_pending_project_events()
                from specify_cli.sync.local_commit import (  # noqa: PLC0415
                    flush_pending_local_commits_async,
                )

                await flush_pending_local_commits_async(self._repo_root, self)
            except Exception:  # noqa: BLE001
                logger.warning("Project sync final flush failed; items remain parked", exc_info=True)
        if self._listen_task:
            self._listen_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._listen_task
            self._listen_task = None

        if self.ws:
            await self.ws.close()
            self.ws = None
            self.connected = False
            self.status = ConnectionStatus.OFFLINE
            logger.info("Disconnected from sync server")

    async def reconnect(self) -> bool:
        """
        Reconnect with exponential backoff.

        Formula: delay = min(500ms * 2^attempt, 30s) + jitter

        Returns:
            True if reconnected successfully, False if max attempts reached
        """
        self.status = ConnectionStatus.RECONNECTING

        while self.reconnect_attempts < self.MAX_RECONNECT_ATTEMPTS:
            # Calculate exponential backoff delay
            delay = min(self.BASE_DELAY_SECONDS * (2**self.reconnect_attempts), self.MAX_DELAY_SECONDS)
            # Add jitter to prevent thundering herd
            jitter = random.uniform(-self.JITTER_RANGE, self.JITTER_RANGE)  # noqa: S311
            delay = max(0, delay + jitter)

            attempt_num = self.reconnect_attempts + 1
            logger.info(
                "Reconnecting to sync server (%s/%s)",
                attempt_num,
                self.MAX_RECONNECT_ATTEMPTS,
            )

            await asyncio.sleep(delay)

            try:
                await self.connect()
                # Success - reset attempt counter
                self.reconnect_attempts = 0
                return True
            except (NotAuthenticatedError, TokenRefreshError):
                self.status = ConnectionStatus.BATCH_MODE
                logger.warning("Authentication failed; please run 'spec-kitty auth login'")
                return False
            except AuthenticationError:
                self.status = ConnectionStatus.BATCH_MODE
                logger.warning("Authentication failed; please run 'spec-kitty auth login'")
                return False
            except Exception:
                self.reconnect_attempts += 1

        # Max attempts reached - switch to batch mode
        self.status = ConnectionStatus.BATCH_MODE
        logger.warning("Max reconnection attempts reached; switched to batch sync mode. Events will be queued locally and synced when connection is restored.")
        return False

    def reset_reconnect_attempts(self):
        """Reset the reconnection attempt counter"""
        self.reconnect_attempts = 0

    @staticmethod
    def _normalize_ws_url(ws_url: str) -> str:
        """Convert provisioned HTTP(S) URLs to WS(S), rejecting insecure remote hosts."""
        parsed = urlparse(ws_url)
        if any("token" in key.casefold() for key, _value in parse_qsl(parsed.query, keep_blank_values=True)):
            raise AuthenticationError("Refusing a WebSocket provisioning URL containing a query token; Authorization header auth is required.")
        scheme = parsed.scheme.lower()

        if scheme == "wss":
            return ws_url
        if scheme == "ws":
            if not WebSocketClient._is_loopback_host(parsed):
                raise AuthenticationError("Refusing insecure WebSocket provisioning URL outside loopback.")
            return ws_url
        if scheme == "https":
            return WebSocketClient._replace_scheme(parsed, "wss")
        if scheme == "http":
            if not WebSocketClient._is_loopback_host(parsed):
                raise AuthenticationError("Refusing insecure WebSocket provisioning URL outside loopback.")
            return WebSocketClient._replace_scheme(parsed, "ws")
        raise AuthenticationError(f"Unsupported WebSocket provisioning URL scheme: {ws_url!r}")

    @staticmethod
    def _is_loopback_host(parsed: ParseResult) -> bool:
        return (parsed.hostname or "").lower() in _LOOPBACK_HOSTS

    @staticmethod
    def _replace_scheme(parsed: ParseResult, scheme: str) -> str:
        return parsed._replace(scheme=scheme).geturl()

    def get_reconnect_delay(self, attempt: int) -> float:
        """
        Calculate reconnect delay for a given attempt number.

        Args:
            attempt: The attempt number (0-indexed)

        Returns:
            Delay in seconds (without jitter)
        """
        return min(self.BASE_DELAY_SECONDS * (2**attempt), self.MAX_DELAY_SECONDS)

    async def send_event(self, event: dict[str, Any]) -> bool:
        """Send one Event through its exact project attempt and Ack fence."""
        if not self.connected or not self.ws:
            raise ConnectionError("Not connected to server")
        if event.get("type") == "LocalCommit":
            raise TypeError("LocalCommit frames require send_local_commit()")
        event_id = str(event.get("event_id") or "").strip()
        project_uuid = str(event.get("project_uuid") or "").strip()
        if not event_id or not project_uuid:
            raise ValueError("Event transport requires event_id and project_uuid")

        from specify_cli.delivery.dispatcher import prepare_event_transport  # noqa: PLC0415
        from specify_cli.sync.project_store import ProjectSyncStore  # noqa: PLC0415

        store = ProjectSyncStore(project_uuid)
        context = store.create_context()
        prepared = prepare_event_transport(
            event,
            event_id=event_id,
            project_uuid=project_uuid,
            context=context,
        )
        terminal = self._terminal_result_projection(prepared.disclosure)
        if terminal.status.value == "terminal":
            outcome = terminal.outcome.value if terminal.outcome is not None else ""
            self._record_event_outbox_result(
                project_uuid=project_uuid,
                event_id=event_id,
                outcome=outcome,
            )
            if outcome in {"delivered", "duplicate"}:
                return True
            if outcome == "refused":
                raise ConnectionError(terminal.terminal_refusal_category or "project write refused")
            raise ConnectionError("terminal_unknown: Event delivery cannot be replayed automatically")
        response = await self._execute_correlated_write(
            wire=dict(prepared.wire_payload),
            disclosure=prepared.disclosure,
            response_key=("event", event_id),
            classify=lambda value: self._classify_event_response(
                value,
                event_id=event_id,
            ),
        )
        outcome, category = self._classify_event_response(response, event_id=event_id)
        self._record_event_outbox_result(
            project_uuid=project_uuid,
            event_id=event_id,
            outcome=outcome,
        )
        if category is not None:
            raise ConnectionError(category)
        return True

    async def send_local_commit(self, frame: Mapping[str, Any]) -> bool:
        """Send one LocalCommit and consume only its full exact authority Ack."""
        if not self.connected or not self.ws:
            raise ConnectionError("Not connected to server")
        wire, disclosure = self._prepare_local_commit(frame)
        terminal = self._terminal_result_projection(disclosure)
        if terminal.status.value == "terminal":
            outcome = terminal.outcome.value if terminal.outcome is not None else ""
            self._reconcile_local_commit_queue(wire, outcome=outcome)
            if outcome in {"delivered", "duplicate"}:
                return True
            if outcome == "refused":
                return False
            raise ConnectionError("terminal_unknown: LocalCommit delivery cannot be replayed automatically")
        response_key = (
            "local_commit",
            str(wire["project_uuid"]),
            str(wire["build_id"]),
            str(wire["git_hash"]),
        )
        response = await self._execute_correlated_write(
            wire=wire,
            disclosure=disclosure,
            response_key=response_key,
            classify=lambda value: self._classify_local_commit_response(
                value,
                expected=wire,
            ),
        )
        outcome, category = self._classify_local_commit_response(
            response,
            expected=wire,
        )
        if category is not None:
            self._reconcile_local_commit_queue(wire, outcome=outcome)
            return False
        from specify_cli.sync.local_commit import record_local_commit_ack  # noqa: PLC0415

        if not record_local_commit_ack(
            self._repo_root,
            response,
            expected_frame=wire,
        ):
            raise RuntimeError("LocalCommit Ack did not match a pending exact frame")
        return True

    @staticmethod
    def _terminal_result_projection(disclosure: Any) -> Any:
        """Read only the typed, exact WP06 terminal projection under a live lease."""
        from specify_cli.sync.project_store import ProjectSyncStore  # noqa: PLC0415
        from specify_cli.sync.transport_attempts import (  # noqa: PLC0415
            DeliveryAttemptSpec,
            get_delivery_terminal_result_projection,
        )
        from specify_cli.sync.transport_lease import acquire_project_transport_lease  # noqa: PLC0415

        spec = DeliveryAttemptSpec(
            attempt_id=disclosure.attempt_id,
            write_kind=disclosure.write_kind,
            native_identity=disclosure.native_identity,
            payload_hash=disclosure.payload_hash,
            payload_reference=disclosure.payload_reference,
            deadline_at=disclosure.deadline_at,
            reconciliation_policy=disclosure.reconciliation_policy,
        )
        store = ProjectSyncStore(disclosure.project_uuid)
        with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
            return get_delivery_terminal_result_projection(unit, context, spec)

    def _reconcile_local_commit_queue(self, wire: Mapping[str, Any], *, outcome: str) -> None:
        from specify_cli.sync.local_commit import reconcile_local_commit_result  # noqa: PLC0415

        reconcile_local_commit_result(
            self._repo_root,
            expected_frame=wire,
            outcome=outcome,
        )

    def _prepare_local_commit(
        self,
        frame: Mapping[str, Any],
    ) -> tuple[dict[str, Any], Any]:
        """Mint one proof-bearing LocalCommit wire item from current authority."""
        from specify_cli.delivery.consent_gate import (  # noqa: PLC0415
            ProjectTransportDisclosure,
            default_transport_deadline,
            stable_transport_id,
        )
        from specify_cli.delivery.targets import compute_target_id  # noqa: PLC0415
        from specify_cli.sync.admission_contract import (  # noqa: PLC0415
            ProjectWriteAdmissionProof,
            attach_admission_proof,
        )
        from specify_cli.sync.local_commit import validate_rfc3339_datetime  # noqa: PLC0415
        from specify_cli.sync.project_store import ProjectSyncStore  # noqa: PLC0415

        required = ("project_uuid", "git_hash", "mission_id", "build_id", "committed_at")
        values = {field: str(frame.get(field) or "").strip() for field in required}
        if not all(values.values()):
            raise ValueError("LocalCommit requires project_uuid, git_hash, mission_id, build_id, and committed_at")
        if frame.get("type") != "LocalCommit":
            raise ValueError("LocalCommit requires the exact LocalCommit frame type")
        changed_files = frame.get("changed_files")
        if not isinstance(changed_files, list) or any(not isinstance(path, str) for path in changed_files):
            raise ValueError("LocalCommit changed_files must be an array of strings")
        validate_rfc3339_datetime(
            frame.get("committed_at"),
            field_name="LocalCommit committed_at",
        )
        if {"admission_generation", "binding_audience"} & frame.keys():
            raise ValueError("LocalCommit cannot supply ambient admission authority")

        store = ProjectSyncStore(values["project_uuid"])
        context = store.create_context()
        target = context.target_audience
        if (
            target is None
            or context.epoch_id is None
            or context.consent_generation is None
            or context.admission_generation is None
            or context.binding_audience is None
        ):
            raise ValueError("LocalCommit transport requires an admitted project context")
        canonical_project = context.project_uuid.storage_token
        if values["project_uuid"] != canonical_project:
            raise ValueError("LocalCommit project UUID does not match its project context")
        target_id = compute_target_id(
            target_identity=target.target_identity,
            account_identity=target.account_identity,
            private_teamspace_id=target.private_teamspace_id,
            project_uuid=context.project_uuid,
            configuration_generation=target.configuration_generation,
        )
        native_identity = f"local-commit:{target_id}:{values['build_id']}:{values['git_hash']}"
        base = {key: value for key, value in frame.items() if key not in {"project_uuid", "admission_generation", "binding_audience"}}
        base["type"] = "LocalCommit"
        base["spec_kitty_delivery_identity"] = native_identity
        wire = attach_admission_proof(
            base,
            ProjectWriteAdmissionProof(
                project_uuid=canonical_project,
                admission_generation=int(context.admission_generation),
                binding_audience=context.binding_audience,
            ),
        )
        proof_fields = ("project_uuid", "admission_generation", "binding_audience")
        if any(field not in wire for field in proof_fields):
            raise ValueError("LocalCommit admission proof is incomplete")
        encoded = json.dumps(
            wire,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        payload_reference = json.dumps(
            {
                "schema": "spec-kitty.local-commit.v1",
                "project_uuid": canonical_project,
                "build_id": values["build_id"],
                "git_hash": values["git_hash"],
                "target_id": target_id,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        disclosure = ProjectTransportDisclosure(
            project_uuid=canonical_project,
            epoch_id=context.epoch_id,
            consent_generation=context.consent_generation,
            target_identity=target.target_identity,
            account_identity=target.account_identity,
            private_teamspace_id=target.private_teamspace_id,
            target_project_uuid=target.project_uuid.storage_token,
            target_generation=target.configuration_generation,
            admission_generation=str(context.admission_generation),
            binding_audience=context.binding_audience,
            write_kind="local_commit",
            native_identity=native_identity,
            payload_hash="sha256:" + hashlib.sha256(encoded).hexdigest(),  # noqa: TID251 - exact transport bytes, not charter content
            payload_reference=payload_reference,
            attempt_id="local-commit:"
            + stable_transport_id(
                "attempt",
                canonical_project,
                target_id,
                values["build_id"],
                values["git_hash"],
            ),
            deadline_at=default_transport_deadline(),
            reconciliation_policy="native_identity_retry",
        )
        return dict(wire), disclosure

    @staticmethod
    def _classify_event_response(
        value: object,
        *,
        event_id: str,
    ) -> tuple[str, str | None]:
        from specify_cli.sync.admission_contract import parse_project_not_admitted  # noqa: PLC0415
        from specify_cli.sync.transport_attempts import DeliveryOutcome  # noqa: PLC0415

        if not isinstance(value, Mapping) or str(value.get("event_id") or "") != event_id:
            raise ValueError("Event acknowledgement does not match its event_id")
        status = value.get("status")
        if status == "accepted" and value.get("type") == "ack":
            return DeliveryOutcome.DELIVERED.value, None
        if status == "duplicate" and value.get("type") == "ack":
            return DeliveryOutcome.DUPLICATE.value, None
        if status == "rejected" and value.get("type") == "error":
            refusal = parse_project_not_admitted("event", value, ("event_id",))
            return DeliveryOutcome.REFUSED.value, refusal.error_category
        raise ValueError("Event acknowledgement has an unsupported status")

    @staticmethod
    def _classify_local_commit_response(
        value: object,
        *,
        expected: Mapping[str, Any],
    ) -> tuple[str, str | None]:
        from specify_cli.sync.admission_contract import parse_project_not_admitted  # noqa: PLC0415
        from specify_cli.sync.local_commit import validate_rfc3339_datetime  # noqa: PLC0415
        from specify_cli.sync.transport_attempts import DeliveryOutcome  # noqa: PLC0415

        if not isinstance(value, Mapping) or value.get("type") != "LocalCommitAck":
            raise ValueError("LocalCommit acknowledgement has the wrong frame type")
        correlation = (
            "git_hash",
            "build_id",
            "project_uuid",
            "admission_generation",
            "binding_audience",
        )
        if any(field not in value or field not in expected or str(value[field]) != str(expected[field]) for field in correlation):
            raise ValueError("LocalCommit acknowledgement authority does not match")
        status = value.get("status")
        if status in {"accepted", "duplicate"}:
            allowed = {
                "type",
                "git_hash",
                "build_id",
                "project_uuid",
                "admission_generation",
                "binding_audience",
                "status",
                "received_at",
            }
            if set(value) != allowed:
                raise ValueError("LocalCommit success acknowledgement has the wrong closed shape")
            validate_rfc3339_datetime(
                value.get("received_at"),
                field_name="LocalCommit success acknowledgement received_at",
            )
        if status == "accepted":
            return DeliveryOutcome.DELIVERED.value, None
        if status == "duplicate":
            return DeliveryOutcome.DUPLICATE.value, None
        if status == "rejected":
            allowed = {
                "type",
                "git_hash",
                "build_id",
                "project_uuid",
                "admission_generation",
                "binding_audience",
                "status",
                "error_category",
                "retryable",
            }
            if set(value) != allowed:
                raise ValueError("LocalCommit refusal acknowledgement has the wrong closed shape")
            category = str(value.get("error_category") or "")
            if category == "project_not_admitted":
                parse_project_not_admitted(
                    "local_commit",
                    value,
                    ("git_hash", "build_id", "project_uuid"),
                )
            elif category != "local_commit_payload_conflict" or value.get("retryable") is not False:
                raise ValueError("LocalCommit acknowledgement has an unsupported refusal")
            return DeliveryOutcome.REFUSED.value, category
        raise ValueError("LocalCommit acknowledgement has an unsupported status")

    async def _execute_correlated_write(
        self,
        *,
        wire: dict[str, Any],
        disclosure: Any,
        response_key: tuple[str, ...],
        classify: Callable[[object], tuple[str, str | None]],
    ) -> dict[str, Any]:
        from specify_cli.delivery.consent_gate import (  # noqa: PLC0415
            ProjectTransportRefusal,
            execute_project_transport_disclosure,
        )

        loop = asyncio.get_running_loop()

        def execute() -> object:
            def send() -> dict[str, Any]:
                future = asyncio.run_coroutine_threadsafe(
                    self._send_and_wait_for_response(
                        wire,
                        response_key=response_key,
                    ),
                    loop,
                )
                return future.result(timeout=self.ACK_TIMEOUT_SECONDS + 1.0)

            return execute_project_transport_disclosure(
                disclosure,
                send=send,
                classify=classify,
            )

        result = await asyncio.to_thread(execute)
        if isinstance(result, ProjectTransportRefusal):
            raise ConnectionError(f"{result.category}: {result.diagnostic}")
        if not isinstance(result, dict):
            raise RuntimeError("project write returned a non-object acknowledgement")
        return result

    async def _send_and_wait_for_response(
        self,
        wire: dict[str, Any],
        *,
        response_key: tuple[str, ...],
    ) -> dict[str, Any]:
        if response_key in self._pending_responses:
            raise RuntimeError("a correlated project write is already pending")
        loop = asyncio.get_running_loop()
        response: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending_responses[response_key] = response
        try:
            await self._send_wire(wire)
            try:
                return await asyncio.wait_for(
                    asyncio.shield(response),
                    timeout=self.ACK_TIMEOUT_SECONDS,
                )
            except TimeoutError as exc:
                raise TimeoutError("project write acknowledgement timed out") from exc
        finally:
            self._pending_responses.pop(response_key, None)

    async def _send_wire(self, wire: dict[str, Any]) -> None:
        if not self.connected or self.ws is None:
            raise ConnectionError("Not connected to server")
        if wire.get("type") != "LocalCommit":
            validate_outbound_payload(wire, "envelope")
            from specify_cli.delivery.receivers import (  # noqa: PLC0415
                OutboundEvent,
                disclosed_event_payload_bytes,
            )

            encoded = disclosed_event_payload_bytes(OutboundEvent(event_id=str(wire["event_id"]), payload=wire)).decode("utf-8")
        else:
            encoded = json.dumps(
                wire,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )

        try:
            await self.ws.send(encoded)
        except ConnectionClosed:
            self.connected = False
            self.status = ConnectionStatus.OFFLINE
            raise ConnectionError("Connection closed") from None

    async def _listen(self):
        """Listen for messages from server"""
        try:
            async for message in self.ws:
                data = json.loads(message)
                await self._handle_message(data)
        except asyncio.CancelledError:
            # Expected during explicit disconnect/shutdown.
            raise
        except ConnectionClosed:
            self.connected = False
            self.status = ConnectionStatus.OFFLINE
            logger.info("Sync WebSocket connection closed by server")
        finally:
            self._listen_task = None

    async def _handle_message(self, data: dict):
        """Handle incoming message"""
        if self._resolve_correlated_response(data):
            return
        msg_type = data.get("type")

        if msg_type == "snapshot":
            self._handle_snapshot(data)
        elif msg_type == "event":
            await self._handle_event(data)
        elif msg_type == "ping":
            await self._handle_ping(data)
        elif msg_type == "LocalCommitAck":
            self._handle_local_commit_ack(data)
        else:
            # Unknown message type
            pass

    def _resolve_correlated_response(self, data: Mapping[str, Any]) -> bool:
        """Resolve only a response carrying the original item's exact key."""
        key: tuple[str, ...] | None = None
        msg_type = data.get("type")
        event_id = str(data.get("event_id") or "").strip()
        if event_id and msg_type in {"ack", "error"}:
            key = ("event", event_id)
        elif msg_type == "LocalCommitAck":
            project_uuid = str(data.get("project_uuid") or "").strip()
            build_id = str(data.get("build_id") or "").strip()
            git_hash = str(data.get("git_hash") or "").strip()
            if project_uuid and build_id and git_hash:
                key = ("local_commit", project_uuid, build_id, git_hash)
        if key is None:
            return False
        pending = self._pending_responses.get(key)
        if pending is None or pending.done():
            return False
        pending.set_result(dict(data))
        return True

    def _record_event_outbox_result(
        self,
        *,
        project_uuid: str,
        event_id: str,
        outcome: str,
    ) -> None:
        """Project the durable WP06 terminal result onto the project outbox."""
        from specify_cli.sync.project_store import ProjectSyncStore  # noqa: PLC0415
        from specify_cli.sync.queue import OfflineQueue  # noqa: PLC0415
        from specify_cli.sync.transport_attempts import DeliveryOutcome  # noqa: PLC0415

        statuses = {
            DeliveryOutcome.DELIVERED.value: "success",
            DeliveryOutcome.DUPLICATE.value: "duplicate",
            DeliveryOutcome.REFUSED.value: "terminal_failed",
        }
        status = statuses.get(outcome)
        if status is None:
            return
        store = ProjectSyncStore(project_uuid)
        with store.unit_of_work() as unit:
            OfflineQueue(unit, store.layout_generation()).process_batch_results([_EventOutboxResult(event_id=event_id, status=status)])

    async def _flush_pending_project_events(self) -> None:
        """Relay the admitted project's outbox through the gated Event sender."""
        if self._project_identity is None or self._project_identity.project_uuid is None:
            return
        from specify_cli.sync.project_store import ProjectSyncStore  # noqa: PLC0415
        from specify_cli.sync.queue import OfflineQueue  # noqa: PLC0415

        project_uuid = str(self._project_identity.project_uuid)
        store = ProjectSyncStore(project_uuid)
        with store.unit_of_work() as unit:
            tasks = OfflineQueue(unit, store.layout_generation()).drain_queue()
        for task in tasks:
            try:
                await self.send_event(task.event)
            except (ConnectionError, TimeoutError):
                # The original WP06 attempt is now either parked before I/O or
                # UNKNOWN after I/O.  Never invent a second send in this flush.
                break

    async def _receive_snapshot(self):
        """Receive and process initial snapshot"""
        message = await self.ws.recv()
        data = json.loads(message)

        if data.get("type") == "snapshot":
            logger.info(
                "Received sync snapshot: %d work packages",
                len(data.get("work_packages", [])),
            )
        else:
            logger.warning("Expected snapshot, got %s", data.get("type"))

    def _handle_snapshot(self, data: dict):
        """Process snapshot"""
        # Store snapshot data locally if needed
        pass

    async def _handle_event(self, data: dict):
        """Process event broadcast"""
        if self.message_handler:
            await self.message_handler(data)

    async def _handle_ping(self, data: dict):
        """Respond to server ping with build_id for identity correlation."""
        pong: dict[str, Any] = {"type": "pong", "timestamp": data.get("timestamp")}
        if self._project_identity is not None and self._project_identity.build_id:
            pong["build_id"] = self._project_identity.build_id
        await self.ws.send(json.dumps(pong))

    def _handle_local_commit_ack(self, data: dict):
        """Ignore unmatched LocalCommit Acks; the exact waiter owns mutation."""
        logger.debug(
            "Unmatched LocalCommitAck received for project=%s build=%s hash=%s",
            data.get("project_uuid"),
            data.get("build_id"),
            data.get("git_hash"),
        )

    def set_message_handler(self, handler: Callable):
        """Set handler for incoming events"""
        self.message_handler = handler

    def get_status(self) -> str:
        """Get current connection status"""
        return self.status

    def is_in_batch_mode(self) -> bool:
        """Check if client is in batch sync mode after max reconnection attempts"""
        return self.status == ConnectionStatus.BATCH_MODE
