# Init-Doctrine Flow — User Journey

**Status**: Implemented (WP07)
**Requirements**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-015, FR-020, NFR-001, C-002
**Implementation**: `src/specify_cli/cli/commands/init.py` — `_run_doctrine_stack_init()`

---

## Overview

When a user runs `spec-kitty init`, the doctrine stack setup step runs automatically
after the project skeleton is created. It configures the project charter —
the governance document that defines paradigms, directives, and tool settings for
all AI agents working in the project.

---

## Decision Tree

```
spec-kitty init
    │
    ▼
Skeleton created + "Project ready." displayed
    │
    ▼
_run_doctrine_stack_init(project_path, non_interactive)
    │
    ├─ [.kittify/charter/charter.md exists?] ──YES──▶ Skip (FR-004)
    │                                                            "Charter already exists — skipping"
    │
    ├─ [.kittify/.init-checkpoint.yaml exists?] ──YES──▶ Offer resume/restart (FR-020)
    │       │
    │       ├─ "resume"  ──▶  _run_inline_interview() [continue from saved state]
    │       └─ "restart" ──▶  Delete checkpoint, continue below
    │
    ├─ [--non-interactive / SPEC_KITTY_NON_INTERACTIVE?] ──YES──▶ _apply_doctrine_defaults() (NFR-001: ≤2s)
    │
    └─ [Interactive prompt] ──────────────────────────────────────────────────────────
            │
            ├─ "defaults"  ──▶  _apply_doctrine_defaults()
            ├─ "manual"    ──▶  _run_inline_interview()
            └─ "skip"      ──▶  Print hint to run `spec-kitty charter interview` later
```

---

## Path Descriptions

### Path 1: Accept Defaults (`defaults`)

**Trigger**: User selects "defaults" at the governance prompt, or `--non-interactive` flag is set.

**Steps**:
1. Load `src/charter/defaults.yaml`.
2. Call `default_interview(mission, profile)` for baseline answers.
3. Apply overrides from defaults.yaml (paradigms, directives, tools).
4. Call `build_charter_draft(mission, interview)`.
5. Write markdown to `.kittify/charter/charter.md`.
6. Print success message.

**Result**: `.kittify/charter/charter.md` exists with standard governance.

**NFR-001**: This path completes in ≤2 seconds (no user prompts, pure computation).

---

### Path 2: Configure Manually — Minimal Depth

**Trigger**: User selects "manual" → then "minimal" at the depth prompt.

**Steps**:
1. Print informational message about charter and governance.
2. Prompt for interview depth (`minimal` / `comprehensive`).
3. For each question in `MINIMAL_QUESTION_ORDER` (7 questions):
   a. Save checkpoint to `.kittify/.init-checkpoint.yaml` (atomic write).
   b. Ask question with default answer pre-filled.
4. Call `apply_answer_overrides(interview, answers)`.
5. Call `build_charter_draft()`.
6. Write `.kittify/charter/charter.md`.
7. Write `.kittify/charter/interview/answers.yaml` for future re-generation.
8. Delete checkpoint.

---

### Path 3: Configure Manually — Comprehensive Depth

Same as Path 2 but uses all 11 questions from `QUESTION_ORDER`.

---

### Path 4: Skip (Charter Already Exists)

**Trigger**: `.kittify/charter/charter.md` already exists (FR-004).

**Steps**: Print skip message. Return immediately.

**Use case**: Re-running `spec-kitty init --here` on an existing project.

---

### Path 5: Non-Interactive (Defaults Applied Automatically)

**Trigger**: `--non-interactive` / `--yes` flag or `SPEC_KITTY_NON_INTERACTIVE=1` (FR-005).

**Steps**: Same as Path 1, but no prompt is shown. Defaults applied silently.

**Use case**: CI/CD pipelines, automated setup scripts.

---

### Path 6: Resume / Restart After Interrupt (FR-020)

**Trigger**: `.kittify/.init-checkpoint.yaml` exists from a previous interrupted session.

```
Previous session interrupted (Ctrl+C during interview)
    │
    └─▶ Checkpoint written to .kittify/.init-checkpoint.yaml
            phase: interview
            depth: minimal|comprehensive
            answers_so_far: {question_id: answer, ...}

Re-run spec-kitty init
    │
    ├─ "resume"  ──▶ _run_inline_interview() (re-runs full interview with defaults
    │                 from prior answers as starting point)
    └─ "restart" ──▶ checkpoint deleted, fall through to fresh path selection
```

**Checkpoint format** (`.kittify/.init-checkpoint.yaml`):
```yaml
phase: interview
depth: minimal   # or comprehensive
answers_so_far:
  project_intent: "..."
  languages_frameworks: "..."
  ...
```

**Location**: `.kittify/.init-checkpoint.yaml` (project-local, not committed).

**Atomicity**: Written via `kernel.atomic.atomic_write` — partial writes never corrupt the file.

**Cleanup**: Checkpoint deleted on successful interview completion or on "restart".

---

## C-002: Independence of Existing Charter Commands

`spec-kitty charter interview` and `spec-kitty charter generate` continue
to work independently. The init flow only **orchestrates** the existing machinery:

- `_run_doctrine_stack_init()` calls `_apply_doctrine_defaults()` or `_run_inline_interview()`.
- These call `charter.interview.default_interview()`, `apply_answer_overrides()`,
  `charter.generator.build_charter_draft()`, and `write_charter()`.
- No code was removed from the charter commands.
- The standalone `spec-kitty charter interview` CLI command is unaffected.

---

## Defaults File

**Location**: `src/charter/defaults.yaml`

**Accessed via**: `importlib.resources.files("charter") / "defaults.yaml"`

**Purpose**: Defines the pre-selected paradigms, directives, and tools applied
when a user accepts defaults or uses `--non-interactive` mode.

**Format** (must match `charter.interview.apply_answer_overrides` input):

```yaml
mission: software-dev
profile: minimal
selected_paradigms:
  - test-first
selected_directives:
  - DIRECTIVE_001
  - DIRECTIVE_010
  ...
available_tools:
  - git
  - pytest
  ...
```

---

## Files Modified / Created

| File | Change |
|------|--------|
| `src/specify_cli/cli/commands/init.py` | Added `_load_doctrine_defaults()`, `_apply_doctrine_defaults()`, `_run_inline_interview()`, `_run_doctrine_stack_init()`; wired `_run_doctrine_stack_init()` call after `_maybe_generate_structure_templates()` |
| `src/charter/defaults.yaml` | Predefined governance selections for accept-defaults path |
| `tests/specify_cli/cli/commands/test_init_doctrine.py` | New: 7 ATDD acceptance tests (US-1 scenarios 1-3, US-2 scenarios 1-4) |
| `architecture/2.x/user_journey/init-doctrine-flow.md` | New: this document |
