"""Freshness computation for charter / synced bundle / synthesized DRG.

Detection rules (per ``contracts/charter-status-json.md``, re-pointed at
``charter.yaml`` by ``consolidate-charter-bundle`` WP06 / data-model.md
Landmine 2):

* ``charter_source.state`` reports whether the resolving charter source —
  ``.kittify/charter/charter.yaml`` — exists and parses: ``missing`` when
  absent, ``invalid`` when present but unparseable, ``fresh`` otherwise.
  Post-inversion ``charter.yaml`` (not ``charter.md``) is the authoritative,
  resolving source; ``charter.md`` is a curated, never-resolving prose
  companion (data-model.md Entity: ``charter.md``) and is not consulted
  here. The historical ``charter.md``-SHA-vs-``metadata.yaml::charter_hash``
  staleness mechanism is **retired outright, not re-homed** — a hash of
  ``charter.yaml`` cannot live *inside* ``charter.yaml`` (chicken-egg), so
  there is no meaningful upstream artifact left to compare against at this
  layer. ``charter_source`` therefore never returns ``stale``.
* ``synced_bundle.state = "missing"`` when ``charter.yaml`` (the sole entry
  in ``_BUNDLE_FILES`` / ``charter.bundle.BUNDLE_CONTENT_HASH_FILES``,
  contracts/manifest-v2.md M1/M3) is absent; ``"stale"`` when it exists but
  ``charter_source`` is not ``fresh`` (i.e. ``invalid``); ``"fresh"``
  otherwise.
* ``synthesized_drg.state = "stale"`` when the synthesis manifest's
  ``bundle_content_hash`` does not match a freshly recomputed content-identity
  hash of the current ``charter.yaml`` (``charter.bundle.
  compute_bundle_content_hash``) — a content comparison, not a timestamp
  comparison. A missing/``None`` stored hash is treated the same as a
  mismatch: ``stale``. Two distinct ``None`` causes with different
  recoveries: a *legacy-manifest* ``None`` (the field predates this fix)
  self-heals to ``fresh`` on the next ``spec-kitty charter synthesize`` /
  ``resynthesize`` run, which stamps the current hash; a *missing-file*
  ``None`` (``compute_bundle_content_hash`` returns ``None`` when
  ``charter.yaml`` itself is absent) does NOT self-heal via ``synthesize``
  alone until the file exists. This comparison only runs once
  ``synced_bundle.state == "fresh"`` (see the precedence rule below).

  **Spurious authoring-staleness (data-model.md Landmine 2 extension,
  alphonso MINOR-3 — DECIDED, option (b), see
  ``traces/decisions.md``)**: because the authored surface and the
  content-hash input are now the SAME file, an authoring-only edit to
  ``governance``/``directives``/``activation`` (which does not change the
  derived ``catalog``) also changes the whole-file hash and therefore trips
  this comparison to ``stale`` — even though nothing *derived* drifted.
  This is accepted as expected behaviour, not a defect: it is always
  healable by the very next ``spec-kitty charter synthesize`` /
  ``resynthesize`` (which recomputes the hash from current content and
  re-stamps the manifest), so it is a transient, self-clearing state, never
  a permanent-stale dead-end (unlike the retired #2758 missing-file trap).
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
  is ``_compute_charter_source`` ("charter.yaml exists but cannot be
  parsed"), a genuine inconsistency that legitimately blocks preflight.

Retired in this pass (#2759, data-model.md / contracts/manifest-v2.md):
the config<->references/graph activation-parity read
(``_activation_parity_drift_reason``) that used to run as a second signal
composed with the content-hash comparison above. It is moot once freshness
reads ``charter.yaml`` directly — activation now lives INSIDE the same file
the content hash already covers, so a config<->references/graph divergence
of the pre-relocation kind cannot exist anymore. (The #2758
``first_missing_bundle_file`` helper is a separate, still-live concern owned
by ``charter.bundle`` / ``specify_cli.cli.commands.charter._synthesis`` —
not this module.)

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

#: The sole resolving charter source (post-inversion; Landmine 1/2). Mirrors
#: (does NOT import — see ``charter.bundle.BUNDLE_CONTENT_HASH_FILES``'s
#: docstring, which explicitly keeps the ``charter``->``specify_cli``
#: dependency direction intact by NOT being imported here) the content-hash
#: input set consolidate-charter-bundle WP01 narrowed from the four legacy
#: bundle files (``governance.yaml``, ``directives.yaml``, ``references.yaml``,
#: ``metadata.yaml``) down to ``charter.yaml`` alone (contracts/manifest-v2.md
#: M1/M3). ``test_bundle_file_lists_stay_in_sync`` pins the two tuples equal.
_CHARTER_YAML_FILENAME = "charter.yaml"
_BUNDLE_FILES = (_CHARTER_YAML_FILENAME,)


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
    """Load a YAML file as a dict; return None when missing, unreadable, or
    not a mapping.

    Used by ``_compute_charter_source`` to decide whether ``charter.yaml``
    parses (``fresh``) or is a genuine inconsistency (``invalid``). LD-3
    only routes the synthesis manifest and graph reads through the
    chokepoint; this raw parse-check of ``charter.yaml`` itself is a sibling
    concern still owned by this module.
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
    """Report presence/parseability of the resolving charter source.

    Landmine 2 (data-model.md): ``charter.yaml`` — not ``charter.md`` — is
    the authoritative, resolving charter source post-inversion. The
    historical ``charter.md``-SHA-vs-``metadata.yaml::charter_hash``
    comparison is retired outright (module docstring); there is no
    self-referential hash to compute here. This sub-state can therefore only
    ever be ``missing``, ``invalid``, or ``fresh`` — never ``stale`` (the
    content-drift question is answered downstream by ``synthesized_drg``).
    """
    charter_yaml_path = repo_root / _CHARTER_DIR / _CHARTER_YAML_FILENAME

    if not charter_yaml_path.exists():
        return FreshnessSubState(
            state="missing",
            last_change=None,
            remediation="spec-kitty charter sync",
        )

    last_change = _mtime_iso(charter_yaml_path)

    if _safe_load_yaml(charter_yaml_path) is None:
        return FreshnessSubState(
            state="invalid",
            last_change=last_change,
            remediation="spec-kitty charter sync",
            detail="charter.yaml exists but cannot be parsed",
        )

    return FreshnessSubState(state="fresh", last_change=last_change, remediation=None)


def _compute_synced_bundle(
    repo_root: Path,
    charter_source: FreshnessSubState,
) -> FreshnessSubState:
    """Report existence/parseability of the synced bundle (``_BUNDLE_FILES``).

    ``_BUNDLE_FILES`` is now the single-entry ``("charter.yaml",)`` set
    (Landmine 1/2), the same file ``charter_source`` inspects — so this
    layer is largely a structural echo of ``charter_source`` kept for
    contract-shape stability (``charter-status-json.md``'s three-key
    payload) and for future re-widening if the bundle ever grows a second
    tracked file. ``missing`` when the file is absent; ``stale`` when it
    exists but ``charter_source`` found it unparseable (``"invalid"`` — the
    only non-``fresh``, non-``missing`` state ``charter_source`` can report
    once the file exists, since the ``charter.md``-hash ``"stale"`` branch
    is retired); ``fresh`` otherwise.
    """
    bundle_paths = [repo_root / _CHARTER_DIR / name for name in _BUNDLE_FILES]
    existing = [p for p in bundle_paths if p.exists()]
    if not existing:
        return FreshnessSubState(
            state="missing",
            last_change=None,
            remediation="spec-kitty charter sync",
        )

    last_change = _latest_mtime(existing)

    if charter_source.state != "fresh":
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

    if built_in_only:
        # FR-006 (C2-f, structural): built_in_only is an authoritative,
        # never-synthesized short-circuit that returns BEFORE the
        # content-hash comparison in ``_synthesized_drg_graph_state`` is
        # ever reached — a fresh-seed project must not be forced stale.
        return _synthesized_drg_built_in_only_state(graph_path, manifest_path, graph_exists=graph_exists)

    if not graph_exists:
        # No graph + manifest does not opt into built_in_only → also a
        # never-synthesized short-circuit (legacy-seed or missing); the
        # content-hash comparison in ``_synthesized_drg_graph_state`` is
        # equally unreached here.
        return _synthesized_drg_missing_graph_state(repo_root)

    return _synthesized_drg_graph_state(repo_root, graph_path, manifest, synced_bundle)


def _synthesized_drg_built_in_only_state(
    graph_path: Path,
    manifest_path: Path,
    *,
    graph_exists: bool,
) -> FreshnessSubState:
    """FR-006 (C2-f, structural): the synthesis manifest is the declared
    authority over graph.yaml presence (#083). A graph.yaml the manifest
    disowns is *residue*, not a contradiction — so the reader reports the
    authoritative ``built_in_only`` state regardless of graph presence and,
    when residue is present, attaches a NON-BLOCKING diagnostic. This is a
    read-time normalization, NOT a reactive self-heal: the reader does not
    run ``synthesize`` and emits no remediation for residue (C-003). The
    blocking ``invalid`` branch for this specific condition is now
    unreachable, so preflight (``built_in_only`` ∈ ``_PASS_STATES``) passes.
    """
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


def _synthesized_drg_missing_graph_state(repo_root: Path) -> FreshnessSubState:
    """No project ``graph.yaml`` and the manifest does not declare
    ``built_in_only`` — either a legacy fresh-project seed marker (self-heals
    on the next synthesize) or a genuine ``missing`` state.
    """
    legacy_fresh_seed = repo_root / _doctrine_dir() / "PROVENANCE.md"
    if _looks_like_legacy_fresh_seed(legacy_fresh_seed):
        return FreshnessSubState(
            state="built_in_only",
            last_change=_mtime_iso(legacy_fresh_seed),
            remediation=None,
            detail="legacy fresh-project seed marker; re-run `spec-kitty charter synthesize` to write synthesis-manifest.yaml",
        )
    return FreshnessSubState(
        state="missing",
        last_change=None,
        remediation="spec-kitty charter synthesize",
    )


def _synthesized_drg_graph_state(
    repo_root: Path,
    graph_path: Path,
    manifest: SynthesisManifest | None,
    synced_bundle: FreshnessSubState,
) -> FreshnessSubState:
    """Compute the synthesized_drg substate once a project ``graph.yaml`` is
    known to exist and the manifest does not short-circuit to
    ``built_in_only``.

    The content-identity hash comparison against ``synced_bundle`` (#2732's
    contract, now re-pointed at ``charter.yaml`` — see the module docstring)
    is the ONLY staleness signal at this layer. The former second signal
    (#2759's config<->derived activation-parity read, composed with the
    hash) is retired: it is moot once freshness reads ``charter.yaml``
    directly, since activation now lives inside the same file the hash
    already covers — a config<->references/graph divergence of the
    pre-relocation kind cannot exist anymore.
    """
    graph_mtime_iso = _mtime_iso(graph_path)

    if synced_bundle.state != "fresh" or synced_bundle.last_change is None:
        # If the bundle is not itself fresh we cannot prove the graph is
        # fresh either; mark it stale so the operator rebuilds upstream.
        return FreshnessSubState(
            state="stale",
            last_change=graph_mtime_iso,
            remediation="spec-kitty charter synthesize",
        )

    # NFR-003: defer the ``charter.bundle`` import until this branch actually
    # needs it, keeping it off the ``spec-kitty next`` startup hot path (LD-3).
    from charter.bundle import compute_bundle_content_hash  # noqa: PLC0415

    current_hash = compute_bundle_content_hash(repo_root)
    stored_hash = manifest.bundle_content_hash if manifest is not None else None
    if stored_hash is None or current_hash is None or stored_hash != current_hash:
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
