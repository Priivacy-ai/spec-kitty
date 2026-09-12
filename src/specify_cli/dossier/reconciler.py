"""DossierReconciler — rebuild a dossier projection and verify it against source.

This module is the parity foundation for provable materialization
(spec-kitty#2180). It rebuilds a dossier projection from source, computes its
**canonical snapshot hash** using WP01's single owning definition
(:func:`specify_cli.dossier.hasher.compute_dossier_snapshot_hash`), compares it
against the recorded/emitted projection, and returns a structured
:class:`ReconciliationResult`:

    PARITY      — the rebuilt hash equals the recorded hash; zero differing
                  artifacts. Parity is a *proof* of sameness, not an assertion.
    DIVERGENCE  — the hashes differ; every divergence NAMES the specific
                  differing artifact path(s) (NFR-004) — never a bare "mismatch".
    ERROR       — any inability to compute or compare a hash. Fail-closed
                  (C-005, FR-006): the reconciler NEVER falls back to a default
                  "parity". There is no ``else: proceed`` escape hatch.

Design invariants:

- **Pure.** No request/DB/filesystem coupling. Inputs are projections (already
  content-addressed entries or projectable domain objects); WP04 wraps this as a
  CLI command + library API. This is the stable entrypoint WP04 depends on.
- **Reuses WP01.** The hash algorithm is injected (defaulting to the canonical
  definition) and is never re-implemented here (C-001).
- **Churn-immune.** Because the per-artifact ``content_hash`` input is WP01's
  normalized static projection, runtime-mutable frontmatter churn cannot move
  the hash and therefore reads as PARITY (AS-4). The reconciler is agnostic to
  how the content hash was produced — it only compares.

See: kitty-specs/dossier-parity-reconciler-01KXYXVP/spec.md
     (FR-004, FR-005, FR-006, NFR-004, C-005, AS-2/AS-3/AS-4).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from specify_cli.dossier.hasher import compute_dossier_snapshot_hash

# A dossier projection is a sequence of (artifact_path, content_hash) entries —
# the exact input shape of WP01's canonical hash. ``content_hash`` may be None
# (treated as the empty string, matching the server contract).
ProjectionEntry = tuple[str, str | None]
ProjectionEntries = list[ProjectionEntry]

# Callable that turns projection entries into the canonical snapshot hash. The
# default is WP01's single owning definition; it is injectable purely so tests
# can force a compute failure and prove the fail-closed path.
HashFn = Callable[[ProjectionEntries], str]

# What the reconciler accepts as a "projection": canonical entry tuples, a
# mapping of path -> content_hash, or projectable domain objects (e.g.
# ``ArtifactRef``) exposing a path + content hash attribute.
ProjectionInput = Mapping[str, str | None] | Iterable[object]


class ReconciliationError(Exception):
    """Raised internally when a projection cannot be normalized or rebuilt.

    Always caught at the :meth:`DossierReconciler.reconcile` boundary and turned
    into an explicit :class:`ReconciliationResult` ERROR — it never escapes as a
    default parity (C-005).
    """


class ReconciliationStatus(StrEnum):
    """The three — and only three — outcomes of a reconciliation."""

    PARITY = "parity"
    DIVERGENCE = "divergence"
    ERROR = "error"


class DivergenceKind(StrEnum):
    """Why a specific artifact diverged (drives actionable reporting, NFR-004)."""

    CONTENT_MISMATCH = "content_mismatch"
    """Present on both sides, but the content hashes differ."""

    MISSING_IN_SOURCE = "missing_in_source"
    """Present in the recorded projection, absent when rebuilt from source."""

    MISSING_IN_PROJECTION = "missing_in_projection"
    """Present in the rebuilt source, absent in the recorded projection."""


@dataclass(frozen=True)
class ArtifactDivergence:
    """One named artifact-level divergence. A DIVERGENCE always carries >=1."""

    artifact_path: str
    kind: DivergenceKind
    source_hash: str | None
    recorded_hash: str | None


@dataclass(frozen=True)
class ReconciliationResult:
    """Structured, gate-able result of a reconciliation.

    Consumers (import-history #2262, WP04's CLI) gate on this. Truthiness is
    PARITY-only, so a divergence or an error can never read as a pass.
    """

    status: ReconciliationStatus
    rebuilt_hash: str | None = None
    recorded_hash: str | None = None
    differing_artifacts: tuple[ArtifactDivergence, ...] = field(default_factory=tuple)
    error: str | None = None

    @property
    def is_parity(self) -> bool:
        return self.status is ReconciliationStatus.PARITY

    @property
    def is_divergence(self) -> bool:
        return self.status is ReconciliationStatus.DIVERGENCE

    @property
    def is_error(self) -> bool:
        return self.status is ReconciliationStatus.ERROR

    @property
    def differing_paths(self) -> tuple[str, ...]:
        """Sorted tuple of the named differing artifact paths (audit/gate use)."""
        return tuple(d.artifact_path for d in self.differing_artifacts)

    def __bool__(self) -> bool:
        """A result is truthy only on proven PARITY — fail-closed for gating."""
        return self.is_parity


def _coerce_entry(item: object) -> ProjectionEntry:
    """Coerce a single projection item to a canonical (path, content_hash) pair.

    Accepts:
      - a 2-item (path, content_hash) tuple/list,
      - a projectable domain object exposing a path attribute
        (``relative_path`` or ``artifact_path``) and a content-hash attribute
        (``content_hash_sha256`` or ``content_hash``).

    Raises:
        ReconciliationError: if the item is neither shape (fail-closed input).
    """
    if isinstance(item, (tuple, list)):
        if len(item) != 2:
            raise ReconciliationError(f"projection entry must be a (path, content_hash) pair; got {item!r}")
        path, content_hash = item
        if not isinstance(path, str):
            raise ReconciliationError(f"artifact path must be a string; got {path!r}")
        if content_hash is not None and not isinstance(content_hash, str):
            raise ReconciliationError(f"content hash must be a string or None; got {content_hash!r}")
        return path, content_hash

    path_attr = getattr(item, "relative_path", None) or getattr(item, "artifact_path", None)
    if isinstance(path_attr, str):
        content_hash = getattr(item, "content_hash_sha256", None)
        if content_hash is None:
            content_hash = getattr(item, "content_hash", None)
        if content_hash is not None and not isinstance(content_hash, str):
            raise ReconciliationError(f"content hash must be a string or None; got {content_hash!r}")
        return path_attr, content_hash

    raise ReconciliationError(f"cannot project artifact from {item!r}: no (path, content_hash) shape")


def _normalize(projection: ProjectionInput) -> ProjectionEntries:
    """Normalize any accepted projection input to canonical entry pairs.

    Raises:
        ReconciliationError: on any unprojectable input (fail-closed).
    """
    if isinstance(projection, Mapping):
        return [(str(path), value) for path, value in projection.items()]
    try:
        items = list(projection)
    except TypeError as exc:
        raise ReconciliationError(f"projection is not iterable: {exc}") from exc
    return [_coerce_entry(item) for item in items]


def _index_by_path(entries: ProjectionEntries) -> dict[str, str | None]:
    """Index entries by artifact path for per-artifact diffing.

    Raises:
        ReconciliationError: on a duplicate path — an ambiguous projection we
            refuse to silently collapse (fail-closed rather than guess).
    """
    indexed: dict[str, str | None] = {}
    for path, content_hash in entries:
        if path in indexed:
            raise ReconciliationError(f"duplicate artifact path in projection: {path!r}")
        indexed[path] = content_hash
    return indexed


def _name_divergences(
    source: ProjectionEntries,
    recorded: ProjectionEntries,
) -> tuple[ArtifactDivergence, ...]:
    """Diff two projections per-artifact and name every difference (NFR-004)."""
    source_map = _index_by_path(source)
    recorded_map = _index_by_path(recorded)

    divergences: list[ArtifactDivergence] = []
    for path in sorted(set(source_map) | set(recorded_map)):
        in_source = path in source_map
        in_recorded = path in recorded_map
        src_hash = source_map.get(path)
        rec_hash = recorded_map.get(path)

        if in_source and not in_recorded:
            kind = DivergenceKind.MISSING_IN_PROJECTION
        elif in_recorded and not in_source:
            kind = DivergenceKind.MISSING_IN_SOURCE
        elif src_hash != rec_hash:
            kind = DivergenceKind.CONTENT_MISMATCH
        else:
            continue  # identical entry — not a divergence

        divergences.append(
            ArtifactDivergence(
                artifact_path=path,
                kind=kind,
                source_hash=src_hash if in_source else None,
                recorded_hash=rec_hash if in_recorded else None,
            )
        )
    return tuple(divergences)


class DossierReconciler:
    """Rebuild a dossier projection from source and verify it against a record.

    Pure and stateless; safe to reuse across missions. The canonical hash
    function is injectable (defaulting to WP01's owning definition) solely so
    the fail-closed compute-failure path is testable.
    """

    def __init__(self, hash_fn: HashFn = compute_dossier_snapshot_hash) -> None:
        self._hash_fn = hash_fn

    def reconcile(
        self,
        source: ProjectionInput,
        recorded: ProjectionInput,
        *,
        recorded_hash: str | None = None,
    ) -> ReconciliationResult:
        """Rebuild ``source``, compare to ``recorded``, return a structured result.

        Args:
            source: The source-of-truth projection to rebuild from.
            recorded: The recorded/emitted projection being verified.
            recorded_hash: Optional emitted snapshot hash anchor. When supplied
                it must equal the recorded projection's own canonical hash; a
                disagreement means the record is internally inconsistent and is
                reported as an ERROR (fail-closed), never trusted into a parity.

        Returns:
            A :class:`ReconciliationResult`. This method never raises for
            reconciliation-domain problems and never defaults to PARITY: any
            inability to compute or compare surfaces as an explicit ERROR
            (C-005, FR-006).
        """
        # ── Rebuild from source (FR-004) ───────────────────────────────────
        try:
            source_entries = _normalize(source)
            recorded_entries = _normalize(recorded)
            rebuilt_hash = self._hash_fn(source_entries)
            recorded_computed_hash = self._hash_fn(recorded_entries)
        except ReconciliationError as exc:
            return ReconciliationResult(status=ReconciliationStatus.ERROR, error=str(exc))
        except Exception as exc:  # noqa: BLE001 - fail-closed: any compute failure is an ERROR, never parity
            return ReconciliationResult(status=ReconciliationStatus.ERROR, error=f"hash computation failed: {exc}")

        # ── Resolve the recorded/emitted hash to compare against (FR-005) ──
        if recorded_hash is not None:
            if recorded_hash != recorded_computed_hash:
                return ReconciliationResult(
                    status=ReconciliationStatus.ERROR,
                    rebuilt_hash=rebuilt_hash,
                    recorded_hash=recorded_hash,
                    error=(
                        "recorded snapshot hash is inconsistent with the recorded projection "
                        f"(emitted={recorded_hash!r}, recomputed={recorded_computed_hash!r}); "
                        "refusing to reconcile against an untrustworthy record"
                    ),
                )
            effective_recorded_hash = recorded_hash
        else:
            effective_recorded_hash = recorded_computed_hash

        # ── Compare (FR-005) — explicit PARITY vs DIVERGENCE, no default ────
        if rebuilt_hash == effective_recorded_hash:
            return ReconciliationResult(
                status=ReconciliationStatus.PARITY,
                rebuilt_hash=rebuilt_hash,
                recorded_hash=effective_recorded_hash,
            )

        # Hashes differ: NAME the differing artifacts (NFR-004).
        try:
            divergences = _name_divergences(source_entries, recorded_entries)
        except ReconciliationError as exc:
            return ReconciliationResult(
                status=ReconciliationStatus.ERROR,
                rebuilt_hash=rebuilt_hash,
                recorded_hash=effective_recorded_hash,
                error=str(exc),
            )

        if not divergences:
            # Hashes disagree but no per-artifact difference could be named. That
            # is an internal inconsistency, not a parity — fail-closed rather
            # than emit a bare, unactionable "mismatch" (NFR-004, C-005).
            return ReconciliationResult(
                status=ReconciliationStatus.ERROR,
                rebuilt_hash=rebuilt_hash,
                recorded_hash=effective_recorded_hash,
                error=("snapshot hashes differ but no differing artifact could be named; the projections are inconsistent"),
            )

        return ReconciliationResult(
            status=ReconciliationStatus.DIVERGENCE,
            rebuilt_hash=rebuilt_hash,
            recorded_hash=effective_recorded_hash,
            differing_artifacts=divergences,
        )
