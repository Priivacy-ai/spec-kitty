"""PEP 503 HTML simple-index ``LatestVersionProvider``.

Upstream ships this helper so forks can subclass with a zero-arg ``__init__``
that sets their private index URL and optional distribution filename prefix.
Stock defaults never embed fork hostnames or private index URLs — callers must
pass ``index_url`` explicitly (typically from a subclass).

Security properties mirror :class:`~specify_cli.compat.provider.PyPIProvider`:

- TLS verification ON (httpx default, never disabled)
- Response body capped at 1 MiB
- Redirects not followed
- Version string regex-validated before return
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlparse

import httpx
from packaging.utils import InvalidWheelFilename, parse_wheel_filename
from packaging.version import InvalidVersion, Version

from specify_cli.compat.provider import (
    LatestVersionResult,
    _get_installed_version,
    _MAX_RESPONSE_BYTES,
    _VERSION_RE,
)

__all__ = [
    "SimpleIndexProvider",
]

_HREF_EXT_RE = re.compile(r"\.(?:whl|tar\.gz|zip|egg)$", re.IGNORECASE)
_PEP503_NORMALIZE_RE = re.compile(r"[-_.]+")


class _AnchorCollector(HTMLParser):
    """Collect ``(href, is_yanked)`` from ``<a>`` tags.

    PEP 592: an anchor carrying a ``data-yanked`` attribute (with any value,
    including empty) marks that file as yanked and it must be excluded from
    normal version selection.
    """

    def __init__(self) -> None:
        super().__init__()
        self.entries: list[tuple[str, bool]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href: str | None = None
        is_yanked = False
        for name, value in attrs:
            lowered = name.lower()
            if lowered == "href" and value:
                href = value
            elif lowered == "data-yanked":
                is_yanked = True  # presence alone = yanked (PEP 592)
        if href:
            self.entries.append((href, is_yanked))


class SimpleIndexProvider:
    """Fetch the latest version of a package from a PEP 503 simple index.

    Args:
        index_url: Base simple-index URL (e.g. ``https://pypi.org/simple/``).
            Required — upstream never defaults this to a private/fork host.
        package_prefix: Optional distribution filename prefix used to filter
            candidate artefacts (e.g. ``acme_spec_kitty_cli``). When omitted,
            all version-bearing links on the project page are considered.
        timeout_s: Seconds to wait before declaring a timeout (default 2.0).
    """

    def __init__(
        self,
        index_url: str,
        *,
        package_prefix: str | None = None,
        timeout_s: float = 2.0,
    ) -> None:
        if not index_url or not str(index_url).strip():
            raise ValueError("index_url is required and must be non-empty")
        self._index_url = str(index_url).rstrip("/") + "/"
        self._package_prefix = package_prefix
        self._timeout_s = timeout_s

    def get_latest(self, package: str) -> LatestVersionResult:
        """Query the simple index for *package* and return the highest version.

        Never raises. Failures return ``version=None, source="none"`` with a
        fixed-vocabulary error token.
        """
        installed_version = _get_installed_version()
        user_agent = f"spec-kitty-cli/{installed_version} compat-planner"
        url = _project_page_url(self._index_url, package)

        try:
            with httpx.Client(follow_redirects=False, timeout=self._timeout_s) as client:
                response = client.get(url, headers={"User-Agent": user_agent})
                raw = response.content
                if len(raw) > _MAX_RESPONSE_BYTES:
                    return LatestVersionResult(version=None, source="none", error="oversized")

                if response.is_error:
                    return LatestVersionResult(version=None, source="none", error="http_error")

                try:
                    html = raw.decode("utf-8", errors="replace")
                except Exception:
                    return LatestVersionResult(version=None, source="none", error="parse_error")

                versions = _versions_from_html(html, self._package_prefix)
                if not versions:
                    return LatestVersionResult(version=None, source="none", error="parse_error")

                best = _highest_version(versions)
                if best is None:
                    return LatestVersionResult(version=None, source="none", error="parse_error")

                return LatestVersionResult(version=best, source="simple_index", error=None)

        except httpx.TimeoutException:
            return LatestVersionResult(version=None, source="none", error="timeout")
        except httpx.HTTPError:
            return LatestVersionResult(version=None, source="none", error="http_error")
        except Exception:
            return LatestVersionResult(version=None, source="none", error="parse_error")


def _project_page_url(index_url: str, package: str) -> str:
    """Build the PEP 503 project page URL for *package* under *index_url*."""
    normalized = _PEP503_NORMALIZE_RE.sub("-", package).lower()
    return urljoin(index_url, f"{normalized}/")


def _versions_from_html(html: str, package_prefix: str | None) -> list[str]:
    """Extract sanitised version strings from simple-index HTML anchors."""
    collector = _AnchorCollector()
    try:
        collector.feed(html)
        collector.close()
    except Exception:
        # Fall back to a tolerant regex scan if the HTML parser chokes. The
        # regex cannot see ``data-yanked``, so treat these as not-yanked.
        collector.entries = [
            (href, False)
            for href in re.findall(r"""href=["']([^"']+)["']""", html, flags=re.I)
        ]

    versions: list[str] = []
    for href, is_yanked in collector.entries:
        if is_yanked:
            continue  # PEP 592: never select a yanked release
        version = _version_from_href(href, package_prefix)
        if version is not None:
            versions.append(version)
    return versions


def _version_from_href(href: str, package_prefix: str | None) -> str | None:
    path = unquote(urlparse(href.split("#", 1)[0]).path)
    filename = path.rsplit("/", 1)[-1]
    if not filename or not _HREF_EXT_RE.search(filename):
        return None

    if filename.lower().endswith(".whl"):
        wheel_version = _version_from_wheel(filename, package_prefix)
        if wheel_version is not None:
            return wheel_version

    stem = _HREF_EXT_RE.sub("", filename)
    if package_prefix:
        matched_prefix = _matching_prefix(stem, package_prefix)
        if matched_prefix is None:
            return None
        stem = stem[len(matched_prefix) + 1 :]

    return _parse_version_stem(stem)


def _matching_prefix(stem: str, package_prefix: str) -> str | None:
    prefixes = {
        package_prefix,
        package_prefix.replace("-", "_"),
        package_prefix.replace("_", "-"),
    }
    for prefix in prefixes:
        if stem.startswith(f"{prefix}-"):
            return prefix
    return None


def _version_from_wheel(filename: str, package_prefix: str | None) -> str | None:
    try:
        name, version, _build, _tags = parse_wheel_filename(filename)
    except InvalidWheelFilename:
        return None
    ver_str = str(version)
    if not _VERSION_RE.match(ver_str):
        return None
    if package_prefix is not None:
        prefixes = {
            package_prefix,
            package_prefix.replace("-", "_"),
            package_prefix.replace("_", "-"),
        }
        if name not in prefixes and str(name) not in prefixes:
            # packaging normalizes to PEP 503 form; also compare normalized.
            normalized_name = _PEP503_NORMALIZE_RE.sub("-", str(name)).lower()
            normalized_prefixes = {
                _PEP503_NORMALIZE_RE.sub("-", p).lower() for p in prefixes
            }
            if normalized_name not in normalized_prefixes:
                return None
    return ver_str


def _parse_version_stem(stem: str) -> str | None:
    """Return the longest leading hyphen-joined segment that is a valid version."""
    parts = stem.split("-")
    for length in range(len(parts), 0, -1):
        candidate = "-".join(parts[:length])
        if not _VERSION_RE.match(candidate):
            continue
        try:
            Version(candidate)
        except InvalidVersion:
            continue
        return candidate
    return None


def _highest_version(versions: list[str]) -> str | None:
    """Return the highest **stable** sanitised version string.

    Mirrors ``PyPIProvider`` (which reads PyPI's maintainer-designated stable
    ``info.version``): pre-releases are excluded so a private index publishing
    ``2.0.0rc1`` alongside ``1.9.0`` does not nag users onto a release
    candidate. Falls back to the highest pre-release only when **no** stable
    version exists on the index. Returns ``None`` if nothing parses.
    """
    best_stable_str: str | None = None
    best_stable_ver: Version | None = None
    best_any_str: str | None = None
    best_any_ver: Version | None = None
    for raw in versions:
        if not _VERSION_RE.match(raw):
            continue
        try:
            parsed = Version(raw)
        except InvalidVersion:
            continue
        if best_any_ver is None or parsed > best_any_ver:
            best_any_ver = parsed
            best_any_str = raw
        if not parsed.is_prerelease and (best_stable_ver is None or parsed > best_stable_ver):
            best_stable_ver = parsed
            best_stable_str = raw
    return best_stable_str if best_stable_str is not None else best_any_str
