# Behavioral contracts — loop-reliability-ci-red-burndown-01KXWWD6

This is a remediation slice: it introduces **no new API/schema contracts**. The "contracts" it
delivers are the behavioral invariants each fix establishes or restores, expressed as the
red-first tests each WP flips green (ATDD, C-003). One section per functional requirement.

## C-FR002 — Consumer-repo pre-review-gate calm-degrade (#2534, WP01)
- **Given** a consumer repo without `tests/architectural/_gate_coverage.py`, **when**
  `move-task --to for_review` runs, **then** the gate degrades to a non-blocking `no_coverage`
  warn whose message NEVER names the internal module (`tests.architectural._gate_coverage`) or
  `src/specify_cli/`.
- **Given** spec-kitty's own source repo (`_is_spec_kitty_source_repo` true), **when** the gate
  runs, **then** behavior is byte-for-byte unchanged (still verifies real scope) — NFR-003.
- Verified by: `tests/review/test_pre_review_gate_engine.py`, `..._integration.py` (58 passed).

## C-FR003 — Sync daemon honors the disable env (#2573b, WP02)
- **Given** `SPEC_KITTY_SYNC_DISABLE` or `SPEC_KITTY_SYNC_MINIMAL_IMPORT` is truthy (`is_truthy`
  grammar), **when** an op would spawn the sync daemon, **then** `_daemon_start_skip_reason`
  returns a skip reason as its FIRST check and the daemon does not spawn.
- **Given** neither env is truthy (falsy/unset), **when** the same op runs, **then**
  `_daemon_start_skip_reason` falls through to the pre-existing rollout/intent/policy chain
  unchanged and the daemon spawns as before — INV-2 / NFR-003.
- Verified by: `tests/sync/test_daemon_sync_disable_env.py` (green; 22+ sibling daemon tests, 0 regressions).

## C-FR001 — Shared per-test sync-env-reset fixture (WP03)
- **Given** any test under `tests/sync/`, **when** it runs, **then** the autouse fixture resets
  `SPEC_KITTY_SYNC_DISABLE`/`SPEC_KITTY_SYNC_MINIMAL_IMPORT` at setup without mutating the real
  process env for sibling tests (mirrors the #2794/#2800 isolation pattern).
- Does NOT perturb the serial/real-port suites (LM-8): `test_orphan_sweep.py` + `test_daemon.py -n0` green.

## C-FR004 — Evidence schema-drift guard (#2807, WP04+WP05)
- **Given** `.kittify/config.yaml`'s `charter:` key holds a **path string** (post-#2773), **when**
  `load_url_list_from_config` runs, **then** the `isinstance` guard returns `()` (no crash); the
  dict-shaped path is preserved. The guard never reaches `charter status --json`.
- **Given** manifest v2 tracks both `charter.md` and `charter.yaml`, **when** `test_bundle_contract`
  runs, **then** the fixture seeds a genuinely git-tracked `charter.yaml`.
- **Given** a logged-out CI env (`logged_out_on_connected_teamspace`), **when** `test_upgrade`
  runs, **then** it skips (env-guard, not a blanket xfail); when authed the real assertions run.
- Verified by: `test_charter_epic_golden_path` full e2e (green, past synthesize), `test_phase3_integration`,
  `test_orchestrator`, `test_bundle_contract`, `test_distribution` (all green/skip-when-logged-out).

## C-FR005 — Strict-JSON test isolation, reconciled (#2809→#2782, WP03)
- The FR-001 fixture is the deliverable; red-first **disproved** the leaked-toggle premise. The
  live red of `test_strict_json_stdout` is #2782's `sync.server_auth_failure … Connection refused`
  (out of scope), quarantined to the **non-blocking** `regression visibility` gate — so NFR-001
  (blocking jobs untracked-red-free) holds. #2782 stays open (deferred-with-followup).

## C-FR006 — Urn-lane flake root-fix + loader-coverage gate parity (#2812, WP06)
- **Given** the urn-lane legacy-warning test runs where a global runtime is ambiently configured
  (real `~/.kittify/cache/version.lock`), **when** it asserts one captured `DeprecationWarning`,
  **then** setting `SPEC_KITTY_HOME` to a fresh empty dir makes `_is_global_runtime_configured()`
  False so `_warn_legacy_asset` takes the emit branch (not suppress-and-nudge) — a reload-immune root
  fix at the real env seam (the earlier `__warningregistry__` clear, and a `patch(...)` of the
  predicate, both chased the wrong cause), not a retry.
- **Given** the mission-loader-coverage gate, **then** `platform` is present in BOTH bound sites of
  `ci-quality.yml` (job `if:` + `JOB_GROUPS`), enforced by the FR-011 parity gate
  `test_workflow_coherence.py` (16 passed). Runtime "job actually runs" effect is post-merge-only
  verifiable (gate-unmask-cannot-self-validate).
