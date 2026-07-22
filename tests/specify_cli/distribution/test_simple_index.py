"""Tests for SimpleIndexProvider."""

from __future__ import annotations

import inspect

import httpx
import pytest

from specify_cli.compat import provider as provider_module
from specify_cli.compat.provider import _MAX_RESPONSE_BYTES
from specify_cli.distribution.simple_index import SimpleIndexProvider


class _FakeResponse:
    def __init__(self, body: bytes, status_code: int = 200) -> None:
        self.content = body
        self.status_code = status_code

    @property
    def is_error(self) -> bool:
        return self.status_code >= 400


class _FakeClient:
    def __init__(self, response: _FakeResponse | Exception) -> None:
        self._response = response
        self.last_url: str | None = None
        self.last_headers: dict[str, str] | None = None
        self.kwargs: dict[str, object] = {}

    def __enter__(self) -> _FakeClient:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def get(self, url: str, headers: dict[str, str] | None = None) -> _FakeResponse:
        self.last_url = url
        self.last_headers = headers
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


HTML = """
<!DOCTYPE html>
<html><body>
<a href="acme_spec_kitty_cli-1.0.0-py3-none-any.whl">1.0.0</a>
<a href="acme_spec_kitty_cli-1.2.0-py3-none-any.whl">1.2.0</a>
<a href="acme_spec_kitty_cli-1.1.0.tar.gz">1.1.0</a>
</body></html>
"""


def test_parses_highest_version(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeClient(_FakeResponse(HTML.encode("utf-8")))
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: client)
    provider = SimpleIndexProvider(
        "https://example.invalid/simple/",
        package_prefix="acme_spec_kitty_cli",
    )
    result = provider.get_latest("acme-spec-kitty-cli")
    assert result.version == "1.2.0"
    assert result.source == "simple_index"
    assert result.error is None
    assert client.last_url == "https://example.invalid/simple/acme-spec-kitty-cli/"


def test_client_disables_redirects(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def factory(**kwargs: object) -> _FakeClient:
        seen.update(kwargs)
        return _FakeClient(_FakeResponse(HTML.encode("utf-8")))

    monkeypatch.setattr(httpx, "Client", factory)
    SimpleIndexProvider(
        "https://example.invalid/simple/",
        package_prefix="acme_spec_kitty_cli",
    ).get_latest("acme-spec-kitty-cli")
    assert seen.get("follow_redirects") is False


def test_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: _FakeClient(_FakeResponse(b"nope", status_code=404)),
    )
    result = SimpleIndexProvider("https://example.invalid/simple/").get_latest("pkg")
    assert result.version is None
    assert result.source == "none"
    assert result.error == "http_error"


def test_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: _FakeClient(httpx.TimeoutException("slow")),
    )
    result = SimpleIndexProvider("https://example.invalid/simple/").get_latest("pkg")
    assert result.error == "timeout"
    assert result.source == "none"


def test_oversized(monkeypatch: pytest.MonkeyPatch) -> None:
    body = b"x" * (_MAX_RESPONSE_BYTES + 1)
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: _FakeClient(_FakeResponse(body)),
    )
    result = SimpleIndexProvider("https://example.invalid/simple/").get_latest("pkg")
    assert result.error == "oversized"
    assert result.source == "none"


def test_parse_error_on_empty_index(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: _FakeClient(_FakeResponse(b"<html><body></body></html>")),
    )
    result = SimpleIndexProvider("https://example.invalid/simple/").get_latest("pkg")
    assert result.error == "parse_error"
    assert result.source == "none"


def test_never_raises_on_unexpected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: _FakeClient(RuntimeError("boom")),
    )
    result = SimpleIndexProvider("https://example.invalid/simple/").get_latest("pkg")
    assert result.source == "none"
    assert result.version is None


def test_zero_arg_subclass_pattern(monkeypatch: pytest.MonkeyPatch) -> None:
    class AcmeSimpleIndexProvider(SimpleIndexProvider):
        def __init__(self) -> None:
            super().__init__(
                index_url="https://example.invalid/simple/",
                package_prefix="acme_spec_kitty_cli",
            )

    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: _FakeClient(_FakeResponse(HTML.encode("utf-8"))),
    )
    result = AcmeSimpleIndexProvider().get_latest("acme-spec-kitty-cli")
    assert result.version == "1.2.0"
    assert result.source == "simple_index"


def test_base_init_requires_index_url() -> None:
    params = inspect.signature(SimpleIndexProvider.__init__).parameters
    assert "index_url" in params
    assert params["index_url"].default is inspect.Parameter.empty


def test_reexported_from_compat_provider() -> None:
    assert provider_module.SimpleIndexProvider is SimpleIndexProvider


# --- #2836 review fold: stable-only + yanked-skipping selection ---

_HTML_WITH_PRERELEASE = """
<html><body>
<a href="acme_spec_kitty_cli-1.9.0-py3-none-any.whl">1.9.0</a>
<a href="acme_spec_kitty_cli-2.0.0rc1-py3-none-any.whl">2.0.0rc1</a>
</body></html>
"""

_HTML_ALL_PRERELEASE = """
<html><body>
<a href="acme_spec_kitty_cli-2.0.0rc1-py3-none-any.whl">2.0.0rc1</a>
<a href="acme_spec_kitty_cli-2.0.0rc2-py3-none-any.whl">2.0.0rc2</a>
</body></html>
"""

_HTML_WITH_YANKED = """
<html><body>
<a href="acme_spec_kitty_cli-1.9.0-py3-none-any.whl">1.9.0</a>
<a href="acme_spec_kitty_cli-2.5.0-py3-none-any.whl" data-yanked="broken build">2.5.0</a>
</body></html>
"""


def _latest_for(monkeypatch: pytest.MonkeyPatch, html: str) -> str | None:
    client = _FakeClient(_FakeResponse(html.encode("utf-8")))
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: client)
    return (
        SimpleIndexProvider(
            "https://example.invalid/simple/",
            package_prefix="acme_spec_kitty_cli",
        )
        .get_latest("acme-spec-kitty-cli")
        .version
    )


def test_prerelease_is_not_selected_over_stable(monkeypatch: pytest.MonkeyPatch) -> None:
    # 2.0.0rc1 > 1.9.0 numerically, but a stable release must win.
    assert _latest_for(monkeypatch, _HTML_WITH_PRERELEASE) == "1.9.0"


def test_falls_back_to_prerelease_when_no_stable(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _latest_for(monkeypatch, _HTML_ALL_PRERELEASE) == "2.0.0rc2"


def test_yanked_release_is_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    # 2.5.0 is the numeric max but is yanked (PEP 592) → 1.9.0 wins.
    assert _latest_for(monkeypatch, _HTML_WITH_YANKED) == "1.9.0"
