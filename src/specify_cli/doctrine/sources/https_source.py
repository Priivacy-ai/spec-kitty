"""HTTPS-bundle backed org doctrine source.

``HttpsBundleSource`` downloads a tar.gz or zip archive over HTTPS, extracts
it into ``target_dir`` and returns a :class:`FetchResult`.  Atomic-write
semantics are layered on by :func:`specify_cli.doctrine.snapshot.write_snapshot`.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import tarfile
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import requests

from .protocol import FetchResult

MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_EXTRACTED_BYTES = 512 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 10_000
_ARTIFACTORY_PATH_MARKER = "/artifactory/"


class ArchiveSizeLimitError(Exception):
    """Raised when a fetched archive exceeds doctrine source safety limits."""


@dataclass(frozen=True)
class _ArtifactoryMetadata:
    """Version provenance bound to one immutable archive body."""

    version: str
    sha256: str


@dataclass(frozen=True)
class _BufferedArchive:
    """Temporary archive plus its exact downloaded-body checksum."""

    path: Path
    sha256: str


@dataclass
class HttpsBundleSource:
    """Source that fetches a packed doctrine archive over HTTPS.

    Args:
        url: Direct download URL for the archive.
        ref: Optional version pin used to populate ``pack_version`` when the
            server does not return an ``ETag`` header.
        if_none_match: Optional ETag from a previous fetch.  Sent as
            ``If-None-Match`` so an unchanged remote returns HTTP 304 and
            skips the download body.
    """

    url: str
    ref: str | None = None
    if_none_match: str | None = None
    source_type: str = "https"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def fetch(self, target_dir: Path) -> FetchResult:
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        storage_url: str | None = None
        if self.source_type == "artifactory":
            storage_url = _artifactory_storage_url(self.url)
            if storage_url is None:
                return FetchResult(
                    ok=False,
                    artifacts_written=0,
                    pack_version=None,
                    errors=[
                        "Artifactory source requires a valid Artifactory item URL "
                        "containing /artifactory/<repo>/<item>."
                    ],
                )

        try:
            response = self._get_with_retry()
        except requests.RequestException as exc:
            return FetchResult(
                ok=False,
                artifacts_written=0,
                pack_version=None,
                errors=[
                    f"Network error fetching {_safe_url_for_error(self.url)}: "
                    f"{type(exc).__name__}"
                ],
            )

        try:
            return self._consume_response(response, target_dir, storage_url)
        finally:
            response.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        custom_header = os.environ.get("SPEC_KITTY_ORG_AUTH_HEADER")
        if custom_header:
            headers["Authorization"] = custom_header
        else:
            token = os.environ.get("SPEC_KITTY_ORG_TOKEN")
            if token:
                headers["Authorization"] = f"Bearer {token}"
        if self.if_none_match:
            headers["If-None-Match"] = self.if_none_match
        return headers

    def _consume_response(
        self,
        response: requests.Response,
        target_dir: Path,
        storage_url: str | None,
    ) -> FetchResult:
        """Validate, buffer, provenance-check, then extract one response."""
        if response.status_code == 304:
            if not self.if_none_match:
                return FetchResult(
                    ok=False,
                    artifacts_written=0,
                    pack_version=None,
                    errors=[
                        "Remote returned HTTP 304 without an If-None-Match validator."
                    ],
                )
            return FetchResult(
                ok=True,
                artifacts_written=0,
                pack_version=self.ref,
                unchanged=True,
                etag=self.if_none_match,
            )

        if response.status_code in (401, 403):
            return FetchResult(
                ok=False,
                artifacts_written=0,
                pack_version=None,
                errors=[
                    "Authentication failed. Set SPEC_KITTY_ORG_TOKEN to a"
                    " valid bearer token for the doctrine bundle endpoint."
                ],
            )
        if response.status_code >= 400:
            return FetchResult(
                ok=False,
                artifacts_written=0,
                pack_version=None,
                errors=[
                    f"HTTP {response.status_code} fetching "
                    f"{_safe_url_for_error(self.url)}."
                ],
            )

        archive_kind = self._detect_archive(response)
        if archive_kind is None:
            return FetchResult(
                ok=False,
                artifacts_written=0,
                pack_version=None,
                errors=[
                    "Could not determine archive format from Content-Type "
                    f"({response.headers.get('Content-Type', '<missing>')}) "
                    "or URL suffix."
                ],
            )

        buffered, buffer_error = self._buffer_archive(response, archive_kind)
        if buffer_error is not None:
            return FetchResult(
                ok=False,
                artifacts_written=0,
                pack_version=None,
                errors=[buffer_error],
            )
        assert buffered is not None

        metadata: _ArtifactoryMetadata | None = None
        if storage_url is not None:
            metadata, metadata_error = self._fetch_artifactory_metadata(storage_url)
            if metadata_error is not None:
                buffered.path.unlink(missing_ok=True)
                return FetchResult(
                    ok=False,
                    artifacts_written=0,
                    pack_version=None,
                    errors=[metadata_error],
                )
            assert metadata is not None
            if not hmac.compare_digest(metadata.sha256, buffered.sha256):
                buffered.path.unlink(missing_ok=True)
                return FetchResult(
                    ok=False,
                    artifacts_written=0,
                    pack_version=None,
                    errors=[
                        "JFrog metadata checksum does not match the downloaded "
                        "archive; the mutable artifact changed during fetch."
                    ],
                )

        try:
            extracted = self._extract(buffered.path, target_dir, archive_kind)
        except (
            ArchiveSizeLimitError,
            tarfile.TarError,
            zipfile.BadZipFile,
            OSError,
        ) as exc:
            return FetchResult(
                ok=False,
                artifacts_written=0,
                pack_version=None,
                errors=[f"Archive extraction failed: {exc}"],
            )
        finally:
            buffered.path.unlink(missing_ok=True)

        return FetchResult(
            ok=True,
            artifacts_written=extracted,
            pack_version=metadata.version if metadata is not None else self.ref,
            etag=response.headers.get("ETag"),
        )

    @staticmethod
    def _buffer_archive(
        response: requests.Response, archive_kind: str
    ) -> tuple[_BufferedArchive | None, str | None]:
        """Stream one bounded response body to disk and hash those exact bytes."""
        tmp_path: Path | None = None
        digest = hashlib.sha256()  # noqa: TID251 - downloaded-body integrity checksum
        try:
            content_length = _parse_content_length(response.headers.get("Content-Length"))
            if content_length is not None and content_length > MAX_ARCHIVE_BYTES:
                raise ArchiveSizeLimitError(
                    f"Archive exceeds raw byte limit: {content_length} > {MAX_ARCHIVE_BYTES}"
                )
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=f".{archive_kind}"
            ) as tmp:
                tmp_path = Path(tmp.name)
                total = 0
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > MAX_ARCHIVE_BYTES:
                        raise ArchiveSizeLimitError(
                            f"Archive exceeds raw byte limit: {total} > {MAX_ARCHIVE_BYTES}"
                        )
                    digest.update(chunk)
                    tmp.write(chunk)
        except (ArchiveSizeLimitError, OSError, requests.RequestException) as exc:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)
            detail = (
                str(exc)
                if not isinstance(exc, requests.RequestException)
                else type(exc).__name__
            )
            return None, f"Failed to buffer archive: {detail}"
        assert tmp_path is not None
        return _BufferedArchive(path=tmp_path, sha256=digest.hexdigest()), None

    def _fetch_artifactory_metadata(
        self, storage_url: str
    ) -> tuple[_ArtifactoryMetadata | None, str | None]:
        """Read the two real JFrog Storage API metadata representations.

        A filtered ``?properties=version`` request returns ``ItemProperties``
        without checksums. The unfiltered item request returns ``FileInfo``
        with checksums. Query both after the archive body, property first and
        checksum second, so a mutable ``latest`` item fails closed if its body
        changes while provenance is being resolved.
        """
        version_payload, version_error = self._get_artifactory_json(
            storage_url,
            params={"properties": "version"},
            label="version property",
        )
        if version_error is not None:
            return None, version_error
        version = _extract_jfrog_version(version_payload)
        if version is None:
            return None, (
                "JFrog artifact has no non-empty version property: "
                f"{_safe_url_for_error(self.url)}"
            )

        file_payload, file_error = self._get_artifactory_json(
            storage_url,
            params=None,
            label="file checksum",
        )
        if file_error is not None:
            return None, file_error
        checksum = _extract_jfrog_sha256(file_payload)
        if checksum is None:
            return None, (
                "JFrog artifact has no valid SHA-256 checksum: "
                f"{_safe_url_for_error(self.url)}"
            )
        return _ArtifactoryMetadata(version=version, sha256=checksum), None

    def _get_artifactory_json(
        self,
        storage_url: str,
        *,
        params: dict[str, str] | None,
        label: str,
    ) -> tuple[object | None, str | None]:
        """Fetch, decode, and close one JFrog Storage API representation."""
        try:
            response = self._get_artifactory_metadata_with_retry(
                storage_url, params=params
            )
        except requests.RequestException as exc:
            return None, f"Failed to read JFrog {label}: {type(exc).__name__}"
        try:
            if response.status_code >= 400:
                return None, (
                    f"Failed to read JFrog {label}: HTTP {response.status_code}"
                )
            try:
                return response.json(), None
            except (ValueError, TypeError):
                return None, f"Failed to read JFrog {label}: invalid JSON response"
        finally:
            response.close()

    def _get_artifactory_metadata_with_retry(
        self, storage_url: str, *, params: dict[str, str] | None
    ) -> requests.Response:
        headers = _without_conditional_header(self._headers())
        kwargs: dict[str, Any] = {"headers": headers, "timeout": 30}
        if params is not None:
            kwargs["params"] = params
        response = requests.get(  # noqa: S113 - timeout supplied below
            storage_url, **kwargs
        )
        if response.status_code == 429 or 500 <= response.status_code < 600:
            delay = 2.0 if response.status_code >= 500 else 1.0
            response.close()
            time.sleep(delay)
            response = requests.get(  # noqa: S113 - timeout supplied in kwargs
                storage_url,
                **kwargs,
            )
        return response

    def _get_with_retry(self) -> requests.Response:
        response = requests.get(  # noqa: S113 - timeout supplied below
            self.url,
            headers=self._headers(),
            stream=True,
            timeout=30,
        )
        if 500 <= response.status_code < 600:
            response.close()
            time.sleep(2.0)
            response = requests.get(
                self.url,
                headers=self._headers(),
                stream=True,
                timeout=30,
            )
        elif response.status_code == 429:
            retry_after = _parse_retry_after(response.headers.get("Retry-After"))
            response.close()
            time.sleep(retry_after)
            response = requests.get(
                self.url,
                headers=self._headers(),
                stream=True,
                timeout=30,
            )
        return response

    @staticmethod
    def _detect_archive(response: requests.Response) -> str | None:
        content_type = (response.headers.get("Content-Type") or "").lower()
        if "gzip" in content_type or "x-tar" in content_type:
            return "tar.gz"
        if "zip" in content_type:
            return "zip"
        url = response.url.lower()
        if url.endswith(".tar.gz") or url.endswith(".tgz"):
            return "tar.gz"
        if url.endswith(".zip"):
            return "zip"
        return None

    @staticmethod
    def _extract(archive_path: Path, target_dir: Path, kind: str) -> int:
        if kind == "tar.gz":
            with tarfile.open(archive_path, "r:gz") as tf:
                _safe_extract_tar(tf, target_dir)
        else:  # zip
            with zipfile.ZipFile(archive_path) as zf:
                _safe_extract_zip(zf, target_dir)

        _flatten_single_top_dir(target_dir)
        return sum(1 for _ in target_dir.rglob("*.yaml"))


def _artifactory_storage_url(artifact_url: str) -> str | None:
    """Translate an Artifactory download URL to its Storage API item URL."""
    parsed = urlsplit(artifact_url)
    if parsed.scheme != "https" or not parsed.hostname:
        return None
    if _ARTIFACTORY_PATH_MARKER not in parsed.path:
        return None
    prefix, item_path = parsed.path.split(_ARTIFACTORY_PATH_MARKER, maxsplit=1)
    repository, separator, artifact_path = item_path.partition("/")
    if not separator or not repository or not artifact_path:
        return None
    storage_path = (
        f"{prefix}{_ARTIFACTORY_PATH_MARKER}api/storage/{item_path}"
    )
    return urlunsplit((parsed.scheme, _safe_netloc(parsed), storage_path, "", ""))


def _without_conditional_header(headers: dict[str, str]) -> dict[str, str]:
    """Return request headers without an artifact-body conditional."""
    return {
        name: value
        for name, value in headers.items()
        if name.lower() != "if-none-match"
    }


def _safe_url_for_error(url: str) -> str:
    """Return an archive URL safe to include in operator-visible errors."""
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, _safe_netloc(parsed), parsed.path, "", ""))


def _safe_netloc(parsed: Any) -> str:
    """Rebuild a URL authority without embedded credentials."""
    hostname = parsed.hostname or ""
    if ":" in hostname:
        hostname = f"[{hostname}]"
    try:
        port = parsed.port
    except ValueError:
        port = None
    return f"{hostname}:{port}" if port is not None else hostname


def _extract_jfrog_version(payload: object) -> str | None:
    """Return the first non-empty value from ``properties.version``."""
    if not isinstance(payload, dict):
        return None
    properties = payload.get("properties")
    if not isinstance(properties, dict):
        return None
    versions = properties.get("version")
    if not isinstance(versions, list):
        return None
    for value in versions:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_jfrog_sha256(payload: object) -> str | None:
    """Return a normalized SHA-256 from JFrog Storage API metadata."""
    if not isinstance(payload, dict):
        return None
    checksums = payload.get("checksums")
    if not isinstance(checksums, dict):
        return None
    checksum = checksums.get("sha256")
    if not isinstance(checksum, str):
        return None
    normalized = checksum.strip().lower()
    return normalized if re.fullmatch(r"[0-9a-f]{64}", normalized) else None


def _parse_retry_after(value: Any) -> float:
    if value is None:
        return 2.0
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return 2.0


def _parse_content_length(value: Any) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _safe_extract_tar(tf: tarfile.TarFile, target_dir: Path) -> None:
    """Extract *tf* into *target_dir* with defence against common tar attacks.

    Checks performed before any bytes reach disk:

    1. **Path traversal / zip-slip** — uses ``Path.relative_to`` so that a
       sibling-prefix name (``/tmp/target-evil/x`` when base is
       ``/tmp/target``) is correctly rejected (the old ``startswith`` check
       was vulnerable to this bypass, P1 fix 2026-05).
    2. **Symlinks and hardlinks** — refused unconditionally; a malicious tar
       can create ``etc -> /etc`` then write ``etc/passwd`` through it.
    3. **Non-regular, non-directory entries** — character/block devices,
       FIFOs and other special files are refused.
    """
    base = target_dir.resolve()
    members = tf.getmembers()
    if len(members) > MAX_ARCHIVE_MEMBERS:
        raise ArchiveSizeLimitError(
            f"Archive exceeds member count limit: {len(members)} > {MAX_ARCHIVE_MEMBERS}"
        )
    extracted_bytes = 0
    for member in members:
        # --- type guard (before path check) ---
        if member.issym() or member.islnk():
            raise tarfile.TarError(
                f"Refusing symlink/hardlink entry: {member.name}"
            )
        if not member.isfile() and not member.isdir():
            raise tarfile.TarError(
                f"Refusing non-file/non-dir entry: {member.name} "
                f"(type={member.type!r})"
            )
        if member.isfile():
            extracted_bytes += member.size
            if extracted_bytes > MAX_EXTRACTED_BYTES:
                raise ArchiveSizeLimitError(
                    "Archive exceeds extracted byte limit: "
                    f"{extracted_bytes} > {MAX_EXTRACTED_BYTES}"
                )
        # --- path traversal guard (use relative_to, not startswith) ---
        member_path = (target_dir / member.name).resolve()
        try:
            member_path.relative_to(base)
        except ValueError as exc:
            raise tarfile.TarError(
                f"Refusing path traversal entry: {member.name}"
            ) from exc
    tf.extractall(target_dir)  # noqa: S202  # nosec B202 - paths and types validated above


def _safe_extract_zip(zf: zipfile.ZipFile, target_dir: Path) -> None:
    """Extract *zf* into *target_dir* with defence against path traversal.

    Uses ``Path.relative_to`` instead of the old ``str.startswith`` check
    which was vulnerable to the sibling-prefix bypass (P1 fix 2026-05).
    """
    base = target_dir.resolve()
    members = zf.infolist()
    if len(members) > MAX_ARCHIVE_MEMBERS:
        raise ArchiveSizeLimitError(
            f"Archive exceeds member count limit: {len(members)} > {MAX_ARCHIVE_MEMBERS}"
        )
    extracted_bytes = 0
    for info in members:
        name = info.filename
        if not info.is_dir():
            extracted_bytes += info.file_size
            if extracted_bytes > MAX_EXTRACTED_BYTES:
                raise ArchiveSizeLimitError(
                    "Archive exceeds extracted byte limit: "
                    f"{extracted_bytes} > {MAX_EXTRACTED_BYTES}"
                )
        member_path = (target_dir / name).resolve()
        try:
            member_path.relative_to(base)
        except ValueError as exc:
            raise zipfile.BadZipFile(
                f"Refusing path traversal entry: {name}"
            ) from exc
    zf.extractall(target_dir)  # noqa: S202  # nosec B202 - paths validated above


def _flatten_single_top_dir(target_dir: Path) -> None:
    """If the archive nested everything under a single top-level dir, hoist it.

    Many bundles produce ``my-pack-v1.2.0/<contents>``.  Operators expect the
    extracted ``target_dir`` to *be* the pack root, so we lift the contents
    one level when there is exactly one child directory and no sibling files.
    """
    entries = list(target_dir.iterdir())
    if len(entries) != 1 or not entries[0].is_dir():
        return
    inner = entries[0]
    for child in list(inner.iterdir()):
        child.rename(target_dir / child.name)
    inner.rmdir()
