---
work_package_id: WP03
title: Diff-scoped fail-closed guard + shared eligibility predicate
dependencies: []
requirement_refs:
- FR-002
- FR-003
- FR-009
- NFR-002
- NFR-003
planning_base_branch: fix/runtime-state-birth-cutover-all-paths
merge_target_branch: fix/runtime-state-birth-cutover-all-paths
branch_strategy: Planning artifacts for this mission were generated on fix/runtime-state-birth-cutover-all-paths. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/runtime-state-birth-cutover-all-paths unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-runtime-state-birth-cutover-all-paths-01KYH654
base_commit: 54ff0587d7f97f83e2005e835a46734886906e7e
created_at: '2026-07-27T07:56:57.924086+00:00'
subtasks:
- T011
- T012
- T013
- T014
- T015
phase: Phase 2 - Guard
history:
- at: '2026-07-27T07:43:31Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/cutover_guard.py
create_intent:
- src/specify_cli/status/cutover_eligibility.py
- src/specify_cli/cli/commands/cutover_guard.py
- tests/specify_cli/status/test_cutover_guard.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/status/cutover_eligibility.py
- src/specify_cli/cli/commands/cutover_guard.py
- tests/specify_cli/migration/test_dogfood_corpus_backfilled.py
- tests/specify_cli/status/test_cutover_guard.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Diff-scoped fail-closed guard + shared eligibility predicate

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile in the frontmatter first.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Build the **binding backstop**: a diff-scoped, fail-closed guard that rejects any
change set leaving an un-cut-over mission in the corpus, keyed on **event-log
evidence** (NOT bare `verify_backfill`, which is vacuous for natively-born
missions — risk R2). See [contracts/pre-merge-guard.md](../contracts/pre-merge-guard.md) — binding.

**Done when**: a PR diff carrying a native un-cut-over mission reds the guard with
the mission name + exact remedy; an all-cut-over diff passes; any verify error /
ambiguity / absent `mission_id` fails closed.

## Context & Constraints

- **FR-009 / R2**: decide "cut over" via the acceptance test's event-log-evidence predicate + non-empty snapshot + `status_phase`, per [data-model.md](../data-model.md). `verify_backfill.ok` is necessary-not-sufficient (it is vacuously true for native missions).
- **R3**: the guard is the *primary* enforcer for seam-bypass paths, so it evaluates **every** mission whose corpus appears in the diff, not just the "current" mission.
- **Single source**: the eligibility predicate currently lives inside `tests/specify_cli/migration/test_dogfood_corpus_backfilled.py` (`_mission_carries_event_log_runtime`, `_assert_birth_invariant_holds`). Extract it to a shared src module and have BOTH the test and the guard import it — do not duplicate (anti-whack-a-field).
- **FR-003**: remedy message is exactly `spec-kitty migrate backfill-runtime-state --mission <slug>`.

## Subtasks & Detailed Guidance

### Subtask T011 – Extract eligibility predicate to a shared src module
- **Purpose**: One authority for "which missions count / are cut over".
- **Steps**: Move `_mission_carries_event_log_runtime` + the birth-invariant check into `src/specify_cli/status/cutover_eligibility.py` with a clean API (e.g. `is_cut_over(feature_dir) -> CutOverVerdict`, `eligible_runtime_missions(repo_root)`). Update the dogfood test to import from there (behavior-preserving; the test must stay green and non-vacuous, incl. its `test_reked_lock_reds_on_born_un_reconciled_mission`).
- **Files**: `src/specify_cli/status/cutover_eligibility.py` (new), `tests/specify_cli/migration/test_dogfood_corpus_backfilled.py` (import swap only).

### Subtask T012 – Build the diff-scoped guard
- **Purpose**: FR-002/FR-009/NFR-002.
- **Steps**: New CLI entrypoint `src/specify_cli/cli/commands/cutover_guard.py` (register in the CLI app). Compute the set of missions whose `kitty-specs/<mission>/` files appear in the PR diff (accept a base ref / changed-paths input; usable in CI). For each, call `is_cut_over(...)`. Diff-scoped for the <30s budget (NFR-002).

### Subtask T013 – Fail closed + exact remedy
- **Purpose**: FR-003/NFR-003.
- **Steps**: On any un-cut-over touched mission → exit non-zero, list mission slug(s) + the exact remedy command. On verify error / ambiguity / absent `mission_id` → also non-zero (never pass on uncertainty).

### Subtask T014 – Red-first native-vacuity + all-cut-over tests [P]
- **Steps**: New test proves (a) a natively-born un-cut-over mission (empty `verify_backfill`, no frontmatter) is flagged un-cut-over (the R2 trap), (b) an all-cut-over diff passes, (c) absent `mission_id` fails closed. Write RED first.
- **Files**: `tests/specify_cli/status/test_cutover_guard.py` (new).

### Subtask T015 – Update the CLI-surface census
- **Purpose**: Adding a CLI command trips the CLI-surface census gate.
- **Steps**: Update the CLI-surface census/expectations for the new `cutover_guard` command (find the census test under `tests/architectural/` or `tests/specify_cli/cli/` and extend it).

## Test Strategy

Red-first. `PWHEADLESS=1 uv run pytest tests/specify_cli/status/test_cutover_guard.py -q`; confirm `tests/specify_cli/migration/test_dogfood_corpus_backfilled.py` stays green after the import swap; run the CLI-surface census test.

## Risks & Mitigations

- **R2** keying on bare `verify_backfill` → vacuous pass. Mitigation: event-log-evidence predicate; the native-vacuity test is the proof.
- Extraction changes test behavior → keep it a pure move + import; assert the dogfood test (incl. the non-vacuity lock) unchanged in outcome.
- Diff computation misses a touched mission → evaluate all `kitty-specs/**` paths in the diff; test with a multi-mission diff.

## Review Guidance

Confirm: predicate extracted (not duplicated) and both consumers import it; guard evaluates ALL diff-touched missions; native-vacuity trap covered; fail-closed paths covered; remedy string exact; CLI census updated.

## Activity Log

- 2026-07-27T07:43:31Z – system – Prompt created.
