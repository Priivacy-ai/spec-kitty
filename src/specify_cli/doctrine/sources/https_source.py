"""HTTPS-bundle backed org doctrine source.

``HttpsBundleSource`` downloads a tar.gz or zip archive over HTTPS, extracts
it into ``target_dir`` and returns a :class:`FetchResult`.  Atomic-write
semantics are layered on by :func:`specify_cli.doctrine.snapshot.write_snapshot`.
"""

from __future__ import annotations

import os
import tarfile
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from .protocol import FetchResult


@dataclass
class HttpsBundleSource:
    """Source that fetches a packed doctrine archive over HTTPS.

    Args:
        url: Direct download URL for the archive.
        ref: Optional version pin used to populate ``pack_version`` when the
            server does not return an ``ETag`` header.
    """

    url: str
    ref: str | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def fetch(self, target_dir: Path) -> FetchResult:
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        try:
            response = self._get_with_retry()
        except requests.RequestException as exc:
            return FetchResult(
                ok=False,
                artifacts_written=0,
                pack_version=None,
                errors=[f"Network error fetching {self.url}: {exc}"],
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
                    f"HTTP {response.status_code} fetching {self.url}: "
                    f"{response.reason}"
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

        try:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=f".{archive_kind}"
            ) as tmp:
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        tmp.write(chunk)
                tmp_path = Path(tmp.name)
        except OSError as exc:
            return FetchResult(
                ok=False,
                artifacts_written=0,
                pack_version=None,
                errors=[f"Failed to buffer archive: {exc}"],
            )

        try:
            extracted = self._extract(tmp_path, target_dir, archive_kind)
        except (tarfile.TarError, zipfile.BadZipFile, OSError) as exc:
            return FetchResult(
                ok=False,
                artifacts_written=0,
                pack_version=None,
                errors=[f"Archive extraction failed: {exc}"],
            )
        finally:
            tmp_path.unlink(missing_ok=True)

        pack_version = self.ref or response.headers.get("ETag")
        return FetchResult(
            ok=True,
            artifacts_written=extracted,
            pack_version=pack_version,
            errors=[],
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        custom_header = os.environ.get("SPEC_KITTY_ORG_AUTH_HEADER")
        if custom_header:
            return {"Authorization": custom_header}
        token = os.environ.get("SPEC_KITTY_ORG_TOKEN")
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    def _get_with_retry(self) -> requests.Response:
        response = requests.get(  # noqa: S113 - timeout supplied below
            self.url,
            headers=self._headers(),
            stream=True,
            timeout=30,
        )
        if 500 <= response.status_code < 600:
            time.sleep(2.0)
            response = requests.get(
                self.url,
                headers=self._headers(),
                stream=True,
                timeout=30,
            )
        elif response.status_code == 429:
            retry_after = _parse_retry_after(response.headers.get("Retry-After"))
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


def _parse_retry_after(value: Any) -> float:
    if value is None:
        return 2.0
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return 2.0


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
    for member in tf.getmembers():
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
    for name in zf.namelist():
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
