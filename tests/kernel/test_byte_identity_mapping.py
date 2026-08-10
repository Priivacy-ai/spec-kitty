"""Per-site byte-identity mapping harness (WP03, plan Sec 4, SC-004).

The plan's "per-site mapping assertion" closes a hole a plain golden fixture
can't: a site's PRIOR serialization signature (precision / separator /
suffix) can be silently dropped on swap-to-producer even though the producer
itself has a passing golden (``test_producers.py``) -- e.g. a site that used
to call ``.isoformat(timespec="seconds")`` gets rehomed onto
:func:`kernel.clock.now_utc_iso` (native precision) instead of
:func:`kernel.clock.now_utc_seconds`, and a bare "does it look like a
timestamp" check would never notice.

This harness holds a REGISTRY of ``{site_id: (producer, prior_signature)}``.
For every registered site it renders the target producer under one shared
fixed instant and asserts the result equals the site's prior signature
rendered under that exact same instant. Package-remediation WPs (WP05-WP14)
append their own migrated sites to :data:`REGISTRY`, each carrying its WP00
census-recorded prior signature.

The registry starts with two door self-checks (this WP proves the harness
mechanism itself is load-bearing before any package WP populates real
entries) -- and this module's own committed non-vacuity proof, per C-009: a
deliberately mismatched entry is exercised via
:func:`test_planted_precision_mismatch_fires_the_harness`, which asserts the
harness's own comparison rejects the fired mismatch, then removed as a
committed registry entry (kept only as an inline fixture inside that test,
never merged into :data:`REGISTRY` itself -- a stray planted mismatch sitting
in the real registry would permanently fail this file for everyone).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pytest

import kernel.clock as clock_module
from kernel.clock import (
    UTC,
    FrozenClock,
    datetime,
    from_epoch,
    now_epoch,
    now_utc,
    now_utc_compact_stamp,
    now_utc_iso,
    now_utc_seconds,
    now_utc_stamp,
    timedelta,
)
from specify_cli.task_utils.support import now_utc as _task_utils_now_utc_stamp

pytestmark = pytest.mark.fast

_FIXED_INSTANT = datetime(2026, 11, 2, 14, 15, 16, 654321, tzinfo=UTC)


@dataclass(frozen=True)
class RegisteredSite:
    """One migrated call site's mapping-harness entry.

    ``producer``: the door producer this WP03+ (or a later package WP)
    routed the site onto -- called with no arguments under the shared frozen
    instant.
    ``prior_signature``: a callable reproducing the site's PRE-MIGRATION
    byte output from the same fixed instant (its old ``strftime``/
    ``isoformat`` call, inlined) -- this is what the WP00 census records per
    site (precision/sep/suffix).
    """

    producer: Callable[[], str]
    prior_signature: Callable[[datetime], str]


#: Populated by package-remediation WPs (WP05-WP14) as they migrate sites;
#: each entry's ``prior_signature`` reproduces that exact site's pre-mission
#: bytes (from the WP00 census), so a swap that silently drops the site's
#: original precision/separator/suffix is caught even though the producer
#: itself has an independent passing golden.
#:
#: This WP (WP03) seeds it with two door SELF-checks only, proving the
#: harness compares correctly before any package WP's real entry lands --
#: the harness format below (``producer``, ``prior_signature``) is the
#: contract those WPs populate against.
REGISTRY: dict[str, RegisteredSite] = {
    "kernel.clock.now_utc_stamp#self": RegisteredSite(
        producer=now_utc_stamp,
        prior_signature=lambda instant: instant.strftime("%Y-%m-%dT%H:%M:%SZ"),
    ),
    "kernel.clock.now_utc_seconds#self": RegisteredSite(
        producer=now_utc_seconds,
        prior_signature=lambda instant: instant.isoformat(timespec="seconds"),
    ),
    "kernel.clock.now_utc_compact_stamp#self": RegisteredSite(
        producer=now_utc_compact_stamp,
        prior_signature=lambda instant: instant.strftime("%Y%m%dT%H%M%SZ"),
    ),
    "kernel.clock.now_utc_iso#self": RegisteredSite(
        producer=now_utc_iso,
        prior_signature=lambda instant: instant.isoformat(),
    ),
    "kernel.clock.now_utc#self": RegisteredSite(
        producer=lambda: now_utc().isoformat(),
        prior_signature=lambda instant: instant.isoformat(),
    ),
    "kernel.clock.now_epoch#self": RegisteredSite(
        producer=lambda: str(now_epoch()),
        prior_signature=lambda instant: str(instant.timestamp()),
    ),
    # WP05 (doctrine): src/doctrine/versioning.py's migrate_v1_to_v2 stamps a
    # sidecar's missing `produced_at` from the sidecar's file mtime. Prior
    # site: `datetime.fromtimestamp(mtime, tz=UTC).isoformat()`. Migrated
    # onto the door's `from_epoch(mtime).isoformat()` -- `from_epoch` is
    # defined as exactly `datetime.fromtimestamp(value, tz=UTC)` (WP04), so
    # this is a byte-identical delegation, not a reformat.
    "doctrine.versioning.migrate_v1_to_v2#produced_at": RegisteredSite(
        producer=lambda: from_epoch(_FIXED_INSTANT.timestamp()).isoformat(),
        prior_signature=lambda instant: datetime.fromtimestamp(instant.timestamp(), tz=UTC).isoformat(),
    ),
    # WP06 (glossary): drg_builder.build_index() stamps `DRGGraph.generated_at`.
    # Prior site: `datetime.now(tz=UTC).isoformat()`. Migrated onto the door's
    # `now_utc_iso()` -- same underlying expression (`datetime.now(UTC).isoformat()`),
    # so byte-identical.
    "glossary.drg_builder.build_index#generated_at": RegisteredSite(
        producer=now_utc_iso,
        prior_signature=lambda instant: instant.isoformat(),
    ),
    # WP06 (glossary): checkpoint.create_checkpoint() stamps `StepCheckpoint.timestamp`,
    # later serialized via `checkpoint_to_dict()`'s `checkpoint.timestamp.isoformat()`
    # into the persisted `.events.jsonl` checkpoint event. Prior site:
    # `datetime.now(UTC)` (aware datetime-returning). Migrated onto the door's
    # `now_utc()`; the eventual `.isoformat()` call is unchanged, so the
    # persisted bytes are identical.
    "glossary.checkpoint.create_checkpoint#timestamp": RegisteredSite(
        producer=lambda: now_utc().isoformat(),
        prior_signature=lambda instant: instant.isoformat(),
    ),
    # WP06 (glossary): every glossary/events.py payload builder (10 call sites)
    # stamped its "timestamp" field via the module-local `_now_iso()` helper
    # (`datetime.now(UTC).isoformat()`, byte-identical to the door's
    # `now_utc_iso`). `_now_iso` is retired; every call site now calls
    # `now_utc_iso()` directly -- registering one representative entry since
    # all ten sites are the identical expression routed through the same
    # shared helper (no per-site divergence possible).
    "glossary.events.build_glossary_scope_activated#timestamp": RegisteredSite(
        producer=now_utc_iso,
        prior_signature=lambda instant: instant.isoformat(),
    ),
    # --- WP07 (charter) ---------------------------------------------------
    # charter/_io.py's ingestion-provenance "at" field. Prior:
    # `datetime.now(tz=UTC).isoformat()` -> now_utc_iso().
    "charter._io.now#at": RegisteredSite(
        producer=now_utc_iso,
        prior_signature=lambda instant: instant.isoformat(),
    ),
    # charter/compiler.py's charter.yaml `metadata.generated_at` (persisted;
    # see also test_compiler_persisted_goldens.py for the pre-migration
    # golden byte capture). Prior: `datetime.now(UTC).strftime(
    # "%Y-%m-%dT%H:%M:%SZ")` -> now_utc_stamp().
    "charter.compiler._build_metadata_dict#generated_at": RegisteredSite(
        producer=now_utc_stamp,
        prior_signature=lambda instant: instant.strftime("%Y-%m-%dT%H:%M:%SZ"),
    ),
    # charter/compiler.py's rendered `charter.md` "Generated: <stamp>" line.
    # Same prior contract as the metadata site above (both were
    # `datetime.now(UTC).strftime(...)` -> now_utc_stamp()).
    "charter.compiler._render_charter_markdown#now": RegisteredSite(
        producer=now_utc_stamp,
        prior_signature=lambda instant: instant.strftime("%Y-%m-%dT%H:%M:%SZ"),
    ),
    # charter/context_state.py's persisted context-state.json first-load
    # timestamp (see also test_context_leaf_seams.py's golden). Prior:
    # `datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")` -> now_utc_stamp().
    "charter.context_state._mark_action_loaded#timestamp": RegisteredSite(
        producer=now_utc_stamp,
        prior_signature=lambda instant: instant.strftime("%Y-%m-%dT%H:%M:%SZ"),
    ),
    # charter/evidence/code_reader.py's retired `_utcnow_iso()` helper (named
    # "utcnow" but was already aware -- `datetime.now(tz=UTC).isoformat()`).
    # Both call sites now call now_utc_iso() directly.
    "charter.evidence.code_reader#detected_at": RegisteredSite(
        producer=now_utc_iso,
        prior_signature=lambda instant: instant.isoformat(),
    ),
    # charter/evidence/corpus_loader.py's `loaded_at`. Prior:
    # `datetime.datetime.now(datetime.UTC).isoformat()` (module-style import)
    # -> now_utc_iso().
    "charter.evidence.corpus_loader#loaded_at": RegisteredSite(
        producer=now_utc_iso,
        prior_signature=lambda instant: instant.isoformat(),
    ),
    # charter/evidence/orchestrator.py's `collected_at`. Same module-style
    # prior contract as corpus_loader above.
    "charter.evidence.orchestrator#collected_at": RegisteredSite(
        producer=now_utc_iso,
        prior_signature=lambda instant: instant.isoformat(),
    ),
    # charter/pack_manager.py's charter.md backup filename suffix (see also
    # test_pack_manager_persisted_goldens.py). Prior (in-function import):
    # `datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")` -> now_utc_compact_stamp().
    "charter.pack_manager.MergePacksAction#backup_ts": RegisteredSite(
        producer=now_utc_compact_stamp,
        prior_signature=lambda instant: instant.strftime("%Y%m%dT%H%M%SZ"),
    ),
    # charter/synthesizer/generated_artifact_adapter.py's `generated_at`
    # derived from the source file's mtime. Prior:
    # `datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)` -> from_epoch(mtime).
    "charter.synthesizer.generated_artifact_adapter#generated_at": RegisteredSite(
        producer=lambda: from_epoch(_FIXED_INSTANT.timestamp()).isoformat(),
        prior_signature=lambda instant: datetime.fromtimestamp(instant.timestamp(), tz=UTC).isoformat(),
    ),
    # charter/synthesizer/project_drg.py's project-overlay DRG `generated_at`
    # (persisted `doctrine/graph.yaml`). Prior: `datetime.now(UTC).isoformat(
    # timespec="seconds")` -> now_utc_seconds().
    "charter.synthesizer.project_drg.emit_project_layer#generated_at": RegisteredSite(
        producer=now_utc_seconds,
        prior_signature=lambda instant: instant.isoformat(timespec="seconds"),
    ),
    # charter/synthesizer/resynthesize_pipeline.py's merged manifest
    # `created_at`. Prior (in-function import): `datetime.now(tz=UTC).isoformat()`
    # -> now_utc_iso().
    "charter.synthesizer.resynthesize_pipeline#created_at": RegisteredSite(
        producer=now_utc_iso,
        prior_signature=lambda instant: instant.isoformat(),
    ),
    # charter/synthesizer/staging.py's staging-log "timestamp" field. Prior:
    # `datetime.now(tz=UTC).isoformat()` -> now_utc_iso().
    "charter.synthesizer.staging#timestamp": RegisteredSite(
        producer=now_utc_iso,
        prior_signature=lambda instant: instant.isoformat(),
    ),
    # charter/synthesizer/synthesize_pipeline.py's ProvenanceEntry
    # `produced_at` (two identical call sites). Prior:
    # `datetime.now(timezone.utc).isoformat()` -> now_utc_iso().
    "charter.synthesizer.synthesize_pipeline#produced_at": RegisteredSite(
        producer=now_utc_iso,
        prior_signature=lambda instant: instant.isoformat(),
    ),
    # charter/synthesizer/write_pipeline.py's promoted-provenance `created_at`.
    # Prior: `datetime.now(tz=UTC).isoformat()` -> now_utc_iso().
    "charter.synthesizer.write_pipeline#created_at": RegisteredSite(
        producer=now_utc_iso,
        prior_signature=lambda instant: instant.isoformat(),
    ),
    # --- WP08 (runtime) ----------------------------------------------------
    # _internal_runtime/engine.py's local run-journal event "timestamp"
    # field (persisted `run.events.jsonl`). Prior: `datetime.now(UTC)
    # .isoformat()` -> now_utc_iso().
    "runtime._internal_runtime.engine._append_event#timestamp": RegisteredSite(
        producer=now_utc_iso,
        prior_signature=lambda instant: instant.isoformat(),
    ),
    # _internal_runtime/retrospective_terminus.py's retired `_now_utc()`
    # helper (named like the door's datetime-returning `now_utc`, but it
    # returned a str -- same shape as `now_utc_iso`). Prior:
    # `datetime.now(UTC).isoformat()` -> now_utc_iso().
    "runtime._internal_runtime.retrospective_terminus#now_ts": RegisteredSite(
        producer=now_utc_iso,
        prior_signature=lambda instant: instant.isoformat(),
    ),
    # runtime_bridge.py's two `now` sites (identical prior contract). Prior:
    # `datetime.now(UTC).isoformat()` -> now_utc_iso().
    "runtime.runtime_bridge#now": RegisteredSite(
        producer=now_utc_iso,
        prior_signature=lambda instant: instant.isoformat(),
    ),
    # --- WP09 (specify_cli/sync) --------------------------------------------
    # sync/body_queue.py's persisted SQLite epoch columns (`created_at`,
    # `next_attempt_at`, `first_failed_at`, `last_failed_at` -- all five call
    # sites shared the identical prior expression, one representative entry
    # covers them). Prior: raw `time.time()` -> now_epoch(). `now_epoch()` is
    # defined as exactly `DEFAULT_CLOCK.now_epoch()` -> `time.time()` (WP03),
    # so this is a byte-identical delegation (the persisted float epoch is
    # unchanged), not a reformat.
    "specify_cli.sync.body_queue.OfflineBodyUploadQueue#persisted_epoch": RegisteredSite(
        producer=lambda: str(now_epoch()),
        prior_signature=lambda instant: str(instant.timestamp()),
    ),
    # sync/queue.py's persisted `queue.timestamp` column (5 call sites, one
    # representative entry). Prior: naive `int(datetime.now().timestamp())`
    # -- a naive `.now()` interpreted under the system's local timezone and
    # immediately reduced to a Unix epoch via `.timestamp()`, which is the
    # SAME epoch float `time.time()`/`now_epoch()` would have produced for
    # that instant (naive-local-`.timestamp()` and aware-UTC-`.timestamp()`
    # both resolve to the one true Unix epoch for "now" -- this is an epoch
    # computation in disguise, not a serialized local-time value, so it is
    # NOT one of the FR-011 byte-changing naive fixes; see
    # research/migration-notes.md). Migrated onto `int(now_epoch())`.
    "specify_cli.sync.queue.OfflineQueue#persisted_timestamp": RegisteredSite(
        producer=lambda: str(int(now_epoch())),
        prior_signature=lambda instant: str(int(instant.timestamp())),
    ),
    # sync/owner.py's `DaemonOwnerRecord.started_at` seconds-precision stamp.
    # Prior: `datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S+00:00")` -- for a
    # UTC-tzinfo datetime this is byte-identical to
    # `isoformat(timespec="seconds")` (both render the zero UTC offset as
    # `+00:00`) -> now_utc_seconds().
    "specify_cli.sync.owner.build_foreground_owner_record#started_at": RegisteredSite(
        producer=now_utc_seconds,
        prior_signature=lambda instant: instant.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
    ),
    # --- WP10 (specify_cli/status + merge + coordination) -------------------
    # coordination/status_transition.py's batch-commit persisted `StatusEvent.at`
    # / annotation `at` fields (status.events.jsonl) -- the batch anchor
    # `started_at` is offset per-event by `timedelta(microseconds=...)` then
    # serialized via `.isoformat()`. Prior: `datetime.now(UTC)` -> `now_utc()`;
    # the door's datetime-returning producer is defined as exactly
    # `DEFAULT_CLOCK.now()` -> `datetime.now(UTC)` (WP02/WP03), so the
    # subsequent timedelta arithmetic + `.isoformat()` is unchanged.
    "specify_cli.coordination.status_transition.transition_batch#at": RegisteredSite(
        producer=lambda: (now_utc() + timedelta(microseconds=3)).isoformat(),
        prior_signature=lambda instant: (instant + timedelta(microseconds=3)).isoformat(),
    ),
    # status/emit.py's batch-claim persisted `StatusEvent.at` / annotation `at`
    # fields (same `started_at`-anchor-plus-offset-plus-isoformat shape as the
    # coordination site above, independent call site). Prior:
    # `datetime.now(UTC)` -> `now_utc()`.
    "specify_cli.status.emit.emit_status_transitions_batch#at": RegisteredSite(
        producer=lambda: (now_utc() + timedelta(microseconds=3)).isoformat(),
        prior_signature=lambda instant: (instant + timedelta(microseconds=3)).isoformat(),
    ),
    # --- WP11 (specify_cli/core + task_utils + decisions + dossier) ---------
    # core/file_lock.py's persisted `LockRecord.started_at` (JSON lock-file
    # record). Prior: `datetime.now(UTC)` -> `now_utc()`.
    "specify_cli.core.file_lock.LockRecord#started_at": RegisteredSite(
        producer=lambda: now_utc().isoformat(),
        prior_signature=lambda instant: instant.isoformat(),
    ),
    # core/upgrade_probe.py's persisted `UpgradeProbeResult.probed_at` (JSON
    # upgrade-check cache). Prior: `datetime.now(UTC)` -> `now_utc()`.
    "specify_cli.core.upgrade_probe.probe_pypi#probed_at": RegisteredSite(
        producer=lambda: now_utc().isoformat(),
        prior_signature=lambda instant: instant.isoformat(),
    ),
    # task_utils/support.py's own `now_utc() -> str` stamp helper (NOT the
    # door's datetime-returning `now_utc()` -- same name, distinct contract,
    # C-003; see the module's FR-010/WP11 docstring note). Its body now
    # delegates to the door's `now_utc_stamp()` instead of a direct
    # `datetime.now(UTC).strftime(...)` call. Prior signature reproduces the
    # exact prior expression (the format string is the SAME door constant,
    # aliased locally as `TIMESTAMP_FORMAT`, both before and after this WP).
    "specify_cli.task_utils.support.now_utc#stamp": RegisteredSite(
        producer=_task_utils_now_utc_stamp,
        prior_signature=lambda instant: instant.strftime("%Y-%m-%dT%H:%M:%SZ"),
    ),
    # decisions/emit.py's persisted `DecisionPointOpened`/`DecisionPointResolved`
    # envelope `at` field (status.events.jsonl) -- previously produced by the
    # module-local `_now_utc()` helper (`datetime.now(UTC)`, retired this WP);
    # call sites now read `kernel.clock.now_utc()` directly.
    "specify_cli.decisions.emit.emit_decision_opened#at": RegisteredSite(
        producer=lambda: now_utc().isoformat(),
        prior_signature=lambda instant: instant.isoformat(),
    ),
    # decisions/service.py's `IndexEntry.created_at`/`resolved_at` (persisted
    # `decisions/index.json` via `model_dump(mode="json")`, and rendered
    # directly into `DM-<id>.md` via `.isoformat()`) -- same retired
    # module-local `_now_utc()` -> `now_utc()` routing as emit.py above.
    "specify_cli.decisions.service.open_decision#created_at": RegisteredSite(
        producer=lambda: now_utc().isoformat(),
        prior_signature=lambda instant: instant.isoformat(),
    ),
    # dossier/models.py's pydantic `default_factory` timestamps (`ArtifactRef
    # .indexed_at`, `MissionDossier.dossier_created_at`/`dossier_updated_at`,
    # `MissionDossierSnapshot.computed_at`) -- one representative entry; all
    # four shared the identical prior expression
    # `default_factory=lambda: datetime.now(UTC)` -> `default_factory=now_utc`.
    # Persisted via `dossier/snapshot.py`'s `a.indexed_at.isoformat()` /
    # `model_dump()`.
    "specify_cli.dossier.models.ArtifactRef#indexed_at": RegisteredSite(
        producer=lambda: now_utc().isoformat(),
        prior_signature=lambda instant: instant.isoformat(),
    ),
    # dossier/drift_detector.py's persisted `BaselineSnapshot.captured_at`
    # (`.kittify/dossiers/<slug>/parity-baseline.json`). Prior:
    # `datetime.now(UTC)` -> `now_utc()`.
    "specify_cli.dossier.drift_detector.capture_baseline#captured_at": RegisteredSite(
        producer=lambda: now_utc().isoformat(),
        prior_signature=lambda instant: instant.isoformat(),
    ),
}


@pytest.fixture
def frozen(monkeypatch: pytest.MonkeyPatch) -> datetime:
    monkeypatch.setattr(clock_module, "DEFAULT_CLOCK", FrozenClock(instant=_FIXED_INSTANT))
    return _FIXED_INSTANT


@pytest.mark.parametrize("site_id", sorted(REGISTRY))
def test_registered_site_matches_prior_signature(site_id: str, frozen: datetime) -> None:
    """Every registered site's chosen producer reproduces its prior bytes
    exactly, under the shared fixed instant."""
    entry = REGISTRY[site_id]
    assert entry.producer() == entry.prior_signature(frozen)


def test_planted_precision_mismatch_fires_the_harness(frozen: datetime) -> None:
    """C-009 non-vacuity: the harness's comparison rejects a real mismatch.

    Plants a deliberately WRONG entry -- pairing ``now_utc_stamp`` (second
    precision, ``Z`` suffix) against a prior-signature that reproduces
    ``now_utc_seconds``'s shape (``+00:00`` offset, no ``Z``) -- entirely
    in-memory (never merged into :data:`REGISTRY`, per NOTE-2: planted
    violations live in-memory/``tmp_path`` only). Confirms the harness
    mechanism itself is load-bearing, not a vacuous pass-through: run with
    the mismatch and the assertion correctly fails.
    """
    planted = RegisteredSite(
        producer=now_utc_stamp,
        prior_signature=lambda instant: instant.isoformat(timespec="seconds"),
    )

    assert planted.producer() != planted.prior_signature(frozen)
