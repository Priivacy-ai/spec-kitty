# Tasks: Placement-Port Residuals Closure

**Mission**: `placement-port-residuals-closure-01KYDEF0`
**Planning base**: `placement-port-residuals` | **Merge target**: `placement-port-residuals`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

7 work packages, 30 subtasks. Lane grouping per C-007. Every code WP is red-first
(DIRECTIVE_041) through the pre-existing entry points in [quickstart.md](./quickstart.md).
Judged per the failing-test remediation framework — fix PRODUCT where the test encodes
a real invariant, re-pin the TEST where the contract legitimately moved; never retry-to-green.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Red-first FR-001: off-partition fail-closed via cutover_mission | WP01 | |
| T002 | Route _flip_phase write-target through the port (CWD-invariant repo_root; raise≠mismatch) | WP01 | |
| T003 | Red-first FR-002: two-leg cutover — seeded_count>0 AND events on COORD | WP01 | |
| T004 | Decouple cutover read-leg(PRIMARY)/write-leg(COORD) internally; signature stable | WP01 | |
| T005 | Corpus validation (NFR-002): 3 single-leg callers byte-unchanged; 0 regressions | WP01 | |
| T006 | ruff/mypy clean; verify | WP01 | |
| T007 | Confirm red-first: status.events.jsonl absent from merge committed-set | WP02 | |
| T008 | Fix executor.py committed-file set to include status.events.jsonl | WP02 | |
| T009 | Verify both merge tests green; no merge-suite regression | WP02 | |
| T010 | ruff/mypy clean | WP02 | |
| T011 | Allow-list executor.py coord-seed in test_no_write_side_rederivation (FR-008) | WP03 | |
| T012 | Allow-list executor.py in guard MERGE_BOOKKEEPING flow (FR-012) | WP03 | |
| T013 | Narrow migration/ prefix→per-file + LOCKSTEP _PINNED_BOUNDARY_SANCTIONED_PREFIXES (FR-003) | WP03 | |
| T014 | Empirical C-001 check + verify all 3 shared-scan consumers green | WP03 | |
| T015 | Reconcile SC-002/NFR-001 wording by anchor; keep mission_runtime/+upgrade/migrations/ (FR-004) | WP03 | |
| T016 | ruff/mypy clean; full tests/architectural/ green | WP03 | |
| T017 | Red-first: decision_log+bookkeeping degrade through the shared helper | WP04 | [P] |
| T018 | Extract resolve_write_target_or_degrade in mission_runtime (port + pre-gate, kind-param) | WP04 | [P] |
| T019 | Migrate the 2 verbatim clones through helper (caller-computed degrade_ref); delete clones | WP04 | [P] |
| T020 | Verify 0 verbatim clones (SC-004); ruff/mypy clean | WP04 | [P] |
| T021 | Red-first: status_transition pre-gate behavior change; STATUS_STATE→coord | WP05 | |
| T022 | Adopt status_transition._resolve_write_target onto helper; preserve get_feature_target_branch | WP05 | |
| T023 | Verify C-004 (coord stays coord); ruff/mypy clean | WP05 | |
| T024 | Red-first: generate_retrospective on deleted-coord mission raises today | WP06 | [P] |
| T025 | Wrap _load_traces read_dir in except (CoordinationBranchDeleted, StatusReadPathNotFound)→[] | WP06 | [P] |
| T026 | Verify degrade; no bare-Exception widening; single call site (C-003); ruff/mypy | WP06 | [P] |
| T027 | FR-009: route/allow-list mission_repair.py:65 raw path; verify green | WP07 | [P] |
| T028 | FR-010: repair→_EXPECTED_COMMANDS(9)+_EXPECTED_FLAGS+positionals; rename count test; contract row | WP07 | [P] |
| T029 | Verify golden-contract green incl. repair flag surface; verify-on-CI registration; ruff/mypy | WP07 | [P] |
| T030 | Tracker hygiene (FR-007): parent epic + native-link #2923/#2924/#2926; Part-C issue (FR-009/010/011); per-FR 1:1 issue-matrix | WP03 | |

---

## Lane A — Birth-cutover & write-side gate (serial)

### WP01 — Cutover writer: port-route `_flip_phase` + partition-decouple

- **Goal**: Enforce PRIMARY-correctness of the sole `status_phase` writer (FR-001) and close the COORD-read/PRIMARY-write silent-loss residual (FR-002) by decoupling the cutover read-leg from the write-leg — internal to `cutover_mission`, public signature stable.
- **Priority**: P1 | **Requirements**: FR-001, FR-002; NFR-001, NFR-002, NFR-003
- **Independent test**: `cutover_mission` fails closed on an off-partition dir; a two-leg cutover with evictable PRIMARY `tasks/` + stale COORD keeps `seeded_count>0` with events on COORD. Corpus flips regression-free.
- **Dependencies**: none | **Prompt**: [tasks/WP01-cutover-writer-port-and-decouple.md](./tasks/WP01-cutover-writer-port-and-decouple.md)
- [ ] T001 Red-first FR-001: off-partition fail-closed via cutover_mission (WP01)
- [ ] T002 Route _flip_phase write-target through the port (CWD-invariant repo_root; raise≠mismatch) (WP01)
- [ ] T003 Red-first FR-002: two-leg cutover — seeded_count>0 AND events on COORD (WP01)
- [ ] T004 Decouple cutover read-leg(PRIMARY)/write-leg(COORD) internally; signature stable (WP01)
- [ ] T005 Corpus validation (NFR-002): 3 single-leg callers byte-unchanged; 0 regressions (WP01)
- [ ] T006 ruff/mypy clean; verify (WP01)

### WP02 — Merge status-event durability

- **Goal**: Ensure merges durably commit `status.events.jsonl` alongside `meta.json`/`status.json` (FR-011) — product regression, the tests encode the real FR-019/FR-020 invariant.
- **Priority**: P2 | **Requirements**: FR-011; NFR-004
- **Independent test**: `test_safe_commit_is_called_with_correct_files` + `test_planning_artifact_only_merge_does_not_require_mission_branch` green.
- **Dependencies**: WP01 | **Prompt**: [tasks/WP02-merge-status-event-durability.md](./tasks/WP02-merge-status-event-durability.md)
- [ ] T007 Confirm red-first: status.events.jsonl absent from merge committed-set (WP02)
- [ ] T008 Fix executor.py committed-file set to include status.events.jsonl (WP02)
- [ ] T009 Verify both merge tests green; no merge-suite regression (WP02)
- [ ] T010 ruff/mypy clean (WP02)

### WP03 — Arch-gate reconciliation (allow-list + prefix narrowing + wording)

- **Goal**: Green all four arch gates PR #2920 left/deferred red: allow-list the `executor.py` coord-seed on the write-side gate (FR-008) and guard-capability gate (FR-012), narrow the `migration/` whole-tree carve-out with the lockstep pinned-tuple edit (FR-003), and reconcile the SC-002/NFR-001 wording (FR-004).
- **Priority**: P1/P2 | **Requirements**: FR-003, FR-004, FR-008, FR-012, FR-007; NFR-004, SC-002, SC-008
- **Independent test**: full `tests/architectural/` green; all 3 shared-scan consumers green; a synthetic bypass in a previously-carved `migration/` module reds; issue-matrix maps per-FR 1:1.
- **Dependencies**: WP02 | **Prompt**: [tasks/WP03-arch-gate-reconciliation.md](./tasks/WP03-arch-gate-reconciliation.md)
- [ ] T011 Allow-list executor.py coord-seed in test_no_write_side_rederivation (FR-008) (WP03)
- [ ] T012 Allow-list executor.py in guard MERGE_BOOKKEEPING flow (FR-012) (WP03)
- [ ] T013 Narrow migration/ prefix→per-file + LOCKSTEP _PINNED_BOUNDARY_SANCTIONED_PREFIXES (FR-003) (WP03)
- [ ] T014 Empirical C-001 check + verify all 3 shared-scan consumers green (WP03)
- [ ] T015 Reconcile SC-002/NFR-001 wording by anchor; keep mission_runtime/+upgrade/migrations/ (FR-004) (WP03)
- [ ] T016 ruff/mypy clean; full tests/architectural/ green (WP03)
- [ ] T030 Tracker hygiene (FR-007): parent epic + native-link #2923/#2924/#2926; Part-C issue (FR-009/010/011); per-FR 1:1 issue-matrix (out-of-map planning artifact) (WP03)

---

## Lane B — Write-target degrade unification

### WP04 — Degrade helper + verbatim-clone removal (IC-06a)

- **Goal**: Extract one kind-parameterized `resolve_write_target_or_degrade` (port-resolution + `_mission_meta_exists` pre-gate) in `mission_runtime`; route the two verbatim clones through it with caller-computed `degrade_ref`; delete the clones (SC-004).
- **Priority**: P2 | **Requirements**: FR-005; NFR-003, SC-004
- **Independent test**: `decision_log` (fail-open) + `bookkeeping_commit` (fail-closed raise) degrade through the shared helper; 0 verbatim clones remain.
- **Dependencies**: none | **Prompt**: [tasks/WP04-degrade-helper-clone-removal.md](./tasks/WP04-degrade-helper-clone-removal.md)
- [ ] T017 Red-first: decision_log+bookkeeping degrade through the shared helper (WP04)
- [ ] T018 Extract resolve_write_target_or_degrade in mission_runtime (port + pre-gate, kind-param) (WP04)
- [ ] T019 Migrate the 2 verbatim clones through helper (caller-computed degrade_ref); delete clones (WP04)
- [ ] T020 Verify 0 verbatim clones (SC-004); ruff/mypy clean (WP04)

### WP05 — status_transition pre-gate adoption (IC-06b, behavior change)

- **Goal**: Adopt `status_transition._resolve_write_target` onto the shared helper — adds the `_mission_meta_exists` pre-gate it lacks (real behavior change per C-004) while preserving the `get_feature_target_branch` degrade and coord routing.
- **Priority**: P2 | **Requirements**: FR-005; C-004, NFR-003
- **Independent test**: the status-emit write path degrades through the helper; `STATUS_STATE` resolves to the coord ref (never PRIMARY).
- **Dependencies**: WP04 | **Prompt**: [tasks/WP05-status-transition-pregate.md](./tasks/WP05-status-transition-pregate.md)
- [ ] T021 Red-first: status_transition pre-gate behavior change; STATUS_STATE→coord (WP05)
- [ ] T022 Adopt status_transition._resolve_write_target onto helper; preserve get_feature_target_branch (WP05)
- [ ] T023 Verify C-004 (coord stays coord); ruff/mypy clean (WP05)

---

## Lane C — Best-effort read + CLI contract (split-candidate)

### WP06 — `_load_traces` best-effort guard (IC-07)

- **Goal**: A deleted-coord retrospective degrades to `[]` traces instead of crashing (FR-006).
- **Priority**: P3 | **Requirements**: FR-006; C-003, SC-005
- **Independent test**: `generate_retrospective` on a coord mission with a deleted `coordination_branch` returns without raising.
- **Dependencies**: none | **Prompt**: [tasks/WP06-load-traces-guard.md](./tasks/WP06-load-traces-guard.md)
- [ ] T024 Red-first: generate_retrospective on deleted-coord mission raises today (WP06)
- [ ] T025 Wrap _load_traces read_dir in except (CoordinationBranchDeleted, StatusReadPathNotFound)→[] (WP06)
- [ ] T026 Verify degrade; no bare-Exception widening; single call site (C-003); ruff/mypy (WP06)

### WP07 — CLI path + golden-contract hygiene (IC-08)

- **Goal**: Green `test_no_raw_mission_spec_paths` at `mission_repair.py:65` (FR-009) and reconcile the mission-CLI golden contract for the sanctioned `repair` command incl. its flag surface (FR-010).
- **Priority**: P2 | **Requirements**: FR-009, FR-010; NFR-004, SC-008
- **Independent test**: raw-path gate green; golden-contract green with `repair` name + flag surface pinned.
- **Dependencies**: none | **Prompt**: [tasks/WP07-cli-path-golden-contract.md](./tasks/WP07-cli-path-golden-contract.md)
- [ ] T027 FR-009: route/allow-list mission_repair.py:65 raw path; verify green (WP07)
- [ ] T028 FR-010: repair→_EXPECTED_COMMANDS(9)+_EXPECTED_FLAGS+positionals; rename count test; contract row (WP07)
- [ ] T029 Verify golden-contract green incl. repair flag surface; verify-on-CI registration; ruff/mypy (WP07)

---

## Dependency graph

```
Lane A:  WP01 ──► WP02 ──► WP03   (WP03 also carries FR-007 tracker hygiene)
Lane B:  WP04 ──► WP05
Lane C:  WP06     WP07            (independent; split-candidate for a fast PR)
```

## MVP / sequencing

- **MVP safety core**: WP01 (the silent-data-loss + off-partition writer) is the highest-value package.
- **Fast-green-main**: WP02 + WP03 close the merged reds in `upstream/main`.
- **Parallelizable**: Lane B (WP04→WP05) and Lane C (WP06, WP07) run alongside Lane A.
