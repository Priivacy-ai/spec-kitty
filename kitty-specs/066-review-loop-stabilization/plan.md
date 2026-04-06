# Implementation Plan: Review Loop Stabilization

**Branch**: `main` | **Date**: 2026-04-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/066-review-loop-stabilization/spec.md`
**Mission**: 066-review-loop-stabilization | **Priority**: P1 stabilization

## Summary

Make the implement/review loop operationally reliable by replacing ephemeral feedback storage with committed artifacts, generating focused fix-mode prompts from structured review data, classifying dirty-state to unblock external reviewer handoff, surfacing baseline test context in review prompts, serializing concurrent reviews, and adding structured arbiter decision rationale. Six work packages across two execution tracks: WP01 -> WP02 (strict chain) and WP03-WP06 (independent, parallelizable).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI), rich (console output), ruamel.yaml (YAML frontmatter parsing), pathlib (filesystem), subprocess (git operations)
**Storage**: Filesystem only — YAML-frontmatter markdown files, JSON files, JSONL event log
**Testing**: pytest with 90%+ coverage for new code, mypy --strict, integration tests for CLI commands
**Target Platform**: Cross-platform (Linux, macOS, Windows 10+)
**Project Type**: Single Python package (`src/specify_cli/`)
**Performance Goals**: CLI operations < 2 seconds; dirty-state classification < 1 second for 100 paths; artifact write + commit < 5 seconds
**Constraints**: No external databases, no network dependencies for core review loop operations
**Scale/Scope**: Review-cycle artifacts are small (< 10 KB each); baseline test results are structured summaries (< 10 KB)

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Charter Requirement | Status | Notes |
|---------------------|--------|-------|
| Python 3.11+ | PASS | All new code targets Python 3.11+ |
| typer for CLI | PASS | Any new CLI surfaces (arbiter commands) use typer |
| rich for console output | PASS | Review lock messages, arbiter checklist output use rich |
| ruamel.yaml for YAML | PASS | Review-cycle artifact frontmatter uses ruamel.yaml |
| pytest 90%+ coverage | PASS | Spec verification expectations include targeted tests for each WP |
| mypy --strict | PASS | All new dataclasses and functions will be fully typed |
| Integration tests for CLI | PASS | End-to-end tests for move-task with review feedback, implement with fix-mode |
| CLI ops < 2 seconds | PASS | All new operations are filesystem I/O, well within budget |
| Cross-platform | PASS | All paths use pathlib; no OS-specific operations |
| "Mission" terminology | PASS | No new user-facing CLI flags or messages use "feature" |
| No `--feature` in new CLI flags | PASS | No new CLI flags in this mission |

**Post-Phase 1 re-check**: No new charter gaps introduced. Data model uses frozen dataclasses with `to_dict()`/`from_dict()` (existing pattern). No new external dependencies added.

## Project Structure

### Documentation (this mission)

```
kitty-specs/066-review-loop-stabilization/
├── spec.md              # Mission specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0 output (complete)
├── data-model.md        # Phase 1 output (complete)
├── quickstart.md        # Phase 1 output
├── checklists/
│   └── requirements.md  # Spec quality checklist (complete)
└── tasks/               # Phase 2 output (/spec-kitty.tasks — NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/specify_cli/
├── cli/commands/agent/
│   ├── tasks.py                    # WP01: _persist_review_feedback() rewrite
│   │                               # WP03: _validate_ready_for_review() dirty-state classification
│   └── workflow.py                 # WP01: _resolve_review_feedback_pointer() dual resolution
│                                   # WP02: fix-mode prompt generation in implement path
│                                   # WP04: baseline test context in review prompt
├── review/                         # NEW MODULE — review artifact domain logic
│   ├── __init__.py                 # Public API exports
│   ├── artifacts.py                # ReviewCycleArtifact, AffectedFile — read/write/versioning
│   ├── fix_prompt.py               # Fix-mode prompt generator (reads artifacts, produces prompt)
│   ├── baseline.py                 # BaselineTestResult — capture, cache, diff
│   ├── lock.py                     # ReviewLock — concurrent review serialization
│   ├── arbiter.py                  # ArbiterDecision, ArbiterChecklist, ArbiterCategory
│   └── dirty_classifier.py         # Dirty-state classification (blocking vs benign)
├── status/
│   └── models.py                   # No changes — existing StatusEvent.review_ref field is sufficient
└── policy/
    └── config.py                   # WP05: read concurrent_isolation config (opt-in)

tests/
├── review/                         # NEW — mirrors src/specify_cli/review/
│   ├── test_artifacts.py           # ReviewCycleArtifact CRUD, versioning, frontmatter
│   ├── test_fix_prompt.py          # Fix-mode prompt generation from artifacts
│   ├── test_baseline.py            # Baseline test capture, cache lookup, diff
│   ├── test_lock.py                # ReviewLock create/release/stale detection
│   ├── test_arbiter.py             # ArbiterDecision serialization, category validation
│   └── test_dirty_classifier.py    # Dirty-state classification rules
├── agent/
│   ├── test_review_feedback_*.py   # Updated: test new artifact persistence path
│   └── test_review_validation_*.py # Updated: test dirty-state classification
└── integration/
    ├── test_rejection_cycle.py     # End-to-end: reject -> persist -> fix-prompt -> re-implement
    └── test_review_handoff.py      # End-to-end: external reviewer handoff with benign dirtiness
```

**Structure Decision**: New `src/specify_cli/review/` module isolates review domain logic from the CLI command layer. This avoids further bloating `tasks.py` (already ~1200 lines) and `workflow.py` (already ~1300 lines). The CLI commands in tasks.py and workflow.py call into the review module for domain logic.

## Per-WP Implementation Guidance

### WP01: Persisted Review Artifact Model

**Issues**: #432, storage side of #433
**Depends on**: Nothing
**Primary files**:
- NEW: `src/specify_cli/review/artifacts.py` — ReviewCycleArtifact dataclass, read/write operations
- MODIFY: `src/specify_cli/cli/commands/agent/tasks.py` — replace `_persist_review_feedback()` (lines 245-265)
- MODIFY: `src/specify_cli/cli/commands/agent/workflow.py` — update `_resolve_review_feedback_pointer()` (lines 87-100) for dual resolution

**Implementation approach**:
1. Create `ReviewCycleArtifact` and `AffectedFile` dataclasses in `review/artifacts.py`
2. Implement `write()` — renders YAML frontmatter + markdown body via ruamel.yaml, writes to `kitty-specs/<mission>/tasks/<WP-slug>/review-cycle-{N}.md`
3. Implement `from_file()` — parses frontmatter + body from existing artifact
4. Implement `latest()` — finds highest-numbered review-cycle file in directory
5. Rewrite `_persist_review_feedback()` in tasks.py to create a ReviewCycleArtifact instead of copying to `.git/`
6. Update pointer format: new artifacts use `review-cycle://<mission>/<wp-slug>/review-cycle-{N}.md`
7. Update `_resolve_review_feedback_pointer()` in workflow.py to resolve both `feedback://` (legacy) and `review-cycle://` (new)
8. Git-commit the artifact after writing (using existing safe-commit pattern)

**Tests**: Artifact CRUD, frontmatter round-trip, cycle number derivation, legacy pointer resolution, new pointer resolution.

### WP02: Focused Rejection Recovery

**Issues**: #430, integration side of #433
**Depends on**: WP01
**Primary files**:
- NEW: `src/specify_cli/review/fix_prompt.py` — fix-mode prompt generator
- MODIFY: `src/specify_cli/cli/commands/agent/workflow.py` — implement path switches between full-prompt and fix-prompt mode

**Implementation approach**:
1. Create `generate_fix_prompt()` in `review/fix_prompt.py`:
   - Input: latest ReviewCycleArtifact, worktree path, WP prompt file path
   - Reads affected files from disk using artifact's `affected_files` list
   - Renders a focused prompt: review findings summary, affected code snippets, reproduction command, commit instructions
   - Output: string (the prompt text)
2. In `workflow.py` implement path (the code that runs on `agent action implement`):
   - Detect if WP has prior review-cycle artifacts (check sub-artifact directory)
   - If yes: call `generate_fix_prompt()` instead of rendering full WP prompt
   - If no: render full WP prompt (existing behavior)
3. Fix-prompt content includes:
   - Verbatim review feedback (from artifact body)
   - Affected file paths with line ranges (from frontmatter)
   - Current file contents read from disk (the code to fix)
   - Reproduction command (from frontmatter)
   - Commit and status-transition instructions

**Tests**: Fix-prompt generation from mock artifact, prompt size vs original WP prompt size, mode-switching detection, end-to-end rejection -> fix-prompt flow.

### WP03: External Reviewer Handoff

**Issues**: #439
**Depends on**: Nothing (parallel-safe with WP01 — different sections of tasks.py)
**Primary files**:
- NEW: `src/specify_cli/review/dirty_classifier.py` — dirty-state classification
- MODIFY: `src/specify_cli/cli/commands/agent/tasks.py` — update `_validate_ready_for_review()` (lines 468-750)
- MODIFY: `src/specify_cli/cli/commands/agent/workflow.py` — surface writable feedback path in review prompt

**Implementation approach**:
1. Create `classify_dirty_paths()` in `review/dirty_classifier.py`:
   - Input: list of dirty paths from `git status --porcelain`, current WP ID, mission slug
   - Output: `(blocking: list[str], benign: list[str])`
   - Classification rules:
     - **Blocking**: files in the worktree's source directories owned by this WP, the WP's own task file
     - **Benign**: `status.events.jsonl`, `status.json`, other WPs' task files (`tasks/WP*.md` where WP != current), generated metadata files
   - Path ownership: a file is "owned by this WP" if it's in the worktree's source tree (implementation files), or is this WP's specific task prompt file
2. Update `_validate_ready_for_review()` in tasks.py:
   - Replace current "any dirty file blocks" logic with `classify_dirty_paths()` call
   - Only fail if `blocking` list is non-empty
   - Show both blocking and benign lists in output (blocking as errors, benign as info)
   - Preserve `--force` escape hatch (skips all checks, unchanged)
3. Update review prompt in workflow.py:
   - Add writable in-repo feedback path to review output: `kitty-specs/<mission>/tasks/<WP-slug>/review-cycle-{N}.md`
   - Replace temp-file feedback path with this committed path

**Tests**: Classification of various dirty-path patterns, validation with only benign dirtiness (should pass), validation with blocking dirtiness (should fail), review prompt includes writable path.

### WP04: Baseline Test Capture

**Issues**: #444
**Depends on**: Nothing
**Primary files**:
- NEW: `src/specify_cli/review/baseline.py` — BaselineTestResult capture and diff
- MODIFY: `src/specify_cli/cli/commands/agent/workflow.py` — inject baseline context into review prompt

**Implementation approach**:
1. Create `BaselineTestResult` and `TestFailure` dataclasses in `review/baseline.py`
2. Implement `capture_baseline()`:
   - Checks out base branch in a temporary worktree (or reads from current checkout if on base)
   - Runs test suite, parses output for structured results
   - Saves to `kitty-specs/<mission>/tasks/<WP-slug>/baseline-tests.json`
   - Commits the artifact
3. Implement `load_baseline()` — reads cached JSON artifact
4. Implement `diff_baseline()`:
   - Input: BaselineTestResult (cached), current test run results
   - Output: `(pre_existing: list[TestFailure], new_failures: list[TestFailure], fixed: list[str])`
5. Hook `capture_baseline()` into WP claim path (when agent claims a WP, run baseline capture if not already cached)
6. Hook `diff_baseline()` into review prompt generation:
   - Add a "Baseline Context" section to review prompt showing pre-existing failures vs new failures
   - Clear labeling: "These N failures existed before this WP" / "These M failures are new"

**Tests**: Baseline capture and JSON round-trip, diff calculation, review prompt includes baseline section, cached lookup skips re-capture.

### WP05: Concurrent Review Isolation

**Issues**: #440
**Depends on**: Nothing
**Primary files**:
- NEW: `src/specify_cli/review/lock.py` — ReviewLock serialization
- MODIFY: `src/specify_cli/cli/commands/agent/workflow.py` — acquire/release lock around review
- MODIFY: `src/specify_cli/policy/config.py` — read `review.concurrent_isolation` config (opt-in)

**Implementation approach**:
1. **Primary path (80% effort): serialization**
   - Create `ReviewLock` dataclass in `review/lock.py`
   - `acquire()`: write lock file to `.spec-kitty/review-lock.json` in worktree. If lock exists and PID is alive, raise with actionable message. If PID is dead, treat as stale and overwrite.
   - `release()`: delete lock file
   - `is_stale()`: check `os.kill(pid, 0)` — cross-platform via `psutil` or try/except (psutil is already a dependency per charter)
   - Hook into `agent action review`: acquire lock before review starts, release after move-task completes
   - Stale lock cleanup: on `agent action review` start, if lock PID is dead, log warning and proceed
2. **Optional path (20% effort): env-var isolation**
   - Read `review.concurrent_isolation` from `.kittify/config.yaml` (new config section)
   - If `strategy: "env_var"`: set the declared env var per agent using the template (e.g., `test_db_{agent}_{wp_id}`)
   - If no config or `strategy: "serialized"` (default): use ReviewLock
   - This is opt-in, not auto-detected — projects configure it explicitly

**Tests**: Lock acquire/release, stale lock detection, concurrent acquire blocks, env-var isolation config parsing, env-var scoping.

### WP06: Arbiter Ergonomics

**Issues**: #441
**Depends on**: Nothing
**Primary files**:
- NEW: `src/specify_cli/review/arbiter.py` — ArbiterDecision, ArbiterChecklist, ArbiterCategory
- MODIFY: `src/specify_cli/cli/commands/agent/tasks.py` — arbiter override path in move-task
- MODIFY: review-cycle artifact (add `arbiter_override` section to frontmatter)

**Implementation approach**:
1. Create `ArbiterCategory` StrEnum, `ArbiterChecklist`, `ArbiterDecision` dataclasses in `review/arbiter.py`
2. Implement `prompt_arbiter_checklist()`:
   - Presents the 5-question checklist (is pre-existing? correct context? in scope? environmental? should be follow-on issue?)
   - Returns populated `ArbiterChecklist`
   - Selects `ArbiterCategory` from checklist responses
   - If category is `CUSTOM`, requires mandatory explanation
3. Hook into move-task arbiter override path:
   - When `--force` is used on a `for_review` -> `planned` transition, run the arbiter checklist
   - Persist `ArbiterDecision` in the review-cycle artifact's frontmatter (add `arbiter_override` section)
   - Set `review_ref` to `"arbiter-override://{category}"` instead of generic `"force-override"`
4. Make arbiter decisions visible:
   - `agent tasks status` shows arbiter override history when displaying review cycles
   - The fix-prompt generator in WP02 can reference arbiter decisions for context

**Tests**: ArbiterCategory validation, checklist -> category mapping, decision serialization in artifact frontmatter, move-task with arbiter override persists structured rationale.

## Execution Plan

### Track A: Review artifact pipeline (sequential)

```
WP01 (artifact model) ──► WP02 (fix-mode prompts + wiring)
```

WP01 must complete before WP02 starts. WP02 includes all integration wiring (absorbed from old WP03).

### Track B: Independent improvements (parallel)

```
WP03 (dirty-state classification)     ─┐
WP04 (baseline test capture)          ─┼── all independent, can run in parallel
WP05 (concurrent review serialization)─┤
WP06 (arbiter ergonomics)             ─┘
```

### Merge Coordination

WP01 and WP03 both modify `tasks.py` but in non-overlapping sections:
- WP01: `_persist_review_feedback()` (lines 245-265) and move-task pointer handling (lines 985-990)
- WP03: `_validate_ready_for_review()` (lines 468-750)

Separated by ~200 lines with no shared helper calls — low merge conflict risk.

WP02 and WP04 both modify `workflow.py` (implement path and review prompt respectively). WP02 depends on WP01, which should land first. WP04 modifies the review prompt template section (~lines 1190-1310), while WP02 modifies the implement action path (~lines 526-662). Different sections, but implementers should coordinate on the workflow.py structure.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Baseline test capture is slow for large projects | Medium | Low | Capture at claim time (one-time cost), cache results. NFR-004 bounds this. |
| ReviewLock stale detection fails on some platforms | Low | Medium | Use `os.kill(pid, 0)` with fallback to PID file age check. psutil available if needed. |
| Legacy feedback:// pointers have edge cases | Low | Low | Comprehensive test coverage for both pointer formats. Legacy path is read-only. |
| WP01/WP03 merge conflicts in tasks.py | Low | Low | Non-overlapping sections. Implementers can verify with `git diff --check`. |
| Arbiter checklist is too rigid for edge cases | Low | Medium | `CUSTOM` category with mandatory explanation is the escape hatch. Categories are extensible via StrEnum. |
