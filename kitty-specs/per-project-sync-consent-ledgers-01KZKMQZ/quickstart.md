# Quickstart: Per-Project Sync Consent Ledgers

## Safety boundary

Use `SPEC_KITTY_HOME` pointing at a temporary test directory. Never run migration or consent commands against a real user home or production SaaS account while developing this mission.

## Environment and focused tests

```bash
uv sync
uv run pytest tests/sync/test_project_store.py -q
uv run pytest tests/sync/test_project_consent_authority.py -q
uv run pytest tests/sync/test_consent_epochs.py -q
uv run pytest tests/sync/test_history_disclosure.py -q
uv run pytest tests/sync/test_admission_operations.py -q
uv run pytest tests/sync/test_transport_attempt_recovery.py -q
uv run pytest tests/sync/test_project_store_migration.py -q
uv run pytest tests/sync/test_opt_out_barrier.py -q
uv run pytest tests/sync/test_legacy_grant_writers.py -q
uv run pytest tests/sync/test_daemon_project_isolation.py -q
uv run pytest tests/sync/test_daemon_cutover_protocol.py -q
uv run pytest tests/architectural/test_project_store_boundary.py -q
```

Red-first evidence must run through public CLI/runtime entry points and include admitted positive controls. Tests trap SQLite connects/commits, filesystem/table opens, exact network bytes, and result writes. Epoch cases use monotonic sequence and both capture/opt-in transaction orderings. History tests prove ordinary selection cannot mint a disclosure capability.

## Migration exercise

1. Create a temporary runtime root with mixed A/B legacy journal, delivery, body, and offline state.
2. Add unknown/malformed UUID rows, ledger ghosts, old grants, and explicit refusals.
3. Start a recognized daemon and foreground legacy writer; verify both participate in layout-generation quiesce/redirect.
4. Create WAL-resident committed rows and take a strictly read-only logical snapshot without invoking source schema constructors.
5. Save exact ID/status/attempt/target/timestamp/hash inventory plus main/WAL/SHM treatment.
6. Hard-kill a subprocess before and after every durable migration phase and rerun.
7. Run atomic cutover and prove current writers redirect and live capture/delivery opens only project stores.
8. Write through an unrecognized old-binary fixture after cutover and prove the residue is diagnosed but never delivered.
9. Confirm unknown rows remain in non-deliverable quarantine and old grants/flags do not grant.

The implementation command names are finalized by `/spec-kitty.tasks`; no production or actual home directory is used.

## Full gates

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy --strict src/specify_cli
uv run pytest
```

Run repository architecture/mutation commands and platform CI as defined in the mission WPs. Any pre-existing failure must be filed before it is accepted as baseline.

## Cross-repository contract

After the SaaS mission publishes `../spec-kitty-saas/contracts/cli-saas-current-api.yaml`:

```bash
uv run pytest tests/sync/test_saas_admission_compatibility.py -q
```

Then run the split six-project scenario from `contracts/sender-and-migration-matrix.md` against local/test SaaS or a dynamically discovered Upsun branch environment. The conforming CLI sends only A. Separate bypass/legacy tests prove B–F refusal. A real stale-generation race makes the conforming CLI receive and terminally park `project_not_admitted`. Do not run mutating canaries against `app.spec-kitty.ai`; it is production.

## Reproducible discovery benchmark

Generate 100 deterministic UUID stores: 80 fresh deny hints and 20 authority reads. Record OS, filesystem, storage, CPU, Python, SQLite, commit, and seed. Warm means repeated scans in one process after fixture warm-up; process-cold means a new process and does not claim OS cache eviction. Randomize paired order, retain raw JSON samples, run 200 warm and 30 process-cold scans, and assert 80 denied projects open no `sync.db` payload table. Warm p95 ≤500 ms; process-cold p95 ≤1 s. CI is advisory; the documented local SSD run is the release gate.

## Handoff

Do not push, open a PR, merge to `main`, release, or deploy without explicit operator authorization. Mission review may conclude recurrence prevention only; it cannot close SaaS #585 until the historical 1,322-event disposition is approved and audited.
