"""WP10 versioned daemon quiesce/restart protocol tests."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from specify_cli.sync.daemon_protocol import (
    DaemonCutoverProtocol,
    DaemonProtocolMismatchError,
    QuiesceAcknowledgement,
)


from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


def _wait_json(path: Path) -> dict[str, object]:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if path.exists():
            return dict(json.loads(path.read_text(encoding="utf-8")))
        time.sleep(0.01)
    raise AssertionError(f"timed out waiting for {path}")


def test_real_subprocess_quiesce_ack_is_versioned_and_authenticated(tmp_path: Path) -> None:
    state = tmp_path / "server.json"
    script = (
        "import json,sys,threading\n"
        "from http.server import BaseHTTPRequestHandler,HTTPServer\n"
        "p=sys.argv[1]\n"
        "class H(BaseHTTPRequestHandler):\n"
        " def log_message(self,*a): pass\n"
        " def do_GET(self):\n"
        "  b=json.dumps({'status':'ok','protocol_version':2,'package_version':'test'}).encode();self.send_response(200);self.end_headers();self.wfile.write(b)\n"
        " def do_POST(self):\n"
        "  n=int(self.headers.get('content-length','0')); d=json.loads(self.rfile.read(n)); assert d['token']=='secret'; assert d['migration_protocol']==1\n"
        "  b=json.dumps({'status':'quiesced','migration_protocol':1,'phase':'quiesced'}).encode();self.send_response(200);self.end_headers();self.wfile.write(b);\n"
        "  threading.Thread(target=self.server.shutdown,daemon=True).start()\n"
        "s=HTTPServer(('127.0.0.1',0),H);open(p,'w').write(json.dumps({'port':s.server_port}));s.serve_forever()\n"
    )
    process = subprocess.Popen([sys.executable, "-c", script, str(state)])
    try:
        port = int(_wait_json(state)["port"])
        protocol = DaemonCutoverProtocol(
            base_url=f"http://127.0.0.1:{port}",
            token="secret",
            package_version="test",
            expected_daemon_protocol=2,
        )
        acknowledgement = protocol.quiesce("migration-1")
        assert acknowledgement == QuiesceAcknowledgement(
            migration_id="migration-1",
            migration_protocol=1,
            daemon_protocol=2,
            package_version="test",
        )
        assert process.wait(timeout=5) == 0
    finally:
        if process.poll() is None:
            process.kill()


def test_unrecognized_protocol_fails_without_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fetch(request: urllib.request.Request, timeout: float) -> dict[str, object]:
        del timeout
        calls.append(request.full_url)
        return {"status": "ok", "protocol_version": 999, "package_version": "old"}

    protocol = DaemonCutoverProtocol(
        base_url="http://127.0.0.1:1",
        token="secret",
        package_version="test",
        expected_daemon_protocol=1,
        fetch_json=fetch,
    )

    with pytest.raises(DaemonProtocolMismatchError):
        protocol.quiesce("migration-1")
    assert calls == ["http://127.0.0.1:1/api/health"]


def test_reachable_identity_drift_after_shutdown_request_fails_closed() -> None:
    calls = 0

    def fetch(request: urllib.request.Request, timeout: float) -> dict[str, object]:
        nonlocal calls
        del timeout
        calls += 1
        if request.full_url.endswith("/api/shutdown"):
            return {"status": "quiesced", "migration_protocol": 1}
        if calls == 1:
            return {"status": "ok", "protocol_version": 2, "package_version": "test"}
        return {"status": "ok", "protocol_version": 999, "package_version": "foreign"}

    protocol = DaemonCutoverProtocol(
        base_url="http://127.0.0.1:1",
        token="secret",
        package_version="test",
        expected_daemon_protocol=2,
        fetch_json=fetch,
    )

    with pytest.raises(DaemonProtocolMismatchError, match="recognized protocol/package"):
        protocol.quiesce("migration-drift")


@pytest.mark.parametrize(
    "candidate_url",
    [
        "https://127.0.0.1:1234",
        "http://127.0.0.1:1234@saas.example.test",
        "http://localhost:1234.evil.example",
        "http://localhost:1234/control",
        "http://localhost",
    ],
)
def test_non_exact_loopback_base_urls_are_rejected_before_io(candidate_url: str) -> None:
    with pytest.raises(ValueError, match="loopback"):
        DaemonCutoverProtocol(
            base_url=candidate_url,
            token="secret",
            package_version="test",
            expected_daemon_protocol=1,
        )
