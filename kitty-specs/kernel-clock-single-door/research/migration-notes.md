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
