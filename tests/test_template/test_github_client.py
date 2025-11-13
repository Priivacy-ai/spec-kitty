from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from specify_cli.template import github_client
from specify_cli.template.github_client import (
    GitHubClientError,
    download_and_extract_template,
    download_template_from_github,
)


class FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, object] | None = None, *, text: str = "", headers: dict[str, str] | None = None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text
        self.headers = headers or {"content-length": "0"}

    def json(self) -> dict[str, object]:
        return self._payload


class FakeStreamResponse:
    def __init__(self, status_code: int, chunks: list[bytes], headers: dict[str, str]):
        self.status_code = status_code
        self._chunks = chunks
        self.headers = headers
        self.text = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):  # noqa: D401
        return False

    def iter_bytes(self, chunk_size: int = 8192):
        for chunk in self._chunks:
            yield chunk


class FakeHttpClient:
    def __init__(self, release_payload: dict[str, object], chunks: list[bytes]):
        self.release_payload = release_payload
        self.chunks = chunks
        self.headers = {"content-length": str(sum(len(c) for c in chunks))}

    def get(self, url, **kwargs):  # noqa: D401
        return FakeResponse(200, self.release_payload, headers={"content-length": "0"})

    def stream(self, method, url, **kwargs):  # noqa: D401
        return FakeStreamResponse(200, self.chunks, self.headers)


def _make_release_payload(name: str) -> dict[str, object]:
    return {
        "tag_name": "v1.2.3",
        "assets": [
            {"name": name, "browser_download_url": "https://example.com/download", "size": 4},
        ],
    }


def test_download_template_from_github_writes_zip(tmp_path: Path):
    asset_name = "spec-kitty-template-test-sh-v1.zip"
    payload = _make_release_payload(asset_name)
    client = FakeHttpClient(payload, [b"AB", b"CD"])

    zip_path, meta = download_template_from_github(
        "spec-kitty",
        "spec-kitty",
        "test",
        tmp_path,
        script_type="sh",
        show_progress=False,
        verbose=False,
        client=client,
    )

    assert zip_path.exists()
    assert zip_path.read_bytes() == b"ABCD"
    assert meta["filename"] == asset_name
    assert meta["release"] == "v1.2.3"


def test_download_template_from_github_missing_asset(tmp_path: Path):
    payload = {
        "tag_name": "v1",
        "assets": [{"name": "other.zip", "browser_download_url": "https://example.com", "size": 1}],
    }
    client = FakeHttpClient(payload, [b"data"])

    with pytest.raises(GitHubClientError):
        download_template_from_github(
            "spec-kitty",
            "spec-kitty",
            "unknown",
            tmp_path,
            script_type="sh",
            verbose=False,
            show_progress=False,
            client=client,
        )


def test_download_and_extract_template_flattens_nested_archives(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    project_path = tmp_path / "project"
    zip_path = tmp_path / "archive.zip"
    nested_dir = tmp_path / "repo"
    nested_dir.mkdir()
    (nested_dir / "README.md").write_text("ok", encoding="utf-8")
    (nested_dir / "docs").mkdir()
    (nested_dir / "docs" / "intro.md").write_text("intro", encoding="utf-8")

    with zipfile.ZipFile(zip_path, "w") as zf:
        for path in nested_dir.rglob("*"):
            zf.write(path, arcname=str(Path("package") / path.relative_to(nested_dir)))

    def fake_download(*args, **kwargs):  # noqa: D401
        return zip_path, {"release": "v1", "size": zip_path.stat().st_size, "filename": zip_path.name}

    monkeypatch.setattr(github_client, "download_template_from_github", fake_download)

    download_and_extract_template(
        project_path,
        "claude",
        "sh",
        verbose=False,
        console=None,
    )

    assert (project_path / "README.md").exists()
    assert (project_path / "docs" / "intro.md").read_text(encoding="utf-8") == "intro"
    assert not zip_path.exists()
