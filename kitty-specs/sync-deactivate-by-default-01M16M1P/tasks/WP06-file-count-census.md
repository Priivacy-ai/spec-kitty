---
work_package_id: WP06
title: File-count census guard
dependencies:
- WP01
- WP05
requirement_refs:
- FR-013
planning_base_branch: spike/3799-sync-deactivation-3798-accept-hermetic
merge_target_branch: spike/3799-sync-deactivation-3798-accept-hermetic
branch_strategy: Planning artifacts for this mission were generated on spike/3799-sync-deactivation-3798-accept-hermetic. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into spike/3799-sync-deactivation-3798-accept-hermetic unless the human explicitly redirects the landing branch.
subtasks:
- T017
history:
- at: '2026-08-29T11:58:38Z'
  actor: claude
  action: created
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_sync_deactivate_census.py
execution_mode: code_change
owned_files:
- tests/architectural/test_sync_deactivate_census.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Before reading further, load your assigned agent profile via `/ad-hoc-profile-load python-pedro` (role: implementer). Then read the mission plan.md "Post-plan squad corrections (BINDING)" section and the relevant contracts/ file — they are authoritative over this prompt where they conflict.

## Objective

Lock the gated sync-test file set so that BOTH silent deletion (a file gone) AND silent un-skipping (a `skipif` removed) fail a test — closing the "deleted test = 0 failures = green" loophole.

- **T017** — a census guard that recomputes the **live set** of skipif-carrying files and asserts `live_set == FROZEN_SET`, where `FROZEN_SET` is loaded from `tests/architectural/census/sync_deactivate_test_census.txt` (frozen in WP01).

## Context

Authoritative sources:

- **plan.md → BINDING** item 5b — the census is a **frozen sorted SET of skipif-carrying file paths**, NOT a count (a rename would mask a deletion). `live_set == FROZEN_SET` reds on both deletion and un-skip.
- **spec.md** — FR-013 (file-count census), NFR-003 (census matches exactly), SC-003 (deletion and un-skip both fail).
- Reuse the shape of `tests/architectural/test_sync_env_census.py` (census-file loading + set comparison convention).

**Why a SET, not a count** (BINDING item 5b): a bare count would let a rename mask a deletion (delete one file, rename another into its slot → count unchanged). Comparing the SET of paths catches deletion (path missing from live) and rename (unexpected path in live); comparing that the same paths still *carry the skipif* catches un-skipping.

**Two failure modes to detect**:
1. **Deletion** — a frozen path no longer exists / no longer appears in the live skipif-carrying set → `live_set` is missing an element → red.
2. **Un-skip** — a file still exists but its `skipif` guard was removed → it drops out of the live skipif-carrying set → red.

Depends on WP01 (the frozen census file) and WP05 (the skipif guards must be in place, so the live set matches the frozen set at HEAD).

## Per-Subtask Guidance

### T017 — Census guard test

**Steps**
1. Create `tests/architectural/test_sync_deactivate_census.py`.
2. Load `FROZEN_SET` from `tests/architectural/census/sync_deactivate_test_census.txt` (repo-root-relative paths, sorted; produced in WP01/T004).
3. Compute `live_set`: walk the tests tree over the census's covered roots and collect every module whose source contains the sync `skipif` guard (match on the canonical reason string / the `sync_active` skipif expression added in WP05 — pick a stable, unambiguous marker so an un-skipped file drops out). Normalize to repo-root-relative paths.
4. Assert `live_set == FROZEN_SET`. On mismatch, produce a helpful diff message: `missing (deleted/un-skipped): ...` and `unexpected (new/renamed): ...`.
5. Keep complexity ≤ 15 — extract a `collect_skipif_files(roots) -> set[str]` helper and a `load_frozen(path) -> set[str]` helper; test the helpers if needed.

**Files**: `tests/architectural/test_sync_deactivate_census.py` (new).

**Census file format** (`sync_deactivate_test_census.txt`, produced in WP01/T004) — repo-root-relative, one path per line, sorted, e.g.:
```
tests/cli/commands/test_sync_daemon.py
tests/delivery/test_delivery_emit.py
tests/dossier/test_snapshot_emit.py
tests/integration/test_offline_queue_overflow.py
tests/specify_cli/sync/test_bootstrap.py
tests/stress/test_concurrent_emits.py
tests/sync/test_emitter_observability.py
...
```

**Detection approach** (pick one, keep it stable):
- **Text-marker match** (simplest): treat a file as skipif-carrying iff its source contains the canonical skipif marker WP05 uses — key on the exact reason substring (e.g. `"opt-in via SPEC_KITTY_ENABLE_SAAS_SYNC (#3799)"`) or on `pytest.mark.skipif(not sync_active()`. Choose whichever WP05 standardized on and reference it explicitly so the two WPs cannot drift.
- **AST match** (sturdier against reformatting): parse each module and look for a module-level `pytestmark` containing a `skipif` call whose condition references `sync_active`. Higher fidelity, slightly more code — still under the complexity ceiling if extracted into a helper.

**Validation**:
- `.venv/bin/python -m pytest tests/architectural/test_sync_deactivate_census.py -q` → **green** at HEAD (live == frozen).
- Negative proof (do NOT commit): temporarily delete a skipif from one gated module → the test reds (un-skip caught); temporarily rename/remove a gated file → the test reds (deletion caught). Revert the probe.

## Branch Strategy

- Planning base branch == merge target branch == `spike/3799-sync-deactivation-3798-accept-hermetic`; `branch_strategy: already-confirmed`.
- `spec-kitty implement WP06` allocates the execution worktree from the computed lane in `lanes.json`.
- WP06 depends on WP01 (frozen census) and WP05 (skipif in place). Land after WP05 so the live set matches.

## Test Strategy

- **Test-first / red-first (DIR-034)**: the census test itself IS the guard. Write it, confirm it is green at HEAD, then prove it reds on a simulated deletion and a simulated un-skip (revert both probes).
- The comparison MUST be a SET of paths, not a count (BINDING item 5b) — a count is insufficient.
- Match the skipif via a stable marker (the canonical reason string or the `sync_active` skipif AST/text) so an un-skipped file reliably drops out of `live_set`.
- **ruff + mypy clean**, complexity ≤ 15 (extract helpers).
- **Targeted pytest only**; never the full suite. **Env footguns**: `.venv/bin/python -m pytest`, never `uv run`. This guard runs on the default path (no opt-in needed — it inspects source, not runtime behavior).

## Definition of Done

- `test_sync_deactivate_census.py` loads the WP01 frozen SET and asserts `live_set == FROZEN_SET` (**FR-013**).
- Deletion of a gated file reds; removal of a `skipif` reds (**SC-003**, NFR-003) — both proven via reverted probes.
- Helpful diff on mismatch; complexity ≤ 15; ruff + mypy clean.

## Risks

| Risk | Mitigation |
|------|------------|
| Count-based census lets a rename mask a deletion | Compare a SET of paths (BINDING item 5b). |
| Fragile skipif detection misses an un-skip | Match on a stable canonical reason string / `sync_active` skipif marker chosen in WP05. |
| Live set diverges from WP05's edited set | WP05 keeps its edited set == the WP01 census SET; this test enforces it. |
| Walk picks up non-census roots and over/under-counts | Scope the walk to the census's covered roots; normalize paths consistently. |

## Reviewer Guidance

- Confirm the comparison is set-based on paths, not a count.
- Confirm the live-set detection keys on a stable skipif marker so an un-skip drops the file.
- Confirm the test is green at HEAD and reds on both a simulated deletion and a simulated un-skip (ask for the probe output or reproduce).
- Confirm complexity ≤ 15 (helpers extracted) and ruff + mypy clean.

---
## Post-tasks squad correction (BINDING)
**Detection = TEXT-marker match, not AST module-level pytestmark.** WP05 uses per-test `@pytest.mark.skipif` for #2809's two tests, which a module-level `pytestmark` scan would miss. Compute `live_set` as every test file whose source contains the canonical reason string:
```
sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run
```
Assert `live_set == FROZEN_SET` (loaded from `tests/architectural/census/sync_deactivate_test_census.txt`, frozen in WP01 T004 as exact file paths, not globs). Deletion (file gone) and un-skip (reason string removed) both red.
