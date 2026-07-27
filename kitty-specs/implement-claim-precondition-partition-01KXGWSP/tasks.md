# Tasks: Partition-Aware Implement-Claim Precondition

**Mission**: `implement-claim-precondition-partition-01KXGWSP` · fixes #2533
**Topology**: LANES · **Planning/merge branch**: `mission/2533-pr-bound-coord-claim-precondition`
**Plan**: [plan.md](./plan.md) · **Contract**: [contracts/resolve-precondition-ref.md](./contracts/resolve-precondition-ref.md)

3 work packages (revised after the post-tasks anti-laziness squad). WP01 is the
read/compare seam; WP02 (write-side partition commit) and WP03 (move-task regression
+ docs) both depend on WP01 and are **independent of each other** (parallel lanes b/c).
Scope: `Closes #2533` only; aligned-downpayment on the landed #2160/#2464-65-08 degod;
stay surgical.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | RED unit tests for `resolve_precondition_ref(path, coord)` + RED integration repro (incl. meta.json) | WP01 | |
| T002 | Add pure `resolve_precondition_ref(repo_rel_path, coord_branch_for_filter) -> str` (None-safe residue predicate) | WP01 | |
| T003 | Route staging core through the resolver (group-partition; keep `_files_changed_vs_ref` signature stable) | WP01 | |
| T004 | Re-pin `test_implement_cores.py:287` only (`:290` untouched) + add invariant tests | WP01 | |
| T005 | Campsite S108 (`implement_cores.py:47`) + `TYPE_CHECKING` import removal; ruff/mypy gates | WP01 | |
| T006 | RED test: genuinely-dirty PRIMARY on coord must land on primary ref | WP02 | |
| T007 | Partition-aware two-transaction commit in `_commit_planning_artifacts_transaction` | WP02 | |
| T008 | Campsite S1192 banner constants (`implement.py:1194`); ruff/mypy gates | WP02 | |
| T009 | Move-task partition regression guarding the silent `_mt_untracked_planning_artifact_paths` consumer | WP03 | [P] |
| T010 | Docs campsite: `branch-target-routing.md:42-44` + `execution-lanes.md:78-82` → kind-based partition | WP03 | [P] |
| T011 | Full verification: targeted pytest + `test_no_legacy_terminology.py`; confirm SC-001..SC-004 | WP03 | |

## Work Packages

### WP01 — Partition-aware precondition ref seam, read/compare side (lane-a)

- **Goal**: Per-path resolver so PRIMARY planning artifacts (incl. `meta.json`) compare
  against the primary ref, not the coord ref → the claim stops falsely aborting.
- **Priority**: P1. **Dependencies**: none.
- **Independent test**: solo PR-bound coord mission with committed spec/plan/tasks/meta
  → `agent action implement WP01` proceeds; `resolve_precondition_ref("…/meta.json", coord) == "HEAD"`.
- **FRs**: FR-001, FR-002, FR-004; **NFR**: NFR-002, NFR-004; **guards**: C-001, C-002.

Included subtasks:

- [x] T001 RED unit tests + RED integration repro (incl. meta.json), `auto_commit=False` (WP01)
- [x] T002 Add pure `resolve_precondition_ref(repo_rel_path, coord_branch_for_filter) -> str` (WP01)
- [x] T003 Route staging core through the resolver (group-partition, stable helper signatures) (WP01)
- [x] T004 Re-pin `test_implement_cores.py:287` only; add invariant tests (WP01)
- [x] T005 Campsite S108 + `TYPE_CHECKING` import removal; ruff/mypy gates (WP01)

Prompt: [tasks/WP01-precondition-ref-seam.md](./tasks/WP01-precondition-ref-seam.md). Est. ~380 lines.

### WP02 — Write-side partition-aware planning-artifact commit (lane-b)

- **Goal**: A genuinely-dirty PRIMARY artifact on a coord mission commits to the primary
  ref, never coord (two-transaction partition in `_commit_planning_artifacts_transaction`).
- **Priority**: P1. **Dependencies**: WP01 (partition predicate).
- **Independent test**: dirty `spec.md` on a coord mission lands on the primary/target
  branch; dirty `status.events.jsonl` lands on coord.
- **FRs**: FR-003; **NFR**: NFR-001; **guards**: C-002.

Included subtasks:

- [x] T006 RED test: dirty PRIMARY on coord → primary ref (WP02)
- [x] T007 Partition-aware two-transaction commit (WP02)
- [x] T008 Campsite S1192 banner constants; ruff/mypy gates (WP02)

Prompt: [tasks/WP02-writeside-partition-commit.md](./tasks/WP02-writeside-partition-commit.md). Est. ~300 lines.

### WP03 — Move-task partition regression + docs campsite (lane-c)

- **Goal**: Guard the silent move-task consumer against a future partition regression;
  correct the stale single-ref architecture docs.
- **Priority**: P2. **Dependencies**: WP01. Independent of WP02.
- **Independent test**: move-task partition regression passes against the WP01 core;
  `test_no_legacy_terminology.py` green; docs describe only the kind-based partition.
- **FRs**: FR-005, FR-006; **SC**: SC-001..SC-004.

Included subtasks:

- [x] T009 Move-task partition regression guarding `_mt_untracked_planning_artifact_paths` (WP03)
- [x] T010 Docs campsite: `branch-target-routing.md:42-44` + `execution-lanes.md:78-82` (WP03)
- [x] T011 Full verification: targeted pytest + `test_no_legacy_terminology.py`; confirm SC-001..SC-004 (WP03)

Prompt: [tasks/WP03-movetask-regression-docs.md](./tasks/WP03-movetask-regression-docs.md). Est. ~300 lines.

## Sequencing / Landing Notes

- **No `tasks_move_task.py` source edit anywhere in the mission** (WP01's public
  signature stays stable; WP03 only adds a test) → the earlier **PR #2639 rebase gate
  no longer applies.** #2570 WP01 (`e7cab2693`) is already in base.
- **WP02 ⊥ WP03** — both depend only on WP01; run as parallel lanes after WP01.
- **PR body at landing**: `Closes #2533`; `Related: #2160, #2570, #2549, #2646, #2334`.

## Post-tasks Squad Corrections (2026-07-14, applied)

- **BLOCKER-1 fixed**: resolver takes `(repo_rel_path, coord_branch_for_filter)` (per-path);
  single-arg form was a no-op.
- **BLOCKER-2 fixed**: uses `is_coordination_artifact_residue_path` (None-safe), defaults
  to `"HEAD"` — `meta.json` (kind→None) now routes to primary, not coord; avoids the
  `is_primary_artifact_kind(None)` mypy-strict trap.
- **Write-side sized in** (operator decision): WP02 does the two-transaction partition
  commit (FR-003) with its own red test; not folded into WP01.
- **Test cites corrected**: only `test_implement_cores.py:287` re-pins; `:290` is a
  still-valid test (left untouched, DIRECTIVE_041).

## Sonar Campsite Disposition (live SonarCloud, 2026-07-14)

- **FOLDED**: S108 dead `TYPE_CHECKING` block `implement_cores.py:47` → WP01/T005;
  S1192 banner constants `implement.py:1194` → WP02/T008.
- **OUT — tracked to the #2465/#2160 degod (do NOT fold):** S3776 `_json_safe_output:127`,
  `_resolve_bookkeeping_transaction_identifiers:345`, `_run_recover_mode:712`,
  `_mt_commit_wp_file:1485`; S107 `_do_move_task:1829`; S8572 `_mt_uncheck_rollback_subtasks:1668`.
  Suggested card: "Sonar degod: implement.py / tasks_move_task.py cognitive-complexity
  + parameter-count reduction (S3776/S107)".
- **Docs (WP03 files):** Sonar-clean.

## Requirement Coverage

- FR-001, FR-002, FR-004 → WP01 · FR-003 → WP02 · FR-005, FR-006 → WP03
- NFR-002, NFR-004 → WP01 · NFR-001 → WP02 · NFR-003 → all
- All FR/NFR covered; C-001/C-002 enforced as guards.
