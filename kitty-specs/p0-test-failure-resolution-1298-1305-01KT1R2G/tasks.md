# Tasks: P0 Test Failure Resolution — Release Blockers 1298-1305

**Mission**: p0-test-failure-resolution-1298-1305-01KT1R2G  
**Branch**: `main` → merge target: `main`  
**Generated**: 2026-06-01

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|---------:|
| T001 | Run full test suite on current main HEAD, capture commit SHA + counts | WP01 | |
| T002 | Group failures into clusters, compare to #1298 original baseline | WP01 | |
| T003 | Run targeted tests for each P0 cluster to confirm still-reproduces vs stale | WP01 | |
| T004 | Write baseline-refresh document in feature_dir | WP01 | |
| T005 | Run targeted tests to reproduce #1301 cluster (sync + contract) | WP02 | |
| T006 | Confirm `spec_kitty_events` installed version vs uv.lock pin; run uv sync if needed | WP02 | |
| T007 | Remove vendored events tree `src/specify_cli/spec_kitty_events/` if present | WP02 | |
| T008 | Fix daemon allowlist in `test_daemon_intent_gate.py` for missing call site | WP02 | |
| T009 | Update `WPCreated` contract fixture payload to include `actor` + `wp_title` fields | WP03 | |
| T010 | Add `# pydantic_model:` frontmatter to YAML codeblock in `check_docs_freshness.md` | WP03 | |
| T011 | Fix `test_init_emits_project_init_event_offline` (sync lifecycle offline mode) | WP03 | |
| T012 | Fix `test_event_queued_when_no_websocket` (offline queue tracker origin) | WP03 | |
| T013 | Run full #1301 targeted test slice and broader sync/contract suite | WP03 | |
| T014 | Run targeted tests to reproduce #1305 cluster; capture exact failure output | WP04 | |
| T015 | Locate `decide_next` call-site divergence between source and test mocks | WP04 | |
| T016 | Fix dispatch/import so `decide_next` is correctly invoked | WP04 | |
| T017 | Fix exit-code logic for terminal and successful-advance scenarios | WP04 | |
| T018 | Run targeted tests and verify all 4 `tests/next/` tests pass | WP04 | |
| T019 | Run targeted tests to reproduce #1304 cluster | WP05 | |
| T020 | Add `doctrine-pack` anchor to glossary contexts | WP05 | [P] |
| T021 | Add `platform-darwin--platform-linux` anchor to glossary contexts | WP05 | [P] |
| T022 | Fix `five-paradigm-parallel-debugging` tactic YAML (schema + refs) | WP05 | |
| T023 | Run targeted tests and verify all 4 doctrine tests pass | WP05 | |
| T024 | Run targeted tests to reproduce #1303 cluster | WP06 | |
| T025 | Fix synthesizer manifest hash non-determinism (sort keys, ordered construction) | WP06 | |
| T026 | Route any direct write primitives through `path_guard.py` | WP06 | |
| T027 | Add/fix chokepoint coverage registration in synthesizer tests | WP06 | |
| T028 | Regenerate/update fixture hashes after determinism fix | WP06 | |
| T029 | Run targeted tests and verify all 5 charter synthesizer tests pass | WP06 | |

---

## Work Packages

### WP01 — Baseline Refresh

**Goal**: Run the full test suite on current `main` HEAD and produce a documented baseline that answers: which of #1301/#1303/#1304/#1305 still reproduce?  
**Priority**: P0 — gates all other WPs  
**Profile**: `debugger-debbie` (investigator)  
**Dependencies**: none  
**Estimated prompt size**: ~200 lines  

#### Subtasks

- [x] T001 Run full test suite on current main HEAD, capture commit SHA + counts (WP01)
- [x] T002 Group failures into clusters, compare to #1298 original baseline (WP01)
- [x] T003 Run targeted tests for each P0 cluster to confirm still-reproduces vs stale (WP01)
- [x] T004 Write baseline-refresh document in feature_dir (WP01)

#### Implementation Notes

Run `PWHEADLESS=1 pytest tests/ -q --tb=no -p no:cacheprovider 2>&1 | tee /tmp/baseline.txt`. Capture the tail for cluster grouping. Then run the four cluster-targeted commands in sequence to confirm each.

**Risks**: Test suite takes ~15 min. Some issues may already be resolved by intervening commits on main.

**Prompt file**: `tasks/WP01-baseline-refresh.md`

---

### WP02 — #1301 Part A: Package Version, Vendored Tree & Daemon Allowlist

**Goal**: Fix the packaging-level causes of the #1301 cluster — ensure the correct `spec_kitty_events` version is installed, remove the vendored copy, and fix the daemon allowlist.  
**Priority**: P0  
**Profile**: `python-pedro` (implementer)  
**Dependencies**: WP01  
**Estimated prompt size**: ~240 lines  

#### Subtasks

- [ ] T005 Run targeted tests to reproduce #1301 cluster (sync + contract) (WP02)
- [ ] T006 Confirm `spec_kitty_events` installed version vs uv.lock pin; run uv sync if needed (WP02)
- [ ] T007 Remove vendored events tree `src/specify_cli/spec_kitty_events/` if present (WP02)
- [ ] T008 Fix daemon allowlist in `test_daemon_intent_gate.py` for missing call site (WP02)

#### Implementation Notes

Start with `pip show spec-kitty-events` or `uv pip show spec-kitty-events` to inspect the installed version. If diverged, `uv sync --frozen` should restore the pinned version. Verify `src/specify_cli/spec_kitty_events/` existence and delete if present. For the daemon allowlist, read `test_daemon_intent_gate.py` carefully to understand the sentinel pattern, then add the missing call site.

**Risks**: `uv sync` may pull a version that conflicts with other packages. Test with `pytest tests/sync/test_daemon_intent_gate.py -q` after each sub-fix.

**Prompt file**: `tasks/WP02-1301-package-and-daemon.md`

---

### WP03 — #1301 Part B: Contract Fixtures & Sync Lifecycle

**Goal**: Fix the contract-fixture and sync-lifecycle causes of the #1301 cluster — update `WPCreated` payloads, fix the YAML codeblock frontmatter, and repair offline sync lifecycle tests.  
**Priority**: P0  
**Profile**: `python-pedro` (implementer)  
**Dependencies**: WP02  
**Estimated prompt size**: ~300 lines  

#### Subtasks

- [ ] T009 Update `WPCreated` contract fixture payload to include `actor` + `wp_title` fields (WP03)
- [ ] T010 Add `# pydantic_model:` frontmatter to YAML codeblock in `check_docs_freshness.md` (WP03)
- [ ] T011 Fix `test_init_emits_project_init_event_offline` (sync lifecycle offline mode) (WP03)
- [ ] T012 Fix `test_event_queued_when_no_websocket` (offline queue tracker origin) (WP03)
- [ ] T013 Run full #1301 targeted test slice and broader sync/contract suite (WP03)

#### Implementation Notes

Run `pytest tests/contract/test_handoff_fixtures.py -q --tb=long` to see exact missing fields. The `spec_kitty_events 5.2.0` schema requires `actor` and `wp_title` in `WPCreated`. Update fixtures under `tests/contract/` accordingly. For the YAML codeblock, grep for `check_docs_freshness.md` and add the missing `# pydantic_model: <Class>` comment. For offline lifecycle tests, read the test to understand what offline mode they exercise, then trace the source path.

**Risks**: T011/T012 may require source changes in `src/specify_cli/sync/` or `src/specify_cli/next/`. Scope carefully.

**Prompt file**: `tasks/WP03-1301-fixtures-and-lifecycle.md`

---

### WP04 — #1305: `next` CLI Exit-Code Fix

**Goal**: Restore correct exit-code behavior for the `next` CLI command and ensure `decide_next` is properly invoked in all tested scenarios.  
**Priority**: P0  
**Profile**: `python-pedro` (implementer)  
**Dependencies**: WP03  
**Estimated prompt size**: ~290 lines  

#### Subtasks

- [ ] T014 Run targeted tests to reproduce #1305 cluster; capture exact failure output (WP04)
- [ ] T015 Locate `decide_next` call-site divergence between source and test mocks (WP04)
- [ ] T016 Fix dispatch/import so `decide_next` is correctly invoked (WP04)
- [ ] T017 Fix exit-code logic for terminal and successful-advance scenarios (WP04)
- [ ] T018 Run targeted tests and verify all 4 `tests/next/` tests pass (WP04)

#### Implementation Notes

Run `pytest tests/next/ -q --tb=long -s` to see which code path is actually being taken. The key signal is `decide_next mocks are no longer invoked` — this means either the mock target path is stale (refactor moved the symbol) or an early-return prevents reaching the call site. Grep `src/specify_cli/next/` for `decide_next` and compare to the mock path in test files.

**Risks**: If the source was intentionally refactored, fixing the mock target may be the right fix (not reverting the source). Validate the intent from git log.

**Prompt file**: `tasks/WP04-1305-next-exit-code.md`

---

### WP05 — #1304: Doctrine/Glossary Anchor & Tactic Fix

**Goal**: Add missing glossary anchors (`doctrine-pack`, `platform-darwin--platform-linux`) and fix the `five-paradigm-parallel-debugging` tactic schema so all 4 doctrine integrity tests pass.  
**Priority**: P0  
**Profile**: `curator-carla` (curator)  
**Dependencies**: WP04  
**Estimated prompt size**: ~260 lines  

#### Subtasks

- [ ] T019 Run targeted tests to reproduce #1304 cluster (WP05)
- [ ] T020 Add `doctrine-pack` anchor to glossary contexts (WP05)
- [ ] T021 Add `platform-darwin--platform-linux` anchor to glossary contexts (WP05)
- [ ] T022 Fix `five-paradigm-parallel-debugging` tactic YAML — add missing schema fields and resolve refs (WP05)
- [ ] T023 Run targeted tests and verify all 4 doctrine tests pass (WP05)

#### Implementation Notes

Run `pytest tests/doctrine/ -q --tb=long` to see which anchors are missing and which refs are broken. Study existing anchor files under `glossary/contexts/` to understand the format, then add entries. For the tactic, read the schema definition (in `src/specify_cli/doctrine/` or `glossary/`) and compare against the `five-paradigm-parallel-debugging` YAML file. Add required fields and fix `$ref` values that point to removed or renamed terms.

T020 and T021 are marked `[P]` because they touch different anchor files and can be done in either order.

**Risks**: Adding new anchors may surface other tests that referenced these terms expecting them to be absent. Run the full doctrine suite after to check.

**Prompt file**: `tasks/WP05-1304-doctrine-glossary.md`

---

### WP06 — #1303: Charter Synthesizer Determinism Fix

**Goal**: Make synthesizer manifest hash computation deterministic, route all file writes through `path_guard.py`, and ensure chokepoint coverage is complete so all 5 charter synthesizer tests pass.  
**Priority**: P0  
**Profile**: `python-pedro` (implementer)  
**Dependencies**: WP05  
**Estimated prompt size**: ~330 lines  

#### Subtasks

- [ ] T024 Run targeted tests to reproduce #1303 cluster (WP06)
- [ ] T025 Fix synthesizer manifest hash non-determinism (sort keys, ordered construction) (WP06)
- [ ] T026 Route any direct write primitives through `path_guard.py` (WP06)
- [ ] T027 Add/fix chokepoint coverage registration in synthesizer tests (WP06)
- [ ] T028 Regenerate/update fixture hashes after determinism fix (WP06)
- [ ] T029 Run targeted tests and verify all 5 charter synthesizer tests pass (WP06)

#### Implementation Notes

Run `pytest tests/charter/synthesizer/ -q --tb=long` to see hash mismatch values. If hashes differ by only ordering, the fix is to sort keys in the manifest dict before hashing. Audit the synthesizer source for any `Path.write_text()`, `open(..., 'w')`, or `shutil.copy()` calls that bypass `path_guard.py`. The `test_path_guard` and `test_chokepoint_coverage` tests will guide which call sites need routing. After fixing, run the tests again — if hashes now match, update the fixture files.

**Risks**: If the hash mismatch stems from a timestamp embedded in the manifest, removing it is the fix (content-only hash). Don't regenerate fixtures until the determinism root cause is fixed.

**Prompt file**: `tasks/WP06-1303-synthesizer-determinism.md`

---

## Dependency Chain

```
WP01 (Baseline)
  └─► WP02 (#1301-A)
        └─► WP03 (#1301-B)
              └─► WP04 (#1305)
                    └─► WP05 (#1304)
                          └─► WP06 (#1303)
```

All WPs are sequential per planning decision (no parallel lanes).
