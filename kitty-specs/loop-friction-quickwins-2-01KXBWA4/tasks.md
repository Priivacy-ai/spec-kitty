# Tasks: Implement-Loop Friction Quick-Wins II

**Mission**: loop-friction-quickwins-2-01KXBWA4 | **Branch**: `feat/loop-friction-quickwins-2`
**Plan**: [plan.md](./plan.md) (7-concern map, post-squad) | **Spec**: [spec.md](./spec.md)

7 work packages, one per Implementation Concern. Each is independently implementable and file-disjoint
(no `owned_files` overlap). WP07 depends on WP01 (reuses its canonical runtime-field helper). Every WP
carries a red-first regression proving the guard's true-positive still fires (NFR-005 / C-001).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Canonical runtime-field accessor from `frontmatter.py::WP_FIELD_ORDER` | WP01 | |
| T002 | `_drop_runtime_frontmatter_only_wp` + wire into `resolve_planning_artifact_staging` | WP01 | |
| T003 | Test: runtime-only WP diff dropped; N-lane 0-commit allocation | WP01 | |
| T004 | Test: body/non-runtime change still blocks; no-op when auto_commit=True | WP01 | |
| T005 | Extend `_normalize_tasks_md` to canonicalize pipe-table status cells | WP02 | [P] |
| T006 | Test: pipe-table `[D]`/`[P]` + mixed churn stays current | WP02 | [P] |
| T007 | Test: substantive `tasks.md` row change still stales (true-positive) | WP02 | [P] |
| T008 | Interpreter-resolution helper (`uv run` → `sys.executable` fallback) | WP03 | [P] |
| T009 | Apply helper + contention lock (own timeout, decoupled from run timeout) | WP03 | [P] |
| T010 | Test: pytest-lacking interpreter → real verdict; update 2 masking tests | WP03 | [P] |
| T011 | Test: concurrent runs serialize; lock-wait ≠ run-timeout | WP03 | [P] |
| T012 | Document sub-agent long-gate contract in the implement-review skill | WP03 | [P] |
| T013 | Thread `project_root` through manifest reader/writer | WP04 | [P] |
| T014 | Serialize `output_path` relative + reconstruct absolute on read | WP04 | [P] |
| T015 | Test: relative on-disk; legacy-absolute tolerance; keying invariant | WP04 | [P] |
| T016 | Regenerate committed `agent_profiles_manifest.json` clean | WP04 | [P] |
| T017 | Issue-matrix blocker leads with schema-drift/column detail | WP05 | [P] |
| T018 | Test: malformed column named, not all-issues-"Missing rows" | WP05 | [P] |
| T019 | Bulk-edit: drop low-weight verbs from the `triggered` sum | WP05 | [P] |
| T020 | Test: ordinary-refactor False; rename-all True; single-HIGH True | WP05 | [P] |
| T021 | Pristine-vs-insufficient predicate near `_substantive.py` | WP06 | [P] |
| T022 | `setup-plan` returns `scaffolded` for pristine; `blocked` for insufficient | WP06 | [P] |
| T023 | Handle new state in `next` engine + source prompt; regen agent copies | WP06 | [P] |
| T024 | Test: pristine→scaffolded; insufficient→blocked; substantive→success | WP06 | [P] |
| T025 | Route move-task staging via authority path (reuse WP01 seam); no guard exemption | WP07 | |
| T026 | #2580: route `_mt_persist_wp_file` shell_pid via canonical writer | WP07 | |
| T027 | Test: dual pin — STATUS_STATE byte-unchanged AND zero lane `kitty-specs/` | WP07 | |
| T028 | Arch guard: IC-07 diff untouched status-bundling symbols | WP07 | |
| T029 | Clean primary route for legitimate solo-empty coord (surface_resolver) | WP08 | [P] |
| T030 | Same-path regression: read surface == write placement == PRIMARY | WP08 | [P] |
| T031 | Preserve warning's true signal (coord-with-lanes empty still warns) | WP08 | [P] |
| T032 | Update surface_resolver coord-empty-warning test | WP08 | [P] |

## Work Packages

### WP01 — Allocator + move-task no-op-stable against runtime frontmatter (FR-001, #2580 helper)

**Goal**: The allocator's uncommitted-artifact check ignores the `shell_pid`/`base_*` WP frontmatter the
claim itself wrote (sourced from the canonical `WP_FIELD_ORDER`), so N lanes batch-allocate with zero
inter-allocation commits — while any body/substantive change still blocks. Provides the canonical helper
WP07 reuses. **Priority: P1 (MVP).** **Independent test**: sequential N-lane allocation needs 0 commits.

- [x] T001 Canonical runtime-field accessor from `frontmatter.py::WP_FIELD_ORDER` (WP01)
- [x] T002 `_drop_runtime_frontmatter_only_wp` + wire into `resolve_planning_artifact_staging` (WP01)
- [x] T003 Test: runtime-only WP diff dropped; N-lane 0-commit allocation (WP01)
- [x] T004 Test: body/non-runtime change still blocks; no-op when auto_commit=True (WP01)

Prompt: [tasks/WP01-allocator-runtime-frontmatter.md](./tasks/WP01-allocator-runtime-frontmatter.md) · ~230 lines · deps: none

### WP02 — Analysis-report freshness normalizes pipe-table status cells (FR-002)

**Goal**: `mark-status`'s pipe-table `[D]`/`[P]` cell churn no longer re-stales the analysis-report; a
substantive `tasks.md` row change still stales it. **Priority: P1.** **Independent test**: mark-status→
implement on a pipe-table mission yields 0 spurious `stale_analysis_report`.

- [x] T005 Extend `_normalize_tasks_md` to canonicalize pipe-table status cells (WP02)
- [x] T006 Test: pipe-table `[D]`/`[P]` + mixed churn stays current (WP02)
- [x] T007 Test: substantive `tasks.md` row change still stales (true-positive) (WP02)

Prompt: [tasks/WP02-freshness-pipe-table.md](./tasks/WP02-freshness-pipe-table.md) · ~170 lines · deps: none

### WP03 — Pre-review gate runner: interpreter + contention + contract (FR-003, FR-004, FR-005)

**Goal**: The gate resolves the runner via `uv run` (so a uv-managed checkout returns a real verdict, not
`no_coverage`→`--force`), is contention-safe under concurrent lanes (lock with its own timeout, decoupled
from the subprocess timeout), and the sub-agent long-gate contract is documented. **Priority: P1.**
**Independent test**: gate under a pytest-lacking interpreter returns a real verdict.

- [x] T008 Interpreter-resolution helper (`uv run` → `sys.executable` fallback) (WP03)
- [x] T009 Apply helper + contention lock (own timeout, decoupled from run timeout) (WP03)
- [x] T010 Test: pytest-lacking interpreter → real verdict; update 2 masking tests (WP03)
- [x] T011 Test: concurrent runs serialize; lock-wait ≠ run-timeout (WP03)
- [x] T012 Document sub-agent long-gate contract in the implement-review skill (WP03)

Prompt: [tasks/WP03-gate-runner-hardening.md](./tasks/WP03-gate-runner-hardening.md) · ~300 lines · deps: none

### WP04 — Manifest `output_path` repo-relative (FR-006)

**Goal**: The committed `agent_profiles_manifest.json` stores `output_path` repo-relative (in-memory +
key stay absolute); the reader tolerates legacy absolute values with zero migration, so `upgrade` is
cross-machine deterministic. **Priority: P2.** **Independent test**: `upgrade` on a second path → 0 diff.

- [x] T013 Thread `project_root` through manifest reader/writer (WP04)
- [x] T014 Serialize `output_path` relative + reconstruct absolute on read (WP04)
- [x] T015 Test: relative on-disk; legacy-absolute tolerance; keying invariant (WP04)
- [x] T016 Regenerate committed `agent_profiles_manifest.json` clean (WP04)

Prompt: [tasks/WP04-manifest-relative-path.md](./tasks/WP04-manifest-relative-path.md) · ~220 lines · deps: none

### WP05 — Diagnostics papercuts: issue-matrix error + bulk-edit inference (FR-007, FR-008)

**Goal**: The issue-matrix blocker names the schema-drift column (not a misleading "Missing rows"); bulk-
edit inference stops blocking on ordinary refactor verbs while genuine bulk edits — including single-HIGH-
phrase — still trip. **Priority: P2.** **Independent test**: malformed-column error names the column;
inference scoring cases pass.

- [x] T017 Issue-matrix blocker leads with schema-drift/column detail (WP05)
- [x] T018 Test: malformed column named, not all-issues-"Missing rows" (WP05)
- [x] T019 Bulk-edit: drop low-weight verbs from the `triggered` sum (WP05)
- [x] T020 Test: ordinary-refactor False; rename-all True; single-HIGH True (WP05)

Prompt: [tasks/WP05-diagnostics-papercuts.md](./tasks/WP05-diagnostics-papercuts.md) · ~230 lines · deps: none

### WP06 — plan scaffold-block ergonomics (FR-009)

**Goal**: The first happy-path `setup-plan` scaffold write returns a distinct non-error state
(`scaffolded`), not `blocked`; a populated-but-insufficient plan still returns `blocked`. The `next`
engine + source prompt handle the new state; the specify side is already `scaffold_only: success`.
**Priority: P2.** **Independent test**: fresh mission → first `setup-plan` returns non-blocked.

- [x] T021 Pristine-vs-insufficient predicate near `_substantive.py` (WP06)
- [x] T022 `setup-plan` returns `scaffolded` for pristine; `blocked` for insufficient (WP06)
- [x] T023 Handle new state in `next` engine + source prompt; regen agent copies (WP06)
- [x] T024 Test: pristine→scaffolded; insufficient→blocked; substantive→success (WP06)

Prompt: [tasks/WP06-scaffold-block-ergonomics.md](./tasks/WP06-scaffold-block-ergonomics.md) · ~250 lines · deps: none

### WP07 — move-task coord-lane staging via authority path + #2580 (FR-010, #2580)

**Goal**: `move-task` on a coord-topology lane routes planning-artifact staging through the authority path
so no manual `git restore` is ever needed, with NO `commit_guard` exemption and STATUS_STATE placement
byte-unchanged; also routes the #2580 `_mt_persist_wp_file` shell_pid write through the canonical writer.
**Priority: P2. Coordination-aware (C-002).** **Independent test**: coord move-task → dual pin holds.

- [ ] T025 Route move-task staging via authority path (reuse WP01 seam); no guard exemption (WP07)
- [ ] T026 #2580: route `_mt_persist_wp_file` shell_pid via canonical writer (WP07)
- [ ] T027 Test: dual pin — STATUS_STATE byte-unchanged AND zero lane `kitty-specs/` (WP07)
- [ ] T028 Arch guard: IC-07 diff untouched status-bundling symbols (WP07)

Prompt: [tasks/WP07-movetask-authority-staging.md](./tasks/WP07-movetask-authority-staging.md) · ~260 lines · deps: WP01

### WP08 — Solo PR-bound coord mission routes empty-coord surface to primary (FR-011, #2533)

**Goal**: A solo PR-bound `--start-branch` mission whose coord worktree is legitimately empty resolves its
status surface cleanly to PRIMARY (no split-brain warning / manual flatten), with the read surface proven to
match the write placement. Consequence-only (the `pr_bound⇒coord` derivation stays; revisited in a follow-up).
**Priority: P2. Coordination-aware (C-002 WP07↔WP08).** **Independent test**: solo-empty coord → primary, no warning.

- [ ] T029 Clean primary route for legitimate solo-empty coord (surface_resolver) (WP08)
- [ ] T030 Same-path regression: read surface == write placement == PRIMARY (WP08)
- [ ] T031 Preserve warning's true signal (coord-with-lanes empty still warns) (WP08)
- [ ] T032 Update surface_resolver coord-empty-warning test (WP08)

Prompt: [tasks/WP08-solo-coord-surface-routing.md](./tasks/WP08-solo-coord-surface-routing.md) · ~200 lines · deps: none

## Dependencies & Parallelization

- **WP01** is the MVP and unblocks **WP07** (shared canonical runtime-field helper).
- **WP02–WP06, WP08** are fully independent and parallelizable (disjoint files).
- **WP07** depends on **WP01**; **WP08** is disjoint from WP07 by file, coordinated by the C-002 boundary rule.

Suggested order: WP01 → (WP02, WP03, WP04, WP05, WP06, WP08 in parallel) → WP07.
