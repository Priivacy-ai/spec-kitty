# Migration notes — naive `datetime.now()`/`utcnow()` adjudication (FR-011 / SC-006)

Per `research/census.yaml`'s `fr_011b_decision`: the default is to convert every
naive site to an aware-UTC door producer (`now_utc()`), unless a package WP
finds a genuinely local-time-display consumer, in which case it escalates
(add a sanctioned `now_naive_local()` to the door, per site). Each entry below
records: the site, the naive→aware conversion applied, whether the fix is
byte-changing (i.e. the naive value was ever serialized), and the behaviour
test that proves the fix (or, for a pinned-naive site, the pinning test).

Package-remediation WPs append their own entries here (Package-WP `Done`
template clause 4, `tasks.md`). If a WP's owned paths carry no naive sites,
it records `naive=∅` for that owner in its own report (no entry needed here).

## WP05 — doctrine

`naive=∅`. Both doctrine importers (`model_task_routing/loader.py`,
`versioning.py`) used only aware `datetime.now(UTC)` / `datetime.fromtimestamp(x,
tz=UTC)` calls; no naive site existed to adjudicate.

## WP06 — glossary

| Site | Was | Now | Byte-changing? | Test |
|---|---|---|---|---|
| `src/glossary/scope.py:157` (`load_seed_file`, `Provenance.timestamp` for seed-loaded terms) | naive `datetime.now()` (local time, mislabeled as an instant) | aware-UTC `now_utc()` | **Yes** — `glossary/models.py:term_sense_to_dict` serializes this via `ts.provenance.timestamp.isoformat()`; a naive `datetime.isoformat()` has no UTC offset suffix, an aware one gets `+00:00`. Any persisted `TermSense` dict for a seed-loaded sense changes bytes (gains the offset, and the value itself may differ if the host's local zone isn't UTC). | `tests/glossary/test_scope.py::TestLoadSeedFile::test_loaded_sense_provenance_timestamp_is_aware_utc` — asserts the loaded sense's `provenance.timestamp.tzinfo is UTC` (fails if the door call is reverted to a naive `datetime.now()`). |

Adjudication: converted (not pinned-naive) — this is the "naive local-time bug
is fixed" scenario from spec.md, not a legitimate local-display consumer.
`now_naive_local()` was NOT added to the door (no WP06 site needed it).

All other glossary naive-looking sites found during remediation (test-fixture
`Provenance(..., datetime.now(), ...)` construction in
`tests/agent/glossary/test_models.py`, `tests/agent/glossary/test_store.py`,
`tests/glossary/test_drg_builder.py`) are **test fixture data only** — the
tests never assert on tz-awareness or a specific instant, they only need *a*
`datetime` to satisfy `Provenance.timestamp`'s type. These were routed onto
the door's aware `now_utc()` producer for consistency (same call-ban
requirement as production code) but carry **no behaviour change** for the
test itself, so they are not separately enumerated as FR-011 adjudications
(no production byte format is at stake).

## WP07 — charter

`naive=∅`. All 16 importers used only aware forms (`datetime.now(UTC)`,
`datetime.now(tz=UTC)`, `datetime.now(timezone.utc)`, module-style
`datetime.datetime.now(datetime.UTC)`) — including the misleadingly-named
`evidence/code_reader.py::_utcnow_iso()` helper, which despite its name was
already `datetime.now(tz=UTC).isoformat()` (aware), not a real `utcnow()`
call. No naive site existed to adjudicate. `now_naive_local()` was NOT
added to the door.

Persisted-artifact goldens (SC-004, captured from the PRE-migration tree
before any charter file was edited, under a frozen instant of
`2026-11-02T14:15:16.654321+00:00`):

| Site | Pre-migration bytes | Golden test |
|---|---|---|
| `charter/compiler.py::_build_metadata_dict` (`charter.yaml` `metadata.generated_at`) | `2026-11-02T14:15:16Z` | `tests/charter/test_compiler_charter_yaml.py::TestChartYamlPartialWrite::test_metadata_generated_at_matches_pre_migration_golden_bytes` |
| `charter/context_state.py::_mark_action_loaded` (`context-state.json` action timestamp) | `2026-11-02T14:15:16Z` | `tests/charter/test_context_leaf_seams.py::TestContextStateBookkeeping::test_mark_action_loaded_matches_pre_migration_golden_bytes` |
| `charter/pack_manager.py` (`MergePacksAction` backup filename suffix) | `20261102T141516Z` | `tests/charter/test_pack_manager.py::TestMergeDefaults::test_backup_filename_matches_pre_migration_golden_bytes` |

All three pre-migration values were captured by executing the actual
pre-edit functions under a monkeypatched frozen `datetime` (not
hand-derived from the format string) before any charter source file was
touched, then re-verified against the same fixed instant post-migration via
the door's `FrozenClock`/`DEFAULT_CLOCK` seam — byte-identical in all three
cases (confirms `now_utc_stamp()`/`now_utc_compact_stamp()` reproduce the
prior `strftime` contracts exactly).

## WP08 — runtime (`src/runtime/`, `tests/next/`, `tests/runtime/`; incl. FR-014/D-1)

`naive=∅`. All wall-clock sites in `_internal_runtime/{contracts,engine,
retrospective_terminus}.py`, `runtime_bridge.py`, and `runtime_bridge_engine.py`
used only aware forms (`datetime.now(UTC)`, `datetime.now(timezone.utc)`).
No naive site existed to adjudicate. `now_naive_local()` was NOT added to
the door.

D-1 (FR-014): `engine.py` and `retrospective_terminus.py` are now routed
through the door directly (no second sanctioned module added — the plan's
recommended default). The `_internal_runtime/{planner,workflow_registry,
workflow_schema}.py` no-kernel-imports docstrings were updated to record
`kernel.clock` as the one sanctioned exception: the invariant protects
runtime re-extractability (not depending on doctrine-family internals), and
`kernel` is the stdlib-only layer floor with no doctrine-family coupling, so
importing `kernel.clock` does not violate that rationale.
`test_shared_package_boundary.py` / `test_no_runtime_pypi_dep.py` /
`test_layer_rules.py` re-confirmed green after the docstring update (D-1
does not regress a boundary test).

## WP09 — specify_cli/sync (`src/specify_cli/sync/`, `tests/sync/`)

`naive=∅` for FR-011 byte-changing local-time bugs — no genuinely naive
`datetime.now()`/`utcnow()` site (a local-time value mislabeled as an
instant) existed in this owner's paths. All datetime-returning/serialized
sites used aware forms (`datetime.now(UTC)`) and are routed onto `now_utc()`
/ `now_utc_iso()` unchanged. `now_naive_local()` was NOT added to the door.

**Adjudicated separately — epoch computations in disguise, NOT naive-local
bugs (byte-identical, no migration note needed):**

| Site | Was | Now | Byte-changing? |
|---|---|---|---|
| `src/specify_cli/sync/queue.py` (5 sites: `queue_event`/`upsert_coalesced` persisted `queue.timestamp` column) | naive `int(datetime.now().timestamp())` | `int(now_epoch())` | **No.** A naive `.now()` immediately reduced via `.timestamp()` resolves to the same Unix epoch float `time.time()`/`now_epoch()` would produce for that instant (`.timestamp()` on a naive value is interpreted in the system's local timezone, then converted to epoch — the same physical instant, not a local-time-labelled string). This is an epoch computation, not a serialized local-time value, so it does not fall under FR-011's naive-local adjudication; see the mapping-harness entry `specify_cli.sync.queue.OfflineQueue#persisted_timestamp` (`tests/kernel/test_byte_identity_mapping.py`) for the behaviour proof. |
| `src/specify_cli/sync/body_queue.py` (5 sites: `created_at`/`next_attempt_at`/`first_failed_at`/`last_failed_at` persisted SQLite epoch columns) | raw `time.time()` | `now_epoch()` | **No.** `now_epoch()` is defined as exactly `DEFAULT_CLOCK.now_epoch()` → `time.time()` (WP03); byte-identical delegation. See `specify_cli.sync.body_queue.OfflineBodyUploadQueue#persisted_epoch` in the mapping harness. |
| `src/specify_cli/sync/diagnose.py:345` (`oldest_task_age_seconds` diagnostic) | raw `time.time()` | `now_epoch()` | No — a live diagnostic float, not persisted. |
| `src/specify_cli/sync/owner.py:1039` (`DaemonOwnerRecord.started_at`) | `datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S+00:00")` | `now_utc_seconds()` | **No.** For a UTC-tzinfo datetime, `strftime("%Y-%m-%dT%H:%M:%S+00:00")` and `isoformat(timespec="seconds")` render identically (verified: both produce the `+00:00`-suffixed zero-offset form) — confirmed byte-identical via `specify_cli.sync.owner.build_foreground_owner_record#started_at` in the mapping harness. |

C-005 (Lamport distinction): `src/specify_cli/sync/clock.py`'s Lamport
logical-clock module already had its `now_utc_iso` import repointed to
`kernel.clock` in WP01a (mechanical import-only repoint); its logical-clock
counter logic is untouched by this WP, per C-005.

The freshness-bounds idiom (`before = datetime.now(UTC)` / … / `after =
datetime.now(UTC)`) in `tests/sync/test_emitter_occurrence_time.py` was
migrated to the door's `now_utc()` per the plan's named idiom migration.

## WP10 — specify_cli/status + merge + coordination (`src/specify_cli/{status,merge,status_service,coordination}/`, `tests/{status,merge}/`)

`naive=∅`. Every wall-clock site across `coordination/{status_transition,
transaction,types}.py` and `status/{doctor,emit,lifecycle,lifecycle_events,
validate}.py` used only aware forms (`datetime.now(UTC)`) or parse/format
helpers (`datetime.fromisoformat`, `datetime.fromtimestamp(…, tz=UTC)`); no
genuinely naive `datetime.now()`/`utcnow()` site existed to adjudicate.
`now_naive_local()` was NOT added to the door. (`src/specify_cli/merge/` and
`src/specify_cli/coordination/status_service.py` carried zero raw datetime/
wall-clock sites already — nothing to migrate there.)

Notable routings (all byte-identical, registered in
`tests/kernel/test_byte_identity_mapping.py`):

| Site | Was | Now | Byte-changing? |
|---|---|---|---|
| `coordination/status_transition.py` (batch `StatusEvent.at` / annotation `at`, persisted `status.events.jsonl`) | `datetime.now(UTC)` anchor + `timedelta` offset + `.isoformat()` | `now_utc()` anchor (same arithmetic) | No — `now_utc()` is exactly `DEFAULT_CLOCK.now()` → `datetime.now(UTC)`. |
| `status/emit.py` (batch-claim `StatusEvent.at` / annotation `at`, same shape as above) | `datetime.now(UTC)` anchor | `now_utc()` anchor | No. |
| `coordination/transaction.py` (`CommitReceipt.committed_at`, in-memory `datetime` field, not itself serialized to a string in this module) | `datetime.now(UTC)` | `now_utc()` | No. |
| `status/doctor.py` (`check_stale_claims` age comparison) | `datetime.now(UTC)` / `datetime.fromisoformat` | `now_utc()` / `parse_iso()` | No. |
| `status/lifecycle.py` (`_parse_dt`, `_fallback_created_at`) | `datetime.fromisoformat` / `datetime.fromtimestamp(mtime, tz=UTC)` | `parse_iso()` / `from_epoch(mtime)` | No — `from_epoch` is exactly `datetime.fromtimestamp(value, tz=UTC)` (WP04). This module already used the WP02 injectable-`Clock` seam (`clock: Clock = DEFAULT_CLOCK`) for its own `now`; only the remaining raw stdlib import/parse sites were routed. |
| `status/lifecycle_events.py` (`_iso_str_to_datetime`, `ProjectInitialized`/`WPCreated` default timestamps) | `datetime.fromisoformat` / `datetime.now(UTC)` | `parse_iso()` / `now_utc()` | No. |
| `status/validate.py` (`_is_valid_iso8601`) | `datetime.fromisoformat` | `parse_iso()` | No. |

C-005: no Lamport-clock files are owned by this WP (the Lamport module lives
under `specify_cli/sync/`, WP09).

## WP11 — specify_cli/core + task_utils + decisions + dossier (`src/specify_cli/{core,task_utils,decisions,dossier,delivery,event_journal}/`, `tests/specify_cli/core/`)

`naive=∅`. Every wall-clock site across `core/{file_lock,stale_detection,
upgrade_notifier,upgrade_probe,vcs/git}.py`, `task_utils/support.py`,
`decisions/{emit,models,service}.py`, and `dossier/{api,drift_detector,
indexer,models,snapshot}.py` used only aware forms (`datetime.now(UTC)`) or
parse/format helpers (`fromisoformat`, `fromtimestamp(…, tz=UTC)`); no
genuinely naive site existed to adjudicate. `now_naive_local()` was NOT
added to the door. (`src/specify_cli/delivery/` and
`src/specify_cli/event_journal/` carried zero raw datetime/wall-clock sites
already — nothing to migrate there.)

`core/file_lock.py`'s naive-*read* fallback ("Treat naive timestamps as UTC
for backwards compatibility", `_record_from_payload`) is defensive handling
of untrusted on-disk JSON, not a naive *write* site — the writer
(`_build_record`) always wrote (and still writes) an aware instant. Not an
FR-011 adjudication target.

Notable routings (all byte-identical, registered in
`tests/kernel/test_byte_identity_mapping.py`):

| Site | Was | Now | Byte-changing? |
|---|---|---|---|
| `core/file_lock.py` (`LockRecord.started_at`, persisted JSON lock record) | `datetime.now(UTC)` / `datetime.fromisoformat` | `now_utc()` / `parse_iso()` | No. |
| `core/upgrade_probe.py` (`UpgradeProbeResult.probed_at`, persisted JSON upgrade-check cache) | `datetime.now(UTC)` | `now_utc()` | No. |
| `core/upgrade_notifier.py` (parses cached `probed_at`) | `datetime.fromisoformat` | `parse_iso()` | No. |
| `core/stale_detection.py` (`get_last_meaningful_commit_time`, `check_wp_staleness`) | `datetime.fromisoformat` / `datetime.now(UTC)` | `parse_iso()` / `now_utc()` | No. |
| `core/vcs/git.py` (git-log/reflog parsers) | `datetime.fromtimestamp(x, tz=UTC)` / `datetime.fromisoformat` / `datetime.now(UTC)` | `from_epoch(x)` / `parse_iso()` / `now_utc()` | No — `from_epoch` is exactly `datetime.fromtimestamp(value, tz=UTC)` (WP04). |
| `task_utils/support.py` (`now_utc() -> str` stamp helper — distinct contract from the door's own datetime-returning `now_utc()`, C-003; same name, kept for caller compatibility) | `datetime.now(UTC).strftime(TIMESTAMP_FORMAT)` | delegates to `now_utc_stamp()` | No — `TIMESTAMP_FORMAT` was already the door's `UTC_SECOND_TIMESTAMP_FORMAT` (aliased, WP03); `now_utc_stamp()` is defined as exactly `DEFAULT_CLOCK.now().strftime(UTC_SECOND_TIMESTAMP_FORMAT)`. |
| `decisions/emit.py` / `decisions/service.py` (retired module-local `_now_utc()` helpers, identical bodies) | `datetime.now(UTC)` | call sites now read `kernel.clock.now_utc()` directly | No. Persisted via `status.events.jsonl` `at` field (emit.py) and `decisions/index.json` `IndexEntry.created_at`/`resolved_at` + `DM-<id>.md` rendering (service.py). |
| `dossier/models.py` (`ArtifactRef.indexed_at`, `MissionDossier.dossier_created_at`/`dossier_updated_at`, `MissionDossierSnapshot.computed_at` — 4 identical `default_factory` sites) | `default_factory=lambda: datetime.now(UTC)` | `default_factory=now_utc` | No. |
| `dossier/indexer.py` / `dossier/snapshot.py` (direct call sites feeding the same model fields) | `datetime.now(UTC)` | `now_utc()` | No. |
| `dossier/drift_detector.py` (`BaselineSnapshot.captured_at`, persisted `parity-baseline.json`) | `datetime.now(UTC)` / `datetime.fromisoformat` | `now_utc()` / `parse_iso()` | No. |
| `dossier/api.py` (parses `indexed_at` from a snapshot summary dict) | `datetime.fromisoformat` (in-function import) | `parse_iso()` | No. |
| `decisions/models.py`, `core/vcs/types.py` (type annotations only: `created_at: datetime`, `timestamp: datetime`, etc.) | `from datetime import datetime` | `from kernel.clock import datetime` | No — type re-export only, no behaviour. |

## WP12 — specify_cli/cli/commands/agent (`src/specify_cli/cli/commands/agent/`)

`naive=∅`. Every wall-clock site across `mission_parsing.py`, `tasks.py`,
`tasks_materialization.py`, `tasks_move_task.py`, and
`tasks_parsing_validation.py` used only aware forms (`datetime.now(UTC)`) or
`datetime.fromisoformat`; no genuinely naive site existed to adjudicate.
`now_naive_local()` was NOT added to the door. `workflow.py` carried only an
unused `from datetime import UTC` (dropped — the door's `UTC` is a click
away for any future consumer in this module, but nothing here reads it).

Two module-local stamp helpers named/shaped exactly like the WP03 dup-constant
family (FR-004) had their bodies routed to the door's `now_utc_stamp()`
rather than reading the wall clock directly (both already imported
`UTC_SECOND_TIMESTAMP_FORMAT`/`TIMESTAMP_FORMAT` sourced from the door, WP03):

| Site | Was | Now | Byte-changing? |
|---|---|---|---|
| `mission_parsing._utc_now_iso()` | `datetime.now(UTC).strftime(TIMESTAMP_FORMAT)` | delegates to `now_utc_stamp()` | No — `TIMESTAMP_FORMAT` was already the door's `UTC_SECOND_TIMESTAMP_FORMAT`. |
| `tasks.py` (history-entry timestamp) | `datetime.now(UTC).strftime(UTC_SECOND_TIMESTAMP_FORMAT)` | `now_utc_stamp()` | No. |
| `tasks_materialization.py` (review-override timestamp) | `datetime.now(UTC).strftime(UTC_SECOND_TIMESTAMP_FORMAT)` | `now_utc_stamp()` | No. |
| `tasks_move_task.py` (auto-approval-ref date stamp, `%Y%m%d` — a DISTINCT contract, C-003, no existing door producer) | `datetime.now(UTC).strftime('%Y%m%d')` | `format_stamp(now_utc(), '%Y%m%d')` | No — `format_stamp` wraps `.strftime` verbatim (WP04); same instant source (`now_utc()`), same format string. |
| `tasks_parsing_validation.py` (`_latest_status_event_time` parse; `now = datetime.now(UTC)` staleness comparison) | `datetime.fromisoformat` / `datetime.now(UTC)` | `parse_iso()` / `now_utc()` | No. |

Registered in `tests/kernel/test_byte_identity_mapping.py` is not needed for
the `mission_parsing`/`tasks`/`tasks_materialization` stamp sites: they
delegate to `now_utc_stamp()` verbatim (no additional formatting/arithmetic
after the door call returns), so they are covered by that producer's own
WP03 self-check golden. The `tasks_move_task.py` date-stamp site (a distinct
`%Y%m%d` contract) and the `tasks_parsing_validation.py` staleness-comparison
`now_utc()` call (not itself serialized — only used for a `>` comparison
against parsed event times) likewise need no separate registry entry: the
former is exercised by `format_stamp`'s own WP04 round-trip tests, the
latter never produces a persisted byte.

## WP13 — specify_cli/cli, rest (`src/specify_cli/cli/` excl. `cli/commands/agent/`)

| Site | Was | Now | Byte-changing? | Test |
|---|---|---|---|---|
| `cli/commands/init.py` (`ProjectMetadata.initialized_at`, persisted `.kittify/metadata.yaml`) | naive `datetime.now()` | aware-UTC `now_utc()` | **Yes** — `ProjectMetadata.save()` renders `self.initialized_at.isoformat()`; a naive `datetime.isoformat()` has no UTC offset suffix, an aware one gets `+00:00`. Every freshly-`init`'d project's `metadata.yaml` gains the offset. | `tests/specify_cli/cli/commands/test_init_integration.py::test_metadata_initialized_at_is_aware_utc` — asserts the on-disk `initialized_at` string ends with `+00:00` (fails if the door call is reverted to a naive `datetime.now()`). |
| `cli/commands/upgrade.py` (`metadata.last_upgraded_at`, persisted `.kittify/metadata.yaml`, the "no migrations needed, still stamp the version" path) | naive `datetime.now()` | aware-UTC `now_utc()` | **Yes** — same `ProjectMetadata.save()` serializer as `initialized_at` above; `last_upgraded_at` is explicitly masked (not omitted) in the compare-before-write dedup check (`_mask_volatile_metadata`), so the on-disk bytes still change on every stamped upgrade. | `tests/specify_cli/cli/commands/test_upgrade_command.py::test_no_op_upgrade_stamps_last_upgraded_at_as_aware_utc` — asserts the on-disk `last_upgraded_at` string ends with `+00:00` (fails under the same naive-revert mutation). |
| `cli/commands/glossary.py` (`_load_store_from_seeds`, 2 sites: the `GlossarySenseUpdated`/`GlossaryClarificationResolved` event-replay fallback used when an event dict lacks a `timestamp` field, `Provenance.timestamp`) | naive `datetime.fromisoformat(event.get("timestamp", datetime.now().isoformat()))` | `parse_iso(event.get("timestamp", now_utc_iso()))` | **Yes** — a naive fallback, once round-tripped through `fromisoformat`, produces a naive `Provenance.timestamp`; any downstream serializer of that field (e.g. `glossary/models.py::term_sense_to_dict`) would render it without a UTC offset. Rare in practice (only trips when a replayed event is missing its `timestamp` key), but adjudicated per FR-011 rather than left un-audited. | `tests/agent/cli/commands/test_glossary.py::TestStoreHelpers::test_replayed_sense_missing_timestamp_gets_aware_utc_fallback` — writes a `GlossarySenseUpdated` event with no `timestamp` field and asserts the resulting sense's `provenance.timestamp.tzinfo` is not `None` (fails if the door's `now_utc_iso()` fallback is reverted to a naive `datetime.now().isoformat()`). |

Adjudication: all three sites above are converted (not pinned-naive) — the
"naive local-time bug is fixed" scenario from spec.md, not a legitimate
local-display consumer. `now_naive_local()` was NOT added to the door (no
WP13 site needed it).

All other WP13 wall-clock sites (`_auth_doctor.py`, `_auth_status.py`,
`charter/_status_collectors.py`, `charter/_widen.py`, `doctor.py`,
`retrospect.py`, `sync.py`, `cli/helpers.py`, and the ten owned test files)
used only aware forms (`datetime.now(UTC)`, `datetime.now(tz=UTC)`) or
parse/format helpers (`datetime.fromisoformat`, `datetime.strptime`); no
further genuinely naive site existed to adjudicate.

Byte-identical routings persisted to disk are registered in
`tests/kernel/test_byte_identity_mapping.py` (`_auth_doctor.assemble_report`,
`widen.state.WidenPendingStore.add_pending`, `cli.helpers._render_nag_if_needed`,
`cli.commands.upgrade._record_agent_choice` — all `datetime.now(UTC)` →
`now_utc()`, unchanged shape). Sites that only ever feed a duration
comparison or display string (`_auth_doctor`'s/`_auth_status`'s/`sync.py`'s
token-expiry and "N ago" `now_utc()` calls, `retrospect.py`'s backfill-window
`now_utc()`, `doctor.py`'s stale-sweep `now=now_utc()` threshold, and every
`parse_iso`/`parse_stamp` parse-only call) never produce a persisted byte and
need no registry entry.

## WP13b — specify_cli/auth + specify_cli/compat (`src/specify_cli/auth/`, `src/specify_cli/compat/`, `tests/auth/`)

`naive=∅`. Every wall-clock site across `auth/{device_flow/state,flows/
authorization_code,flows/device_code,flows/refresh,http/transport,loopback/
state,session,session_hot_path,transport}.py` and `compat/{cache,history,
planner}.py` used only aware forms (`datetime.now(UTC)`, `datetime.now(tz=
UTC)`) or parse/format helpers (`datetime.fromisoformat`) — no genuinely
naive `datetime.now()`/`utcnow()` site existed to adjudicate. `now_naive_
local()` was NOT added to the door.

**`time.time()` sites — adjudicated as epoch computations, not naive-local
bugs (byte-identical, no migration note needed):**

| Site | Was | Now | Byte-changing? |
|---|---|---|---|
| `auth/session_hot_path.py::publish_session_hot_path` (persisted `session.hot-path.json` `generated_at` field) | raw `time.time()` | `now_epoch()` | **No.** `now_epoch()` is defined as exactly `DEFAULT_CLOCK.now_epoch()` → `time.time()` (WP03); byte-identical delegation. Registered as `specify_cli.auth.session_hot_path.publish_session_hot_path#generated_at` in the mapping harness. |
| `auth/session_hot_path.py::load_session_hot_path` (freshness-comparison `now` against the parsed `generated_at`) | raw `time.time()` | `now_epoch()` | No — a live comparison value, never itself persisted. |
| `compat/history.py::UpgradeAttemptStore.consecutive_failure_count` (`cutoff` window-comparison against the persisted `created_at` epoch column, itself a `record.timestamp.timestamp()` derivation) | raw `time.time()` | `now_epoch()` | No — `cutoff` is a comparison threshold, never itself persisted; the epoch semantics match the column it's compared against (both are wall-clock Unix epoch, not intra-process duration), so `now_epoch()` — not `monotonic` — is the correct route per the classification rule (elapsed-window-over-persisted-wall-clock-epoch). |

**Persisted, byte-identical `datetime.now(UTC)` → `now_utc()` routings**
(registered in `tests/kernel/test_byte_identity_mapping.py`; representative
entries only where multiple call sites share the identical producer/prior
shape, per the WP11/WP12 dossier-style convention):

| Site | Was | Now | Byte-changing? |
|---|---|---|---|
| `auth/flows/{authorization_code,device_code,refresh}.py` (`StoredSession.issued_at`/`access_token_expires_at`/`last_used_at`, persisted `session.json` via `to_dict()`/`to_json()`) and `auth/session.py::StoredSession.touch()`/`is_access_token_expired()`/`is_refresh_token_expired()` | `datetime.now(UTC)` | `now_utc()` | **No.** Registered (one representative entry) as `specify_cli.auth.session.StoredSession#issued_at`. |
| `compat/planner.py::plan()`'s `now` default (feeds `_write_nag_cache_for_fetch`'s persisted `NagCacheRecord.fetched_at`, `.kittify/upgrade-nag-cache.json`) | `datetime.now(UTC)` | `now_utc()` | **No.** Registered as `specify_cli.compat.planner.plan#now_default`. |
| `auth/device_flow/state.py` (`DeviceFlowState.created_at`/`expires_at`/`last_polled_at`) and `auth/loopback/state.py` (`PKCEState.created_at`/`expires_at`) | `datetime.now(UTC)` | `now_utc()` | No — both dataclasses are explicitly documented as in-flight, in-memory-only (never persisted); no registry entry needed. |
| `auth/http/transport.py`/`auth/transport.py` (`_force_access_token_expired`, in-memory `session.access_token_expires_at` mutation for test-forcing a refresh) | `datetime.now(UTC)` | `now_utc()` | No — mutates an in-memory session object; not itself a persistence boundary. |

All other `now_utc()`/`parse_iso()` routings (token-expiry comparisons in
`session.py`/`session_hot_path.py`/`device_flow/state.py`/`loopback/state.py`,
and every `datetime.fromisoformat` parse-only call in `session.py`,
`compat/cache.py`, `compat/history.py`, `auth/flows/*.py`,
`auth/session_hot_path.py`) never produce a persisted byte on their own (they
either feed a boolean/`timedelta` comparison or reconstruct an in-memory
`datetime` already covered by the producer-side registry entry above) and
need no separate registry entry.

C-005: no Lamport-clock files are owned by this WP (the Lamport module lives
under `specify_cli/sync/`, WP09).
