# Independent Review — WP03 (reviewer-renata, Op 01KZS0QVDFRH5S3DASD31YM4E0)

## Verdict: **APPROVE**

(Per my governing instructions I do not run `move-task`; the verdict is returned here for the orchestrator to apply.)

## Scope reviewed
Commit `032bc5d62` (lane-c) vs coordination base `kitty/mission-worktree-owned-root-3328-01KZRG01`. Both modified files read in full: `src/specify_cli/cli/commands/next_cmd.py` (+77/−6) and `tests/agent/test_context_validation_unit.py` (+159). Read in full: spec.md, plan.md, contracts/checkout-ownership-cli-contract.md, tasks/WP03-next-integration.md, charter, review prompt, plus WP01's `core/checkout_ownership.py`, `git/commit_helpers.is_worktree_of`, `status/locking.py`, and the runtime bridge plumbing.

## Root-identity probes (real disposable git primary + two linked worktrees, real `spec-kitty` CLI, `PYTHONPATH`=lane-c src, venv `…/spec-kitty/.venv`)

| Probe | Result |
|---|---|
| **1. Primary exact root** `--owned-checkout <primary>` | ✅ Accepted; effective root stays primary. Query decision returned; the run seeded only in the linked checkout was invisible (`run_id: null`). |
| **2. Linked exact root** `--owned-checkout <linked>` | ✅ Accepted; effective root = linked, never primary. Proven two ways: (a) in-process capture at the live entry point showed `_run_query_mode` receiving `/private/tmp/rv3328/linked`; (b) a `feature-runs.json` seeded only under `<linked>/.kittify/runtime/` was read (surfaced as a fixture-validation error from that seeded run), while `owned=primary` and no-flag runs did not see it. |
| **3. Primary subdirectory** `--owned-checkout <primary>/subdir` | ✅ Rejected pre-runtime with typed `{"success": false, "error_code": "OWNERSHIP_NESTED"}`, exit 1 — before runtime notice, charter preflight, or mission lookup (also verified in advancing mode). |
| **4. Linked subdirectory** `--owned-checkout <linked>/src` | ✅ Rejected identically with `OWNERSHIP_NESTED`, exit 1, no mission work. |

Additional probes: generic linked CWD **without** flag → ambient-to-primary behavior byte-preserved (rc 0, linked's seeded run invisible) ✅; `.worktrees/lit` CWD without flag → legacy `require_main_repo` refusal verbatim, exit 1 ✅; `.worktrees/lit` with valid flag → bypass + accept (rc 0) ✅; `.worktrees/lit` with foreign claim → `OWNERSHIP_FOREIGN` ✅ (bypass ≠ acceptance); foreign repo/worktree claims → `OWNERSHIP_FOREIGN` naming both common-dirs ✅; nested registered worktree → `OWNERSHIP_NESTED` ✅; broken gitdir pointer → `OWNERSHIP_BROKEN_POINTER` ✅; human (non-JSON) refusal renders to stderr, exit 1 ✅; status lock `feature_status_lock_path(primary)==feature_status_lock_path(linked)` under the shared git common-dir ✅; no stray writes in any tree after all probes ✅.

## Independent commands/results
- `pytest tests/agent/test_context_validation_unit.py` → **30 passed** (52s)
- `pytest tests/core/test_checkout_ownership.py test_next_preflight.py test_selector_resolution.py` → **56 passed**
- `pytest tests/runtime/test_bridge_io.py tests/runtime/next` → **44 passed**
- `ruff check` both files → clean; `mypy next_cmd.py` → no issues
- Implementer evidence corroborated: RED JUnit (parser rejected `--owned-checkout`), GREEN 723 tests/0 failures, compat 35/0 — consistent with my runs.
- Scope: `git show --stat 032bc5d62` = only the two owned files; `context_validation.py` (shared decorator), `merge.py`, `implement.py` untouched on this lane (grep confirms `owned_checkout` exists only in `next_cmd.py`).

## Anti-pattern checklist
1. Dead code **PASS** (dispatcher + error emitter both live). 2. Synthetic fixtures **PASS** (tests use real `git worktree` topologies; monkeypatching is confined to post-routing internals and is corroborated by my real-CLI probes). 3. Silent empty return **PASS** (`error_for_claim` None-on-OWNED documented). 4. FR coverage **PASS** (FR-002/FR-004/FR-007/C-001/C-002 each have assertions, incl. status-lock exclusion test). 5. Frozen surface **PASS**. 6. Locked decisions **PASS** (no `allow_worktree_context`, no ambient fallback on failed validation, no retrofitted refusal). 7. Shared-file ownership **PASS**. 8. Production fragility **PASS** (only new raise is structured `typer.Exit(1)`).

## Contract / #3128 reconciliation
The success table's `path == CWD` rows and the Non-Goal deferring caller-vs-declared-workspace comparison to #3128 are in apparent tension. Resolution: the table states **sufficient** success conditions; the explicit Non-Goal is binding that the CWD-vs-claimed equality check is **not** enforced by this mission. The implementation follows the Non-Goal — validation is topology-only and CWD-agnostic (probe 2 from a primary CWD claiming the linked root succeeded and routed state there). No contradiction once the table is read as scenario enumeration, but #3128 must know the landed shape: `next --owned-checkout X` from a CWD ≠ X is currently accepted whenever X passes topology validation.

## Findings (none blocking)
- **Observation (medium, out-of-scope note for WP04/WP05/#3128):** mission *content* reads (tasks/status via `mission_context_for`/`placement_seam`) still anchor to the primary checkout even when the effective root is the owned linked checkout — my probe returned MISSION_NOT_FOUND for a mission existing only in the linked working tree until content was mirrored to the primary anchor. FR-007 runtime state (`feature-runs.json`, merge runtime dir) *is* correctly rooted at the owned checkout, which is all T011 requires; but the contract phrase "mission decision resolves against the mission stored at the owned checkout" holds only for runtime state, not artifact reads. Flagging so downstream WPs don't assume otherwise.
- **Nit:** the stale-runtime notice now emits after `locate_project_root()` rather than before (all paths). Cosmetic, human-mode only.
- **Nit:** WP03's new tests invoke `next_step` in-process; real-CLI end-to-end proof for the owned path exists only in this review's live probes (WP05 owns the ATDD concurrency proof). Acceptable given mission decomposition.

## Residual risks
Low. Dispatcher/decorator interplay is Typer-safe (`functools.wraps` + `inspect.signature` unwrap; verified via `--help` and CliRunner test). Path portability confirmed (macOS `/tmp`→`/private/tmp` symlink resolution consistent). No regression surface for non-opt-in callers was observed in any probe.
