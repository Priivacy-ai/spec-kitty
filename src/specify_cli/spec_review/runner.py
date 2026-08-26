"""Safe local OpenCode pricing probe used before a spec-review launch."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
import os
import signal
import subprocess
import time
from typing import Final, Protocol, TypeVar
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen


MODEL_NOT_FREE: Final = "SPEC_REVIEW_MODEL_NOT_FREE"
AUTH_REQUIRED: Final = "SPEC_REVIEW_AUTH_REQUIRED"
LOOPBACK_PROVIDER_ERROR: Final = "SPEC_REVIEW_PROVIDER_ERROR"
LOOPBACK_TIMEOUT: Final = "SPEC_REVIEW_TIMEOUT"
LOOPBACK_INVALID_OUTPUT: Final = "SPEC_REVIEW_INVALID_OUTPUT"
LOOPBACK_CLEANUP_FAILED: Final = "SPEC_REVIEW_SESSION_CLEANUP_FAILED"
LOOPBACK_RESPONSE_LIMIT: Final = 2 * 1024 * 1024
DISABLED_TOOLS: Final = {
    "bash": False,
    "edit": False,
    "read": False,
    "grep": False,
    "glob": False,
    "lsp": False,
    "apply_patch": False,
    "skill": False,
    "todowrite": False,
    "webfetch": False,
    "websearch": False,
    "question": False,
}


@dataclass(frozen=True)
class PricingVerdict:
    """Metadata-only result for one exact OpenCode model route."""

    route: str
    is_free: bool
    code: str


@dataclass(frozen=True)
class PricingPermit:
    """Unforgeable-in-practice local proof from the exact pricing gate."""

    route: str
    _issuer: object


class ModelNotFreeError(RuntimeError):
    """Fail-closed refusal before a prompt or model subprocess is created."""

    def __init__(self, route: str) -> None:
        super().__init__(f"{MODEL_NOT_FREE}: {route}")
        self.route = route
        self.code = MODEL_NOT_FREE


class LoopbackTransportError(RuntimeError):
    """Metadata-only failure; deliberately never contains server output."""

    def __init__(self, code: str = LOOPBACK_PROVIDER_ERROR) -> None:
        super().__init__(code)
        self.code = code


class AuthRequiredError(LoopbackTransportError):
    """A server auth failure without disclosure of its raw response."""

    def __init__(self) -> None:
        super().__init__(AUTH_REQUIRED)


class LoopbackTimeoutError(LoopbackTransportError):
    """A bounded local HTTP timeout without retrying the provider."""

    def __init__(self) -> None:
        super().__init__(LOOPBACK_TIMEOUT)


class InvalidProviderResponseError(LoopbackTransportError):
    """A malformed or oversized response that must never be exposed."""

    def __init__(self) -> None:
        super().__init__(LOOPBACK_INVALID_OUTPUT)


class SessionCleanupError(RuntimeError):
    """Refuse the local result when deletion of an OpenCode session is uncertain."""

    def __init__(self) -> None:
        super().__init__(LOOPBACK_CLEANUP_FAILED)
        self.code = LOOPBACK_CLEANUP_FAILED


RunProcess = Callable[..., subprocess.CompletedProcess[bytes]]
ValidatedResponse = TypeVar("ValidatedResponse")


@dataclass(frozen=True)
class HttpResponse:
    """Bounded HTTP response used only inside the transport boundary."""

    status: int
    body: bytes


HttpRequest = Callable[[str, str, bytes, int], HttpResponse]
SpawnProcess = Callable[..., subprocess.Popen[bytes]]


class ReviewSessionClient(Protocol):
    """Small injectable API surface: all prompts remain request bodies."""

    def create_session(self) -> str: ...

    def send_review(self, session_id: str, *, route: str, prompt: bytes) -> bytes: ...

    def delete_session(self, session_id: str) -> bool: ...

    def close(self) -> bool: ...


class OpenCodeLoopbackClient:
    """Strict client for an already isolated OpenCode server on 127.0.0.1."""

    def __init__(self, base_url: str, *, request: HttpRequest | None = None, timeout_seconds: float = 180.0) -> None:
        parsed = urlsplit(base_url)
        if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.port is None or timeout_seconds <= 0:
            raise ValueError("OpenCode server must use an explicit 127.0.0.1 HTTP URL")
        self._base_url = base_url.rstrip("/")
        self._request = request
        self._timeout_seconds = timeout_seconds

    def create_session(self) -> str:
        document = self._json("POST", "/session", b"{}")
        session_id = document.get("id")
        if not isinstance(session_id, str) or not session_id:
            raise LoopbackTransportError()
        return session_id

    def send_review(self, session_id: str, *, route: str, prompt: bytes) -> bytes:
        provider, separator, model_id = route.partition("/")
        if not provider or not separator or not model_id:
            raise LoopbackTransportError()
        try:
            prompt_text = prompt.decode("utf-8")
        except UnicodeDecodeError:
            raise InvalidProviderResponseError() from None
        body = json.dumps(
            {
                "model": {"providerID": provider, "modelID": model_id},
                "tools": DISABLED_TOOLS,
                "parts": [{"type": "text", "text": prompt_text}],
            },
            separators=(",", ":"),
        ).encode("utf-8")
        document = self._json("POST", f"/session/{quote(session_id, safe='')}/message", body)
        parts = document.get("parts")
        if not isinstance(parts, list):
            raise InvalidProviderResponseError()
        text_parts = [part.get("text") for part in parts if isinstance(part, dict) and part.get("type") == "text"]
        if len(text_parts) != 1 or not isinstance(text_parts[0], str):
            raise InvalidProviderResponseError()
        return text_parts[0].encode("utf-8")

    def delete_session(self, session_id: str) -> bool:
        try:
            response = self._call("DELETE", f"/session/{quote(session_id, safe='')}", b"")
            return 200 <= response.status < 300 and response.body == b"true"
        except LoopbackTransportError:
            return False

    def close(self) -> bool:
        """A client does not own a process; its enclosing server owns disposal."""
        return True

    def _json(self, method: str, path: str, body: bytes) -> dict[str, object]:
        response = self._call(method, path, body)
        if response.status in {401, 403}:
            raise AuthRequiredError()
        if not 200 <= response.status < 300:
            raise LoopbackTransportError()
        try:
            document = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise InvalidProviderResponseError() from None
        if not isinstance(document, dict):
            raise InvalidProviderResponseError()
        return document

    def _call(self, method: str, path: str, body: bytes) -> HttpResponse:
        try:
            if self._request is None:
                response = _http_request(
                    method,
                    self._base_url + path,
                    body,
                    LOOPBACK_RESPONSE_LIMIT,
                    self._timeout_seconds,
                )
            else:
                response = self._request(method, self._base_url + path, body, LOOPBACK_RESPONSE_LIMIT)
        except TimeoutError:
            raise LoopbackTimeoutError() from None
        except Exception:
            raise LoopbackTransportError() from None
        if len(response.body) > LOOPBACK_RESPONSE_LIMIT:
            raise InvalidProviderResponseError()
        return response


def _http_request(method: str, url: str, body: bytes, limit: int, timeout_seconds: float) -> HttpResponse:
    """Read only a bounded response body; never surface failed-server text."""
    request = Request(
        url,
        data=body if body else None,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    # OpenCodeLoopbackClient accepts only an explicit http://127.0.0.1:<port>
    # authority before this transport can be reached.  The project-data consent
    # seam is confirm_and_load_spec in service.py and is pinned by the egress
    # boundary allowlist.
    with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310  # noqa: S310
        return HttpResponse(response.status, response.read(limit + 1))


class OpenCodeHeadlessServer:
    """Start one disposable OpenCode server, bound only to the numeric loopback host."""

    def __init__(
        self,
        *,
        port: int,
        executable: str = "npx",
        command_prefix: tuple[str, ...] = ("-y", "opencode-ai"),
        run_process: SpawnProcess = subprocess.Popen,
        request: HttpRequest | None = None,
        startup_timeout_seconds: float = 5.0,
        request_timeout_seconds: float = 180.0,
    ) -> None:
        if not 1 <= port <= 65535 or startup_timeout_seconds <= 0 or request_timeout_seconds <= 0:
            raise ValueError("invalid loopback server configuration")
        self._port = port
        self._executable = executable
        self._command_prefix = command_prefix
        self._run_process = run_process
        self._request = request
        self._startup_timeout_seconds = startup_timeout_seconds
        self._process: subprocess.Popen[bytes] | None = None
        self._client = OpenCodeLoopbackClient(
            f"http://127.0.0.1:{port}", request=request, timeout_seconds=request_timeout_seconds
        )

    def create_session(self) -> str:
        self._ensure_started()
        return self._client.create_session()

    def send_review(self, session_id: str, *, route: str, prompt: bytes) -> bytes:
        return self._client.send_review(session_id, route=route, prompt=prompt)

    def delete_session(self, session_id: str) -> bool:
        return self._client.delete_session(session_id)

    def close(self) -> bool:
        process = self._process
        self._process = None
        if process is None or process.poll() is not None:
            return True
        try:
            if os.name == "nt":
                result = subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    timeout=5,
                )
                if result.returncode != 0:
                    return False
            else:
                kill_process_group = getattr(os, "killpg", None)
                if not callable(kill_process_group):
                    return False
                kill_process_group(process.pid, signal.SIGTERM)
            process.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            try:
                if os.name == "nt":
                    process.kill()
                else:
                    kill_process_group = getattr(os, "killpg", None)
                    if not callable(kill_process_group):
                        return False
                    kill_process_group(process.pid, getattr(signal, "SIGKILL", signal.SIGTERM))
                process.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                return False
        return process.poll() is not None

    def _ensure_started(self) -> None:
        if self._process is not None:
            return
        kwargs: dict[str, object] = {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "shell": False,
        }
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        else:
            kwargs["start_new_session"] = True
        try:
            self._process = self._run_process(
                [
                    self._executable,
                    *self._command_prefix,
                    "serve",
                    "--hostname",
                    "127.0.0.1",
                    "--port",
                    str(self._port),
                    "--pure",
                ],
                **kwargs,
            )
        except OSError:
            raise LoopbackTransportError() from None
        deadline = time.monotonic() + self._startup_timeout_seconds
        while time.monotonic() < deadline:
            if self._is_healthy():
                return
            if self._process.poll() is not None:
                break
            time.sleep(0.05)
        self.close()
        raise LoopbackTransportError()

    def _is_healthy(self) -> bool:
        try:
            response = self._client._call("GET", "/global/health", b"")
            if not 200 <= response.status < 300:
                return False
            document = json.loads(response.body.decode("utf-8"))
            return isinstance(document, dict) and document.get("healthy") is True
        except (LoopbackTransportError, UnicodeDecodeError, json.JSONDecodeError):
            return False


class OpenCodeLoopbackRunner:
    """Run one validated review through a disposable OpenCode loopback session."""

    def __init__(self, pricing_probe: OpenCodePricingProbe, session_client: ReviewSessionClient) -> None:
        self._pricing_probe = pricing_probe
        self._session_client = session_client
        self._permit_issuer = object()

    def authorize(self, route: str) -> PricingPermit:
        """Return a permit only after the exact requested route proves zero-cost."""
        self._pricing_probe.require_free(route)
        return PricingPermit(route=route, _issuer=self._permit_issuer)

    def run(
        self,
        *,
        permit: PricingPermit,
        prompt: bytes,
        validate_response: Callable[[bytes], ValidatedResponse],
    ) -> ValidatedResponse:
        """Run only with a same-runner permit, then delete the session on every later path."""
        if permit._issuer is not self._permit_issuer:
            raise ModelNotFreeError(permit.route)
        try:
            session_id = self._session_client.create_session()
        except Exception:
            if not self._session_client.close():
                raise SessionCleanupError() from None
            raise
        try:
            payload = self._session_client.send_review(session_id, route=permit.route, prompt=prompt)
            return validate_response(payload)
        finally:
            session_deleted = self._session_client.delete_session(session_id)
            server_closed = self._session_client.close()
            if not session_deleted or not server_closed:
                raise SessionCleanupError()


class OpenCodePricingProbe:
    """Read cached OpenCode model metadata without a model invocation or refresh."""

    def __init__(
        self,
        executable: str = "npx",
        *,
        command_prefix: tuple[str, ...] = ("-y", "opencode-ai"),
        run_process: RunProcess = subprocess.run,
    ) -> None:
        self._executable = executable
        self._command_prefix = command_prefix
        self._run_process = run_process

    def check(self, route: str) -> PricingVerdict:
        """Accept only an exact route whose complete advertised cost tree is zero."""
        provider, separator, model_id = route.partition("/")
        if not provider or not separator or not model_id:
            return PricingVerdict(route, False, MODEL_NOT_FREE)
        try:
            completed = self._run_process(
                [self._executable, *self._command_prefix, "models", provider, "--verbose", "--pure"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return PricingVerdict(route, False, MODEL_NOT_FREE)
        if completed.returncode != 0:
            return PricingVerdict(route, False, MODEL_NOT_FREE)
        document = _model_document(completed.stdout, route)
        if document is None or not _zero_cost(document.get("cost")):
            return PricingVerdict(route, False, MODEL_NOT_FREE)
        return PricingVerdict(route, True, "OK")

    def require_free(self, route: str) -> None:
        """Raise before the caller can construct/send a review prompt."""
        if not self.check(route).is_free:
            raise ModelNotFreeError(route)


def _model_document(payload: bytes, route: str) -> dict[str, object] | None:
    """Extract exactly one matching verbose-model JSON object from bounded output."""
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return None
    decoder = json.JSONDecoder()
    offset = 0
    matches: list[dict[str, object]] = []
    while True:
        start = text.find("{", offset)
        if start < 0:
            break
        try:
            value, end = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            offset = start + 1
            continue
        offset = end
        if not isinstance(value, dict):
            continue
        provider = value.get("providerID")
        model_id = value.get("id")
        if isinstance(provider, str) and isinstance(model_id, str) and f"{provider}/{model_id}" == route:
            matches.append(value)
    return matches[0] if len(matches) == 1 else None


def _zero_cost(value: object) -> bool:
    """Require a non-empty cost mapping containing only numeric zero leaves."""
    if not isinstance(value, dict) or not value:
        return False
    leaves: list[float | int] = []

    def visit(node: object) -> bool:
        if isinstance(node, bool):
            return False
        if isinstance(node, (int, float)):
            leaves.append(node)
            return node == 0
        if isinstance(node, dict):
            return bool(node) and all(visit(child) for child in node.values())
        if isinstance(node, list):
            return all(visit(child) for child in node)
        return False

    return visit(value) and bool(leaves)
