"""Fail-closed pricing contracts; no test starts an OpenCode model."""

from __future__ import annotations

import json
import subprocess

import pytest

from specify_cli.spec_review.runner import (
    MODEL_NOT_FREE,
    AUTH_REQUIRED,
    LOOPBACK_CLEANUP_FAILED,
    HttpResponse,
    AuthRequiredError,
    InvalidProviderResponseError,
    LoopbackTransportError,
    LoopbackTimeoutError,
    ModelNotFreeError,
    OpenCodeHeadlessServer,
    OpenCodeLoopbackClient,
    OpenCodeLoopbackRunner,
    OpenCodePricingProbe,
    SessionCleanupError,
)


pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _completed(payload: bytes, code: int = 0) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(["opencode"], code, stdout=payload, stderr=b"ignored")


def _model(cost: str) -> bytes:
    return (
        b"opencode/x-preview-f-free\n"
        + ('{"id":"x-preview-f-free","providerID":"opencode","cost":' + cost + "}\n").encode()
    )


def test_pricing_probe_accepts_only_exact_zero_cost_route() -> None:
    calls: list[object] = []

    def fake(argv: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append((argv, kwargs))
        return _completed(_model('{"input":0,"output":0,"cache":{"read":0,"write":0}}'))

    verdict = OpenCodePricingProbe(run_process=fake).check("opencode/x-preview-f-free")

    assert verdict.is_free is True
    assert calls[0][0] == ["npx", "-y", "opencode-ai", "models", "opencode", "--verbose", "--pure"]
    assert calls[0][1]["stdin"] is subprocess.DEVNULL


@pytest.mark.parametrize("cost", ['{"input":0.01,"output":0}', '{}'])
def test_pricing_probe_refuses_paid_or_incomplete_metadata(cost: str) -> None:
    probe = OpenCodePricingProbe(run_process=lambda *args, **kwargs: _completed(_model(cost)))

    with pytest.raises(ModelNotFreeError, match=MODEL_NOT_FREE):
        probe.require_free("opencode/x-preview-f-free")


def test_pricing_probe_refuses_missing_route_without_fallback() -> None:
    probe = OpenCodePricingProbe(run_process=lambda *args, **kwargs: _completed(b"opencode/other\n{}\n"))

    verdict = probe.check("opencode/x-preview-f-free")

    assert verdict.is_free is False
    assert verdict.code == MODEL_NOT_FREE


class _FakeSessionClient:
    def __init__(self, events: list[object], *, cleanup: bool = True) -> None:
        self._events = events
        self._cleanup = cleanup

    def create_session(self) -> str:
        self._events.append("create")
        return "session-1"

    def send_review(self, session_id: str, *, route: str, prompt: bytes) -> bytes:
        self._events.append(("send", session_id, route, prompt))
        return b'{"schema":"review-response/v1","findings":[]}'

    def delete_session(self, session_id: str) -> bool:
        self._events.append(("delete", session_id))
        return self._cleanup

    def close(self) -> bool:
        self._events.append("close")
        return self._cleanup


def test_loopback_runner_refuses_paid_route_before_session_or_prompt() -> None:
    events: list[object] = []
    pricing = OpenCodePricingProbe(run_process=lambda *args, **kwargs: _completed(_model('{"input":1,"output":0}')))
    runner = OpenCodeLoopbackRunner(pricing, _FakeSessionClient(events))

    with pytest.raises(ModelNotFreeError, match=MODEL_NOT_FREE):
        runner.authorize("opencode/x-preview-f-free")

    assert events == []


def test_loopback_runner_sends_prompt_only_after_free_check_and_deletes_session() -> None:
    events: list[object] = []
    pricing = OpenCodePricingProbe(run_process=lambda *args, **kwargs: _completed(_model('{"input":0,"output":0}')))
    runner = OpenCodeLoopbackRunner(pricing, _FakeSessionClient(events))

    permit = runner.authorize("opencode/x-preview-f-free")
    result = runner.run(permit=permit, prompt=b"synthetic", validate_response=lambda payload: payload)

    assert result == b'{"schema":"review-response/v1","findings":[]}'
    assert events == ["create", ("send", "session-1", "opencode/x-preview-f-free", b"synthetic"), ("delete", "session-1"), "close"]


def test_loopback_runner_refuses_result_when_session_cleanup_is_unconfirmed() -> None:
    pricing = OpenCodePricingProbe(run_process=lambda *args, **kwargs: _completed(_model('{"input":0,"output":0}')))
    runner = OpenCodeLoopbackRunner(pricing, _FakeSessionClient([], cleanup=False))

    with pytest.raises(SessionCleanupError, match=LOOPBACK_CLEANUP_FAILED):
        runner.run(permit=runner.authorize("opencode/x-preview-f-free"), prompt=b"synthetic", validate_response=lambda payload: payload)


def test_loopback_runner_closes_started_server_when_session_creation_fails() -> None:
    events: list[object] = []

    class FailingSessionClient(_FakeSessionClient):
        def create_session(self) -> str:
            events.append("create")
            raise LoopbackTransportError()

    pricing = OpenCodePricingProbe(run_process=lambda *args, **kwargs: _completed(_model('{"input":0,"output":0}')))
    runner = OpenCodeLoopbackRunner(pricing, FailingSessionClient(events))

    with pytest.raises(LoopbackTransportError):
        runner.run(permit=runner.authorize("opencode/x-preview-f-free"), prompt=b"synthetic", validate_response=lambda payload: payload)

    assert events == ["create", "close"]


def test_loopback_http_client_uses_only_loopback_body_and_exact_session_cleanup() -> None:
    calls: list[tuple[str, str, bytes, int]] = []

    def fake_request(method: str, url: str, body: bytes, limit: int) -> HttpResponse:
        calls.append((method, url, body, limit))
        if method == "POST" and url.endswith("/session"):
            return HttpResponse(200, b'{"id":"session-1"}')
        if method == "POST":
            return HttpResponse(200, b'{"parts":[{"type":"text","text":"{\\\"schema\\\":\\\"review-response/v1\\\",\\\"findings\\\":[]}"}]}')
        return HttpResponse(200, b"true")

    client = OpenCodeLoopbackClient("http://127.0.0.1:4096", request=fake_request)
    session_id = client.create_session()
    payload = client.send_review(session_id, route="opencode/x-preview-f-free", prompt=b"synthetic")

    assert payload == b'{"schema":"review-response/v1","findings":[]}'
    assert client.delete_session(session_id) is True
    assert calls[1][0:2] == ("POST", "http://127.0.0.1:4096/session/session-1/message")
    request_body = json.loads(calls[1][2])
    assert request_body["parts"] == [{"type": "text", "text": "synthetic"}]
    assert all(value is False for value in request_body["tools"].values())
    assert all("127.0.0.1" in call[1] for call in calls)


def test_loopback_http_client_applies_requested_timeout_to_its_default_request(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: list[float] = []

    class Response:
        status = 200

        def read(self, size: int) -> bytes:
            return b'{"id":"session-1"}'

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def fake_urlopen(request: object, *, timeout: float) -> Response:
        observed.append(timeout)
        return Response()

    monkeypatch.setattr("specify_cli.spec_review.runner.urlopen", fake_urlopen)
    client = OpenCodeLoopbackClient("http://127.0.0.1:4096", timeout_seconds=42.0)

    assert client.create_session() == "session-1"
    assert observed == [42.0]


def test_loopback_http_client_never_exposes_server_body_or_exception_text() -> None:
    sentinel = "DO-NOT-LEAK-THIS-PROMPT"

    def fake_request(*args: object) -> HttpResponse:
        raise RuntimeError(sentinel)

    client = OpenCodeLoopbackClient("http://127.0.0.1:4096", request=fake_request)  # type: ignore[arg-type]

    with pytest.raises(LoopbackTransportError) as error:
        client.create_session()

    assert sentinel not in str(error.value)
    assert error.value.__cause__ is None


def test_loopback_http_client_classifies_auth_timeout_provider_and_invalid_response_without_retry() -> None:
    sentinel = "DO-NOT-LEAK"
    cases: list[tuple[object, type[LoopbackTransportError], str]] = [
        (HttpResponse(401, sentinel.encode()), AuthRequiredError, AUTH_REQUIRED),
        (HttpResponse(429, sentinel.encode()), LoopbackTransportError, "SPEC_REVIEW_PROVIDER_ERROR"),
        (HttpResponse(200, sentinel.encode()), InvalidProviderResponseError, "SPEC_REVIEW_INVALID_OUTPUT"),
        (TimeoutError(sentinel), LoopbackTimeoutError, "SPEC_REVIEW_TIMEOUT"),
    ]

    for response, error_type, code in cases:
        calls: list[object] = []

        def fake_request(
            *args: object,
            captured: list[object] = calls,
            result: object = response,
        ) -> HttpResponse:
            captured.append(args)
            if isinstance(result, BaseException):
                raise result
            assert isinstance(result, HttpResponse)
            return result

        client = OpenCodeLoopbackClient("http://127.0.0.1:4096", request=fake_request)  # type: ignore[arg-type]
        with pytest.raises(error_type) as error:
            client.create_session()
        assert error.value.code == code
        assert sentinel not in str(error.value)
        assert len(calls) == 1


def test_headless_server_uses_numeric_loopback_argv_and_never_captures_streams() -> None:
    calls: list[object] = []

    class FakeProcess:
        def __init__(self) -> None:
            self.running = True

        def poll(self) -> int | None:
            return None if self.running else 0

        def terminate(self) -> None:
            self.running = False

        def kill(self) -> None:
            self.running = False

        def wait(self, timeout: float) -> int:
            self.running = False
            return 0

    def fake_popen(argv: object, **kwargs: object) -> FakeProcess:
        calls.append((argv, kwargs))
        return FakeProcess()

    server = OpenCodeHeadlessServer(
        port=4097,
        run_process=fake_popen,  # type: ignore[arg-type]
        request=lambda method, url, body, limit: HttpResponse(
            200,
            b'{"healthy":true}' if url.endswith("/global/health") else b'{"id":"session-1"}',
        ),
    )

    assert server.create_session() is not None
    assert calls[0][0] == ["npx", "-y", "opencode-ai", "serve", "--hostname", "127.0.0.1", "--port", "4097", "--pure"]
    assert calls[0][1]["shell"] is False
    assert calls[0][1]["stdin"] is subprocess.DEVNULL
    assert calls[0][1]["stdout"] is subprocess.DEVNULL
    assert calls[0][1]["stderr"] is subprocess.DEVNULL


@pytest.mark.parametrize("candidate_url", ["https://127.0.0.1:4096", "http://localhost:4096", "http://127.0.0.1"])
def test_loopback_http_client_refuses_non_explicit_loopback_urls(candidate_url: str) -> None:
    with pytest.raises(ValueError):
        OpenCodeLoopbackClient(candidate_url, request=lambda *args: HttpResponse(200, b"{}"))
