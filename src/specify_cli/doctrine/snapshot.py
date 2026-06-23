"""Atomic snapshot writer for non-git org doctrine sources.

The atomic-write pattern guarantees that ``local_path`` never observes a
partial snapshot:

1. Stage into ``<local_path>.parent/.tmp-<uuid>``.
2. Validate that the staged tree contains at least one recognised artifact
   subdirectory.
3. Replace ``local_path`` with the staged tree using a single rename.
4. Write ``pack-manifest.yaml`` describing the snapshot.

:class:`specify_cli.doctrine.sources.git_source.GitSource` deliberately
does NOT use this helper.  Git owns ``target_dir`` and provides its own
consistency story via ``fetch`` + ``reset --hard``.
"""

from __future__ import annotations

import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from .config import OrgPackConfig

import yaml

from .sources.protocol import FetchResult, OrgDoctrineSource

# ``OrgPackConfig`` is imported lazily inside helpers to avoid a circular import
# at module load time (config.py lives in the same package).


# Recognised artifact subdirectories per the pack-layout contract.
_RECOGNISED_ARTIFACT_DIRS: frozenset[str] = frozenset(
    {
        "directives",
        "tactics",
        "styleguides",
        "toolguides",
        "paradigms",
        "procedures",
        "agent_profiles",
        "mission_step_contracts",
        "drg",
    }
)

# Suffix → artifact-count bucket name for ``pack-manifest.yaml``.
_ARTIFACT_BUCKETS: dict[str, str] = {
    "directive.yaml": "directives",
    "tactic.yaml": "tactics",
    "styleguide.yaml": "styleguides",
    "toolguide.yaml": "toolguides",
    "paradigm.yaml": "paradigms",
    "procedure.yaml": "procedures",
    "agent.yaml": "agent_profiles",
    "contract.yaml": "mission_step_contracts",
    "graph.yaml": "drg_fragments",
}


def write_snapshot(
    source: OrgDoctrineSource,
    local_path: Path,
    *,
    source_url: str | None = None,
    source_type: str | None = None,
) -> FetchResult:
    """Fetch from ``source`` into a temp dir and atomically move into place.

    Args:
        source: Any object satisfying :class:`OrgDoctrineSource`.
        local_path: Destination directory.  Replaced atomically on success.
        source_url: Public URL recorded in ``pack-manifest.yaml`` (credentials
            stripped automatically).  Defaults to ``getattr(source, "url",
            None)``.
        source_type: Pack source classification (``git``, ``https``, ``api``);
            inferred from ``source`` class name when omitted.

    Returns:
        The :class:`FetchResult` produced by ``source.fetch`` (with extra
        validation errors appended if the staged tree is empty).
    """
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_dir = local_path.parent / f".tmp-{uuid4().hex}"

    try:
        result = source.fetch(tmp_dir)
    except Exception as exc:  # pragma: no cover - defensive
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return FetchResult(
            ok=False,
            artifacts_written=0,
            pack_version=None,
            errors=[f"Unexpected error during fetch: {exc}"],
        )

    if not result.ok:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return result

    if not _has_recognised_artifacts(tmp_dir):
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return FetchResult(
            ok=False,
            artifacts_written=result.artifacts_written,
            pack_version=result.pack_version,
            errors=[
                "No artifact directories found in fetched snapshot. Expected"
                " at least one of: "
                + ", ".join(sorted(_RECOGNISED_ARTIFACT_DIRS))
            ],
        )

    # Replace local_path by first moving the old snapshot aside. This avoids
    # the delete-then-move ENOENT window and preserves the old tree if promote
    # fails before the new snapshot is in place.
    old_dir: Path | None = None
    try:
        if local_path.exists():
            old_dir = local_path.parent / f".old-{local_path.name}-{uuid4().hex}"
            local_path.replace(old_dir)
        tmp_dir.replace(local_path)
    except OSError as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        if old_dir is not None and old_dir.exists() and not local_path.exists():
            old_dir.replace(local_path)
        return FetchResult(
            ok=False,
            artifacts_written=result.artifacts_written,
            pack_version=result.pack_version,
            errors=[f"Failed to replace snapshot: {exc}"],
        )
    finally:
        if old_dir is not None and old_dir.exists():
            shutil.rmtree(old_dir, ignore_errors=True)

    resolved_url = source_url if source_url is not None else getattr(source, "url", "")
    resolved_type = source_type or _infer_source_type(source)
    write_pack_manifest(
        local_path,
        result,
        source_url=resolved_url,
        source_type=resolved_type,
    )
    return result


def write_pack_manifest(
    local_path: Path,
    result: FetchResult,
    *,
    source_url: str,
    source_type: str,
) -> None:
    """Write ``pack-manifest.yaml`` to ``local_path``.

    The manifest is read-only metadata for tooling and humans.  Credentials in
    ``source_url`` are stripped before persistence.
    """
    local_path = Path(local_path)
    manifest_path = local_path / "pack-manifest.yaml"
    payload: dict[str, Any] = {
        "pack_version": result.pack_version,
        "fetched_at": _iso_now(),
        "source_type": source_type,
        "source_url": _strip_credentials(source_url),
        "artifact_counts": _count_artifacts(local_path),
    }
    manifest_path.write_text(
        yaml.safe_dump(payload, sort_keys=True), encoding="utf-8"
    )


# ----------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------
def _has_recognised_artifacts(snapshot_dir: Path) -> bool:
    if not snapshot_dir.exists():
        return False
    return any(
        entry.is_dir() and entry.name in _RECOGNISED_ARTIFACT_DIRS
        for entry in snapshot_dir.iterdir()
    )


def _count_artifacts(snapshot_dir: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not snapshot_dir.exists():
        return counts
    for entry in snapshot_dir.iterdir():
        if not entry.is_dir() or entry.name not in _RECOGNISED_ARTIFACT_DIRS:
            continue
        bucket = entry.name if entry.name != "drg" else "drg_fragments"
        counts[bucket] = sum(1 for _ in entry.rglob("*.yaml"))
    return counts


def _strip_credentials(url: str) -> str:
    """Remove ``user:pass@`` from an HTTPS URL before logging/persisting."""
    if not url:
        return ""
    return re.sub(r"^(https?://)[^/@]+@", r"\1", url)


def _infer_source_type(source: OrgDoctrineSource) -> str:
    cls_name = type(source).__name__.lower()
    if "git" in cls_name:
        return "git"
    if "https" in cls_name or "bundle" in cls_name:
        return "https"
    if "api" in cls_name:
        return "api"
    return "unknown"


def _iso_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ----------------------------------------------------------------------
# Pack-level fetch entry point (consumed by `spec-kitty doctrine fetch`).
# ----------------------------------------------------------------------
def _build_source(pack: OrgPackConfig) -> OrgDoctrineSource:
    """Construct the fetch-source adapter for *pack*.

    Raises:
        ValueError: When ``source_type`` is unset/unknown or required fields
            (``url``) are missing.
    """
    if pack.source_type is None:
        raise ValueError(
            f"Pack '{pack.name}' has no source_type configured; "
            "set doctrine.org.packs[].source_type to one of: git, https, api."
        )
    if not pack.url:
        raise ValueError(
            f"Pack '{pack.name}' has source_type={pack.source_type!r} "
            "but no url; set doctrine.org.packs[].url."
        )

    if pack.source_type == "git":
        from .sources.git_source import GitSource

        return GitSource(url=pack.url, ref=pack.ref)
    if pack.source_type == "https":
        from .sources.https_source import HttpsBundleSource

        return HttpsBundleSource(url=pack.url, ref=pack.ref)
    if pack.source_type == "api":
        from .sources.api_source import ApiSource

        return ApiSource(url=pack.url, ref=pack.ref)

    raise ValueError(
        f"Unknown source_type: {pack.source_type!r} for pack '{pack.name}'"
    )


def fetch_pack(pack: OrgPackConfig, repo_root: Path) -> FetchResult:
    """Fetch a single configured pack using its declared source type.

    Git sources manage their own working directory; all other sources go
    through :func:`write_snapshot` for atomic-replace semantics.

    ``repo_root`` is needed to compute :meth:`OrgPackConfig.effective_root`
    for post-fetch artifact counting (FR-007).  The clone target is always
    ``pack.local_path`` (C-003).
    """
    try:
        source = _build_source(pack)
    except ValueError as exc:
        return FetchResult(
            ok=False,
            artifacts_written=0,
            pack_version=None,
            errors=[str(exc)],
        )

    from .sources.git_source import GitSource

    if isinstance(source, GitSource):
        result = source.fetch(pack.local_path)
    else:
        result = write_snapshot(
            source,
            pack.local_path,
            source_url=pack.url or "",
            source_type=pack.source_type,
        )

    if result.ok:
        effective = pack.effective_root(repo_root)
        result = FetchResult(
            ok=result.ok,
            artifacts_written=sum(_count_artifacts(effective).values()),
            pack_version=result.pack_version,
            errors=result.errors,
        )
    return result
