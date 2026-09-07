---
work_package_id: WP07
title: Writer Census Addendum (decisions/emit.py, rebuild_state.py)
dependencies:
- WP03
requirement_refs:
- FR-001
- FR-002
- NFR-001
planning_base_branch: missions/coreloop-proto-missions
merge_target_branch: missions/coreloop-proto-missions
branch_strategy: Planning artifacts for this mission were generated on missions/coreloop-proto-missions. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into missions/coreloop-proto-missions unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-fsm-write-path-integrity-01M1TZV6
base_commit: 7b90adcfdaf4ab5ef5229fa466bb6091f5769a07
created_at: '2026-09-06T14:20:14.252697+00:00'
subtasks:
- T040
- T041
- T042
phase: Wave 2 - Census addendum (after WP03 gates)
agent: claude
history:
- at: '2026-09-06T14:20:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks (addendum minted after WP03's gates found two writers the dossier census missed)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/decisions/
create_intent:
- tests/specify_cli/decisions/test_emit_locking.py
- tests/specify_cli/migration/test_rebuild_state_locking.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/decisions/emit.py
- src/specify_cli/migration/rebuild_state.py
- tests/specify_cli/decisions/test_emit_locking.py
- tests/specify_cli/migration/test_rebuild_state_locking.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP07 – Writer Census Addendum

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log. Address every item before completion and log what changed.

## Review Feedback

*[Populated by the reviewer via the status event log.]*

---

## Objectives & Success Criteria

WP03's AST writes-gate (`tests/architectural/test_status_events_writes_gate.py`) found two out-of-pipeline writers of `status.events.jsonl` that the research dossier's census (FR-001, families ①–⑦) did not enumerate. They are ledgered there as **FINDING**, not blessed (`design-notes/WP03-gates.md` §5). SC-008 ("0 unlocked writer families") cannot be claimed until they are hardened. This WP closes them the WP01 way.

Done means:

1. `src/specify_cli/decisions/emit.py:100-112` (`_append_raw_event`, `DecisionPointOpened` rows): the append runs under `feature_status_lock(resolve_status_lock_root(feature_dir), feature_dir.name)` with the atomic primitive `append_raw_rows_atomic` imported from `specify_cli.status._unsafe`; `specify_cli.decisions.emit` is added to `_unsafe.ALLOWED_CALLERS` and the allowlist gate's `BASELINE`; its FINDING entry is removed from the writes-gate ledger (`ALLOWED_OUT_OF_STORE_WRITE_SITES` or equivalent) so the gate proves the raw write is gone.
2. `src/specify_cli/migration/rebuild_state.py:758-766` (whole-log `tmp.open("w")` + `os.replace`): wrapped in the same lock so a concurrent shell append cannot be lost during the rewrite; its ledger entry is re-labelled from FINDING to a documented, locked, atomic rewrite (the `os.replace` shape is fine under the lock).
3. Lock-held tests for both (the WP01 recorder pattern in `tests/status/test_writer_serialization.py`); the seven-family parametrized lock-held test gains these two rows (→ nine families).
4. `design-notes/WP01-lock-rules.md` census table gets an addendum section (write it to the scratch path below; the orchestrator lands it) and the WP03 gate ledger no longer carries a FINDING label for either site.
5. NFR-001: no lock held across a git subprocess in either region.

## Context & Constraints

- Contract `contracts/emit-pipeline.md` §4 (hardening pattern), `contracts/write-gates.md` §1–§3; `design-notes/WP01-lock-rules.md` (lock rules, the `nullcontext()` per-site decision, `BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS`); `design-notes/WP03-gates.md` §5 (the findings and the recommended fixes).
- Depends on WP03 (the `_unsafe` door and both gates exist on your base).
- Out-of-map edits allowed with a one-line rationale each: `src/specify_cli/status/_unsafe.py` (ALLOWED_CALLERS +1), `tests/architectural/test_status_unsafe_allowlist.py` (BASELINE +1), `tests/architectural/test_status_events_writes_gate.py` (ledger −1 FINDING, relabel 1), `tests/status/test_writer_serialization.py` (+2 parametrized rows).
- Sonar: complexity ≤15; no `# noqa`/`# type: ignore`; tests for every new branch. `ruff format` your files (live format gate).
- No kitty-specs files on the lane branch (lane gate); Activity Log via `spec-kitty agent tasks add-history WP07 …`.

## Branch Strategy

- **Strategy**: Planning artifacts were generated on missions/coreloop-proto-missions; completed changes must merge back into missions/coreloop-proto-missions.
- **Planning base branch**: missions/coreloop-proto-missions
- **Merge target branch**: missions/coreloop-proto-missions

Execution worktrees are allocated per computed lane from `lanes.json`; enter yours with `spec-kitty implement WP07 --mission fsm-write-path-integrity-01M1TZV6` (based on WP03's lane).

## Subtasks & Detailed Guidance

### Subtask T040 – Harden `decisions/emit.py` `_append_raw_event`

- **Purpose**: An unlocked, non-atomic append of `DecisionPointOpened` rows is exactly the FR-001/FR-002 defect class; a rollback truncate (`transaction.py:944`) can destroy it.
- **Steps**: read `decisions/emit.py` fully and its callers (`grep -rn "_append_raw_event\|decisions.emit" src`). Replace the raw `events_path.open("a")` with `append_raw_rows_atomic(events_path, [row])` under `feature_status_lock(resolve_status_lock_root(feature_dir), feature_dir.name, timeout=BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS if <reachable from an L3/L5 scope> else -1)` — check whether decision opening can run inside a merge or verdict-save scope; if not, the default is acceptable and documented. Import from `specify_cli.status._unsafe`; add `specify_cli.decisions.emit` to `ALLOWED_CALLERS` (+ BASELINE) with the justification "family ⑧ decision-point rows". Remove the FINDING ledger entry in the writes gate. Red-first: a rollback-truncate race test in the WP01 shape (thread + short timeout) that FAILS before the change.
- **Files**: `src/specify_cli/decisions/emit.py`, `tests/specify_cli/decisions/test_emit_locking.py` (new), out-of-map gate/allowlist rows.
- **Parallel?**: No.

### Subtask T041 – Lock the `rebuild_state.py` whole-log rewrite

- **Purpose**: A migration-only rewrite, but an interleaved shell append during the rewrite is lost.
- **Steps**: wrap `:758-766` (tmp write + `os.replace`) in the mission lock keyed on `feature_dir.name`; keep the `os.replace` shape. Relabel the writes-gate ledger entry (documented locked rewrite). Test: a thread holding the lock blocks the rewrite; an append made before the rewrite is present after it.
- **Files**: `src/specify_cli/migration/rebuild_state.py`, `tests/specify_cli/migration/test_rebuild_state_locking.py` (new), gate ledger row.
- **Parallel?**: Yes.

### Subtask T042 – Census addendum + lock-held rows

- **Purpose**: SC-008 evidence.
- **Steps**: add families ⑧ (`decisions/emit.py`) and ⑨ (`migration/rebuild_state.py`) to the parametrized lock-held test in `tests/status/test_writer_serialization.py`; write the addendum section for `design-notes/WP01-lock-rules.md` (census table rows ⑧/⑨, per-site `nullcontext()` decision, timeout choice) to `/private/tmp/claude-501/-Users-robert-spec-kitty-dev-spec-kitty-20260906-133035-6beqef-spec-kitty/d6a1e43f-e4df-4933-ab8d-8bfde3cb71b9/scratchpad/wp07-planning-artifacts/WP01-lock-rules-addendum.md`; confirm both gates are green with no FINDING label left for these two sites.
- **Files**: tests, scratch note.
- **Parallel?**: No.

## Test Strategy

```bash
.venv/bin/pytest tests/specify_cli/decisions tests/specify_cli/migration tests/status/test_writer_serialization.py tests/status tests/specify_cli/status -q -p no:cacheprovider
.venv/bin/pytest tests/architectural/test_status_unsafe_allowlist.py tests/architectural/test_status_events_writes_gate.py tests/architectural/test_status_module_boundary.py tests/architectural/test_ruff_format_enforcement.py -q
CHANGED=$(git diff --name-only --diff-filter=AMR $(git merge-base HEAD missions/coreloop-proto-missions) | grep '\.py$'); .venv/bin/ruff check $CHANGED && .venv/bin/ruff format --check $CHANGED && .venv/bin/mypy src/specify_cli/decisions/emit.py src/specify_cli/migration/rebuild_state.py
```

## Risks & Mitigations

- Decision opening reachable under an enclosing lock → L1 is re-entrant per thread; add a nesting test if a caller holds L1.
- Migration rewrite under lock spawning git → read the function; it must not (NFR-001).

## Review Guidance

- RED proof for T040 (Activity Log); both gates green with the FINDING labels gone; ALLOWED_CALLERS/BASELINE grew by exactly one; nine-family lock-held test green; no `# noqa`.

## Activity Log

> **CRITICAL**: chronological order, oldest first. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`.

- 2026-09-06T14:20:00Z – system – Prompt created (addendum).
- 2026-09-06T14:57:55Z – claude – shell_pid=12990 – T040 RED proof: tests/specify_cli/decisions/test_emit_locking.py::test_decision_append_waits_for_rollback_and_lands_after_truncate FAILED on the unchanged emit.py -- 'AssertionError: SC-001: the DecisionPointOpened row was truncated away by the rollback / assert []' (1 failed, 33.67s). Then hardened _append_raw_event: feature_status_lock(resolve_status_lock_root(feature_dir), feature_dir.name) + append_raw_rows_atomic via status/_unsafe, Lamport readback under the same acquisition; timeout = lock default (no L3/L5 caller); ALLOWED_CALLERS/BASELINE +1 (family 8); FINDING ledger entry removed; race + lock-held + NFR-001 + AST tests GREEN (21 passed with test_emit.py).
- 2026-09-06T14:57:57Z – claude – shell_pid=12990 – T041 RED proof: tests/specify_cli/migration/test_rebuild_state_locking.py 3 failed on the unchanged rebuild_state.py -- test_append_landing_during_the_rebuild_is_not_lost: "'01EVT0000000000000000LATE' in ['01EVT00000000000000000001'] -- the shell append was lost under the whole-log rewrite"; test_rewrite_runs_while_mission_lock_is_held: os.replace ran with set() locks held. Fix: rebuild_event_log takes L1 keyed on feature_dir.name around the whole read->reconcile->os.replace (body moved to _rebuild_event_log_locked; pre-existing C901 noqa carried over, none added); ledger entry relabelled from FINDING to family 9 locked atomic rewrite; lock-composition census +2 (decisions.emit, migration.rebuild_state). NFR-001: no subprocess import in the module; only the pre-acquire lock-root git probe spawns (asserted). 5 tests GREEN.
- 2026-09-06T14:57:59Z – claude – shell_pid=12990 – T042: families 8 (decisions/emit.py) and 9 (migration/rebuild_state.py) added to test_family_writes_only_while_holding_its_mission_lock; recorder also snapshots os.replace whose destination is status.events.jsonl (family 9 is a rewrite, not a store append). Census addendum for design-notes/WP01-lock-rules.md written to scratchpad/wp07-planning-artifacts/WP01-lock-rules-addendum.md (orchestrator lands it; no kitty-specs files on the lane).
- 2026-09-06T14:58:00Z – claude – shell_pid=12990 – Extra (WP03 reviewer minor): ALLOWED_OUT_OF_STORE_WRITE_SITES is now a Mapping[(module, kind, path_expr) -> allowed site count]; out_of_store_violations reports every site of an over-counted key (line-number independent), ledger_shortfall drives the live test; floor test_writes_gate_counts_ledgered_sites duplicates an allowed shape in a synthetic module and proves it is reported. test_no_dead_symbols: content-tier hash of _unsafe::ALLOWED_CALLERS re-minted (the set grew by family 8). test_store_sanitized: sanitizer tracker re-anchored on the store primitive.
- 2026-09-06T14:58:02Z – claude – shell_pid=12990 – Verification: broad suite (tests/specify_cli/decisions tests/specify_cli/migration tests/status/test_writer_serialization.py tests/status tests/specify_cli/status) 1933 passed, 1 skipped, 1 xfailed (WP02 strict xfail) + the one sanitizer test fixed; gates (unsafe allowlist, writes gate, module boundary, no_dead_symbols) all green after re-mint; ruff check + C901 clean; mypy clean on emit.py/rebuild_state.py; ruff format clean on every WP07 file -- the whole-repo format gate stays red on WP01's five pre-existing test files (not touched).
