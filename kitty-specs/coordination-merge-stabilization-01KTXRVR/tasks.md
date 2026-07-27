# Tasks: Coordination and Merge Stabilization

**Mission**: `coordination-merge-stabilization-01KTXRVR` (mid8 `01KTXRVR`) | **Date**: 2026-06-12
**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [contracts/](contracts/), [validation/](validation/)

## WP Shaping Note

plan.md §Phase 2 hinted 6 WPs. Ownership analysis (no two WPs may own the same file) collapsed this to **5**: Class F hardening (IC-06) shares `src/specify_cli/lanes/merge.py` with the Class B resync (IC-03) → merged into WP03, which also satisfies C-004's ordering internally; the #1814 finalize-residue fix (IC-05 part) shares `src/specify_cli/cli/commands/agent/mission.py` with the validate-only guard (IC-02) → moved into WP02.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----|
| T001 | Close 7 fixed issues with commit citations | WP01 | [P] |
| T002 | Re-scope 4 partially-fixed issues to residuals | WP01 | [P] |
| T003 | File #1666 follow-up umbrella issue (C-001 non-goals) | WP01 | [P] |
| T004 | Write issue-hygiene log artifact | WP01 | |
| T005 | Red test: validate-only leaves HEAD/tree untouched | WP02 | [P] |
| T006 | Gate `_ensure_branch_checked_out` behind `not validate_only` | WP02 | |
| T007 | Suppress "Upgrade complete!" on `--dry-run` + test | WP02 | [P] |
| T008 | Finalize residue cleanup-at-source in `_stage_finalize_artifacts_in_coord_worktree` | WP02 | |
| T009 | Residue regression test (extend paused-mission blockers suite) | WP02 | |
| T010 | Red test: coord-topology merge resync (AC-B1/B2) | WP03 | [P] |
| T011 | Ref-advance helper with checked-out-worktree resync | WP03 | |
| T012 | Migrate 3 update-ref sites to the helper | WP03 | |
| T013 | Dirty-worktree refusal (structured error, AC-B4) | WP03 | |
| T014 | Backstop message names divergence cause (FR-012) | WP03 | |
| T015 | Extract `_make_merge_env()` + all subprocess sites (AC-F1) | WP03 | |
| T016 | Narrow `status_transition.py` except + tests (AC-F3) | WP03 | |
| T017 | Ratchets: no-raw-update-ref + mixed-timestamp sort (AC-B3, AC-F2) | WP03 | |
| T018 | Red test: planted husk → structured failure (AC-D1) | WP04 | [P] |
| T019 | `ResolvedWorkspace.exists` requires `.git` marker | WP04 | |
| T020 | Review claim: lock-after-create; worktree-add hard error | WP04 | |
| T021 | move-task toplevel assertion before git calls | WP04 | |
| T022 | Doctor husk check (report + `--fix` removal) | WP04 | |
| T023 | Husk-recovery doc note + AC-D2/D3 assertions | WP04 | |
| T024 | Route `retrospective/gate.py:597` through `resolve_status_surface` | WP05 | [P] |
| T025 | Route `agent_retrospect.py:432` through `resolve_status_surface` | WP05 | [P] |
| T026 | AC10 read-surface architectural ratchet (after T024/T025) | WP05 | |
| T027 | Coord-topology baseline-recording regression test (AC-A3) | WP05 | |

## Work Package WP01 — Issue Hygiene and Follow-Up Umbrella

**Prompt**: [tasks/WP01-issue-hygiene-and-umbrella.md](tasks/WP01-issue-hygiene-and-umbrella.md) | **Est. size**: ~220 lines
**Goal**: Tracker reflects code reality — 7 fixed issues closed citing landed commits, 4 issues re-scoped to residuals, one #1666 umbrella filed for deferred non-goals. (FR-011)
**Priority**: P1 — do first (unblocks triage; C-004). **Independent test**: every cluster issue's GitHub state matches the disposition table in the hygiene log.

- [x] T001 Close #1770 #1789 #1816 #1771 #1571 #1784 #1735 citing 8544012fa / 9c8bff06f / c5a10ce56 / PR #1719 (WP01)
- [x] T002 Re-scope #1814 #1736 #1833 #1861 titles/bodies to residual scope (WP01)
- [x] T003 File follow-up umbrella under epic #1666 with C-001 non-goals and explicit non-goal list (WP01)
- [x] T004 Write kitty-specs/coordination-merge-stabilization-01KTXRVR/issue-hygiene-log.md recording every action + URL (WP01)

**Dependencies**: none. **Risks**: wrong commit citations — copy from validation comments posted 2026-06-12.

## Work Package WP02 — Read-Only Honesty and Finalize Residue (mission.py)

**Prompt**: [tasks/WP02-validate-only-and-finalize-residue.md](tasks/WP02-validate-only-and-finalize-residue.md) | **Est. size**: ~320 lines
**Goal**: `finalize-tasks --validate-only` mutates nothing (FR-002); finalize leaves zero planning-artifact residue on the primary checkout (FR-006); `upgrade --dry-run` stops claiming success (FR-013). Closes #1861-P1, #1814-residual.
**Priority**: P1. **Independent test**: AC-C1 byte-identical HEAD/porcelain; AC-A1 clean primary tree post-finalize.

- [x] T005 Red test test_finalize_tasks_validate_only_readonly.py: HEAD + porcelain identical before/after (WP02)
- [x] T006 Guard mission.py:2462 `_ensure_branch_checked_out` behind `not validate_only` (WP02)
- [x] T007 upgrade.py:987 — no success line on --dry-run; assert in test (WP02)
- [x] T008 `_stage_finalize_artifacts_in_coord_worktree` (mission.py:99-131) removes/never-creates its primary-side copies; C-003: do NOT widen COORD_OWNED_STATUS_FILES (WP02)
- [x] T009 Extend tests/specify_cli/test_wp06_sc2_paused_mission_blockers.py: post-finalize porcelain clean; record-analysis unblocked (WP02)

**Dependencies**: none. **Risks**: cleanup must only remove stager-materialized paths (research R6) — never operator files.

## Work Package WP03 — Merge Pipeline: Ref-Advance Resync and Driver Hardening

**Prompt**: [tasks/WP03-ref-advance-resync-and-driver-hardening.md](tasks/WP03-ref-advance-resync-and-driver-hardening.md) | **Est. size**: ~450 lines
**Goal**: Coordination worktree never left behind its own branch (FR-001 — #1826, the release blocker); backstop names the divergence (FR-012); merge-driver env/except/sort hardened with ratchets (FR-008b/c/d — #1736 residuals). Contracts: [class-b](contracts/class-b-ref-advance-resync.md), [class-f](contracts/class-f-merge-driver-hardening.md).
**Priority**: P0 — the only fully-live blocker. **Independent test**: AC-B1 unattended 2-lane coord merge, zero `SafeCommitBackstopError`.

- [x] T010 Red test test_merge_coord_worktree_resync_1826.py (pattern: test_merge_coord_topology_1772.py): 2 lanes + baking; assert AC-B1/AC-B2 (WP03)
- [x] T011 Shared ref-advance helper (research R1): update-ref + resync any worktree checking out the ref; one mechanism, no transaction self-heal (WP03)
- [x] T012 Migrate lanes/merge.py:440,:474 and cli/commands/merge.py:993-998 to the helper (C-002: only these three) (WP03)
- [x] T013 Dirty-worktree refusal: structured error naming worktree/ref/SHAs/dirty entries; merge stays resumable (AC-B4, NFR-002) (WP03)
- [x] T014 commit_helpers.py:321-339 backstop message names which worktree/ref diverged and likely cause (FR-012) (WP03)
- [x] T015 Extract `_make_merge_env()` in lanes/merge.py; route every subprocess call (AC-F1) (WP03)
- [x] T016 status_transition.py:399-400 catches only (ValueError, FileNotFoundError); fallback documented; propagation + fallback tests (AC-F3; lands after T011-T013 per C-004) (WP03)
- [x] T017 Ratchet tests: no raw `git update-ref` in src/specify_cli outside helper (AC-B3); mixed at/timestamp/neither deterministic sort in tests/status/test_event_log_merge.py (AC-F2) (WP03)

**Dependencies**: none (C-004 ordering is internal: T016 after T011-T013). **Risks**: `reset --hard` safety — T013's guard is mandatory before T012 ships.

## Work Package WP04 — Workspace Resolution: Fall-Through Is Failure

**Prompt**: [tasks/WP04-workspace-fallthrough-is-failure.md](tasks/WP04-workspace-fallthrough-is-failure.md) | **Est. size**: ~380 lines
**Goal**: Husk directories can never be silently used as workspaces (FR-003/004/005); doctor lists/removes husks (FR-007). Closes #1833 residuals. Contract: [class-d](contracts/class-d-workspace-resolution.md).
**Priority**: P1. **Independent test**: AC-D1 planted husk → structured resolution error, zero git calls against primary repo.

- [x] T018 Red test test_workspace_husk_resolution_1833.py: husk `.worktrees/<slug>-lane-a` (no .git) → move-task fails with named resolution error, NOT "No implementation commits"/primary-dirty verdicts (WP04)
- [x] T019 workspace/context.py:148-150 — `ResolvedWorkspace.exists` requires `.git` entry (file OR dir) (WP04)
- [x] T020 workflow.py:2237/2243/2265 — acquire ReviewLock only after workspace exists; `git worktree add` failure → hard error (WP04)
- [x] T021 tasks.py:1346 — assert `git -C <path> rev-parse --show-toplevel` == path before any git call; structured failure otherwise (WP04)
- [x] T022 Doctor husk check: report `.worktrees/*` lacking `.git`; `--fix` removes only entries NOT in `git worktree list` (research R5) (WP04)
- [x] T023 AC-D2/D3 assertions + short recovery note in the doctor check's output text (WP04)

**Dependencies**: none. **Risks**: pre-existing husks start erroring — T022 ships in the same WP (spec edge case).

## Work Package WP05 — Canonical Read Surfaces and Baseline Coverage

**Prompt**: [tasks/WP05-read-surfaces-and-baseline-coverage.md](tasks/WP05-read-surfaces-and-baseline-coverage.md) | **Est. size**: ~280 lines
**Goal**: Last two coord-unaware status reads route through `resolve_status_surface` (FR-009 — #1735 residuals); AC10 architectural ratchet forbids regression (FR-008e); #1827's fix gets its regression test (FR-010). Contract: [class-a](contracts/class-a-residual-cleanups.md).
**Priority**: P2. **Independent test**: AC-A2 ratchet green only because the two sites are routed; AC-A3 baseline present in merged target.

- [x] T024 retrospective/gate.py:597 — events via resolve_status_surface, never resolved.feature_dir direct read (WP05)
- [x] T025 cli/commands/agent_retrospect.py:432 — same routing (WP05)
- [x] T026 Extend tests/architectural/test_execution_context_parity.py: forbid feature_dir-anchored read_events()/status.events.jsonl outside the surface resolver (AC10; lands after T024/T025) (WP05)
- [x] T027 Baseline regression test: unmock _record_baseline_merge_commit path (test_merge_coord_topology_1772.py:224-225 or sibling); assert `git show <target>:.../meta.json` has baseline_merge_commit; document crash-edge (WP05)

**Dependencies**: none. **Risks**: AC10 ratchet ordering (T026 last); keep ratchet scope to the two known read families to avoid false positives.

## Execution Order & Parallelism

- **WP01 first** (convention, not a hard dependency — unblocks triage noise).
- **WP02, WP03, WP04, WP05 are mutually independent** — four parallel lanes possible.
- Within WP03: T016 strictly after T011–T013 (C-004).
- MVP scope: **WP03 alone** removes the only live release blocker (#1826).

## Quality Gates (every WP)

`pytest` green incl. existing ratchets (NFR-005); `ruff check .` clean; `mypy --strict` zero suppressions (NFR-004); ≥90% coverage on changed lines; `pytest tests/architectural/test_no_legacy_terminology.py` before push (C-005).
