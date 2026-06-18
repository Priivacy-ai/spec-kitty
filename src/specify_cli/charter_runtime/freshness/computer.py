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
  ``built_in_only: true`` (FR-009). When a project ``graph.yaml`` is ALSO
  present the manifest disowns it — it is *stale graph residue* (FR-006 /
  C2-f), not a contradiction: the reader still reports the authoritative
  ``built_in_only`` state and attaches a non-blocking residue diagnostic in
  ``detail`` (the formerly-terminal ``invalid`` state is unreachable for this
  condition, so preflight is no longer blocked).
* ``synthesized_drg`` never returns ``invalid`` — the only ``invalid`` producer
  is ``_compute_charter_source`` ("charter.md exists but cannot be hashed"),
  a genuine inconsistency that legitimately blocks preflight.

All sub-objects are always present in the result; ``state="missing"`` is the
default when a file is absent.

LD-3 routing (FR-013 / WP07): the synthesis manifest is loaded through the
``charter.synthesizer.manifest`` public read API (``load_yaml`` + the canonical
``MANIFEST_PATH`` constant); the doctrine graph path is anchored to
``charter.bundle.DOCTRINE_DIR``. This consumes the chokepoint module's
read-only surface without invoking ``ensure_charter_bundle_fresh``'s
refresh/write semantics — ``compute_freshness`` is a pure observer and must
never trigger a sync (NFR-001 perf, and would otherwise defeat the freshness
report it produces).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from charter.synthesizer.manifest import SynthesisManifest

from ruamel.yaml import YAML

# LD-3 chokepoint imports are kept LAZY (inside
# ``_load_synthesis_manifest_via_chokepoint``) to preserve NFR-003 latency.
# Eagerly importing ``charter.bundle`` / ``charter.synthesizer.manifest``
# at module-load time pulls in the full ``doctrine.service``,
# ``jsonschema``, and ``rfc3987_syntax`` graph (>500 ms) onto the
# ``spec-kitty next`` startup hot path. The architectural intent of LD-3
# (consume reads through the chokepoint API, not raw YAML loads) is
# preserved — only the *binding* is deferred.

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
_CHARTER_FILENAME = "charter.md"
_METADATA_FILENAME = "metadata.yaml"
_BUNDLE_FILES = ("governance.yaml", "directives.yaml", "references.yaml", _METADATA_FILENAME)


def _synthesis_manifest_path(repo_root: Path) -> Path:
    """Return the canonical synthesis manifest path via lazy chokepoint import."""
    from charter.synthesizer.manifest import MANIFEST_PATH  # noqa: PLC0415

    return repo_root / MANIFEST_PATH


def _doctrine_graph_path(repo_root: Path) -> Path:
    """Return the canonical doctrine graph path via lazy chokepoint imports.

    Both the doctrine dir and the graph filename are resolved lazily to keep
    this ``specify_cli`` module from eagerly importing the heavy
    ``charter.synthesizer`` package at load time (LD-3 discipline). The graph
    filename is single-sourced from the leaf ``charter.synthesizer._constants``.
    """
    from charter.bundle import DOCTRINE_DIR  # noqa: PLC0415
    from charter.synthesizer._constants import (  # noqa: PLC0415
        GRAPH_FILENAME as _GRAPH_FILENAME,
    )

    return repo_root / DOCTRINE_DIR / _GRAPH_FILENAME


def _doctrine_dir() -> Path:
    """Return the canonical project doctrine directory via lazy chokepoint import."""
    from charter.bundle import DOCTRINE_DIR  # noqa: PLC0415

    return DOCTRINE_DIR


def _safe_load_yaml(path: Path) -> dict[str, object] | None:
    """Load a YAML file as a dict; return None when missing or unreadable.

    Retained for ``metadata.yaml`` (the bundle metadata file, owned by
    ``charter.sync`` rather than the synthesizer manifest). LD-3 only routes
    the synthesis manifest and graph reads through the chokepoint; the bundle
    metadata read is a sibling concern still owned by this module's
    ``_compute_charter_source`` path.
    """
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


def _load_synthesis_manifest_via_chokepoint(repo_root: Path) -> SynthesisManifest | None:
    """Load the synthesis manifest through the chokepoint's read API.

    Routes through ``charter.synthesizer.manifest.load_yaml`` (the canonical
    typed reader) instead of an ad-hoc YAML parse. Returns ``None`` when the
    manifest is absent or fails validation — preserves the pre-WP07
    "missing/unreadable → None" fallback semantics that ``compute_freshness``
    depends on (a corrupt manifest must NOT raise out of a freshness
    computation; it must surface as a downstream state, not an exception).

    This is a read-only call: it does NOT invoke
    ``ensure_charter_bundle_fresh`` and therefore never triggers a refresh
    side-effect. ``compute_freshness`` is an observer; mutating the bundle
    from inside the observer would both break NFR-001 (preflight perf budget)
    and defeat the staleness report it produces.
    """
    manifest_path = _synthesis_manifest_path(repo_root)
    if not manifest_path.exists():
        return None
    # NFR-003: defer the chokepoint import until first call so module-import
    # of ``charter_freshness`` stays off the ``spec-kitty next`` hot path.
    from charter.synthesizer.manifest import load_yaml as _chokepoint_load_manifest  # noqa: PLC0415
    try:
        return _chokepoint_load_manifest(manifest_path)
    except Exception:  # noqa: BLE001 — manifest validation/parse errors are non-fatal here
        return None


def _charter_hash_of(path: Path) -> str | None:
    """Return the canonical charter-content hash hex digest, or None when missing."""
    if not path.exists():
        return None
    try:
        from charter.hasher import hash_content  # noqa: PLC0415

        hashed = hash_content(path.read_text(encoding="utf-8"))
        if hashed.startswith("sha256:"):
            return hashed.split(":", 1)[1]
        return hashed
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

    current_hash = _charter_hash_of(charter_path)
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

    # charter_source already proves the canonical charter hash matches
    # metadata.yaml.  Treat the bundle as fresh once required files exist;
    # mtimes can move independently when git checks out or restages identical
    # content, and must not make a synced bundle fail preflight.
    return FreshnessSubState(state="fresh", last_change=last_change, remediation=None)


def _compute_synthesized_drg(
    repo_root: Path,
    synced_bundle: FreshnessSubState,
) -> FreshnessSubState:
    # LD-3: synthesis manifest and graph reads are routed through the
    # chokepoint module's public surface (``charter.synthesizer.manifest``
    # for the typed manifest; ``charter.bundle.DOCTRINE_DIR`` for the graph
    # location). No direct ``_safe_load_yaml`` reads of either file from this
    # module — see module docstring for the FR-013 routing contract.
    manifest_path = _synthesis_manifest_path(repo_root)
    graph_path = _doctrine_graph_path(repo_root)
    manifest = _load_synthesis_manifest_via_chokepoint(repo_root)

    built_in_only = bool(manifest.built_in_only) if manifest is not None else False
    graph_exists = graph_path.exists()
    manifest_exists = manifest is not None

    legacy_fresh_seed = repo_root / _doctrine_dir() / "PROVENANCE.md"

    if built_in_only:
        # FR-006 (C2-f, structural): the synthesis manifest is the declared
        # authority over graph.yaml presence (#083). A graph.yaml the manifest
        # disowns is *residue*, not a contradiction — so the reader reports the
        # authoritative ``built_in_only`` state regardless of graph presence and,
        # when residue is present, attaches a NON-BLOCKING diagnostic. This is a
        # read-time normalization, NOT a reactive self-heal: the reader does not
        # run ``synthesize`` and emits no remediation for residue (C-003). The
        # blocking ``invalid`` branch for this specific condition is now
        # unreachable, so preflight (``built_in_only`` ∈ ``_PASS_STATES``) passes.
        if graph_exists:
            return FreshnessSubState(
                state="built_in_only",
                last_change=_mtime_iso(graph_path),
                remediation=None,
                detail=(
                    "stale graph residue: graph.yaml present but the synthesis "
                    "manifest declares built_in_only; the manifest is "
                    "authoritative, the residual graph.yaml is ignored"
                ),
            )
        # Authoritative built-in-only state (FR-009).
        return FreshnessSubState(
            state="built_in_only",
            last_change=_mtime_iso(manifest_path),
            remediation=None,
        )

    if not graph_exists:
        if _looks_like_legacy_fresh_seed(legacy_fresh_seed):
            return FreshnessSubState(
                state="built_in_only",
                last_change=_mtime_iso(legacy_fresh_seed),
                remediation=None,
                detail="legacy fresh-project seed marker; re-run `spec-kitty charter synthesize` to write synthesis-manifest.yaml",
            )
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
    if manifest is not None:
        created_at = manifest.created_at
        try:
            manifest_ts = datetime.fromisoformat(created_at).timestamp()
        except ValueError:
            manifest_ts = None
    if manifest_ts is None and manifest_exists:
        try:
            manifest_ts = manifest_path.stat().st_mtime
        except OSError:
            manifest_ts = None
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


def _looks_like_legacy_fresh_seed(path: Path) -> bool:
    """Return True for pre-manifest fresh-seed provenance files."""
    if not path.exists():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    lowered = text.lower()
    return (
        "fresh project seed" in lowered
        and "llm-authored yaml" in lowered
        and "built-in doctrine" in lowered
    )


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
