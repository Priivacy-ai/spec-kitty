"""Contract tests for the OrgDoctrineSource protocol and the three concrete
implementations: GitSource, HttpsBundleSource, ApiSource.

These tests intentionally exercise the **public contract** (the protocol
shape, FetchResult fields, side effects on ``target_dir``) rather than
implementation internals.
"""

from __future__ import annotations

import io
import json
import subprocess
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from specify_cli.doctrine.sources import (
    ApiSource,
    FetchResult,
    GitSource,
    HttpsBundleSource,
    OrgDoctrineSource,
)


# ---------------------------------------------------------------------------
# Protocol contract
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.unit, pytest.mark.fast]

class TestOrgDoctrineSourceProtocol:
    """The runtime_checkable protocol must accept all three concrete sources."""

    def test_git_source_satisfies_protocol(self) -> None:
        source = GitSource(url="git@example.com:org/doctrine.git")
        assert isinstance(source, OrgDoctrineSource)

    def test_https_source_satisfies_protocol(self) -> None:
        source = HttpsBundleSource(url="https://example.com/pack.tar.gz")
        assert isinstance(source, OrgDoctrineSource)

    def test_api_source_satisfies_protocol(self) -> None:
        source = ApiSource(url="https://example.com/api")
        assert isinstance(source, OrgDoctrineSource)

    def test_fetch_result_defaults(self) -> None:
        result = FetchResult(ok=True, artifacts_written=0, pack_version=None)
        assert result.errors == []


# ---------------------------------------------------------------------------
# GitSource
# ---------------------------------------------------------------------------
@dataclass
class _FakeCompletedProcess:
    returncode: int
    stdout: str = ""
    stderr: str = ""


class _GitRunRecorder:
    """Replaces ``subprocess.run`` so we can drive GitSource via scripted exits.

    Each entry in ``script`` is a tuple ``(returncode, stdout, stderr)`` and
    is consumed in order.  An optional ``side_effect`` callable receives the
    invoked argv before the scripted result is returned (used to materialise
    a fake ``.git/`` directory during ``git clone``).
    """

    def __init__(
        self,
        script: list[tuple[int, str, str]],
        side_effects: dict[str, Any] | None = None,
    ) -> None:
        self.script = list(script)
        self.calls: list[list[str]] = []
        self.side_effects = side_effects or {}

    def __call__(
        self,
        argv: list[str],
        capture_output: bool = True,
        text: bool = True,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append(argv)
        for keyword, effect in self.side_effects.items():
            if any(keyword == part for part in argv):
                effect(argv)
        if not self.script:
            return _FakeCompletedProcess(returncode=0)  # type: ignore[return-value]
        returncode, stdout, stderr = self.script.pop(0)
        return _FakeCompletedProcess(  # type: ignore[return-value]
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
        )


def _make_fake_clone(directives_count: int = 2):
    """Return a side-effect that materialises a fake clone under target_dir."""

    def _effect(argv: list[str]) -> None:
        target_dir = Path(argv[-1])
        (target_dir / ".git").mkdir(parents=True, exist_ok=True)
        directives = target_dir / "directives"
        directives.mkdir(parents=True, exist_ok=True)
        for i in range(directives_count):
            (directives / f"DIR-{i}.directive.yaml").write_text("id: x\n")

    return _effect


class TestGitSource:
    def test_first_install_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "doctrine"
        runner = _GitRunRecorder(
            script=[
                (0, "", ""),  # clone
                (0, "v1.2.0\n", ""),  # describe
            ],
            side_effects={"clone": _make_fake_clone(directives_count=2)},
        )
        monkeypatch.setattr(
            "specify_cli.doctrine.sources.git_source.subprocess.run", runner
        )

        result = GitSource(url="git@example.com:org/d.git").fetch(target)

        assert result.ok is True
        assert result.artifacts_written == 2
        assert result.pack_version == "v1.2.0"
        # The .git directory exists in the materialised target.
        assert (target / ".git").exists()
        # No reset/fetch on first install — just clone + describe.
        assert any(call[1] == "clone" for call in runner.calls)
        assert not any(call[1:3] == ["-C", str(target)] and "fetch" in call for call in runner.calls)

    def test_update_path_used_when_dot_git_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "doctrine"
        (target / ".git").mkdir(parents=True)
        (target / "directives").mkdir()
        (target / "directives" / "A.yaml").write_text("id: a\n")

        runner = _GitRunRecorder(
            script=[
                (0, "", ""),  # fetch
                (0, "", ""),  # reset
                (0, "v1.3.0\n", ""),  # describe
            ],
        )
        monkeypatch.setattr(
            "specify_cli.doctrine.sources.git_source.subprocess.run", runner
        )

        result = GitSource(url="git@example.com:org/d.git").fetch(target)

        assert result.ok is True
        assert result.pack_version == "v1.3.0"
        # First call must be `git fetch`, second must be `git reset`. No clone.
        invocations = [call[1] if len(call) > 1 else "" for call in runner.calls]
        assert "fetch" in runner.calls[0]
        assert "reset" in runner.calls[1]
        assert not any(part == "clone" for call in runner.calls for part in call)
        assert invocations  # silence the unused-var lint

    def test_first_install_failure_cleans_up(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "doctrine"

        def _partial_clone(argv: list[str]) -> None:
            # git clone wrote some files but then failed.
            target_dir = Path(argv[-1])
            target_dir.mkdir(parents=True, exist_ok=True)
            (target_dir / "junk").write_text("partial\n")

        runner = _GitRunRecorder(
            script=[(128, "", "fatal: repo not found")],
            side_effects={"clone": _partial_clone},
        )
        monkeypatch.setattr(
            "specify_cli.doctrine.sources.git_source.subprocess.run", runner
        )

        result = GitSource(url="git@example.com:org/d.git").fetch(target)

        assert result.ok is False
        assert "fatal: repo not found" in result.errors[0]
        assert not target.exists()

    def test_update_failure_leaves_existing_clone_untouched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "doctrine"
        (target / ".git").mkdir(parents=True)
        (target / "directives").mkdir()
        (target / "directives" / "A.yaml").write_text("id: a\n")

        runner = _GitRunRecorder(script=[(1, "", "network unreachable")])
        monkeypatch.setattr(
            "specify_cli.doctrine.sources.git_source.subprocess.run", runner
        )

        result = GitSource(url="git@example.com:org/d.git").fetch(target)

        assert result.ok is False
        assert "network unreachable" in result.errors[0]
        # Existing clone preserved.
        assert (target / ".git").exists()
        assert (target / "directives" / "A.yaml").read_text() == "id: a\n"

    def test_https_url_gets_token_injected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "doctrine"
        monkeypatch.setenv("GIT_TOKEN", "secret-abc")

        runner = _GitRunRecorder(
            script=[(0, "", ""), (0, "v1\n", "")],
            side_effects={"clone": _make_fake_clone(directives_count=1)},
        )
        monkeypatch.setattr(
            "specify_cli.doctrine.sources.git_source.subprocess.run", runner
        )

        result = GitSource(url="https://example.com/org/d.git").fetch(target)

        assert result.ok is True
        clone_argv = runner.calls[0]
        # Token must appear in the URL passed to git, not in any other arg.
        assert any("oauth2:secret-abc@example.com" in part for part in clone_argv)

    def test_ssh_url_unaffected_by_git_token(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "doctrine"
        monkeypatch.setenv("GIT_TOKEN", "secret-abc")

        runner = _GitRunRecorder(
            script=[(0, "", ""), (0, "v1\n", "")],
            side_effects={"clone": _make_fake_clone(directives_count=1)},
        )
        monkeypatch.setattr(
            "specify_cli.doctrine.sources.git_source.subprocess.run", runner
        )

        GitSource(url="git@example.com:org/d.git").fetch(target)
        clone_argv = runner.calls[0]
        assert "secret-abc" not in " ".join(clone_argv)

    def test_ref_checkout_after_first_clone(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "doctrine"
        runner = _GitRunRecorder(
            script=[
                (0, "", ""),  # clone
                (0, "", ""),  # checkout
                (0, "v1.0.0\n", ""),  # describe
            ],
            side_effects={"clone": _make_fake_clone()},
        )
        monkeypatch.setattr(
            "specify_cli.doctrine.sources.git_source.subprocess.run", runner
        )

        result = GitSource(url="git@example.com:org/d.git", ref="v1.0.0").fetch(target)

        assert result.ok is True
        # 2nd call must be checkout to ``ref``.
        assert runner.calls[1][-1] == "v1.0.0"


# ---------------------------------------------------------------------------
# HttpsBundleSource
# ---------------------------------------------------------------------------
class _FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
        body: bytes = b"",
        headers: dict[str, str] | None = None,
        url: str = "",
        reason: str = "OK",
    ) -> None:
        self.status_code = status_code
        self._body = body
        self.headers = headers or {}
        self.url = url
        self.reason = reason

    def iter_content(self, chunk_size: int = 65536):
        for i in range(0, len(self._body), chunk_size):
            yield self._body[i : i + chunk_size]

    def json(self) -> Any:
        return json.loads(self._body.decode("utf-8"))


def _make_tar_gz_bundle(top_dir: str | None = None) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        prefix = f"{top_dir}/" if top_dir else ""
        for name, content in [
            ("directives/sec.directive.yaml", "id: sec\n"),
            ("agent_profiles/eng.agent.yaml", "id: eng\n"),
        ]:
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name=f"{prefix}{name}")
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _make_zip_bundle() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("directives/sec.directive.yaml", "id: sec\n")
        zf.writestr("agent_profiles/eng.agent.yaml", "id: eng\n")
    return buf.getvalue()


class TestHttpsBundleSource:
    def test_tar_gz_extraction(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "snapshot"
        bundle = _make_tar_gz_bundle(top_dir="my-pack-v1.0.0")

        def _fake_get(url: str, **kwargs: Any) -> _FakeResponse:
            return _FakeResponse(
                status_code=200,
                body=bundle,
                headers={"Content-Type": "application/gzip", "ETag": "abc123"},
                url=url,
            )

        monkeypatch.setattr(
            "specify_cli.doctrine.sources.https_source.requests.get", _fake_get
        )

        result = HttpsBundleSource(
            url="https://example.com/pack.tar.gz"
        ).fetch(target)

        assert result.ok is True
        assert result.pack_version == "abc123"
        # Top-level dir was flattened away.
        assert (target / "directives" / "sec.directive.yaml").is_file()
        assert (target / "agent_profiles" / "eng.agent.yaml").is_file()
        assert result.artifacts_written == 2

    def test_zip_extraction(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "snapshot"
        bundle = _make_zip_bundle()

        def _fake_get(url: str, **kwargs: Any) -> _FakeResponse:
            return _FakeResponse(
                status_code=200,
                body=bundle,
                headers={"Content-Type": "application/zip"},
                url=url,
            )

        monkeypatch.setattr(
            "specify_cli.doctrine.sources.https_source.requests.get", _fake_get
        )

        result = HttpsBundleSource(
            url="https://example.com/pack.zip",
            ref="v2.0.0",
        ).fetch(target)

        assert result.ok is True
        assert result.pack_version == "v2.0.0"  # ref wins over (absent) ETag
        assert (target / "directives" / "sec.directive.yaml").is_file()

    def test_401_returns_auth_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _fake_get(url: str, **kwargs: Any) -> _FakeResponse:
            return _FakeResponse(status_code=401, body=b"", reason="Unauthorized")

        monkeypatch.setattr(
            "specify_cli.doctrine.sources.https_source.requests.get", _fake_get
        )

        result = HttpsBundleSource(
            url="https://example.com/pack.tar.gz"
        ).fetch(tmp_path / "snapshot")

        assert result.ok is False
        assert any("SPEC_KITTY_ORG_TOKEN" in err for err in result.errors)

    def test_5xx_retried_once(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        bundle = _make_tar_gz_bundle()
        responses = iter(
            [
                _FakeResponse(status_code=503, body=b"", reason="Service Unavailable"),
                _FakeResponse(
                    status_code=200,
                    body=bundle,
                    headers={"Content-Type": "application/gzip"},
                    url="https://example.com/pack.tar.gz",
                ),
            ]
        )

        def _fake_get(url: str, **kwargs: Any) -> _FakeResponse:
            return next(responses)

        monkeypatch.setattr(
            "specify_cli.doctrine.sources.https_source.requests.get", _fake_get
        )
        monkeypatch.setattr(
            "specify_cli.doctrine.sources.https_source.time.sleep", lambda _s: None
        )

        result = HttpsBundleSource(
            url="https://example.com/pack.tar.gz"
        ).fetch(tmp_path / "snapshot")

        assert result.ok is True

    def test_auth_header_is_used(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        bundle = _make_tar_gz_bundle()
        seen_headers: dict[str, str] = {}

        def _fake_get(url: str, **kwargs: Any) -> _FakeResponse:
            seen_headers.update(kwargs.get("headers") or {})
            return _FakeResponse(
                status_code=200,
                body=bundle,
                headers={"Content-Type": "application/gzip"},
                url=url,
            )

        monkeypatch.setenv("SPEC_KITTY_ORG_TOKEN", "tok123")
        monkeypatch.setattr(
            "specify_cli.doctrine.sources.https_source.requests.get", _fake_get
        )

        HttpsBundleSource(url="https://example.com/pack.tar.gz").fetch(
            tmp_path / "snapshot"
        )

        assert seen_headers.get("Authorization") == "Bearer tok123"


# ---------------------------------------------------------------------------
# ApiSource
# ---------------------------------------------------------------------------
class _FakeApiServer:
    """Tiny dispatcher used to mock ``requests.request`` for ApiSource tests."""

    def __init__(self, routes: dict[str, _FakeResponse]) -> None:
        self.routes = routes
        self.headers_seen: list[dict[str, str]] = []
        self.calls: list[str] = []

    def __call__(
        self, method: str, url: str, **kwargs: Any
    ) -> _FakeResponse:
        self.calls.append(url)
        self.headers_seen.append(dict(kwargs.get("headers") or {}))
        for suffix, response in self.routes.items():
            if url.endswith(suffix):
                return response
        return _FakeResponse(status_code=404, body=b"", reason="Not Found")


def _json_response(payload: Any, status_code: int = 200) -> _FakeResponse:
    return _FakeResponse(
        status_code=status_code,
        body=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )


class TestApiSource:
    def test_full_flow(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "snapshot"
        server = _FakeApiServer(
            routes={
                "/artifact-types": _json_response(
                    {"types": ["directives", "agent_profiles"]}
                ),
                "/artifacts/directives": _json_response(
                    {
                        "artifacts": [
                            {
                                "id": "sec-001",
                                "filename": "sec-001.directive.yaml",
                                "content": "id: sec-001\n",
                            }
                        ]
                    }
                ),
                "/artifacts/agent_profiles": _json_response(
                    {
                        "artifacts": [
                            {
                                "id": "eng",
                                "filename": "eng.agent.yaml",
                                "content": "id: eng\n",
                            }
                        ]
                    }
                ),
                "/drg-extensions": _json_response(
                    {
                        "fragments": [
                            {
                                "filename": "010-security.graph.yaml",
                                "content": "edges: []\n",
                            }
                        ]
                    }
                ),
                "/version": _json_response({"version": "v1.4.2"}),
            }
        )
        monkeypatch.setattr(
            "specify_cli.doctrine.sources.api_source.requests.request", server
        )

        result = ApiSource(url="https://example.com/api").fetch(target)

        assert result.ok is True
        assert result.pack_version == "v1.4.2"
        assert (target / "directives" / "sec-001.directive.yaml").is_file()
        assert (target / "agent_profiles" / "eng.agent.yaml").is_file()
        assert (target / "drg" / "010-security.graph.yaml").is_file()
        # 1 directive + 1 agent + 1 drg fragment.
        assert result.artifacts_written == 3

    def test_no_drg_endpoint(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "snapshot"
        server = _FakeApiServer(
            routes={
                "/artifact-types": _json_response({"types": ["directives"]}),
                "/artifacts/directives": _json_response(
                    {
                        "artifacts": [
                            {
                                "id": "x",
                                "filename": "x.directive.yaml",
                                "content": "id: x\n",
                            }
                        ]
                    }
                ),
                # /drg-extensions and /version both fall through to 404.
            }
        )
        monkeypatch.setattr(
            "specify_cli.doctrine.sources.api_source.requests.request", server
        )

        result = ApiSource(url="https://example.com/api", ref="v0.9").fetch(target)

        assert result.ok is True
        assert not (target / "drg").exists()
        # Falls back to ref when /version returns 404 without Date.
        assert result.pack_version == "v0.9"

    def test_default_types_when_artifact_types_404(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "snapshot"
        # All endpoints 404 -> default type list, all empty.
        server = _FakeApiServer(routes={})
        monkeypatch.setattr(
            "specify_cli.doctrine.sources.api_source.requests.request", server
        )

        result = ApiSource(url="https://example.com/api").fetch(target)

        assert result.ok is True
        assert result.artifacts_written == 0
        # Should have called /artifact-types AND each default type's endpoint.
        called_suffixes = {url.split("/api", 1)[1] for url in server.calls}
        assert "/artifact-types" in called_suffixes
        assert "/artifacts/directives" in called_suffixes
        assert "/artifacts/agent_profiles" in called_suffixes

    def test_auth_header_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "snapshot"
        server = _FakeApiServer(
            routes={"/artifact-types": _json_response({"types": []})}
        )
        monkeypatch.setattr(
            "specify_cli.doctrine.sources.api_source.requests.request", server
        )
        monkeypatch.setenv("SPEC_KITTY_ORG_AUTH_HEADER", "Basic dXNlcjpwYXNz")

        ApiSource(url="https://example.com/api").fetch(target)

        # The custom header must appear verbatim on the first request.
        assert server.headers_seen[0].get("Authorization") == "Basic dXNlcjpwYXNz"

    def test_credential_error_propagates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        server = _FakeApiServer(
            routes={
                "/artifact-types": _FakeResponse(
                    status_code=401, body=b"", reason="Unauthorized"
                )
            }
        )
        monkeypatch.setattr(
            "specify_cli.doctrine.sources.api_source.requests.request", server
        )

        result = ApiSource(url="https://example.com/api").fetch(
            tmp_path / "snapshot"
        )

        assert result.ok is False
        assert any("SPEC_KITTY_ORG_TOKEN" in err for err in result.errors)
