"""Freshness computation for charter / synced bundle / synthesized DRG.

Detection rules (per ``contracts/charter-status-json.md``):

* ``charter_source.state = "stale"`` when ``.kittify/charter/charter.md``
  SHA-256 differs from the hash stored in ``.kittify/charter/metadata.yaml``.
* ``synced_bundle.state = "stale"`` when any bundle file mtime is older than
  ``charter_source.last_change``.
* ``synthesized_drg.state = "stale"`` when the synthesis manifest's
  ``run_id`` references inputs whose mtime is older than
  ``synced_bundle.last_change`` (proxy: the synthesis manifest's
  ``created_at`` is older than the latest bundle mtime).
* ``synthesized_drg.state = "missing"`` when ``.kittify/doctrine/graph.yaml``
  is absent AND the manifest does not declare ``built_in_only: true``.
* ``synthesized_drg.state = "built_in_only"`` when the manifest declares
  ``built_in_only: true`` (FR-009).
* ``synthesized_drg.state = "invalid"`` when the manifest declares
  ``built_in_only: true`` AND ``.kittify/doctrine/graph.yaml`` ALSO exists
  (architect conflict-resolution per data-model.md §6).

All sub-objects are always present in the result; ``state="missing"`` is the
default when a file is absent.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from ruamel.yaml import YAML

__all__ = [
    "CharterFreshness",
    "FreshnessSubState",
    "compute_freshness",
]


FreshnessState = Literal["fresh", "stale", "missing", "built_in_only", "invalid"]


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FreshnessSubState:
    """One freshness sub-object on the ``charter status --json`` payload.

    Fields:
        state: One of ``fresh``, ``stale``, ``missing``, ``built_in_only``,
            ``invalid``.  Matches ``contracts/charter-status-json.md``.
        last_change: ISO 8601 timestamp of the most recent change to the
            tracked asset (None when missing or unknown).
        remediation: Operator-facing hint (e.g. ``spec-kitty charter sync``)
            or None when no action is required.
        detail: Optional human-readable explanation surfaced for ``invalid``
            states so operators understand why an artifact is broken.
    """

    state: FreshnessState
    last_change: str | None
    remediation: str | None
    detail: str | None = None


@dataclass(frozen=True)
class CharterFreshness:
    """The full freshness sub-payload for ``charter status --json``.

    Each field is a ``FreshnessSubState`` representing one layer of the
    charter -> bundle -> synthesized DRG pipeline.
    """

    charter_source: FreshnessSubState
    synced_bundle: FreshnessSubState
    synthesized_drg: FreshnessSubState

    def to_dict(self) -> dict[str, dict[str, str | None]]:
        """Return a JSON-ready nested dict matching the contract shape."""
        return {
            "charter_source": asdict(self.charter_source),
            "synced_bundle": asdict(self.synced_bundle),
            "synthesized_drg": asdict(self.synthesized_drg),
        }


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------


_CHARTER_DIR = Path(".kittify") / "charter"
_DOCTRINE_DIR = Path(".kittify") / "doctrine"
_CHARTER_FILENAME = "charter.md"
_METADATA_FILENAME = "metadata.yaml"
_SYNTHESIS_MANIFEST = _CHARTER_DIR / "synthesis-manifest.yaml"
_GRAPH_FILENAME = "graph.yaml"
_BUNDLE_FILES = ("governance.yaml", "directives.yaml", "references.yaml", _METADATA_FILENAME)


def _safe_load_yaml(path: Path) -> dict[str, object] | None:
    """Load a YAML file as a dict; return None when missing or unreadable."""
    if not path.exists():
        return None
    try:
        yaml = YAML(typ="safe")
        data = yaml.load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001 — YAML parse failures are non-fatal here
        return None
    if isinstance(data, dict):
        return data
    return None


def _sha256_of(path: Path) -> str | None:
    """Return SHA-256 hex digest of a file, or None when missing."""
    if not path.exists():
        return None
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _mtime_iso(path: Path) -> str | None:
    """Return ISO 8601 UTC mtime of a file, or None when missing."""
    if not path.exists():
        return None
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()
    except OSError:
        return None


def _latest_mtime(paths: list[Path]) -> str | None:
    """Return ISO 8601 UTC of the latest mtime across ``paths``."""
    stamps: list[float] = []
    for p in paths:
        if p.exists():
            try:
                stamps.append(p.stat().st_mtime)
            except OSError:
                continue
    if not stamps:
        return None
    return datetime.fromtimestamp(max(stamps), tz=UTC).isoformat()


def _oldest_mtime(paths: list[Path]) -> float | None:
    stamps: list[float] = []
    for p in paths:
        if p.exists():
            try:
                stamps.append(p.stat().st_mtime)
            except OSError:
                continue
    if not stamps:
        return None
    return min(stamps)


# ---------------------------------------------------------------------------
# Sub-state computers
# ---------------------------------------------------------------------------


def _compute_charter_source(repo_root: Path) -> FreshnessSubState:
    charter_path = repo_root / _CHARTER_DIR / _CHARTER_FILENAME
    metadata_path = repo_root / _CHARTER_DIR / _METADATA_FILENAME

    if not charter_path.exists():
        return FreshnessSubState(
            state="missing",
            last_change=None,
            remediation="spec-kitty charter sync",
        )

    current_hash = _sha256_of(charter_path)
    last_change = _mtime_iso(charter_path)

    metadata = _safe_load_yaml(metadata_path)
    stored_hash_raw = ""
    if isinstance(metadata, dict):
        stored = metadata.get("charter_hash", "")
        if isinstance(stored, str):
            stored_hash_raw = stored

    # Bundle hasher stores values prefixed with ``sha256:``.  Normalise both
    # sides so a comparison is meaningful regardless of prefix.
    def _normalize(h: str) -> str:
        if h.startswith("sha256:"):
            return h.split(":", 1)[1]
        return h

    if not stored_hash_raw:
        # No metadata recorded yet → bundle was never synced.
        return FreshnessSubState(
            state="stale",
            last_change=last_change,
            remediation="spec-kitty charter sync",
        )

    if current_hash is None:
        return FreshnessSubState(
            state="invalid",
            last_change=last_change,
            remediation="spec-kitty charter sync",
            detail="charter.md exists but cannot be hashed",
        )

    if _normalize(stored_hash_raw) != current_hash:
        return FreshnessSubState(
            state="stale",
            last_change=last_change,
            remediation="spec-kitty charter sync",
        )

    return FreshnessSubState(state="fresh", last_change=last_change, remediation=None)


def _compute_synced_bundle(
    repo_root: Path,
    charter_source: FreshnessSubState,
) -> FreshnessSubState:
    bundle_paths = [repo_root / _CHARTER_DIR / name for name in _BUNDLE_FILES]
    existing = [p for p in bundle_paths if p.exists()]
    if not existing:
        return FreshnessSubState(
            state="missing",
            last_change=None,
            remediation="spec-kitty charter sync",
        )

    last_change = _latest_mtime(existing)

    # If charter_source itself is missing/invalid we cannot compare relative
    # mtimes — surface the bundle as fresh-ish (its files exist) but signal
    # "stale" when the upstream charter is stale so the operator runs sync.
    if charter_source.state in ("missing", "stale", "invalid"):
        return FreshnessSubState(
            state="stale",
            last_change=last_change,
            remediation="spec-kitty charter sync",
        )

    # charter_source is fresh → require every bundle file's mtime to be at
    # least as recent as charter_source.last_change.
    charter_last = charter_source.last_change
    if charter_last is None:
        return FreshnessSubState(state="fresh", last_change=last_change, remediation=None)

    oldest_bundle = _oldest_mtime(existing)
    try:
        charter_ts = datetime.fromisoformat(charter_last).timestamp()
    except ValueError:
        return FreshnessSubState(state="fresh", last_change=last_change, remediation=None)

    # Allow a tiny epsilon to tolerate single-call sync that writes charter
    # and metadata within the same second.
    if oldest_bundle is not None and oldest_bundle + 1.0 < charter_ts:
        return FreshnessSubState(
            state="stale",
            last_change=last_change,
            remediation="spec-kitty charter sync",
        )

    return FreshnessSubState(state="fresh", last_change=last_change, remediation=None)


def _compute_synthesized_drg(
    repo_root: Path,
    synced_bundle: FreshnessSubState,
) -> FreshnessSubState:
    manifest_path = repo_root / _SYNTHESIS_MANIFEST
    graph_path = repo_root / _DOCTRINE_DIR / _GRAPH_FILENAME
    manifest_data = _safe_load_yaml(manifest_path)

    built_in_only = False
    if isinstance(manifest_data, dict):
        flag = manifest_data.get("built_in_only", False)
        built_in_only = bool(flag)

    graph_exists = graph_path.exists()
    manifest_exists = manifest_data is not None

    # Conflict resolution (data-model §6): built_in_only=true AND graph.yaml
    # present is an inconsistent stale-residue state.
    if built_in_only and graph_exists:
        return FreshnessSubState(
            state="invalid",
            last_change=_mtime_iso(graph_path),
            remediation="spec-kitty charter synthesize --force-overwrite",
            detail=(
                "synthesis manifest declares built_in_only=true but "
                "graph.yaml exists; this is a stale artifact"
            ),
        )

    if built_in_only:
        # Authoritative built-in-only state (FR-009).
        return FreshnessSubState(
            state="built_in_only",
            last_change=_mtime_iso(manifest_path),
            remediation=None,
        )

    if not graph_exists:
        # No graph + manifest does not opt into built_in_only → missing.
        return FreshnessSubState(
            state="missing",
            last_change=None,
            remediation="spec-kitty charter synthesize",
        )

    # graph_exists is true → check staleness vs. synced_bundle.
    graph_mtime_iso = _mtime_iso(graph_path)

    if synced_bundle.state != "fresh" or synced_bundle.last_change is None:
        # If the bundle is not itself fresh we cannot prove the graph is
        # fresh either; mark it stale so the operator rebuilds upstream.
        return FreshnessSubState(
            state="stale",
            last_change=graph_mtime_iso,
            remediation="spec-kitty charter synthesize",
        )

    try:
        bundle_ts = datetime.fromisoformat(synced_bundle.last_change).timestamp()
    except ValueError:
        return FreshnessSubState(state="fresh", last_change=graph_mtime_iso, remediation=None)

    # Prefer the manifest's created_at when present (more precise than file
    # mtime); fall back to graph mtime.
    manifest_ts: float | None = None
    if isinstance(manifest_data, dict):
        created_at = manifest_data.get("created_at")
        if isinstance(created_at, str):
            try:
                manifest_ts = datetime.fromisoformat(created_at).timestamp()
            except ValueError:
                manifest_ts = None
    if manifest_ts is None and manifest_exists:
        manifest_ts = (repo_root / _SYNTHESIS_MANIFEST).stat().st_mtime
    if manifest_ts is None:
        try:
            manifest_ts = graph_path.stat().st_mtime
        except OSError:
            manifest_ts = None

    if manifest_ts is not None and manifest_ts + 1.0 < bundle_ts:
        return FreshnessSubState(
            state="stale",
            last_change=graph_mtime_iso,
            remediation="spec-kitty charter synthesize",
        )

    return FreshnessSubState(state="fresh", last_change=graph_mtime_iso, remediation=None)


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


def compute_freshness(repo_root: Path) -> CharterFreshness:
    """Compute the three freshness sub-states for ``repo_root``.

    The returned ``CharterFreshness`` always has all three sub-objects
    populated (per ``contracts/charter-status-json.md``).  Missing files
    surface as ``state="missing"`` rather than being elided from the payload.
    """
    charter_source = _compute_charter_source(repo_root)
    synced_bundle = _compute_synced_bundle(repo_root, charter_source)
    synthesized_drg = _compute_synthesized_drg(repo_root, synced_bundle)
    return CharterFreshness(
        charter_source=charter_source,
        synced_bundle=synced_bundle,
        synthesized_drg=synthesized_drg,
    )
