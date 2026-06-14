---
work_package_id: WP01
title: Safe-now coverage-neutral test reductions
dependencies: []
requirement_refs:
- FR-006
- FR-008
- FR-013
- NFR-003
tracker_refs: []
planning_base_branch: feat/test-suite-acceleration
merge_target_branch: feat/test-suite-acceleration
branch_strategy: Planning artifacts for this mission were generated on feat/test-suite-acceleration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/test-suite-acceleration unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-test-suite-acceleration-01KV3H59-01KV3H59
base_commit: c0f798f34de5717550053cc547d75cdbfdd82ad5
created_at: '2026-06-14T17:28:33.179069+00:00'
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Safe-now wave
agent: claude
shell_pid: '70899'
history:
- at: '2026-06-14T17:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: tests/charter/test_integration.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/charter/test_integration.py
- tests/mission_metadata/test_mission_identity.py
- tests/sync/test_final_sync_diagnostics.py
- pytest.ini
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Safe-now coverage-neutral test reductions

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter before parsing the rest of this prompt.

- **Profile**: `randy-reducer` (semantic compression: fewer lines/iterations, same proven behavior)
- **Role**: `implementer`
- **Agent/tool**: `claude`

Randy's envelope rule applies: map what must NOT change first, then remove only redundancy evidence proves is redundant. Keep every functional assertion.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

## Objectives & Success Criteria

Land the four coverage-neutral wins that need **no** parallelism dependency. Together they remove ≥60s of CI CPU per push (NFR-003) and shave local time, with **zero** change to what any test asserts.

**Done when**: all four changed areas pass serially; the full-volume ULID path is reachable via env gate; `pytest.ini` no longer forces `-v`; no functional assertion was deleted.

## Context & Constraints

- Evidence: `architecture/test-suite-acceleration-plan.md` (items R4/PP-06a, R5/A4/PP-02, R10 part 1, B2 `-v`).
- Constraints: C-001 (no coverage loss), C-004 (preserve volume-sensitive power via a retained full path), C-006 (no production signature change — patch sleep at module scope only).
- This is the safe-now wave (FR-013). Do NOT touch `.github/workflows/ci-quality.yml` (owned by WP05) — the slow-test CI de-dup lives there.

## Branch Strategy

- **Strategy**: feat/test-suite-acceleration planning base; lane base from lanes.json at implement time.
- **Planning base branch**: feat/test-suite-acceleration
- **Merge target branch**: feat/test-suite-acceleration

## Subtasks & Detailed Guidance

### Subtask T001 – Convert charter `<0.1` timing floors to `@pytest.mark.timeout`

- **Purpose**: The two `assert elapsed < 0.1` floors at `tests/charter/test_integration.py:427` and `:450` flake under CPU contention and block parallelizing the charter shard (WP05 depends on this).
- **Steps**:
  1. At both sites, remove the `elapsed < 0.1` wall-clock assertion.
  2. Add `@pytest.mark.timeout(2)` (generous ceiling — still trips a pathological O(n) regression) to each affected test function.
  3. **Keep verbatim** the functional assertions that accompany them (`isinstance(...)`, `len(...) == 2`, any spy/cache-call-count checks).
  4. Audit the rest of `tests/charter/test_integration.py` for other tight (`< 0.5`) wall-clock floors; convert only tight contention-sensitive ones, leave generous (`< 2.0`/`< 5.0`) NFR budgets as-is.
- **Files**: `tests/charter/test_integration.py`.
- **Notes**: `pytest-timeout` is already a dependency. Do not delete the timing intent — the timeout preserves it.

### Subtask T002 – Reduce ULID volume 100→25 with a full-volume env gate

- **Purpose**: A `@slow` ULID volume test generates ~100 ULIDs (~0.49s × ~75 iters ≈ 36s/push + 36s local). 25 proves the uniqueness/ordering contract; 100 stays available for nightly.
- **Steps**:
  1. Locate the ULID volume test. Start at `tests/mission_metadata/test_mission_identity.py`; confirm via `grep -rn "range(100)" tests/` and the audit's R4 reference. If it lives elsewhere, edit that file and record a one-line rationale in the Activity Log (out-of-map edit) rather than forcing the wrong file.
  2. Introduce `_VOLUME = 100 if os.environ.get("SPEC_KITTY_ULID_VOLUME_FULL") else 25` and use it for the iteration count.
  3. **Keep both assertions unchanged**: uniqueness (`len(set(ids)) == _VOLUME`) and pairwise monotonic ordering.
  4. Keep the `@pytest.mark.slow` marker.
- **Files**: the ULID volume test (default `tests/mission_metadata/test_mission_identity.py`).
- **Notes**: Wire the env-gated full run into the nightly path in coordination with WP05’s slow job (note it in the Activity Log; do not edit CI here).

### Subtask T003 – Sync swallow tests → module-scoped sleep no-op

- **Purpose**: Two `_guarded_final_sync` swallow tests sleep through real retry backoff (~4s on fast-sync).
- **Steps**:
  1. In `tests/sync/test_final_sync_diagnostics.py`, patch the sleep used by the retry loop at **module scope**: `monkeypatch.setattr("specify_cli.sync.batch.time.sleep", lambda *_: None)` (confirm the exact import path of the sleep the code under test calls — patch where it is looked up, not the global `time`).
  2. Add a positive assertion that the retry actually happened, e.g. `assert mock_sync.call_count == 3`, so removing the wait does not weaken the retry guard.
- **Files**: `tests/sync/test_final_sync_diagnostics.py`.
- **Notes**: C-006 — do not change any `src/` signature; this is test-local patching only.

### Subtask T004 – Remove `-v` from `pytest.ini` addopts

- **Purpose**: `addopts = -v --tb=short` forces verbose output in every run, including CI jobs that don’t pass `-q`. Most CI jobs already pass `-q` explicitly; dropping the global `-v` reduces log volume with no behavior change.
- **Steps**:
  1. In `pytest.ini`, change `addopts = -v --tb=short` to `addopts = --tb=short`.
  2. Do not remove `--tb=short`.
- **Files**: `pytest.ini`.
- **Notes**: Per project CLAUDE.md, developers can still pass `-v` locally. This is a CI-noise reduction, not a coverage change.

## Test Strategy

- Run each changed file serially and confirm green: `.venv/bin/pytest tests/charter/test_integration.py tests/sync/test_final_sync_diagnostics.py <ulid_test> -q`.
- Confirm both ULID scales: unset env (25) and `SPEC_KITTY_ULID_VOLUME_FULL=1` (100) both pass.
- `ruff` + `mypy --strict` clean on changed files.

## Risks & Mitigations

- **Risk**: patching the wrong `time.sleep` (global vs module). **Mitigation**: patch at the lookup site in the module under test; assert retry count.
- **Risk**: converting a generous NFR budget to a timeout loses the budget. **Mitigation**: only convert tight `<0.1` floors; leave `<2.0`/`<5.0` as asserts.

## Review Guidance

- Confirm no functional assertion was deleted (only timing floors converted).
- Confirm the ULID full-volume path is reachable and asserts identically.
- Reviewer profile suggestion: randy-reducer self-review or reviewer-renata.

## Activity Log

- 2026-06-14T17:10:00Z – system – Prompt created.
