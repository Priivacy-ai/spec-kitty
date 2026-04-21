# Tasks: Stabilization Release: Core Bug Fixes

**Mission ID**: 01KPQJAN4P2V4MTHRFGS7VW17M  
**Mission Slug**: stabilization-release-core-bug-fixes-01KPQJAN  
**Branch**: `main` → `main`  
**Execution strategy**: Single lane, serial (WP01 → WP02 → WP03 → WP04)

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----|
| T001 | Parse `??` porcelain prefix and skip untracked lines in invariant | WP01 | | [D] |
| T002 | Bifurcate error message by failure type (sparse-checkout vs generic) | WP01 | | [D] |
| T003 | Regression test: untracked files do not abort merge | WP01 | [D] |
| T004 | Regression test: tracked-dirty files abort with correct message | WP01 | [D] |
| T005 | Full suite green check | WP01 | | [D] |
| T006 | Add Gemini + Qwen to `AGENT_ARG_PLACEHOLDERS` (`{{args}}`) | WP02 | | [D] |
| T007 | Add `AGENT_SHIM_FORMATS` dispatch dict (`gemini → toml`) | WP02 | | [D] |
| T008 | Implement `generate_shim_content_toml()` for Gemini TOML schema | WP02 | | [D] |
| T009 | Update `generate_all_shims()` for per-agent format + extension dispatch | WP02 | | [D] |
| T010 | Regression tests: Gemini produces `.toml`, correct schema, `{{args}}` | WP02 | [D] |
| T011 | Regression tests: Qwen stays `.md` but uses `{{args}}` | WP02 | [D] |
| T012 | Regression tests: Claude/Codex output unchanged | WP02 | [D] |
| T013 | Change review-claim emit to `Lane.IN_REVIEW`, remove `force=True` | WP03 | |
| T014 | Update `is_review_claimed` to OR new + legacy shapes | WP03 | |
| T015 | Update lane-entry guard to accept `{FOR_REVIEW, IN_REVIEW, legacy-in-progress-claim}` | WP03 | |
| T016 | Regression test: new review claim emits `in_review` | WP03 | [P] |
| T017 | Regression test: approval from `in_review` succeeds | WP03 | [P] |
| T018 | Regression test: rejection from `in_review` succeeds | WP03 | [P] |
| T019 | Regression test: historical `in_progress + review_ref` logs parse without error | WP03 | [P] |
| T020 | Atomic write (temp + replace) in `write_mission_brief()` | WP04 | |
| T021 | Add `MAX_BRIEF_FILE_SIZE_BYTES` constant + size guard in `intake.py` | WP04 | |
| T022 | Add repo-root containment check in `scan_for_plans()` | WP04 | |
| T023 | Add symlink exclusion in `scan_for_plans()` directory expansion | WP04 | |
| T024 | Regression tests: brief atomicity (partial write does not block re-ingest) | WP04 | [P] |
| T025 | Regression tests: oversized file rejected before read | WP04 | [P] |
| T026 | Regression tests: out-of-bounds path excluded, in-bounds accepted | WP04 | [P] |
| T027 | Regression tests: symlink excluded, regular file accepted | WP04 | [P] |

---

## WP01 — Merge Post-Merge Invariant Fix

**Priority**: Critical (highest user impact — all multi-agent users affected)  
**Depends on**: none  
**Prompt**: [WP01-merge-post-merge-invariant-fix.md](tasks/WP01-merge-post-merge-invariant-fix.md)  
**Estimated size**: ~300 lines

**Goal**: Fix the false-positive merge abort caused by untracked files, and make the error message accurate.

**Subtasks**:
- [x] T001 Parse `??` porcelain prefix and skip untracked lines in invariant (WP01)
- [x] T002 Bifurcate error message by failure type (sparse-checkout vs generic) (WP01)
- [x] T003 Regression test: untracked files do not abort merge (WP01)
- [x] T004 Regression test: tracked-dirty files abort with correct message (WP01)
- [x] T005 Full suite green check (WP01)

**Success criteria**: `spec-kitty merge` completes when `.claude/`, `.agents/`, etc. are untracked. Genuinely dirty tracked files still abort with an accurate, actionable error.

---

## WP02 — Gemini/Qwen Shim Generation Fix

**Priority**: Critical (Gemini agent integration fully broken without this)  
**Depends on**: WP01  
**Prompt**: [WP02-gemini-qwen-shim-generation-fix.md](tasks/WP02-gemini-qwen-shim-generation-fix.md)  
**Estimated size**: ~420 lines

**Goal**: Produce valid TOML shims for Gemini and correct argument placeholders for Gemini and Qwen, without regressing any other agent.

**Subtasks**:
- [x] T006 Add Gemini + Qwen to `AGENT_ARG_PLACEHOLDERS` (`{{args}}`) (WP02)
- [x] T007 Add `AGENT_SHIM_FORMATS` dispatch dict (`gemini → toml`) (WP02)
- [x] T008 Implement `generate_shim_content_toml()` for Gemini TOML schema (WP02)
- [x] T009 Update `generate_all_shims()` for per-agent format + extension dispatch (WP02)
- [x] T010 Regression tests: Gemini produces `.toml`, correct schema, `{{args}}` (WP02)
- [x] T011 Regression tests: Qwen stays `.md` but uses `{{args}}` (WP02)
- [x] T012 Regression tests: Claude/Codex output unchanged (WP02)

**Success criteria**: Running shim generation for a project with Gemini produces `.toml` files with `{{args}}`. Qwen produces `.md` files with `{{args}}`. All other agent output is byte-for-byte identical to pre-fix.

---

## WP03 — Review Lane Semantics Fix

**Priority**: High (review-claim writes illegal lane state into event log)  
**Depends on**: WP02  
**Prompt**: [WP03-review-lane-semantics-fix.md](tasks/WP03-review-lane-semantics-fix.md)  
**Estimated size**: ~410 lines

**Goal**: Review claims emit `for_review → in_review`. Approval/rejection from `in_review` works. Historical `in_progress` review-claim logs remain readable.

**Subtasks**:
- [ ] T013 Change review-claim emit to `Lane.IN_REVIEW`, remove `force=True` (WP03)
- [ ] T014 Update `is_review_claimed` to OR new + legacy shapes (WP03)
- [ ] T015 Update lane-entry guard to accept `{FOR_REVIEW, IN_REVIEW, legacy-in-progress-claim}` (WP03)
- [ ] T016 Regression test: new review claim emits `in_review` (WP03)
- [ ] T017 Regression test: approval from `in_review` succeeds (WP03)
- [ ] T018 Regression test: rejection from `in_review` succeeds (WP03)
- [ ] T019 Regression test: historical `in_progress + review_ref` logs parse without error (WP03)

**Success criteria**: Event log shows `for_review → in_review` for new claims. Approval and rejection from that state complete normally. Old-format logs are readable.

---

## WP04 — Intake Hardening Cluster

**Priority**: High (atomic write crash-safety is severe when hit; path escape is a correctness hazard)  
**Depends on**: WP03  
**Prompt**: [WP04-intake-hardening-cluster.md](tasks/WP04-intake-hardening-cluster.md)  
**Estimated size**: ~480 lines

**Goal**: Brief writes are atomic, oversized inputs are rejected before read, auto-scan stays within the repo root, and directory expansion does not follow symlinks out of the allowed tree.

**Subtasks**:
- [ ] T020 Atomic write (temp + replace) in `write_mission_brief()` (WP04)
- [ ] T021 Add `MAX_BRIEF_FILE_SIZE_BYTES` constant + size guard in `intake.py` (WP04)
- [ ] T022 Add repo-root containment check in `scan_for_plans()` (WP04)
- [ ] T023 Add symlink exclusion in `scan_for_plans()` directory expansion (WP04)
- [ ] T024 Regression tests: brief atomicity (partial write does not block re-ingest) (WP04)
- [ ] T025 Regression tests: oversized file rejected before read (WP04)
- [ ] T026 Regression tests: out-of-bounds path excluded, in-bounds accepted (WP04)
- [ ] T027 Regression tests: symlink excluded, regular file accepted (WP04)

**Success criteria**: A simulated mid-write crash leaves no blocking partial state. A file exceeding 5 MB is rejected with a human-readable error before any read. An out-of-bounds path never appears in auto-scan results. A symlink to an external file is not followed. Normal in-repo markdown intake is unchanged.
