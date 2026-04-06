# Tasks: 066 Review Loop Stabilization

**Mission**: 066-review-loop-stabilization
**Target Branch**: main
**Created**: 2026-04-06

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Create review module scaffold (__init__.py, artifacts.py with dataclasses) | WP01 | | [D] | [D] |
| T002 | Implement ReviewCycleArtifact write() — YAML frontmatter + markdown body | WP01 | | [D] |
| T003 | Implement from_file() and latest() — parse artifacts, find highest cycle | WP01 | | [D] |
| T004 | Rewrite _persist_review_feedback() in tasks.py — create ReviewCycleArtifact | WP01 | | [D] |
| T005 | Update _resolve_review_feedback_pointer() — dual resolution (legacy + new) | WP01 | | [D] |
| T006 | Write tests for artifact CRUD, frontmatter round-trip, pointer resolution | WP01 | | [D] |
| T007 | Create fix_prompt.py with generate_fix_prompt() | WP02 | |
| T008 | Implement fix-prompt template rendering | WP02 | |
| T009 | Add fix-mode detection in workflow.py implement path | WP02 | |
| T010 | Implement mode switching — fix-prompt vs full-prompt | WP02 | |
| T011 | Write tests for fix-prompt generation, sizing, end-to-end flow | WP02 | |
| T012 | Create dirty_classifier.py with classify_dirty_paths() | WP03 | [D] |
| T013 | Implement classification rules — blocking vs benign path patterns | WP03 | [D] |
| T014 | Update _validate_ready_for_review() — use classifier, only block on blocking | WP03 | [D] |
| T015 | Update review prompt — surface writable in-repo feedback path | WP03 | [D] |
| T016 | Write tests for classification, validation, review prompt path | WP03 | [D] |
| T017 | Create baseline.py with BaselineTestResult and TestFailure dataclasses | WP04 | [D] |
| T018 | Implement capture_baseline() — pytest --junitxml + JUnit XML parsing | WP04 | [D] |
| T019 | Implement load_baseline() and diff_baseline() — cached lookup + diff | WP04 | [D] |
| T020 | Hook capture_baseline() into implement path (before agent starts coding) | WP04 | [D] |
| T021 | Hook diff_baseline() into review prompt — Baseline Context section | WP04 | [D] |
| T022 | Add review.test_command config support for non-pytest runners | WP04 | [D] |
| T023 | Write tests for capture, JSON round-trip, diff, config, review prompt | WP04 | [D] |
| T024 | Create lock.py with ReviewLock dataclass — acquire, release, is_stale | WP05 | [D] |
| T025 | Implement stale lock detection — cross-platform PID check | WP05 | [D] |
| T026 | Hook lock acquire/release into agent action review | WP05 | [D] |
| T027 | Add .spec-kitty/ to .gitignore | WP05 | [D] |
| T028 | Implement opt-in env-var isolation config from .kittify/config.yaml | WP05 | [D] |
| T029 | Write tests for lock lifecycle, stale detection, concurrent block, config | WP05 | [D] |
| T030 | Create arbiter.py with ArbiterCategory, ArbiterChecklist, ArbiterDecision | WP06 | [D] |
| T031 | Implement prompt_arbiter_checklist() — 5-question checklist + category | WP06 | [D] |
| T032 | Implement override detection in move-task — forward --force after rejection | WP06 | [D] |
| T033 | Persist ArbiterDecision in review-cycle artifact frontmatter | WP06 | [D] |
| T034 | Make arbiter decisions visible in agent tasks status | WP06 | [D] |
| T035 | Write tests for checklist, detection, persistence, visibility | WP06 | [D] |

## Work Packages

### WP01: Persisted Review Artifact Model

**Goal**: Define review-cycle artifact schema, move feedback from `.git/` to committed `kitty-specs/` artifacts, add backward-compatible pointer resolution.
**Priority**: P0 — foundation for WP02
**Dependencies**: None
**Issues**: #432, storage side of #433
**Estimated prompt size**: ~400 lines

- [ ] T001 Create review module scaffold (__init__.py, artifacts.py with dataclasses) (WP01)
- [ ] T002 Implement ReviewCycleArtifact write() — YAML frontmatter + markdown body (WP01)
- [ ] T003 Implement from_file() and latest() — parse artifacts, find highest cycle (WP01)
- [ ] T004 Rewrite _persist_review_feedback() in tasks.py — create ReviewCycleArtifact (WP01)
- [ ] T005 Update _resolve_review_feedback_pointer() — dual resolution (legacy + new) (WP01)
- [ ] T006 Write tests for artifact CRUD, frontmatter round-trip, pointer resolution (WP01)

**Implementation sketch**: Create new `src/specify_cli/review/` module. Define ReviewCycleArtifact and AffectedFile frozen dataclasses following existing StatusEvent patterns. Replace `_persist_review_feedback()` to write review-cycle artifacts to `kitty-specs/<mission>/tasks/<WP-slug>/`. Update pointer resolver for dual-format resolution.

**Risks**: Legacy `feedback://` pointers must continue resolving. Test with pre-066 event log entries.

---

### WP02: Focused Rejection Recovery

**Goal**: Generate fix-mode prompts from persisted review-cycle artifacts instead of replaying full WP prompts.
**Priority**: P0 — core value proposition
**Dependencies**: WP01
**Issues**: #430, integration side of #433
**Estimated prompt size**: ~380 lines

- [ ] T007 Create fix_prompt.py with generate_fix_prompt() (WP02)
- [ ] T008 Implement fix-prompt template rendering (WP02)
- [ ] T009 Add fix-mode detection in workflow.py implement path (WP02)
- [ ] T010 Implement mode switching — fix-prompt vs full-prompt (WP02)
- [ ] T011 Write tests for fix-prompt generation, sizing, end-to-end flow (WP02)

**Implementation sketch**: Create `generate_fix_prompt()` that reads latest ReviewCycleArtifact, extracts affected file paths/line ranges, reads current code from disk, and produces a focused prompt. Modify `agent action implement` in workflow.py to detect prior rejection cycles and switch modes.

**Risks**: Fix-prompt must be self-contained — agent should not need to read the original WP prompt. Verify prompt sizing meets NFR-001 (<25% of original for single-file findings).

---

### WP03: External Reviewer Handoff

**Goal**: Implement dirty-state classification and writable in-repo feedback path for external reviewers.
**Priority**: P1
**Dependencies**: None
**Issues**: #439
**Estimated prompt size**: ~370 lines

- [ ] T012 Create dirty_classifier.py with classify_dirty_paths() (WP03)
- [ ] T013 Implement classification rules — blocking vs benign path patterns (WP03)
- [ ] T014 Update _validate_ready_for_review() — use classifier, only block on blocking (WP03)
- [ ] T015 Update review prompt — surface writable in-repo feedback path (WP03)
- [ ] T016 Write tests for classification, validation, review prompt path (WP03)

**Implementation sketch**: Create `classify_dirty_paths()` that partitions `git status --porcelain` output. Blocking: WP-owned source files, WP's task file. Benign: status.events.jsonl, status.json, other WPs' task files, metadata. Update `_validate_ready_for_review()` to call classifier. Update review prompt to show in-repo writable path.

**WP01 interaction note**: WP03 changes where the review prompt tells the reviewer to write. The `--review-feedback-file` flag still accepts any path. If WP01 hasn't landed, move-task persists to `.git/` (old behavior). After WP01 lands, move-task persists to the same in-repo location. Convergence is natural.

**Risks**: Classification rules must not accidentally block on WP-owned files that were legitimately committed. Test with real multi-WP dirty state.

---

### WP04: Baseline Test Capture

**Goal**: Capture baseline test results at implement time, surface delta in review prompts.
**Priority**: P1
**Dependencies**: None
**Issues**: #444
**Estimated prompt size**: ~450 lines

- [ ] T017 Create baseline.py with BaselineTestResult and TestFailure dataclasses (WP04)
- [ ] T018 Implement capture_baseline() — pytest --junitxml + JUnit XML parsing (WP04)
- [ ] T019 Implement load_baseline() and diff_baseline() — cached lookup + diff (WP04)
- [ ] T020 Hook capture_baseline() into implement path (before agent starts coding) (WP04)
- [ ] T021 Hook diff_baseline() into review prompt — Baseline Context section (WP04)
- [ ] T022 Add review.test_command config support for non-pytest runners (WP04)
- [ ] T023 Write tests for capture, JSON round-trip, diff, config, review prompt (WP04)

**Implementation sketch**: Run `pytest --junitxml=<tmpfile>` on the base branch at implement time. Parse JUnit XML via `xml.etree.ElementTree`. Save structured results to `baseline-tests.json`. At review time, diff cached baseline against current test run. Add "Baseline Context" section to review prompt. Non-pytest projects configure `review.test_command` in `.kittify/config.yaml`.

**Risks**: Test suite may fail to run at implement time (missing deps, broken env). Handle gracefully — create baseline artifact with sentinel values and warn, don't block implementation.

---

### WP05: Concurrent Review Isolation

**Goal**: Serialize concurrent reviews by default; opt-in env-var isolation for projects that configure it.
**Priority**: P2
**Dependencies**: None
**Issues**: #440
**Estimated prompt size**: ~380 lines

- [x] T024 Create lock.py with ReviewLock dataclass — acquire, release, is_stale (WP05)
- [x] T025 Implement stale lock detection — cross-platform PID check (WP05)
- [x] T026 Hook lock acquire/release into agent action review (WP05)
- [x] T027 Add .spec-kitty/ to .gitignore (WP05)
- [x] T028 Implement opt-in env-var isolation config from .kittify/config.yaml (WP05)
- [x] T029 Write tests for lock lifecycle, stale detection, concurrent block, config (WP05)

**Implementation sketch**: Primary (80% effort): ReviewLock serialization via `.spec-kitty/review-lock.json`. Acquire on review start, release on move-task. Stale detection via `os.kill(pid, 0)`. Optional (20%): read `review.concurrent_isolation` from config for env-var scoping. Add `.spec-kitty/` to `.gitignore`.

**Risks**: PID-based stale detection may behave differently across platforms. Use try/except around `os.kill` with fallback to file age check.

---

### WP06: Arbiter Ergonomics

**Goal**: Add structured arbiter checklist and rationale model for false-positive review rejections.
**Priority**: P2
**Dependencies**: None
**Issues**: #441
**Estimated prompt size**: ~400 lines

- [x] T030 Create arbiter.py with ArbiterCategory, ArbiterChecklist, ArbiterDecision (WP06)
- [x] T031 Implement prompt_arbiter_checklist() — 5-question checklist + category (WP06)
- [x] T032 Implement override detection in move-task — forward --force after rejection (WP06)
- [x] T033 Persist ArbiterDecision in review-cycle artifact frontmatter (WP06)
- [x] T034 Make arbiter decisions visible in agent tasks status (WP06)
- [x] T035 Write tests for checklist, detection, persistence, visibility (WP06)

**Implementation sketch**: Create ArbiterCategory StrEnum (5 categories), ArbiterChecklist (5 boolean questions), ArbiterDecision. Detect override: when `--force` moves WP forward from `planned` and latest event was `for_review` → `planned` with `review_ref`. Run checklist, persist decision in review-cycle artifact frontmatter. `review_ref` points to same `review-cycle://` artifact — no new pointer scheme.

**Risks**: Override detection must not trigger on normal claim/re-claim workflows. Only trigger when a rejection event exists in the log.

## Execution Tracks

### Track A: Review artifact pipeline (sequential)

```
WP01 (artifact model) ──> WP02 (fix-mode prompts + wiring)
```

### Track B: Independent improvements (parallel)

```
WP03 (dirty-state classification)      ─┐
WP04 (baseline test capture)           ─┼── all independent
WP05 (concurrent review serialization) ─┤
WP06 (arbiter ergonomics)              ─┘
```

Maximum parallelization: 5 WPs can execute simultaneously (WP02 after WP01 completes, WP03-WP06 in parallel from the start).
